"""
Agent Wrapper - Wraps an LLM with persona, memory, and skills.
This is the main abstraction that gives persistence and identity to an agent.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol, Union
from datetime import datetime, timezone
import asyncio
import time

from gathering.agents.persona import AgentPersona
from gathering.agents.project_context import ProjectContext
from gathering.agents.session import AgentSession, InjectedContext
from gathering.agents.memory import MemoryService, build_agent_context
from gathering.events import event_bus, Event, EventType
from gathering.telemetry.decorators import trace_async_method
from gathering.telemetry.metrics import agent_metrics
from gathering.telemetry.config import get_tracer


class LLMProvider(Protocol):
    """Protocol for LLM providers (Anthropic, OpenAI, etc.).

    Note: Matches ILLMProvider interface - complete() is synchronous
    and returns Dict[str, Any] with 'content' key.
    """

    def complete(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Send messages to LLM and get response dict."""
        ...


class Skill(Protocol):
    """Protocol for agent skills."""

    @property
    def name(self) -> str:
        """Skill name."""
        ...

    @property
    def tools(self) -> List[Dict[str, Any]]:
        """Tool definitions for the LLM."""
        ...

    async def execute(self, tool_name: str, **params) -> Any:
        """Execute a tool."""
        ...


@dataclass
class AgentConfig:
    """Configuration for an agent."""

    # LLM settings
    provider: str = "anthropic"  # "anthropic", "openai", "deepseek"
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    temperature: float = 0.7

    # Behavior settings
    auto_remember: bool = True  # Automatically remember important exchanges
    remember_threshold: float = 0.7  # Importance threshold for auto-remember
    max_history: int = 20  # Max messages to keep in session

    # Tool settings
    allow_tools: bool = True
    tool_timeout: int = 30  # Seconds

    # Safety settings
    max_iterations: int = 10  # Max tool use iterations per request


