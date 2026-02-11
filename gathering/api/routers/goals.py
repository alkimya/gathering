"""
Agent Goals API endpoints.
Manages hierarchical goal tracking and decomposition.
"""

from typing import Optional, List, Any, Dict
from fastapi import APIRouter, HTTPException, Depends
from starlette.requests import Request

from gathering.api.rate_limit import limiter, TIER_READ, TIER_WRITE
from pydantic import BaseModel, Field

from gathering.api.dependencies import (
    get_database_service,
    get_agent_registry,
    DatabaseService,
    AgentRegistry,
)
from gathering.agents.goals import (
    get_goal_manager,
    Goal,
    GoalStatus,
    GoalPriority,
)


# =============================================================================
# Pydantic Schemas
# =============================================================================

class GoalCreate(BaseModel):
    agent_id: int = Field(..., description="Agent responsible for this goal")
    title: str = Field(..., min_length=1, max_length=255, description="Goal title")
    description: str = Field(..., min_length=1, description="Detailed description")
    circle_id: Optional[int] = Field(None, description="Optional circle context")
    parent_id: Optional[int] = Field(None, description="Parent goal for subgoals")
    success_criteria: Optional[str] = Field(None, description="How to know when goal is complete")
    priority: str = Field("medium", description="Priority: low, medium, high, critical")
    deadline: Optional[str] = Field(None, description="ISO format deadline")
    estimated_hours: Optional[float] = Field(None, ge=0, description="Estimated hours to complete")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")


class GoalUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    success_criteria: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    progress_percent: Optional[int] = Field(None, ge=0, le=100)
    status_message: Optional[str] = None
    deadline: Optional[str] = None
    estimated_hours: Optional[float] = Field(None, ge=0)
    result_summary: Optional[str] = None
    lessons_learned: Optional[str] = None
    tags: Optional[List[str]] = None


class DecomposeRequest(BaseModel):
    max_subgoals: int = Field(5, ge=1, le=10, description="Maximum subgoals to create")


class DependencyRequest(BaseModel):
    depends_on_id: int = Field(..., description="Goal ID this goal depends on")
    dependency_type: str = Field("blocks", description="Type: blocks, informs, enhances")


class GoalResponse(BaseModel):
    id: int
    agent_id: int
    title: str
    description: str
    status: str
    priority: str
    progress_percent: int
    circle_id: Optional[int] = None
    parent_id: Optional[int] = None
    depth: int = 0
    success_criteria: Optional[str] = None
    status_message: Optional[str] = None
    deadline: Optional[str] = None
    estimated_hours: Optional[float] = None
    actual_hours: float = 0
    is_decomposed: bool = False
    background_task_id: Optional[int] = None
    attempts: int = 0
    max_attempts: int = 3
    result_summary: Optional[str] = None
    artifacts: List[Dict[str, Any]] = []
    tags: List[str] = []
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    agent_name: Optional[str] = None
    subgoal_count: int = 0
    completed_subgoals: int = 0
    blocking_count: int = 0

    class Config:
        from_attributes = True


class ActivityResponse(BaseModel):
    id: int
    goal_id: int
    activity_type: str
    description: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    actor_type: Optional[str] = None
    tokens_used: int = 0
    duration_ms: int = 0
    created_at: Optional[str] = None


# =============================================================================
# Router
# =============================================================================

router = APIRouter(prefix="/goals", tags=["goals"])


def _serialize_goal(goal: Goal) -> dict:
    """Convert Goal to JSON-serializable dict."""
    data = goal.to_dict()
    return data


@router.get("", response_model=dict)
@limiter.limit(TIER_READ)
async def list_goals(
    request: Request,
    agent_id: Optional[int] = None,
    circle_id: Optional[int] = None,
    status: Optional[str] = None,
    parent_id: Optional[int] = None,
    root_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    db: DatabaseService = Depends(get_database_service),
):
    """List goals with optional filters."""
    manager = get_goal_manager(db_service=db)

    status_enum = GoalStatus(status) if status else None

    goals = await manager.list_goals(
        agent_id=agent_id,
        circle_id=circle_id,
        status=status_enum,
        parent_id=parent_id,
        root_only=root_only,
        limit=limit,
        offset=offset,
    )

    # Count by status
    status_counts = {}
    try:
        counts = db.execute("""
            SELECT status::text, COUNT(*) as count
            FROM agent.goals
            GROUP BY status
        """)
        status_counts = {r['status']: r['count'] for r in counts}
    except Exception:
        pass  # Table may not exist yet

    return {
        "goals": [_serialize_goal(g) for g in goals],
        "total": len(goals),
        "counts": status_counts,
    }


