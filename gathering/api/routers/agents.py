"""
Agent management endpoints.
Authentication is enforced by the AuthenticationMiddleware.
"""

import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from starlette.requests import Request

from gathering.api.rate_limit import limiter, TIER_READ, TIER_WRITE
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
    RecallRequest,
    RecallResponse,
)
from gathering.api.dependencies import (
    get_agent_registry,
    get_memory_service,
    get_database_service,
    AgentRegistry,
    DatabaseService,
)
from gathering.api.async_db import AsyncDatabaseService, get_async_db
from gathering.agents import (
    AgentWrapper,
    AgentPersona,
    AgentConfig,
    MemoryService,
)
from gathering.llm.providers import LLMProviderFactory
from gathering.core.config import get_settings

logger = logging.getLogger(__name__)


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
@limiter.limit(TIER_READ)
async def list_agents(
    request: Request,
    registry: AgentRegistry = Depends(get_agent_registry),
) -> AgentListResponse:
    """List all agents."""
    agents = registry.list_all()
    return AgentListResponse(
        agents=[_agent_to_response(a) for a in agents],
        total=len(agents),
    )


@router.post("", response_model=AgentDetailResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(TIER_WRITE)
async def create_agent(
    request: Request,
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

    # Create a real LLM provider using the factory
    settings = get_settings()
    provider_name = data.config.provider.lower()

    # Get API key for the provider
    api_key = settings.get_llm_api_key(provider_name)

    if api_key:
        try:
            llm = LLMProviderFactory.create(provider_name, {
                "api_key": api_key,
                "model": data.config.model,
                "max_tokens": data.config.max_tokens,
                "temperature": data.config.temperature,
            })
            logger.info(f"Created {provider_name} LLM provider for agent {agent_id}")
        except Exception as exc:
            logger.warning(f"Failed to create LLM provider: {exc}, using mock")
            error_msg = str(exc)
            # Fallback to mock if provider creation fails
            class MockLLM:
                def complete(self, messages, **kwargs):
                    return {"content": f"LLM provider '{provider_name}' configuration failed: {error_msg}"}
            llm = MockLLM()
    else:
        logger.warning(f"No API key for provider '{provider_name}', using mock LLM")
        # Use mock LLM if no API key
        class MockLLM:
            def complete(self, messages, **kwargs):
                return {"content": f"LLM not configured. Please set {provider_name.upper()}_API_KEY environment variable."}
        llm = MockLLM()

    agent = AgentWrapper(
        agent_id=agent_id,
        persona=persona,
        llm=llm,
        memory=memory,
        config=config,
    )

    registry.add(agent)
    return _agent_to_detail(agent)


@router.get("/{agent_id}", response_model=AgentDetailResponse)
@limiter.limit(TIER_READ)
async def get_agent(
    request: Request,
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
@limiter.limit(TIER_WRITE)
async def update_agent(
    request: Request,
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


@router.get("/{agent_id}/history")
async def get_agent_history(
    agent_id: int,
    limit: int = 50,
    registry: AgentRegistry = Depends(get_agent_registry),
    db: AsyncDatabaseService = Depends(get_async_db),
) -> dict:
    """
    Get chat history for an agent.

    Returns the recent messages from the database.
    Uses AsyncDatabaseService for non-blocking DB access.
    """
    agent = registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )

    # Get messages from database (async -- does not block event loop)
    messages = []
    try:
        rows = await db.execute(
            """
            SELECT id, role, content, created_at
            FROM communication.chat_history
            WHERE agent_id = %(agent_id)s
            ORDER BY created_at DESC
            LIMIT %(limit)s
            """,
            {"agent_id": agent_id, "limit": limit},
        )
        # Reverse to get chronological order
        for row in reversed(rows):
            messages.append({
                "id": row["id"],
                "role": row["role"],
                "content": row["content"],
                "timestamp": row["created_at"].isoformat() if row["created_at"] else datetime.now(timezone.utc).isoformat(),
                "agent_name": agent.name if row["role"] == "assistant" else None,
            })
    except Exception as e:
        logger.warning(f"Failed to load history from DB, falling back to session: {e}")
        # Fallback to session if DB fails
        session = agent.session
        for msg in session.recent_messages[-limit:]:
            messages.append({
                "id": hash(f"{msg.get('timestamp', '')}{msg.get('content', '')[:20]}"),
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
                "timestamp": msg.get("timestamp", datetime.now(timezone.utc).isoformat()),
                "agent_name": agent.name if msg.get("role") == "assistant" else None,
            })

    return {"messages": messages}


@router.post("/{agent_id}/chat", response_model=ChatResponse)
async def chat_with_agent(
    agent_id: int,
    data: ChatRequest,
    registry: AgentRegistry = Depends(get_agent_registry),
    db: AsyncDatabaseService = Depends(get_async_db),
) -> ChatResponse:
    """
    Chat with an agent.

    Sends a message to the agent and returns its response.
    The agent's persona, project context, and memories are automatically injected.
    Uses AsyncDatabaseService for non-blocking DB writes.
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

        # Save to database (async -- does not block event loop)
        try:
            # Save user message
            await db.execute(
                """
                INSERT INTO communication.chat_history
                (agent_id, role, content, created_at)
                VALUES (%(agent_id)s, 'user', %(content)s, NOW())
                """,
                {"agent_id": agent_id, "content": data.message},
            )
            # Save assistant response
            await db.execute(
                """
                INSERT INTO communication.chat_history
                (agent_id, role, content, model_used, tokens_output, created_at)
                VALUES (%(agent_id)s, 'assistant', %(content)s, %(model)s, %(tokens)s, NOW())
                """,
                {"agent_id": agent_id, "content": response.content, "model": response.model, "tokens": response.tokens_used},
            )
        except Exception as e:
            logger.warning(f"Failed to save chat to database: {e}")

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


# =============================================================================
# Skills Management Endpoints
# =============================================================================


@router.get("/{agent_id}/skills")
async def get_agent_skills(
    agent_id: int,
    registry: AgentRegistry = Depends(get_agent_registry),
    db: DatabaseService = Depends(get_database_service),
) -> dict:
    """
    Get skills configured for an agent.

    Returns:
        - configured_skills: Skills assigned to this agent in DB
        - loaded_skills: Skills currently loaded in memory
        - available_skills: All skills available in the system
    """
    agent = registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )

    # Get skills from DB
    skill_row = db.execute_one(
        "SELECT skill_names FROM agent.agents WHERE id = %(id)s",
        {'id': agent_id}
    )
    configured_skills = skill_row.get('skill_names') or [] if skill_row else []

    # Get loaded skills from agent wrapper
    loaded_skills = list(agent._skills.keys())

    # Get all available skills
    from gathering.skills.registry import SkillRegistry
    available_skills = SkillRegistry.list_skills()

    # Get tool count per loaded skill
    skill_details = []
    for skill_name in loaded_skills:
        skill = agent._skills.get(skill_name)
        if skill:
            skill_details.append({
                "name": skill_name,
                "description": getattr(skill, 'description', ''),
                "version": getattr(skill, 'version', '1.0.0'),
                "tools_count": len(skill.tools),
                "tools": [t.get('name') for t in skill.tools],
            })

    return {
        "agent_id": agent_id,
        "configured_skills": configured_skills,
        "loaded_skills": loaded_skills,
        "skill_details": skill_details,
        "available_skills": available_skills,
        "tools_count": len(agent._tool_map),
    }


@router.put("/{agent_id}/skills")
async def update_agent_skills(
    agent_id: int,
    skills: List[str],
    registry: AgentRegistry = Depends(get_agent_registry),
    db: DatabaseService = Depends(get_database_service),
) -> dict:
    """
    Update skills for an agent.

    Args:
        skills: List of skill names to assign to the agent

    Returns:
        Updated skill configuration
    """
    agent = registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )

    # Validate skill names
    from gathering.skills.registry import SkillRegistry
    available_skills = SkillRegistry.list_skills()
    invalid_skills = [s for s in skills if s not in available_skills]
    if invalid_skills:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid skill names: {invalid_skills}. Available: {available_skills}",
        )

    # Update in database
    try:
        db._db.execute(
            "UPDATE agent.agents SET skill_names = %(skills)s WHERE id = %(id)s",
            {'id': agent_id, 'skills': skills}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update skills in database: {str(e)}",
        )

    # Reload skills in agent wrapper
    # First remove existing skills
    for skill_name in list(agent._skills.keys()):
        agent.remove_skill(skill_name)

    # Load new skills
    project_path = "/home/loc/workspace/gathering"
    loaded = []
    failed = []

    for skill_name in skills:
        try:
            skill = SkillRegistry.get(
                skill_name,
                config={"working_dir": project_path, "allowed_paths": [project_path]},
            )
            agent.add_skill(skill)
            loaded.append(skill_name)
        except Exception as e:
            logger.warning(f"Failed to load skill {skill_name}: {e}")
            failed.append({"skill": skill_name, "error": str(e)})

    return {
        "agent_id": agent_id,
        "configured_skills": skills,
        "loaded_skills": loaded,
        "failed_skills": failed,
        "tools_count": len(agent._tool_map),
    }


@router.post("/{agent_id}/skills/{skill_name}")
async def add_agent_skill(
    agent_id: int,
    skill_name: str,
    registry: AgentRegistry = Depends(get_agent_registry),
    db: DatabaseService = Depends(get_database_service),
) -> dict:
    """Add a single skill to an agent."""
    agent = registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )

    # Validate skill name
    from gathering.skills.registry import SkillRegistry
    available_skills = SkillRegistry.list_skills()
    if skill_name not in available_skills:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid skill name: {skill_name}. Available: {available_skills}",
        )

    # Get current skills from DB
    skill_row = db.execute_one(
        "SELECT skill_names FROM agent.agents WHERE id = %(id)s",
        {'id': agent_id}
    )
    current_skills = skill_row.get('skill_names') or [] if skill_row else []

    # Add skill if not already present
    if skill_name in current_skills:
        return {
            "status": "already_exists",
            "agent_id": agent_id,
            "skill": skill_name,
            "skills": current_skills,
        }

    new_skills = current_skills + [skill_name]

    # Update in database
    db._db.execute(
        "UPDATE agent.agents SET skill_names = %(skills)s WHERE id = %(id)s",
        {'id': agent_id, 'skills': new_skills}
    )

    # Load skill in agent wrapper
    try:
        project_path = "/home/loc/workspace/gathering"
        skill = SkillRegistry.get(
            skill_name,
            config={"working_dir": project_path, "allowed_paths": [project_path]},
        )
        agent.add_skill(skill)
    except Exception as e:
        logger.warning(f"Failed to load skill {skill_name}: {e}")

    return {
        "status": "added",
        "agent_id": agent_id,
        "skill": skill_name,
        "skills": new_skills,
        "tools_count": len(agent._tool_map),
    }


@router.delete("/{agent_id}/skills/{skill_name}")
async def remove_agent_skill(
    agent_id: int,
    skill_name: str,
    registry: AgentRegistry = Depends(get_agent_registry),
    db: DatabaseService = Depends(get_database_service),
) -> dict:
    """Remove a skill from an agent."""
    agent = registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )

    # Get current skills from DB
    skill_row = db.execute_one(
        "SELECT skill_names FROM agent.agents WHERE id = %(id)s",
        {'id': agent_id}
    )
    current_skills = skill_row.get('skill_names') or [] if skill_row else []

    # Remove skill if present
    if skill_name not in current_skills:
        return {
            "status": "not_found",
            "agent_id": agent_id,
            "skill": skill_name,
            "skills": current_skills,
        }

    new_skills = [s for s in current_skills if s != skill_name]

    # Update in database
    db._db.execute(
        "UPDATE agent.agents SET skill_names = %(skills)s WHERE id = %(id)s",
        {'id': agent_id, 'skills': new_skills}
    )

    # Remove skill from agent wrapper
    agent.remove_skill(skill_name)

    return {
        "status": "removed",
        "agent_id": agent_id,
        "skill": skill_name,
        "skills": new_skills,
        "tools_count": len(agent._tool_map),
    }