@dataclass
class AgentResponse:
    """Response from an agent."""

    content: str
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    tokens_used: int = 0
    model: str = ""
    duration_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentWrapper:
    """
    Wraps an LLM with persistent identity and context.

    The AgentWrapper provides:
    - Persistent persona that survives sessions
    - Automatic context injection from memory
    - Session tracking for resume capability
    - Skill/tool integration
    - Project context awareness

    Usage:
        # Create the wrapper
        agent = AgentWrapper(
            agent_id=1,
            persona=ARCHITECT_PERSONA,
            llm=anthropic_provider,
            memory=memory_service,
        )

        # Add skills
        agent.add_skill(git_skill)
        agent.add_skill(test_skill)

        # Set project context
        agent.set_project(my_project)

        # Chat with the agent
        response = await agent.chat("Implémente la feature X")
    """

    def __init__(
        self,
        agent_id: int,
        persona: AgentPersona,
        llm: LLMProvider,
        memory: Optional[MemoryService] = None,
        config: Optional[AgentConfig] = None,
    ):
        """
        Initialize the agent wrapper.

        Args:
            agent_id: Unique identifier for this agent
            persona: The agent's persistent identity
            llm: LLM provider for completions
            memory: Memory service for context (creates one if not provided)
            config: Agent configuration
        """
        self.agent_id = agent_id
        self.persona = persona
        self.llm = llm
        self.memory = memory or MemoryService()
        self.config = config or AgentConfig()

        # Register persona with memory service
        self.memory.set_persona(agent_id, persona)

        # Skills registry
        self._skills: Dict[str, Skill] = {}
        self._tool_map: Dict[str, str] = {}  # tool_name -> skill_name

        # Current project
        self._project: Optional[ProjectContext] = None
        self._project_id: Optional[int] = None

        # Callbacks
        self._on_tool_call: Optional[Callable] = None
        self._on_response: Optional[Callable] = None

        # State
        self._is_processing = False

    @property
    def name(self) -> str:
        """Agent's name from persona."""
        return self.persona.name

    @property
    def role(self) -> str:
        """Agent's role from persona."""
        return self.persona.role

    @property
    def session(self) -> AgentSession:
        """Current session for this agent."""
        return self.memory.get_or_create_session(self.agent_id, self._project_id)

    def add_skill(self, skill: Skill) -> None:
        """
        Add a skill to the agent.

        Args:
            skill: Skill to add
        """
        self._skills[skill.name] = skill

        # Map tool names to skill
        for tool in skill.tools:
            tool_name = tool.get("name") or tool.get("function", {}).get("name")
            if tool_name:
                self._tool_map[tool_name] = skill.name

    def remove_skill(self, skill_name: str) -> None:
        """Remove a skill from the agent."""
        if skill_name in self._skills:
            skill = self._skills[skill_name]
            # Remove tool mappings
            for tool in skill.tools:
                tool_name = tool.get("name") or tool.get("function", {}).get("name")
                if tool_name and tool_name in self._tool_map:
                    del self._tool_map[tool_name]
            del self._skills[skill_name]

    def set_project(self, project: ProjectContext, project_id: Optional[int] = None) -> None:
        """
        Set the current project context.

        Args:
            project: Project context
            project_id: Optional ID for caching
        """
        self._project = project
        self._project_id = project_id or project.id

        if self._project_id:
            self.memory.set_project(self._project_id, project)

    def load_project_context(self, project_path: str, project_id: Optional[int] = None) -> ProjectContext:
        """
        Load project context from a filesystem path.

        Args:
            project_path: Absolute path to the project directory
            project_id: Optional project ID for linking to database

        Returns:
            ProjectContext instance

        Example:
            agent.load_project_context("/home/user/my-app", project_id=5)
            response = await agent.chat("Analyze the codebase")
        """
        project = ProjectContext.from_path(project_path)
        project.id = project_id
        self.set_project(project, project_id)
        return project

    def get_project(self) -> Optional[ProjectContext]:
        """Get current project context."""
        return self._project

    def get_project_id(self) -> Optional[int]:
        """Get current project ID."""
        return self._project_id

    def on_tool_call(self, callback: Callable) -> None:
        """Register callback for tool calls."""
        self._on_tool_call = callback

    def on_response(self, callback: Callable) -> None:
        """Register callback for responses."""
        self._on_response = callback

    def _get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all tool definitions from all skills."""
        tools = []
        for skill in self._skills.values():
            tools.extend(skill.tools)
        return tools

    async def _execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Execute a tool from a skill."""
        skill_name = self._tool_map.get(tool_name)
        if not skill_name:
            return {"error": f"Unknown tool: {tool_name}"}

        skill = self._skills.get(skill_name)
        if not skill:
            return {"error": f"Skill not found: {skill_name}"}

        # Inject project context for path-based skills
        if self._project and skill_name in ("filesystem", "git", "code"):
            # If path is relative, resolve it against project root
            if "path" in params:
                from pathlib import Path
                path = Path(params["path"])
                if not path.is_absolute():
                    # Resolve relative path against project root
                    project_root = Path(self._project.path)
                    params["path"] = str(project_root / path)

        try:
            # Skills use execute(tool_name, tool_input) with dict, not **kwargs
            # Use execute_async if available, otherwise wrap sync execute
            if hasattr(skill, 'execute_async'):
                result = await asyncio.wait_for(
                    skill.execute_async(tool_name, params),
                    timeout=self.config.tool_timeout,
                )
            else:
                # Sync skill - run in executor
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, skill.execute, tool_name, params),
                    timeout=self.config.tool_timeout,
                )

            # Publish tool execution event
            # result can be SkillResponse object or dict
            if hasattr(result, 'success'):
                success = result.success
            elif isinstance(result, dict):
                success = "error" not in result
            else:
                success = True

            await event_bus.publish(Event(
                type=EventType.AGENT_TOOL_EXECUTED,
                data={
                    "tool_name": tool_name,
                    "skill_name": skill_name,
                    "params": params,
                    "success": success,
                },
                source_agent_id=self.agent_id,
                circle_id=getattr(self, '_circle_id', None),
                project_id=self._project_id,
            ))

            # Convert SkillResponse to dict for LLM consumption
            if hasattr(result, 'to_dict'):
                return result.to_dict()
            return result
        except asyncio.TimeoutError:
            return {"error": f"Tool {tool_name} timed out"}
        except Exception as e:
            return {"error": f"Tool {tool_name} failed: {str(e)}"}

    async def chat(
        self,
        message: str,
        include_memories: bool = True,
        allow_tools: bool = True,
    ) -> AgentResponse:
        """
        Send a message to the agent and get a response.

        This is the main entry point for interacting with the agent.
        It handles:
        - Context building (persona, project, memories)
        - Session tracking
        - Tool execution
        - Memory recording

        Args:
            message: User message
            include_memories: Whether to include RAG memories
            allow_tools: Whether to allow tool use

        Returns:
            AgentResponse with content and metadata
        """
        if self._is_processing:
            return AgentResponse(
                content="Je suis déjà en train de traiter une requête.",
                metadata={"error": "already_processing"},
            )

        self._is_processing = True
        start_time = datetime.now(timezone.utc)

        try:
            # Build context
            context = await self.memory.build_context(
                agent_id=self.agent_id,
                user_message=message,
                project_id=self._project_id,
                include_memories=include_memories,
            )

            # Add project context if set
            if self._project:
                if context.system_prompt:
                    # Append project context to existing prompt
                    context.system_prompt += f"\n\n## Contexte Projet\n{self._project.to_prompt()}"
                else:
                    # Build complete prompt with project
                    context.system_prompt = self.persona.build_system_prompt(self._project)

            # Add resume info if needed
            if context.resume_info:
                context.system_prompt += f"\n\n## Reprise de Session\n{context.resume_info}"

            # Add memories if any
            if context.memories:
                memories_text = "\n".join(f"- {m}" for m in context.memories)
                context.system_prompt += f"\n\n## Contexte Pertinent\n{memories_text}"

            # Build messages
            messages = context.to_messages(message)

            # Get tools if allowed
            tools = self._get_all_tools() if (allow_tools and self.config.allow_tools) else None

            # Agent loop: call LLM, execute tools, repeat until done
            all_tool_calls: List[Dict[str, Any]] = []
            all_tool_results: List[Dict[str, Any]] = []
            iteration = 0
            final_content = ""

            while iteration < self.config.max_iterations:
                iteration += 1

                # Call LLM (synchronous - returns Dict)
                llm_response = self.llm.complete(
                    messages=messages,
                    tools=tools,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                )

                # Extract content and tool_calls from response
                response_content = llm_response.get("content", "")
                tool_calls = llm_response.get("tool_calls", [])

                # If no tool calls, we're done
                if not tool_calls:
                    final_content = response_content or ""
                    break

                # Execute each tool call
                all_tool_calls.extend(tool_calls)

                # Add assistant message with tool calls to conversation
                messages.append({
                    "role": "assistant",
                    "content": response_content or "",
                    "tool_calls": tool_calls,
                })

                # Execute tools and collect results
                for tool_call in tool_calls:
                    tool_id = tool_call.get("id", "")
                    tool_name = tool_call.get("name", "")
                    tool_args = tool_call.get("arguments", {})

                    # Callback before tool execution
                    if self._on_tool_call:
                        await self._on_tool_call(tool_name, tool_args)

                    # Execute the tool
                    result = await self._execute_tool(tool_name, tool_args)

                    tool_result = {
                        "id": tool_id,
                        "tool": tool_name,
                        "arguments": tool_args,
                        "result": result,
                    }
                    all_tool_results.append(tool_result)

                    # Add tool result to messages for next LLM call
                    # Format compatible with provider conversion
                    result_content = str(result) if not isinstance(result, str) else result
                    messages.append({
                        "role": "tool",
                        "tool_use_id": tool_id,
                        "name": tool_name,
                        "content": result_content,
                    })

                # Continue loop to let LLM process tool results

            # Build final response
            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

            response = AgentResponse(
                content=final_content,
                tool_calls=all_tool_calls,
                tool_results=all_tool_results,
                model=self.config.model,
                duration_ms=duration_ms,
                metadata={"iterations": iteration},
            )

            # Record exchange in memory
            await self.memory.record_exchange(
                agent_id=self.agent_id,
                user_message=message,
                assistant_response=final_content,
                should_remember=self.config.auto_remember,
            )

            # Callback
            if self._on_response:
                await self._on_response(response)

            return response

        finally:
            self._is_processing = False

    async def remember(self, content: str, memory_type: str = "learning") -> int:
        """
        Explicitly remember something.

        Args:
            content: What to remember
            memory_type: Type of memory

        Returns:
            Memory ID
        """
        return await self.memory.remember(
            agent_id=self.agent_id,
            content=content,
            memory_type=memory_type,
        )

    async def recall(self, query: str, limit: int = 5) -> List[str]:
        """
        Recall relevant memories.

        Args:
            query: What to search for
            limit: Max results

        Returns:
            List of relevant memories
        """
        return await self.memory.recall(
            agent_id=self.agent_id,
            query=query,
            limit=limit,
        )

    def track_file(self, file_path: str) -> None:
        """Track a file being worked on."""
        self.memory.track_file(self.agent_id, file_path)

    def untrack_file(self, file_path: str) -> None:
        """Stop tracking a file."""
        self.memory.untrack_file(self.agent_id, file_path)

    def add_pending_action(self, action: str) -> None:
        """Add an action to be done."""
        self.memory.add_pending_action(self.agent_id, action)

    def complete_action(self, action: str) -> None:
        """Mark an action as completed."""
        self.memory.complete_action(self.agent_id, action)

    def set_current_task(self, task_id: int, title: str, progress: str = "") -> None:
        """Set the current task."""
        self.memory.set_current_task(self.agent_id, task_id, title, progress)

    def clear_current_task(self) -> None:
        """Clear the current task."""
        self.memory.clear_current_task(self.agent_id)

    def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        session = self.session
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "provider": self.config.provider,
            "model": self.config.model,
            "is_processing": self._is_processing,
            "session": {
                "status": session.status,
                "last_activity": session.last_activity.isoformat(),
                "time_since": session.time_since_str,
                "needs_resume": session.needs_resume,
                "working_files": session.working_files,
                "pending_actions": session.pending_actions,
                "current_task": session.current_task_title or None,
            },
            "skills": list(self._skills.keys()),
            "tools_count": len(self._tool_map),
            "project": self._project.name if self._project else None,
        }

    async def plan_action(self, goal: str, context: Dict[str, Any]) -> str:
        """
        Plan the next action toward a goal.

        Used by BackgroundTaskRunner to get the next step.

        Args:
            goal: The goal to work toward
            context: Current context (progress, recent steps, etc.)

        Returns:
            Planned action description
        """
        prompt = f"""You are planning the next action toward a goal.

GOAL: {goal}

CURRENT CONTEXT:
- Step: {context.get('current_step', 0)}/{context.get('max_steps', 50)}
- Progress: {context.get('progress_percent', 0)}%
- Last action: {context.get('last_action', 'None')}
- Summary: {context.get('progress_summary', 'Starting')}

Recent steps:
{context.get('recent_steps', 'None')}

Plan your next specific action. Be concrete and actionable.
If you believe the goal is complete, start with [COMPLETE]."""

        response = await self.chat(prompt, include_memories=True, allow_tools=False)
        return response.content

    async def execute_action(self, action: str, goal: str) -> Dict[str, Any]:
        """
        Execute a planned action.

        Used by BackgroundTaskRunner to perform steps.

        Args:
            action: The action to execute
            goal: The overarching goal (for context)

        Returns:
            Dict with output and tool usage
        """
        prompt = f"""Execute this action to progress toward the goal.

GOAL: {goal}

ACTION TO EXECUTE: {action}

Use available tools to complete this action. Report your results clearly."""

        response = await self.chat(prompt, include_memories=False, allow_tools=True)

        return {
            "output": response.content,
            "tool_calls": response.tool_calls,
            "tool_results": response.tool_results,
            "tokens_used": response.tokens_used,
            "duration_ms": response.duration_ms,
        }

    async def is_goal_complete(self, goal: str, current_state: Dict[str, Any]) -> bool:
        """
        Check if a goal has been achieved.

        Used by BackgroundTaskRunner to detect completion.

        Args:
            goal: The goal to check
            current_state: Current progress state

        Returns:
            True if goal is complete
        """
        # Quick check for explicit completion marker
        last_output = current_state.get("last_output", "")
        if "[COMPLETE]" in last_output.upper():
            return True

        prompt = f"""Evaluate if this goal has been achieved.

GOAL: {goal}

CURRENT STATE:
- Steps completed: {current_state.get('current_step', 0)}
- Progress: {current_state.get('progress_percent', 0)}%
- Last result: {last_output[:800] if last_output else 'None'}

Has the goal been FULLY achieved? Reply ONLY with 'YES' or 'NO'."""

        response = await self.chat(prompt, include_memories=False, allow_tools=False)
        return response.content.strip().upper().startswith("YES")

    def export_state(self) -> Dict[str, Any]:
        """Export agent state for persistence."""
        return {
            "agent_id": self.agent_id,
            "persona": self.persona.to_dict(),
            "config": {
                "provider": self.config.provider,
                "model": self.config.model,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "auto_remember": self.config.auto_remember,
            },
            "session": self.memory.export_session(self.agent_id),
            "project_id": self._project_id,
        }

    @classmethod
    def from_state(
        cls,
        state: Dict[str, Any],
        llm: LLMProvider,
        memory: Optional[MemoryService] = None,
    ) -> "AgentWrapper":
        """
        Restore agent from exported state.

        Args:
            state: Exported state dictionary
            llm: LLM provider
            memory: Memory service (creates one if not provided)

        Returns:
            Restored AgentWrapper
        """
        persona = AgentPersona.from_dict(state["persona"])
        config = AgentConfig(**state.get("config", {}))

        agent = cls(
            agent_id=state["agent_id"],
            persona=persona,
            llm=llm,
            memory=memory,
            config=config,
        )

        # Restore session if present
        if state.get("session"):
            agent.memory.import_session(state["agent_id"], state["session"])

        return agent


