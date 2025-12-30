"""
Agent management endpoints.
Authentication is enforced by the AuthenticationMiddleware.
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from gathering.api.schemas import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentDetailResponse,
    AgentListResponse,
    AgentStatus,
    ChatRequest,
    ChatResponse,
    MemoryCreate,
    MemoryResponse,
    MemoryListResponse,
    RecallRequest,
    RecallResponse,
)
from gathering.api.dependencies import (
    get_agent_registry,
    get_memory_service,
    AgentRegistry,
)
from gathering.agents import (
    AgentWrapper,
    AgentPersona,
    AgentConfig,
    MemoryService,
)


router = APIRouter(prefix="/agents", tags=["agents"])


def _agent_to_response(agent: AgentWrapper) -> AgentResponse:
    """Convert AgentWrapper to AgentResponse."""
    session = agent.session
    status_val = AgentStatus.BUSY if agent._is_processing else AgentStatus.IDLE

    return AgentResponse(
        id=agent.agent_id,
        name=agent.name,
        role=agent.role,
        provider=agent.config.provider,
        model=agent.config.model,
        status=status_val,
        competencies=list(agent.persona.specializations),
        can_review=[],  # From AgentHandle, not AgentWrapper
        current_task=session.current_task_title,
        created_at=session.started_at,
        last_activity=session.last_activity,
    )


def _agent_to_detail(agent: AgentWrapper) -> AgentDetailResponse:
    """Convert AgentWrapper to AgentDetailResponse."""
    from gathering.api.schemas import AgentPersonaSchema, AgentConfigSchema

    session = agent.session
    status_val = AgentStatus.BUSY if agent._is_processing else AgentStatus.IDLE

    persona_schema = AgentPersonaSchema(
        name=agent.persona.name,
        role=agent.persona.role,
        traits=list(agent.persona.traits),
        communication_style=agent.persona.communication_style,
        specializations=list(agent.persona.specializations),
        languages=list(agent.persona.languages),
    )

    config_schema = AgentConfigSchema(
        provider=agent.config.provider,
        model=agent.config.model,
        max_tokens=agent.config.max_tokens,
        temperature=agent.config.temperature,
        competencies=list(agent.persona.specializations),
        can_review=[],
    )

    session_data = {
        "status": session.status,
        "working_files": session.working_files,
        "pending_actions": session.pending_actions,
        "message_count": len(session.recent_messages),
        "needs_resume": session.needs_resume,
        "time_since": session.time_since_str,
    }

    return AgentDetailResponse(
        id=agent.agent_id,
        name=agent.name,
        role=agent.role,
        provider=agent.config.provider,
        model=agent.config.model,
        status=status_val,
        competencies=list(agent.persona.specializations),
        can_review=[],
        current_task=session.current_task_title,
        created_at=session.started_at,
        last_activity=session.last_activity,
        persona=persona_schema,
        config=config_schema,
        session=session_data,
        skills=list(agent._skills.keys()),
        tools_count=len(agent._tool_map),
    )


# =============================================================================
# CRUD Endpoints
# =============================================================================


@router.get("", response_model=AgentListResponse)
async def list_agents(
    registry: AgentRegistry = Depends(get_agent_registry),
) -> AgentListResponse:
    """List all agents."""
    agents = registry.list_all()
    return AgentListResponse(
        agents=[_agent_to_response(a) for a in agents],
        total=len(agents),
    )


@router.post("", response_model=AgentDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    data: AgentCreate,
    registry: AgentRegistry = Depends(get_agent_registry),
    memory: MemoryService = Depends(get_memory_service),
) -> AgentDetailResponse:
    """
    Create a new agent.

    Note: This creates an agent without an LLM provider.
    The agent will need to be configured with an LLM before it can chat.
    """
    agent_id = registry.next_id()

    persona = AgentPersona(
        name=data.persona.name,
        role=data.persona.role,
        traits=data.persona.traits,
        communication_style=data.persona.communication_style,
        specializations=data.persona.specializations,
        languages=data.persona.languages,
    )

    config = AgentConfig(
        provider=data.config.provider,
        model=data.config.model,
        max_tokens=data.config.max_tokens,
        temperature=data.config.temperature,
    )

    # Create a mock LLM provider for now
    # In production, this would be configured separately
    class MockLLM:
        async def complete(self, **kwargs) -> str:
            return "LLM not configured. Please set up an LLM provider."

    agent = AgentWrapper(
        agent_id=agent_id,
        persona=persona,
        llm=MockLLM(),
        memory=memory,
        config=config,
    )

    registry.add(agent)
    return _agent_to_detail(agent)


@router.get("/{agent_id}", response_model=AgentDetailResponse)
async def get_agent(
    agent_id: int,
    registry: AgentRegistry = Depends(get_agent_registry),
) -> AgentDetailResponse:
    """Get agent details by ID."""
    agent = registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )
    return _agent_to_detail(agent)


@router.patch("/{agent_id}", response_model=AgentDetailResponse)
async def update_agent(
    agent_id: int,
    data: AgentUpdate,
    registry: AgentRegistry = Depends(get_agent_registry),
) -> AgentDetailResponse:
    """Update an agent."""
    agent = registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )

    if data.persona:
        agent.persona = AgentPersona(
            name=data.persona.name,
            role=data.persona.role,
            traits=data.persona.traits,
            communication_style=data.persona.communication_style,
            specializations=data.persona.specializations,
            languages=data.persona.languages,
        )

    if data.config:
        agent.config = AgentConfig(
            provider=data.config.provider,
            model=data.config.model,
            max_tokens=data.config.max_tokens,
            temperature=data.config.temperature,
        )

    return _agent_to_detail(agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: int,
    registry: AgentRegistry = Depends(get_agent_registry),
):
    """Delete an agent."""
    if not registry.remove(agent_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )


# =============================================================================
# Chat Endpoints
# =============================================================================


@router.post("/{agent_id}/chat", response_model=ChatResponse)
async def chat_with_agent(
    agent_id: int,
    data: ChatRequest,
    registry: AgentRegistry = Depends(get_agent_registry),
) -> ChatResponse:
    """
    Chat with an agent.

    Sends a message to the agent and returns its response.
    The agent's persona, project context, and memories are automatically injected.
    """
    agent = registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )

    try:
        response = await agent.chat(
            message=data.message,
            include_memories=data.include_memories,
            allow_tools=data.allow_tools,
        )

        return ChatResponse(
            content=response.content,
            agent_id=agent.agent_id,
            agent_name=agent.name,
            model=response.model,
            duration_ms=response.duration_ms,
            tool_calls=response.tool_calls,
            tool_results=response.tool_results,
            tokens_used=response.tokens_used,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {str(e)}",
        )


@router.get("/{agent_id}/status")
async def get_agent_status(
    agent_id: int,
    registry: AgentRegistry = Depends(get_agent_registry),
) -> dict:
    """Get agent status including session info."""
    agent = registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )
    return agent.get_status()


# =============================================================================
# Memory Endpoints
# =============================================================================


@router.post("/{agent_id}/memories", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(
    agent_id: int,
    data: MemoryCreate,
    registry: AgentRegistry = Depends(get_agent_registry),
) -> MemoryResponse:
    """Create a memory for an agent."""
    agent = registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )

    memory_id = await agent.remember(
        content=data.content,
        memory_type=data.memory_type,
    )

    return MemoryResponse(
        id=memory_id,
        content=data.content,
        memory_type=data.memory_type,
        created_at=datetime.now(timezone.utc),
    )


@router.post("/{agent_id}/memories/recall", response_model=RecallResponse)
async def recall_memories(
    agent_id: int,
    data: RecallRequest,
    registry: AgentRegistry = Depends(get_agent_registry),
) -> RecallResponse:
    """Recall relevant memories for an agent."""
    agent = registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )

    memories = await agent.recall(
        query=data.query,
        limit=data.limit,
    )

    return RecallResponse(
        memories=memories,
        query=data.query,
    )


# =============================================================================
# Session Management
# =============================================================================


@router.post("/{agent_id}/session/track-file")
async def track_file(
    agent_id: int,
    file_path: str,
    registry: AgentRegistry = Depends(get_agent_registry),
):
    """Track a file being worked on."""
    agent = registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )

    agent.track_file(file_path)
    return {"status": "ok", "file": file_path}


@router.post("/{agent_id}/session/set-task")
async def set_current_task(
    agent_id: int,
    task_id: int,
    title: str,
    progress: str = "",
    registry: AgentRegistry = Depends(get_agent_registry),
):
    """Set the current task for an agent."""
    agent = registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )

    agent.set_current_task(task_id, title, progress)
    return {"status": "ok", "task_id": task_id, "title": title}


@router.delete("/{agent_id}/session/task")
async def clear_current_task(
    agent_id: int,
    registry: AgentRegistry = Depends(get_agent_registry),
):
    """Clear the current task for an agent."""
    agent = registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )

    agent.clear_current_task()
    return {"status": "ok"}
