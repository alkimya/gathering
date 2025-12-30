"""
Circle orchestration endpoints.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from gathering.api.schemas import (
    CircleCreate,
    CircleResponse,
    CircleDetailResponse,
    CircleListResponse,
    CircleStatus,
    TaskCreate,
    TaskResponse,
    TaskListResponse,
    TaskStatus,
    TaskResultSubmit,
    AgentResponse,
    AgentStatus,
)
from gathering.api.dependencies import (
    get_circle_registry,
    get_agent_registry,
    CircleRegistry,
    AgentRegistry,
)
from gathering.orchestration import GatheringCircle, AgentHandle, CircleTask


router = APIRouter(prefix="/circles", tags=["circles"])


def _circle_to_response(circle: GatheringCircle) -> CircleResponse:
    """Convert GatheringCircle to CircleResponse."""
    status_map = {
        "initializing": CircleStatus.STOPPED,
        "stopped": CircleStatus.STOPPED,
        "starting": CircleStatus.STARTING,
        "running": CircleStatus.RUNNING,
        "stopping": CircleStatus.STOPPING,
        "paused": CircleStatus.STOPPED,
    }

    active_statuses = {"assigned", "in_progress", "in_review"}
    active_tasks = len([
        t for t in circle.tasks.values()
        if t.status in active_statuses
    ])

    # Get started_at from first task or use now as fallback
    started_at = None
    if circle.tasks:
        first_task = min(circle.tasks.values(), key=lambda t: t.created_at)
        started_at = first_task.created_at

    return CircleResponse(
        id=circle.name,
        name=circle.name,
        status=status_map.get(circle.status.value, CircleStatus.STOPPED),
        agent_count=len(circle.agents),
        task_count=len(circle.tasks),
        active_tasks=active_tasks,
        require_review=circle.require_review,
        auto_route=circle.auto_route,
        created_at=datetime.now(timezone.utc),
        started_at=started_at,
    )


def _circle_to_detail(circle: GatheringCircle) -> CircleDetailResponse:
    """Convert GatheringCircle to CircleDetailResponse."""
    base = _circle_to_response(circle)

    agents = []
    for agent in circle.agents.values():
        agents.append(AgentResponse(
            id=agent.id,
            name=agent.name,
            role=agent.model,  # Using model as role for AgentHandle
            provider=agent.provider,
            model=agent.model,
            status=AgentStatus.IDLE,
            competencies=list(agent.competencies),
            can_review=list(agent.can_review),
            current_task=None,
            created_at=datetime.now(timezone.utc),
            last_activity=None,
        ))

    pending = len([t for t in circle.tasks.values() if t.status == "pending"])
    completed = len([t for t in circle.tasks.values() if t.status == "completed"])
    failed = len([t for t in circle.tasks.values() if t.status == "failed"])
    conflicts = len(circle.facilitator.get_pending_conflicts())

    return CircleDetailResponse(
        id=base.id,
        name=base.name,
        status=base.status,
        agent_count=base.agent_count,
        task_count=base.task_count,
        active_tasks=base.active_tasks,
        require_review=base.require_review,
        auto_route=base.auto_route,
        created_at=base.created_at,
        started_at=base.started_at,
        agents=agents,
        pending_tasks=pending,
        completed_tasks=completed,
        failed_tasks=failed,
        conflicts=conflicts,
    )


def _task_to_response(task: CircleTask, circle: GatheringCircle) -> TaskResponse:
    """Convert CircleTask to TaskResponse."""
    status_map = {
        "pending": TaskStatus.PENDING,
        "assigned": TaskStatus.ASSIGNED,
        "in_progress": TaskStatus.IN_PROGRESS,
        "in_review": TaskStatus.IN_REVIEW,
        "completed": TaskStatus.COMPLETED,
        "failed": TaskStatus.FAILED,
    }

    assigned_name = None
    if task.assigned_agent_id:
        agent = circle.agents.get(task.assigned_agent_id)
        if agent:
            assigned_name = agent.name

    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        status=status_map.get(task.status, TaskStatus.PENDING),
        priority=task.priority,
        assigned_agent_id=task.assigned_agent_id,
        assigned_agent_name=assigned_name,
        reviewer_id=None,
        reviewer_name=None,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        result=task.result,
    )


# =============================================================================
# Circle CRUD
# =============================================================================


@router.get("", response_model=CircleListResponse)
async def list_circles(
    registry: CircleRegistry = Depends(get_circle_registry),
) -> CircleListResponse:
    """List all circles."""
    circles = registry.list_all()
    return CircleListResponse(
        circles=[_circle_to_response(c) for c in circles],
        total=len(circles),
    )


@router.post("", response_model=CircleDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_circle(
    data: CircleCreate,
    registry: CircleRegistry = Depends(get_circle_registry),
) -> CircleDetailResponse:
    """Create a new circle."""
    if registry.get(data.name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Circle '{data.name}' already exists",
        )

    circle = GatheringCircle(
        name=data.name,
        require_review=data.require_review,
        auto_route=data.auto_route,
    )

    registry.add(circle)
    return _circle_to_detail(circle)


@router.get("/{name}", response_model=CircleDetailResponse)
async def get_circle(
    name: str,
    registry: CircleRegistry = Depends(get_circle_registry),
) -> CircleDetailResponse:
    """Get circle details by name."""
    circle = registry.get(name)
    if not circle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circle '{name}' not found",
        )
    return _circle_to_detail(circle)


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_circle(
    name: str,
    registry: CircleRegistry = Depends(get_circle_registry),
):
    """Delete a circle."""
    circle = registry.get(name)
    if not circle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circle '{name}' not found",
        )

    if circle.status.value == "running":
        await circle.stop()

    registry.remove(name)


# =============================================================================
# Circle Lifecycle
# =============================================================================


@router.post("/{name}/start")
async def start_circle(
    name: str,
    registry: CircleRegistry = Depends(get_circle_registry),
):
    """Start a circle."""
    circle = registry.get(name)
    if not circle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circle '{name}' not found",
        )

    if circle.status.value == "running":
        return {"status": "already_running"}

    await circle.start()
    return {"status": "started"}


@router.post("/{name}/stop")
async def stop_circle(
    name: str,
    registry: CircleRegistry = Depends(get_circle_registry),
):
    """Stop a circle."""
    circle = registry.get(name)
    if not circle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circle '{name}' not found",
        )

    if circle.status.value == "stopped":
        return {"status": "already_stopped"}

    await circle.stop()
    return {"status": "stopped"}


# =============================================================================
# Circle Agents
# =============================================================================


@router.post("/{name}/agents")
async def add_agent_to_circle(
    name: str,
    agent_id: int,
    agent_name: str,
    provider: str = "anthropic",
    model: str = "claude-sonnet-4-20250514",
    competencies: str = "",  # Comma-separated
    can_review: str = "",  # Comma-separated
    registry: CircleRegistry = Depends(get_circle_registry),
):
    """Add an agent to a circle."""
    circle = registry.get(name)
    if not circle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circle '{name}' not found",
        )

    if agent_id in circle.agents:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent {agent_id} already in circle",
        )

    comp_list = [c.strip() for c in competencies.split(",") if c.strip()]
    review_list = [r.strip() for r in can_review.split(",") if r.strip()]

    handle = AgentHandle(
        id=agent_id,
        name=agent_name,
        provider=provider,
        model=model,
        competencies=comp_list,
        can_review=review_list,
    )

    circle.add_agent(handle)
    return {"status": "added", "agent_id": agent_id}


@router.delete("/{name}/agents/{agent_id}")
async def remove_agent_from_circle(
    name: str,
    agent_id: int,
    registry: CircleRegistry = Depends(get_circle_registry),
):
    """Remove an agent from a circle."""
    circle = registry.get(name)
    if not circle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circle '{name}' not found",
        )

    if agent_id not in circle.agents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not in circle",
        )

    circle.remove_agent(agent_id)
    return {"status": "removed", "agent_id": agent_id}


# =============================================================================
# Tasks
# =============================================================================


@router.get("/{name}/tasks", response_model=TaskListResponse)
async def list_tasks(
    name: str,
    status_filter: Optional[str] = None,
    registry: CircleRegistry = Depends(get_circle_registry),
) -> TaskListResponse:
    """List tasks in a circle."""
    circle = registry.get(name)
    if not circle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circle '{name}' not found",
        )

    tasks = list(circle.tasks.values())

    if status_filter:
        tasks = [t for t in tasks if t.status.value == status_filter]

    return TaskListResponse(
        tasks=[_task_to_response(t, circle) for t in tasks],
        total=len(tasks),
    )


@router.post("/{name}/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    name: str,
    data: TaskCreate,
    registry: CircleRegistry = Depends(get_circle_registry),
) -> TaskResponse:
    """Create a new task in a circle."""
    circle = registry.get(name)
    if not circle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circle '{name}' not found",
        )

    if circle.status.value != "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Circle must be running to create tasks",
        )

    task_id = await circle.create_task(
        title=data.title,
        description=data.description,
        required_competencies=data.required_competencies,
        priority=data.priority,
    )

    task = circle.tasks[task_id]
    return _task_to_response(task, circle)


@router.get("/{name}/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    name: str,
    task_id: int,
    registry: CircleRegistry = Depends(get_circle_registry),
) -> TaskResponse:
    """Get task details."""
    circle = registry.get(name)
    if not circle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circle '{name}' not found",
        )

    task = circle.tasks.get(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    return _task_to_response(task, circle)


@router.post("/{name}/tasks/{task_id}/submit", response_model=TaskResponse)
async def submit_task_result(
    name: str,
    task_id: int,
    data: TaskResultSubmit,
    registry: CircleRegistry = Depends(get_circle_registry),
) -> TaskResponse:
    """Submit task result."""
    circle = registry.get(name)
    if not circle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circle '{name}' not found",
        )

    task = circle.tasks.get(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    if task.status.value not in ("assigned", "in_progress"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task is in {task.status.value} status, cannot submit",
        )

    await circle.submit_work(
        task_id=task_id,
        agent_id=task.assigned_agent_id,
        result=data.result,
        files_modified=data.files_modified,
    )

    return _task_to_response(circle.tasks[task_id], circle)


@router.post("/{name}/tasks/{task_id}/approve")
async def approve_task(
    name: str,
    task_id: int,
    reviewer_id: int,
    comments: str = "",
    registry: CircleRegistry = Depends(get_circle_registry),
):
    """Approve a task in review."""
    circle = registry.get(name)
    if not circle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circle '{name}' not found",
        )

    task = circle.tasks.get(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    if task.status.value != "in_review":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task is in {task.status.value} status, not in review",
        )

    await circle.approve_task(
        task_id=task_id,
        reviewer_id=reviewer_id,
        comments=comments,
    )

    return {"status": "approved", "task_id": task_id}


@router.post("/{name}/tasks/{task_id}/reject")
async def reject_task(
    name: str,
    task_id: int,
    reviewer_id: int,
    reason: str,
    registry: CircleRegistry = Depends(get_circle_registry),
):
    """Reject a task in review."""
    circle = registry.get(name)
    if not circle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circle '{name}' not found",
        )

    task = circle.tasks.get(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    if task.status.value != "in_review":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task is in {task.status.value} status, not in review",
        )

    await circle.reject_task(
        task_id=task_id,
        reviewer_id=reviewer_id,
        reason=reason,
    )

    return {"status": "rejected", "task_id": task_id}


# =============================================================================
# Conflicts & Events
# =============================================================================


@router.get("/{name}/conflicts")
async def get_conflicts(
    name: str,
    registry: CircleRegistry = Depends(get_circle_registry),
):
    """Get active conflicts in the circle."""
    circle = registry.get(name)
    if not circle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circle '{name}' not found",
        )

    conflicts = []
    for i, conflict in enumerate(circle.facilitator.get_pending_conflicts()):
        conflicts.append({
            "id": i + 1,
            "type": conflict.type.value,
            "resource": conflict.resource,
            "agents": conflict.agent_ids,
            "detected_at": conflict.detected_at.isoformat(),
            "resolved": conflict.resolved,
        })

    return {"conflicts": conflicts, "total": len(conflicts)}


@router.get("/{name}/metrics")
async def get_circle_metrics(
    name: str,
    registry: CircleRegistry = Depends(get_circle_registry),
):
    """Get circle metrics including agent performance."""
    circle = registry.get(name)
    if not circle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circle '{name}' not found",
        )

    agent_metrics = []
    for agent_id, metrics in circle.facilitator.get_all_metrics().items():
        agent = circle.agents.get(agent_id)
        agent_metrics.append({
            "agent_id": agent_id,
            "agent_name": agent.name if agent else "Unknown",
            "tasks_completed": metrics.tasks_completed,
            "tasks_failed": metrics.tasks_failed,
            "current_workload": metrics.current_workload,
            "approval_rate": metrics.approval_rate,
            "average_quality_score": metrics.average_quality_score,
        })

    return {
        "agents": agent_metrics,
        "total_tasks": len(circle.tasks),
        "pending_tasks": len([t for t in circle.tasks.values() if t.status == "pending"]),
        "active_tasks": len([t for t in circle.tasks.values() if t.status in ("assigned", "in_progress", "in_review")]),
        "completed_tasks": len([t for t in circle.tasks.values() if t.status == "completed"]),
        "failed_tasks": len([t for t in circle.tasks.values() if t.status == "failed"]),
    }
