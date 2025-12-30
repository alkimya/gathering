"""
GatheringCircle - Main orchestrator for multi-agent collaboration.
Coordinates agents, manages shared context, handles the full workflow.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum

from gathering.orchestration.events import EventBus, EventType, Event
from gathering.orchestration.facilitator import Facilitator, Conflict, ConflictType

logger = logging.getLogger(__name__)


class CircleStatus(Enum):
    """Status of the Gathering Circle."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass
class AgentHandle:
    """Handle to an agent in the circle."""
    id: int
    name: str
    provider: str  # claude, deepseek, openai
    model: str
    competencies: List[str]
    can_review: List[str]
    persona: Optional[str] = None
    is_active: bool = True
    current_task_id: Optional[int] = None

    # Callbacks for agent operations
    process_message: Optional[Callable[[str], Awaitable[str]]] = None
    accept_task: Optional[Callable[[Dict], Awaitable[bool]]] = None
    execute_task: Optional[Callable[[Dict], Awaitable[Dict]]] = None
    perform_review: Optional[Callable[[Dict], Awaitable[Dict]]] = None


@dataclass
class CircleTask:
    """A task in the circle."""
    id: int
    title: str
    description: str
    required_competencies: List[str]
    priority: int = 5
    status: str = "pending"
    assigned_agent_id: Optional[int] = None
    result: Optional[str] = None
    artifacts: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    iteration: int = 1