# Factory functions for common agent types

def create_architect_agent(
    agent_id: int,
    llm: LLMProvider,
    memory: Optional[MemoryService] = None,
    project: Optional[ProjectContext] = None,
) -> AgentWrapper:
    """Create an architect agent (Opus-style)."""
    from gathering.agents.persona import ARCHITECT_PERSONA

    config = AgentConfig(
        model="claude-sonnet-4-20250514",  # Or claude-3-opus
        temperature=0.7,
        auto_remember=True,
    )

    agent = AgentWrapper(
        agent_id=agent_id,
        persona=ARCHITECT_PERSONA,
        llm=llm,
        memory=memory,
        config=config,
    )

    if project:
        agent.set_project(project)

    return agent


def create_developer_agent(
    agent_id: int,
    llm: LLMProvider,
    memory: Optional[MemoryService] = None,
    project: Optional[ProjectContext] = None,
) -> AgentWrapper:
    """Create a developer agent (Sonnet-style)."""
    from gathering.agents.persona import SENIOR_DEV_PERSONA

    config = AgentConfig(
        model="claude-sonnet-4-20250514",
        temperature=0.5,
        auto_remember=True,
    )

    agent = AgentWrapper(
        agent_id=agent_id,
        persona=SENIOR_DEV_PERSONA,
        llm=llm,
        memory=memory,
        config=config,
    )

    if project:
        agent.set_project(project)

    return agent


def create_code_specialist_agent(
    agent_id: int,
    llm: LLMProvider,
    memory: Optional[MemoryService] = None,
    project: Optional[ProjectContext] = None,
) -> AgentWrapper:
    """Create a code specialist agent (DeepSeek-style)."""
    from gathering.agents.persona import CODE_SPECIALIST_PERSONA

    config = AgentConfig(
        provider="deepseek",
        model="deepseek-coder",
        temperature=0.3,
        auto_remember=True,
    )

    agent = AgentWrapper(
        agent_id=agent_id,
        persona=CODE_SPECIALIST_PERSONA,
        llm=llm,
        memory=memory,
        config=config,
    )

    if project:
        agent.set_project(project)

    return agent
