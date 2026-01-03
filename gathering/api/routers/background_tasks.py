"""
Background Tasks API endpoints.
Manages long-running autonomous agent tasks.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from gathering.api.dependencies import (
    get_database_service,
    get_agent_registry,
    DatabaseService,
    AgentRegistry,
)
from gathering.orchestration.background import (
    get_background_executor,
)


# =============================================================================
# Pydantic Schemas
# =============================================================================

class BackgroundTaskCreate(BaseModel):
    agent_id: int = Field(..., description="Agent to execute the task")
    goal: str = Field(..., description="What the task should accomplish")
    circle_id: Optional[int] = Field(None, description="Optional circle context")
    goal_context: Optional[dict] = Field(default_factory=dict, description="Additional context")
    max_steps: int = Field(50, ge=1, le=500, description="Maximum execution steps")
    timeout_seconds: int = Field(3600, ge=60, le=86400, description="Timeout in seconds (max 24h)")
    checkpoint_interval: int = Field(5, ge=1, le=50, description="Steps between checkpoints")


class BackgroundTaskResponse(BaseModel):
    id: int
    agent_id: int
    goal: str
    status: str
    circle_id: Optional[int] = None
    current_step: int = 0
    max_steps: int = 50
    progress_percent: int = 0
    progress_summary: Optional[str] = None
    last_action: Optional[str] = None
    error_message: Optional[str] = None
    total_llm_calls: int = 0
    total_tokens_used: int = 0
    total_tool_calls: int = 0
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: int = 0

    class Config:
        from_attributes = True


class TaskStepResponse(BaseModel):
    id: int
    task_id: int
    step_number: int
    action_type: str
    action_input: Optional[str] = None
    action_output: Optional[str] = None
    tool_name: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None
    tokens_input: int = 0
    tokens_output: int = 0
    duration_ms: int = 0
    created_at: Optional[str] = None


# =============================================================================
# Router
# =============================================================================

router = APIRouter(prefix="/background-tasks", tags=["background-tasks"])


def _serialize_row(row: dict) -> dict:
    """Convert database row to JSON-serializable dict."""
    result = {}
    for key, value in row.items():
        if hasattr(value, 'isoformat'):
            result[key] = value.isoformat()
        elif isinstance(value, (list, tuple)):
            result[key] = list(value) if value else []
        else:
            result[key] = value
    return result


@router.get("", response_model=dict)
async def list_background_tasks(
    status: Optional[str] = None,
    agent_id: Optional[int] = None,
    limit: int = 50,
    db: DatabaseService = Depends(get_database_service),
):
    """List all background tasks with optional filters."""
    # Build query
    sql = "SELECT * FROM public.background_tasks_dashboard WHERE 1=1"
    params = {}

    if status:
        sql += " AND status = %(status)s"
        params['status'] = status

    if agent_id:
        sql += " AND agent_id = %(agent_id)s"
        params['agent_id'] = agent_id

    sql += " ORDER BY created_at DESC LIMIT %(limit)s"
    params['limit'] = limit

    tasks = db.execute(sql, params)
    tasks = [_serialize_row(t) for t in tasks]

    # Count by status
    counts = db.execute("""
        SELECT status, COUNT(*) as count
        FROM circle.background_tasks
        GROUP BY status
    """)
    status_counts = {r['status']: r['count'] for r in counts}

    return {
        "tasks": tasks,
        "total": len(tasks),
        "counts": status_counts,
    }


@router.get("/{task_id}", response_model=dict)
async def get_background_task(
    task_id: int,
    db: DatabaseService = Depends(get_database_service),
):
    """Get details of a specific background task."""
    task = db.execute_one("""
        SELECT * FROM public.background_tasks_dashboard
        WHERE id = %(id)s
    """, {'id': task_id})

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return _serialize_row(task)


@router.post("", response_model=dict, status_code=201)
async def create_background_task(
    data: BackgroundTaskCreate,
    db: DatabaseService = Depends(get_database_service),
    agent_registry: AgentRegistry = Depends(get_agent_registry),
):
    """Create and start a new background task."""
    # Get agent from registry
    agent = agent_registry.get(data.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {data.agent_id} not found in registry")

    # Get executor
    executor = get_background_executor(db_service=db)

    try:
        task_id = await executor.start_task(
            agent=agent,
            goal=data.goal,
            circle_id=data.circle_id,
            goal_context=data.goal_context,
            max_steps=data.max_steps,
            timeout_seconds=data.timeout_seconds,
            checkpoint_interval=data.checkpoint_interval,
        )

        # Fetch created task
        task = db.execute_one("""
            SELECT * FROM public.background_tasks_dashboard
            WHERE id = %(id)s
        """, {'id': task_id})

        return _serialize_row(task)

    except RuntimeError as e:
        raise HTTPException(status_code=429, detail=str(e))


@router.post("/{task_id}/pause", response_model=dict)
async def pause_background_task(
    task_id: int,
    db: DatabaseService = Depends(get_database_service),
):
    """Pause a running background task."""
    executor = get_background_executor(db_service=db)
    success = await executor.pause_task(task_id)

    if not success:
        raise HTTPException(status_code=400, detail="Cannot pause task (not running or not found)")

    return {"status": "paused", "task_id": task_id}


@router.post("/{task_id}/resume", response_model=dict)
async def resume_background_task(
    task_id: int,
    db: DatabaseService = Depends(get_database_service),
    agent_registry: AgentRegistry = Depends(get_agent_registry),
):
    """Resume a paused background task."""
    # Get task to find agent_id
    task_row = db.execute_one("""
        SELECT agent_id FROM circle.background_tasks WHERE id = %(id)s
    """, {'id': task_id})

    if not task_row:
        raise HTTPException(status_code=404, detail="Task not found")

    # Get agent from registry
    agent = agent_registry.get(task_row['agent_id'])
    if not agent:
        raise HTTPException(
            status_code=400,
            detail=f"Agent {task_row['agent_id']} not found in registry. Cannot resume."
        )

    executor = get_background_executor(db_service=db)
    success = await executor.resume_task(task_id, agent)

    if not success:
        raise HTTPException(status_code=400, detail="Cannot resume task (not paused)")

    return {"status": "resumed", "task_id": task_id}


@router.post("/{task_id}/cancel", response_model=dict)
async def cancel_background_task(
    task_id: int,
    db: DatabaseService = Depends(get_database_service),
):
    """Cancel a background task."""
    executor = get_background_executor(db_service=db)
    success = await executor.cancel_task(task_id)

    if not success:
        raise HTTPException(status_code=400, detail="Cannot cancel task (already completed or not found)")

    return {"status": "cancelled", "task_id": task_id}


@router.get("/{task_id}/steps", response_model=dict)
async def get_task_steps(
    task_id: int,
    limit: int = 100,
    offset: int = 0,
    db: DatabaseService = Depends(get_database_service),
):
    """Get execution steps for a task."""
    # Verify task exists
    task = db.execute_one("""
        SELECT id FROM circle.background_tasks WHERE id = %(id)s
    """, {'id': task_id})

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    steps = db.execute("""
        SELECT * FROM circle.background_task_steps
        WHERE task_id = %(task_id)s
        ORDER BY step_number DESC
        LIMIT %(limit)s OFFSET %(offset)s
    """, {
        'task_id': task_id,
        'limit': limit,
        'offset': offset,
    })

    total = db.execute_one("""
        SELECT COUNT(*) as count FROM circle.background_task_steps
        WHERE task_id = %(task_id)s
    """, {'task_id': task_id})

    return {
        "steps": [_serialize_row(s) for s in steps],
        "total": total['count'] if total else 0,
        "task_id": task_id,
    }


@router.delete("/{task_id}", status_code=204)
async def delete_background_task(
    task_id: int,
    db: DatabaseService = Depends(get_database_service),
):
    """Delete a background task (must be completed, failed, or cancelled)."""
    # Check task status
    task = db.execute_one("""
        SELECT status FROM circle.background_tasks WHERE id = %(id)s
    """, {'id': task_id})

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task['status'] in ('pending', 'running', 'paused'):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete task in '{task['status']}' status. Cancel it first."
        )

    # Delete (cascades to steps)
    db.execute(
        "DELETE FROM circle.background_tasks WHERE id = %(id)s",
        {'id': task_id}
    )


# Export router
background_tasks_router = router