class GatheringCircle:
    """
    The Gathering Circle orchestrator.

    Manages a group of autonomous agents working together on tasks.
    Uses a Facilitator to route tasks and a shared event bus for communication.

    Usage:
        circle = GatheringCircle()

        # Add agents
        circle.add_agent(AgentHandle(
            id=1, name="Claude", provider="anthropic",
            model="claude-3-opus", competencies=["architecture", "python"],
            can_review=["code", "architecture"],
        ))

        # Start the circle
        await circle.start()

        # Create a task
        task_id = await circle.create_task(
            title="Implement feature X",
            description="...",
            required_competencies=["python"],
        )

        # Let agents work autonomously...
    """

    def __init__(
        self,
        name: str = "default",
        auto_route: bool = True,
        require_review: bool = True,
    ):
        """
        Initialize the Gathering Circle.

        Args:
            name: Circle name
            auto_route: Automatically route tasks to agents
            require_review: Require review before task completion
        """
        self.name = name
        self.auto_route = auto_route
        self.require_review = require_review

        self.status = CircleStatus.INITIALIZING
        self.event_bus = EventBus()
        self.facilitator = Facilitator(self.event_bus)

        self._agents: Dict[int, AgentHandle] = {}
        self._tasks: Dict[int, CircleTask] = {}
        self._next_task_id = 1

        # Human callbacks
        self._on_escalation: Optional[Callable[[Dict], Awaitable[None]]] = None
        self._on_conflict: Optional[Callable[[Conflict], Awaitable[str]]] = None

        self._setup_event_handlers()

    def _setup_event_handlers(self) -> None:
        """Set up internal event handlers."""

        @self.event_bus.on(EventType.TASK_CREATED)
        async def on_task_created(event: Event):
            if self.auto_route:
                task_id = event.data.get("task_id")
                task = self._tasks.get(task_id)
                if task and task.status == "pending":
                    await self.facilitator.route_task(
                        task_id=task_id,
                        title=task.title,
                        required_competencies=task.required_competencies,
                        priority=task.priority,
                    )

        @self.event_bus.on(EventType.TASK_CLAIMED)
        async def on_task_claimed(event: Event):
            task_id = event.data.get("task_id")
            agent_id = event.data.get("agent_id")

            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.status = "in_progress"
                task.assigned_agent_id = agent_id
                task.started_at = datetime.now(timezone.utc)

            if agent_id in self._agents:
                self._agents[agent_id].current_task_id = task_id

        @self.event_bus.on(EventType.TASK_COMPLETED)
        async def on_task_completed(event: Event):
            task_id = event.data.get("task_id")
            agent_id = event.data.get("agent_id")
            result = event.data.get("result")
            artifacts = event.data.get("artifacts", [])

            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.result = result
                task.artifacts = artifacts

                if self.require_review:
                    task.status = "review"
                    # Route to reviewer
                    await self.facilitator.route_review(
                        task_id=task_id,
                        author_id=agent_id,
                        review_type="quality",
                        work_summary=result[:500] if result else "",
                    )
                else:
                    task.status = "completed"
                    task.completed_at = datetime.now(timezone.utc)

            if agent_id in self._agents:
                self._agents[agent_id].current_task_id = None

        @self.event_bus.on(EventType.REVIEW_APPROVED)
        async def on_review_approved(event: Event):
            task_id = event.data.get("task_id")
            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.status = "completed"
                task.completed_at = datetime.now(timezone.utc)

        @self.event_bus.on(EventType.REVIEW_CHANGES_REQUESTED)
        async def on_changes_requested(event: Event):
            task_id = event.data.get("task_id")
            changes = event.data.get("changes", [])

            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.status = "in_progress"
                task.iteration += 1

                # Notify assigned agent
                if task.assigned_agent_id:
                    await self.event_bus.emit(
                        EventType.MENTION_RECEIVED,
                        {
                            "task_id": task_id,
                            "message": f"Changes requested: {changes}",
                            "mentioned_agent_id": task.assigned_agent_id,
                        },
                        target_agent_id=task.assigned_agent_id,
                    )

        @self.event_bus.on(EventType.REVIEW_REJECTED)
        async def on_review_rejected(event: Event):
            task_id = event.data.get("task_id")
            reason = event.data.get("reason", "Unknown")

            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.status = "blocked"

            # Escalate to human
            await self._escalate(
                task_id=task_id,
                reason=f"Review rejected: {reason}",
                severity="high",
            )

        @self.event_bus.on(EventType.CONFLICT_DETECTED)
        async def on_conflict(event: Event):
            if self._on_conflict:
                conflict = Conflict(
                    type=ConflictType(event.data.get("conflict_type")),
                    agent_ids=event.data.get("agent_ids", []),
                    resource=event.data.get("resource", ""),
                    description=event.data.get("description", ""),
                )
                resolution = await self._on_conflict(conflict)
                self.facilitator.resolve_conflict(conflict, resolution)

    def _try_emit_event(
        self,
        event_type: EventType,
        data: Dict[str, Any],
        source_agent_id: Optional[int] = None,
        target_agent_id: Optional[int] = None,
    ) -> None:
        """Try to emit an event, handling case when no event loop is running."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.event_bus.emit(
                event_type, data,
                source_agent_id=source_agent_id,
                target_agent_id=target_agent_id,
            ))
        except RuntimeError:
            # No event loop running, skip async emit
            pass

    async def start(self) -> None:
        """Start the Gathering Circle."""
        self.status = CircleStatus.RUNNING
        await self.event_bus.emit(
            EventType.CIRCLE_STARTED,
            {"name": self.name, "agent_count": len(self._agents)},
        )
        logger.info(f"Gathering Circle '{self.name}' started with {len(self._agents)} agents")

    async def stop(self) -> None:
        """Stop the Gathering Circle."""
        self.status = CircleStatus.STOPPED
        await self.event_bus.emit(
            EventType.CIRCLE_STOPPED,
            {"name": self.name},
        )
        logger.info(f"Gathering Circle '{self.name}' stopped")

    @property
    def agents(self) -> Dict[int, AgentHandle]:
        """Get all agents in the circle."""
        return self._agents

    @property
    def tasks(self) -> Dict[int, CircleTask]:
        """Get all tasks in the circle."""
        return self._tasks

    def add_agent(self, agent: AgentHandle) -> None:
        """
        Add an agent to the circle.

        Args:
            agent: Agent handle with callbacks
        """
        self._agents[agent.id] = agent
        self.facilitator.register_agent(
            agent_id=agent.id,
            name=agent.name,
            competencies=agent.competencies,
            can_review=agent.can_review,
        )

        # Emit join event (fire and forget if in async context)
        self._try_emit_event(
            EventType.AGENT_JOINED,
            {
                "agent_id": agent.id,
                "name": agent.name,
                "provider": agent.provider,
                "competencies": agent.competencies,
                "can_review": agent.can_review,
            },
            source_agent_id=agent.id,
        )

        logger.info(f"Agent '{agent.name}' (id={agent.id}) added to circle")

    def remove_agent(self, agent_id: int) -> None:
        """Remove an agent from the circle."""
        if agent_id in self._agents:
            agent = self._agents[agent_id]
            agent.is_active = False
            self.facilitator.unregister_agent(agent_id)

            self._try_emit_event(
                EventType.AGENT_LEFT,
                {"agent_id": agent_id, "name": agent.name},
                source_agent_id=agent_id,
            )

    def get_agent(self, agent_id: int) -> Optional[AgentHandle]:
        """Get an agent by ID."""
        return self._agents.get(agent_id)

    def get_agents(self) -> List[AgentHandle]:
        """Get all agents."""
        return list(self._agents.values())

    async def create_task(
        self,
        title: str,
        description: str,
        required_competencies: List[str],
        priority: int = 5,
        requires_review: Optional[bool] = None,
    ) -> int:
        """
        Create a new task.

        Args:
            title: Task title
            description: Task description
            required_competencies: Required competencies
            priority: Priority (1-10, lower = higher)
            requires_review: Override circle-level review setting

        Returns:
            Task ID
        """
        task_id = self._next_task_id
        self._next_task_id += 1

        task = CircleTask(
            id=task_id,
            title=title,
            description=description,
            required_competencies=required_competencies,
            priority=priority,
        )
        self._tasks[task_id] = task

        await self.event_bus.emit(
            EventType.TASK_CREATED,
            {
                "task_id": task_id,
                "title": title,
                "description": description,
                "required_competencies": required_competencies,
                "priority": priority,
            },
        )

        logger.info(f"Task {task_id} created: {title}")
        return task_id

    def get_task(self, task_id: int) -> Optional[CircleTask]:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    def get_tasks(self, status: Optional[str] = None) -> List[CircleTask]:
        """Get tasks, optionally filtered by status."""
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    async def claim_task(self, task_id: int, agent_id: int) -> bool:
        """
        Have an agent claim a task.

        Args:
            task_id: Task ID
            agent_id: Agent ID

        Returns:
            True if claim successful
        """
        task = self._tasks.get(task_id)
        agent = self._agents.get(agent_id)

        if not task or not agent:
            return False

        if task.status != "pending":
            return False

        # Check if agent accepts
        if agent.accept_task:
            accepted = await agent.accept_task({
                "task_id": task_id,
                "title": task.title,
                "description": task.description,
                "required_competencies": task.required_competencies,
            })
            if not accepted:
                await self.event_bus.emit(
                    EventType.TASK_REFUSED,
                    {"task_id": task_id, "agent_id": agent_id, "reason": "Agent declined"},
                    source_agent_id=agent_id,
                )
                return False

        await self.event_bus.emit(
            EventType.TASK_CLAIMED,
            {"task_id": task_id, "agent_id": agent_id},
            source_agent_id=agent_id,
        )

        return True

    async def submit_task(
        self,
        task_id: int,
        agent_id: int,
        result: str,
        artifacts: Optional[List[str]] = None,
    ) -> None:
        """
        Submit completed task work.

        Args:
            task_id: Task ID
            agent_id: Agent ID
            result: Work result
            artifacts: List of created/modified files
        """
        await self.event_bus.emit(
            EventType.TASK_COMPLETED,
            {
                "task_id": task_id,
                "agent_id": agent_id,
                "result": result,
                "artifacts": artifacts or [],
            },
            source_agent_id=agent_id,
        )

    async def submit_review(
        self,
        task_id: int,
        reviewer_id: int,
        status: str,  # approved, changes_requested, rejected
        score: int,
        feedback: str,
        changes: Optional[List[str]] = None,
    ) -> None:
        """
        Submit a review.

        Args:
            task_id: Task ID
            reviewer_id: Reviewer agent ID
            status: Review status
            score: Quality score (0-100)
            feedback: Review feedback
            changes: Requested changes (if applicable)
        """
        task = self._tasks.get(task_id)
        if not task:
            return

        event_type = {
            "approved": EventType.REVIEW_APPROVED,
            "changes_requested": EventType.REVIEW_CHANGES_REQUESTED,
            "rejected": EventType.REVIEW_REJECTED,
        }.get(status, EventType.REVIEW_COMPLETED)

        await self.event_bus.emit(
            event_type,
            {
                "task_id": task_id,
                "author_id": task.assigned_agent_id,
                "reviewer_id": reviewer_id,
                "status": status,
                "score": score,
                "feedback": feedback,
                "changes": changes or [],
            },
            source_agent_id=reviewer_id,
        )

    async def send_message(
        self,
        from_agent_id: int,
        content: str,
        mentions: Optional[List[int]] = None,
    ) -> None:
        """
        Send a message in the circle.

        Args:
            from_agent_id: Sender agent ID
            content: Message content
            mentions: List of mentioned agent IDs
        """
        await self.event_bus.emit(
            EventType.MESSAGE_SENT,
            {
                "from_agent_id": from_agent_id,
                "content": content,
                "mentions": mentions or [],
            },
            source_agent_id=from_agent_id,
        )

        # Emit mention events
        for mentioned_id in (mentions or []):
            await self.event_bus.emit(
                EventType.MENTION_RECEIVED,
                {
                    "mentioned_agent_id": mentioned_id,
                    "mentioner_id": from_agent_id,
                    "message_content": content,
                },
                source_agent_id=from_agent_id,
                target_agent_id=mentioned_id,
            )

    async def _escalate(
        self,
        task_id: int,
        reason: str,
        severity: str = "medium",
    ) -> None:
        """Escalate an issue to the human."""
        await self.event_bus.emit(
            EventType.ESCALATION_CREATED,
            {
                "task_id": task_id,
                "reason": reason,
                "severity": severity,
            },
        )

        if self._on_escalation:
            await self._on_escalation({
                "task_id": task_id,
                "reason": reason,
                "severity": severity,
                "task": self._tasks.get(task_id),
            })

    def on_escalation(self, handler: Callable[[Dict], Awaitable[None]]) -> None:
        """Set handler for escalations to human."""
        self._on_escalation = handler

    def on_conflict(self, handler: Callable[[Conflict], Awaitable[str]]) -> None:
        """Set handler for conflict resolution."""
        self._on_conflict = handler

    def get_circle_status(self) -> Dict[str, Any]:
        """Get overall circle status."""
        tasks_by_status = {}
        for task in self._tasks.values():
            tasks_by_status[task.status] = tasks_by_status.get(task.status, 0) + 1

        active_agents = [a for a in self._agents.values() if a.is_active]
        busy_agents = [a for a in active_agents if a.current_task_id]

        return {
            "name": self.name,
            "status": self.status.value,
            "agents": {
                "total": len(self._agents),
                "active": len(active_agents),
                "busy": len(busy_agents),
            },
            "tasks": {
                "total": len(self._tasks),
                "by_status": tasks_by_status,
            },
            "pending_conflicts": len(self.facilitator.get_pending_conflicts()),
        }

    def get_agent_workload(self) -> Dict[int, Dict[str, Any]]:
        """Get workload information for all agents."""
        result = {}
        for agent_id, agent in self._agents.items():
            metrics = self.facilitator.get_agent_metrics(agent_id)
            result[agent_id] = {
                "name": agent.name,
                "is_active": agent.is_active,
                "current_task_id": agent.current_task_id,
                "tasks_completed": metrics.tasks_completed if metrics else 0,
                "average_quality": metrics.average_quality_score if metrics else 0,
                "workload": metrics.current_workload if metrics else 0,
            }
        return result

    async def collaborate(
        self,
        topic: str,
        agent_ids: List[int],
        max_turns: int = 10,
        initial_prompt: str = "",
    ) -> "ConversationResult":
        """
        Start a collaborative conversation between agents.

        This allows multiple agents to work together on a topic,
        discussing and contributing their expertise.

        Args:
            topic: What to collaborate on (e.g., "Écrire les scénarios BDD")
            agent_ids: List of agent IDs to participate
            max_turns: Maximum conversation turns
            initial_prompt: Optional instructions for the conversation

        Returns:
            ConversationResult with transcript and summary

        Example:
            result = await circle.collaborate(
                topic="Écrire les scénarios BDD pour l'authentification",
                agent_ids=[sonnet.id, deepseek.id],
                max_turns=10,
            )
            print(result.summary)
        """
        from gathering.agents.conversation import (
            AgentConversation,
            ConversationResult,
            AgentParticipant,
        )

        # Build participant list with conversation adapters
        participants: List[AgentParticipant] = []

        for agent_id in agent_ids:
            agent = self._agents.get(agent_id)
            if not agent:
                raise ValueError(f"Agent {agent_id} not found in circle")
            if not agent.is_active:
                raise ValueError(f"Agent {agent_id} ({agent.name}) is not active")

            # Create a simple participant adapter for AgentHandle
            participants.append(_AgentHandleParticipant(agent))

        # Create and run conversation
        conversation = AgentConversation(
            topic=topic,
            participants=participants,
            max_turns=max_turns,
            initial_prompt=initial_prompt,
        )

        # Emit event for conversation start
        await self.event_bus.emit(
            EventType.MESSAGE_SENT,
            {
                "type": "collaboration_started",
                "topic": topic,
                "participants": agent_ids,
            },
        )

        result = await conversation.run()

        # Emit event for conversation end
        await self.event_bus.emit(
            EventType.MESSAGE_SENT,
            {
                "type": "collaboration_completed",
                "topic": topic,
                "turns": result.turns_taken,
                "status": result.status.value,
            },
        )

        return result


class _AgentHandleParticipant:
    """Adapter to make AgentHandle compatible with conversation protocol."""

    def __init__(self, agent: AgentHandle):
        self._agent = agent

    @property
    def agent_id(self) -> int:
        return self._agent.id

    @property
    def name(self) -> str:
        return self._agent.name

    async def respond(
        self,
        conversation_context: str,
        last_message: str,
        from_agent: str,
    ) -> str:
        """Generate response using agent's process_message callback."""
        if not self._agent.process_message:
            return f"[{self._agent.name} n'a pas de callback process_message configuré]"

        prompt = f"""
{conversation_context}

{from_agent} vient de dire: "{last_message}"

Réponds de manière concise et constructive. Contribue avec ton expertise.
Si tu penses que la collaboration est terminée, inclus [TERMINÉ] dans ta réponse.
"""
        return await self._agent.process_message(prompt)