@router.get("/{goal_id}", response_model=dict)
@limiter.limit(TIER_READ)
async def get_goal(
    request: Request,
    goal_id: int,
    db: DatabaseService = Depends(get_database_service),
):
    """Get details of a specific goal."""
    manager = get_goal_manager(db_service=db)
    goal = await manager.get_goal(goal_id)

    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    return _serialize_goal(goal)


@router.post("", response_model=dict, status_code=201)
@limiter.limit(TIER_WRITE)
async def create_goal(
    request: Request,
    data: GoalCreate,
    db: DatabaseService = Depends(get_database_service),
):
    """Create a new goal."""
    from datetime import datetime
    from decimal import Decimal

    manager = get_goal_manager(db_service=db)

    # Calculate depth if parent specified
    depth = 0
    if data.parent_id:
        parent = await manager.get_goal(data.parent_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent goal not found")
        depth = parent.depth + 1

    # Create goal object
    goal = Goal(
        id=0,
        agent_id=data.agent_id,
        circle_id=data.circle_id,
        parent_id=data.parent_id,
        depth=depth,
        title=data.title,
        description=data.description,
        success_criteria=data.success_criteria,
        priority=GoalPriority(data.priority),
        deadline=datetime.fromisoformat(data.deadline) if data.deadline else None,
        estimated_hours=Decimal(str(data.estimated_hours)) if data.estimated_hours else None,
        tags=data.tags,
        context=data.context,
        created_by="user",
    )

    goal_id = await manager.create_goal(goal)

    # Fetch created goal
    created_goal = await manager.get_goal(goal_id)
    return _serialize_goal(created_goal)


@router.patch("/{goal_id}", response_model=dict)
@limiter.limit(TIER_WRITE)
async def update_goal(
    request: Request,
    goal_id: int,
    data: GoalUpdate,
    db: DatabaseService = Depends(get_database_service),
):
    """Update a goal."""
    from datetime import datetime
    from decimal import Decimal

    manager = get_goal_manager(db_service=db)

    # Verify goal exists
    goal = await manager.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    # Build updates dict, converting types as needed
    updates = {}
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is None:
            continue
        if field == "priority":
            updates[field] = GoalPriority(value)
        elif field == "status":
            updates[field] = GoalStatus(value)
        elif field == "deadline" and isinstance(value, str):
            updates[field] = datetime.fromisoformat(value)
        elif field == "estimated_hours":
            updates[field] = Decimal(str(value))
        else:
            updates[field] = value

    if updates:
        success = await manager.update_goal(goal_id, updates)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to update goal")

    # Return updated goal
    updated_goal = await manager.get_goal(goal_id)
    return _serialize_goal(updated_goal)


@router.delete("/{goal_id}", status_code=204)
@limiter.limit(TIER_WRITE)
async def delete_goal(
    request: Request,
    goal_id: int,
    db: DatabaseService = Depends(get_database_service),
):
    """Delete a goal and its subgoals."""
    manager = get_goal_manager(db_service=db)

    goal = await manager.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    # Check if goal is active
    if goal.status == GoalStatus.ACTIVE:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete active goal. Pause or complete it first."
        )

    success = await manager.delete_goal(goal_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete goal")


# =============================================================================
# Status Management Endpoints
# =============================================================================

@router.post("/{goal_id}/start", response_model=dict)
@limiter.limit(TIER_WRITE)
async def start_goal(
    request: Request,
    goal_id: int,
    db: DatabaseService = Depends(get_database_service),
):
    """Start working on a goal."""
    manager = get_goal_manager(db_service=db)

    success = await manager.start_goal(goal_id)
    if not success:
        goal = await manager.get_goal(goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        if goal.is_blocked():
            raise HTTPException(status_code=400, detail="Goal is blocked by dependencies")
        if goal.status != GoalStatus.PENDING:
            raise HTTPException(status_code=400, detail=f"Cannot start goal in '{goal.status.value}' status")
        raise HTTPException(status_code=400, detail="Cannot start goal")

    goal = await manager.get_goal(goal_id)
    return _serialize_goal(goal)


@router.post("/{goal_id}/complete", response_model=dict)
@limiter.limit(TIER_WRITE)
async def complete_goal(
    request: Request,
    goal_id: int,
    result_summary: Optional[str] = None,
    db: DatabaseService = Depends(get_database_service),
):
    """Mark a goal as completed."""
    manager = get_goal_manager(db_service=db)

    success = await manager.complete_goal(goal_id, result_summary=result_summary)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to complete goal")

    goal = await manager.get_goal(goal_id)
    return _serialize_goal(goal)


@router.post("/{goal_id}/fail", response_model=dict)
@limiter.limit(TIER_WRITE)
async def fail_goal(
    request: Request,
    goal_id: int,
    reason: str,
    lessons_learned: Optional[str] = None,
    db: DatabaseService = Depends(get_database_service),
):
    """Mark a goal as failed."""
    manager = get_goal_manager(db_service=db)

    success = await manager.fail_goal(goal_id, reason=reason, lessons_learned=lessons_learned)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to mark goal as failed")

    goal = await manager.get_goal(goal_id)
    return _serialize_goal(goal)


@router.post("/{goal_id}/pause", response_model=dict)
@limiter.limit(TIER_WRITE)
async def pause_goal(
    request: Request,
    goal_id: int,
    reason: Optional[str] = None,
    db: DatabaseService = Depends(get_database_service),
):
    """Pause a goal."""
    manager = get_goal_manager(db_service=db)

    success = await manager.pause_goal(goal_id, reason=reason)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to pause goal")

    goal = await manager.get_goal(goal_id)
    return _serialize_goal(goal)


@router.post("/{goal_id}/resume", response_model=dict)
@limiter.limit(TIER_WRITE)
async def resume_goal(
    request: Request,
    goal_id: int,
    db: DatabaseService = Depends(get_database_service),
):
    """Resume a paused goal."""
    manager = get_goal_manager(db_service=db)

    success = await manager.resume_goal(goal_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to resume goal")

    goal = await manager.get_goal(goal_id)
    return _serialize_goal(goal)


@router.post("/{goal_id}/progress", response_model=dict)
@limiter.limit(TIER_WRITE)
async def update_progress(
    request: Request,
    goal_id: int,
    percent: int,
    message: Optional[str] = None,
    db: DatabaseService = Depends(get_database_service),
):
    """Update goal progress."""
    manager = get_goal_manager(db_service=db)

    success = await manager.update_progress(goal_id, percent, message)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update progress")

    goal = await manager.get_goal(goal_id)
    return _serialize_goal(goal)


# =============================================================================
# Decomposition and Hierarchy
# =============================================================================

@router.post("/{goal_id}/decompose", response_model=dict)
@limiter.limit(TIER_WRITE)
async def decompose_goal(
    request: Request,
    goal_id: int,
    data: DecomposeRequest,
    db: DatabaseService = Depends(get_database_service),
    agent_registry: AgentRegistry = Depends(get_agent_registry),
):
    """Decompose a goal into subgoals using the agent."""
    manager = get_goal_manager(db_service=db)

    # Get goal to find agent
    goal = await manager.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    if goal.is_decomposed:
        raise HTTPException(status_code=400, detail="Goal is already decomposed")

    # Get agent from registry
    agent = agent_registry.get(goal.agent_id)
    if not agent:
        raise HTTPException(
            status_code=400,
            detail=f"Agent {goal.agent_id} not found in registry. Cannot decompose."
        )

    subgoal_ids = await manager.decompose_goal(
        goal_id=goal_id,
        agent=agent,
        max_subgoals=data.max_subgoals,
    )

    # Fetch subgoals
    subgoals = []
    for sid in subgoal_ids:
        subgoal = await manager.get_goal(sid)
        if subgoal:
            subgoals.append(_serialize_goal(subgoal))

    return {
        "goal_id": goal_id,
        "subgoal_count": len(subgoals),
        "subgoals": subgoals,
    }


@router.get("/{goal_id}/subgoals", response_model=dict)
@limiter.limit(TIER_READ)
async def get_subgoals(
    request: Request,
    goal_id: int,
    db: DatabaseService = Depends(get_database_service),
):
    """Get subgoals of a goal."""
    manager = get_goal_manager(db_service=db)

    goal = await manager.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    subgoals = await manager.get_subgoals(goal_id)

    return {
        "goal_id": goal_id,
        "subgoals": [_serialize_goal(g) for g in subgoals],
    }


@router.get("/{goal_id}/tree", response_model=dict)
@limiter.limit(TIER_READ)
async def get_goal_tree(
    request: Request,
    goal_id: int,
    db: DatabaseService = Depends(get_database_service),
):
    """Get full goal tree with all nested subgoals."""
    manager = get_goal_manager(db_service=db)

    goal = await manager.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    tree = await manager.get_goal_tree(goal_id)
    return tree


# =============================================================================
# Dependencies
# =============================================================================

@router.post("/{goal_id}/dependencies", response_model=dict)
@limiter.limit(TIER_WRITE)
async def add_dependency(
    request: Request,
    goal_id: int,
    data: DependencyRequest,
    db: DatabaseService = Depends(get_database_service),
):
    """Add a dependency to a goal."""
    manager = get_goal_manager(db_service=db)

    # Verify both goals exist
    goal = await manager.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    depends_on = await manager.get_goal(data.depends_on_id)
    if not depends_on:
        raise HTTPException(status_code=404, detail="Dependency goal not found")

    # Prevent circular dependencies (simple check)
    if goal_id == data.depends_on_id:
        raise HTTPException(status_code=400, detail="Goal cannot depend on itself")

    success = await manager.add_dependency(
        goal_id=goal_id,
        depends_on_id=data.depends_on_id,
        dependency_type=data.dependency_type,
    )

    if not success:
        raise HTTPException(status_code=400, detail="Failed to add dependency")

    return {
        "goal_id": goal_id,
        "depends_on_id": data.depends_on_id,
        "dependency_type": data.dependency_type,
    }


@router.delete("/{goal_id}/dependencies/{depends_on_id}", status_code=204)
@limiter.limit(TIER_WRITE)
async def remove_dependency(
    request: Request,
    goal_id: int,
    depends_on_id: int,
    db: DatabaseService = Depends(get_database_service),
):
    """Remove a dependency from a goal."""
    manager = get_goal_manager(db_service=db)

    success = await manager.remove_dependency(goal_id, depends_on_id)
    if not success:
        raise HTTPException(status_code=404, detail="Dependency not found")


@router.get("/{goal_id}/dependencies", response_model=dict)
@limiter.limit(TIER_READ)
async def get_dependencies(
    request: Request,
    goal_id: int,
    db: DatabaseService = Depends(get_database_service),
):
    """Get goals that this goal depends on."""
    manager = get_goal_manager(db_service=db)

    goal = await manager.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    dependencies = await manager.get_dependencies(goal_id)

    return {
        "goal_id": goal_id,
        "dependencies": [_serialize_goal(g) for g in dependencies],
    }


@router.get("/{goal_id}/dependents", response_model=dict)
@limiter.limit(TIER_READ)
async def get_dependents(
    request: Request,
    goal_id: int,
    db: DatabaseService = Depends(get_database_service),
):
    """Get goals that depend on this goal."""
    manager = get_goal_manager(db_service=db)

    goal = await manager.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    dependents = await manager.get_dependents(goal_id)

    return {
        "goal_id": goal_id,
        "dependents": [_serialize_goal(g) for g in dependents],
    }


# =============================================================================
# Activities
# =============================================================================

@router.get("/{goal_id}/activities", response_model=dict)
@limiter.limit(TIER_READ)
async def get_goal_activities(
    request: Request,
    goal_id: int,
    limit: int = 50,
    offset: int = 0,
    db: DatabaseService = Depends(get_database_service),
):
    """Get activity log for a goal."""
    manager = get_goal_manager(db_service=db)

    goal = await manager.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    activities = await manager.get_activities(goal_id, limit=limit, offset=offset)

    return {
        "goal_id": goal_id,
        "activities": [
            {
                "id": a.id,
                "goal_id": a.goal_id,
                "activity_type": a.activity_type,
                "description": a.description,
                "old_value": a.old_value,
                "new_value": a.new_value,
                "actor_type": a.actor_type,
                "tokens_used": a.tokens_used,
                "duration_ms": a.duration_ms,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in activities
        ],
    }


# Export router
goals_router = router
