"""
API router for Scheduled Actions.
Provides endpoints for managing cron-like schedules for agent tasks.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from gathering.api.dependencies import get_database_service, DatabaseService
from gathering.orchestration.scheduler import (
    get_scheduler,
    ScheduledAction,
    ScheduleType,
)

router = APIRouter(prefix="/scheduled-actions", tags=["scheduled-actions"])


# Request/Response models

class ScheduledActionCreate(BaseModel):
    """Create a scheduled action."""
    agent_id: int
    name: str
    goal: str
    schedule_type: str = Field(default="cron", description="cron, interval, once, or event")
    cron_expression: Optional[str] = Field(None, description="Cron expression (e.g., '0 9 * * MON-FRI')")
    interval_seconds: Optional[int] = Field(None, ge=60, description="Interval in seconds (min 60)")
    event_trigger: Optional[str] = Field(None, description="Event name to trigger on")
    circle_id: Optional[int] = None
    description: Optional[str] = None
    max_steps: int = 50
    timeout_seconds: int = 3600
    retry_on_failure: bool = True
    max_retries: int = 3
    retry_delay_seconds: int = 300
    allow_concurrent: bool = False
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    max_executions: Optional[int] = None
    tags: List[str] = []
    metadata: dict = {}
    next_run_at: Optional[datetime] = Field(None, description="For 'once' type: when to run")


class ScheduledActionUpdate(BaseModel):
    """Update a scheduled action."""
    name: Optional[str] = None
    description: Optional[str] = None
    goal: Optional[str] = None
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    max_steps: Optional[int] = None
    timeout_seconds: Optional[int] = None
    retry_on_failure: Optional[bool] = None
    max_retries: Optional[int] = None
    allow_concurrent: Optional[bool] = None
    end_date: Optional[datetime] = None
    max_executions: Optional[int] = None
    tags: Optional[List[str]] = None


class ScheduledActionResponse(BaseModel):
    """Scheduled action response."""
    id: int
    agent_id: int
    circle_id: Optional[int]
    name: str
    description: Optional[str]
    goal: str
    schedule_type: str
    cron_expression: Optional[str]
    interval_seconds: Optional[int]
    event_trigger: Optional[str]
    status: str
    max_steps: int
    timeout_seconds: int
    retry_on_failure: bool
    max_retries: int
    retry_delay_seconds: int
    allow_concurrent: bool
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    max_executions: Optional[int]
    execution_count: int
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    tags: List[str]
    created_at: datetime

    # Dashboard additions
    agent_name: Optional[str] = None
    circle_name: Optional[str] = None
    last_run_status: Optional[str] = None
    last_run_duration: Optional[int] = None
    successful_runs: int = 0
    failed_runs: int = 0


class ScheduledActionRunResponse(BaseModel):
    """Scheduled action run response."""
    id: int
    scheduled_action_id: int
    background_task_id: Optional[int]
    run_number: int
    triggered_at: datetime
    triggered_by: str
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    result_summary: Optional[str]
    error_message: Optional[str]
    retry_count: int
    duration_ms: int
    steps_executed: int


def _row_to_response(row: dict) -> ScheduledActionResponse:
    """Convert a database row to a response model."""
    return ScheduledActionResponse(
        id=row["id"],
        agent_id=row["agent_id"],
        circle_id=row.get("circle_id"),
        name=row["name"],
        description=row.get("description"),
        goal=row["goal"],
        schedule_type=row["schedule_type"],
        cron_expression=row.get("cron_expression"),
        interval_seconds=row.get("interval_seconds"),
        event_trigger=row.get("event_trigger"),
        status=row["status"],
        max_steps=row.get("max_steps", 50),
        timeout_seconds=row.get("timeout_seconds", 3600),
        retry_on_failure=row.get("retry_on_failure", True),
        max_retries=row.get("max_retries", 3),
        retry_delay_seconds=row.get("retry_delay_seconds", 300),
        allow_concurrent=row.get("allow_concurrent", False),
        start_date=row.get("start_date"),
        end_date=row.get("end_date"),
        max_executions=row.get("max_executions"),
        execution_count=row.get("execution_count", 0),
        last_run_at=row.get("last_run_at"),
        next_run_at=row.get("next_run_at"),
        tags=row.get("tags") or [],
        created_at=row["created_at"],
        agent_name=row.get("agent_name"),
        circle_name=row.get("circle_name"),
        last_run_status=row.get("last_run_status"),
        last_run_duration=row.get("last_run_duration"),
        successful_runs=row.get("successful_runs", 0),
        failed_runs=row.get("failed_runs", 0),
    )


# Endpoints

@router.get("", response_model=List[ScheduledActionResponse])
async def list_scheduled_actions(
    status: Optional[str] = Query(None, description="Filter by status"),
    agent_id: Optional[int] = Query(None, description="Filter by agent"),
    db: DatabaseService = Depends(get_database_service),
):
    """List all scheduled actions."""
    try:
        # Build query with filters
        query = "SELECT * FROM public.scheduled_actions_dashboard WHERE 1=1"
        params = {}

        if status:
            query += " AND status = %(status)s"
            params["status"] = status

        if agent_id:
            query += " AND agent_id = %(agent_id)s"
            params["agent_id"] = agent_id

        query += " ORDER BY created_at DESC"

        rows = db.execute(query, params) if params else db.execute(query)

        return [_row_to_response(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{action_id}", response_model=ScheduledActionResponse)
async def get_scheduled_action(
    action_id: int,
    db: DatabaseService = Depends(get_database_service),
):
    """Get a scheduled action by ID."""
    try:
        row = db.execute_one(
            "SELECT * FROM public.scheduled_actions_dashboard WHERE id = %(action_id)s",
            {"action_id": action_id},
        )

        if not row:
            raise HTTPException(status_code=404, detail="Scheduled action not found")

        return _row_to_response(row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=ScheduledActionResponse)
async def create_scheduled_action(
    data: ScheduledActionCreate,
    db: DatabaseService = Depends(get_database_service),
):
    """Create a new scheduled action."""
    # Validate schedule type configuration
    if data.schedule_type == "cron" and not data.cron_expression:
        raise HTTPException(status_code=400, detail="cron_expression required for cron schedule")
    if data.schedule_type == "interval" and not data.interval_seconds:
        raise HTTPException(status_code=400, detail="interval_seconds required for interval schedule")
    if data.schedule_type == "once" and not data.next_run_at:
        raise HTTPException(status_code=400, detail="next_run_at required for once schedule")
    if data.schedule_type == "event" and not data.event_trigger:
        raise HTTPException(status_code=400, detail="event_trigger required for event schedule")

    try:
        # Calculate initial next_run_at for cron/interval
        next_run = data.next_run_at
        if data.schedule_type == "cron" and data.cron_expression:
            from croniter import croniter
            cron = croniter(data.cron_expression, datetime.now(timezone.utc))
            next_run = cron.get_next(datetime)
        elif data.schedule_type == "interval" and data.interval_seconds:
            next_run = datetime.now(timezone.utc) + timedelta(seconds=data.interval_seconds)

        import json
        row = db.execute_one("""
            INSERT INTO circle.scheduled_actions
            (agent_id, circle_id, name, description, schedule_type,
             cron_expression, interval_seconds, event_trigger, goal,
             max_steps, timeout_seconds, retry_on_failure, max_retries,
             retry_delay_seconds, allow_concurrent, start_date, end_date,
             max_executions, next_run_at, tags, metadata)
            VALUES (%(agent_id)s, %(circle_id)s, %(name)s, %(description)s, %(schedule_type)s,
                    %(cron_expression)s, %(interval_seconds)s, %(event_trigger)s, %(goal)s,
                    %(max_steps)s, %(timeout_seconds)s, %(retry_on_failure)s, %(max_retries)s,
                    %(retry_delay_seconds)s, %(allow_concurrent)s, %(start_date)s, %(end_date)s,
                    %(max_executions)s, %(next_run_at)s, %(tags)s, %(metadata)s)
            RETURNING id, created_at
        """, {
            "agent_id": data.agent_id,
            "circle_id": data.circle_id,
            "name": data.name,
            "description": data.description,
            "schedule_type": data.schedule_type,
            "cron_expression": data.cron_expression,
            "interval_seconds": data.interval_seconds,
            "event_trigger": data.event_trigger,
            "goal": data.goal,
            "max_steps": data.max_steps,
            "timeout_seconds": data.timeout_seconds,
            "retry_on_failure": data.retry_on_failure,
            "max_retries": data.max_retries,
            "retry_delay_seconds": data.retry_delay_seconds,
            "allow_concurrent": data.allow_concurrent,
            "start_date": data.start_date,
            "end_date": data.end_date,
            "max_executions": data.max_executions,
            "next_run_at": next_run,
            "tags": data.tags,
            "metadata": json.dumps(data.metadata),
        })

        # Notify scheduler of new action
        scheduler = get_scheduler(db_service=db)
        action = ScheduledAction(
            id=row["id"],
            agent_id=data.agent_id,
            circle_id=data.circle_id,
            name=data.name,
            description=data.description,
            goal=data.goal,
            schedule_type=ScheduleType(data.schedule_type),
            cron_expression=data.cron_expression,
            interval_seconds=data.interval_seconds,
            event_trigger=data.event_trigger,
            max_steps=data.max_steps,
            timeout_seconds=data.timeout_seconds,
            retry_on_failure=data.retry_on_failure,
            max_retries=data.max_retries,
            retry_delay_seconds=data.retry_delay_seconds,
            allow_concurrent=data.allow_concurrent,
            start_date=data.start_date,
            end_date=data.end_date,
            max_executions=data.max_executions,
            next_run_at=next_run,
            tags=data.tags,
            metadata=data.metadata,
            created_at=row["created_at"],
        )
        # Add to scheduler's in-memory cache
        scheduler._actions[action.id] = action

        return ScheduledActionResponse(
            id=row["id"],
            agent_id=data.agent_id,
            circle_id=data.circle_id,
            name=data.name,
            description=data.description,
            goal=data.goal,
            schedule_type=data.schedule_type,
            cron_expression=data.cron_expression,
            interval_seconds=data.interval_seconds,
            event_trigger=data.event_trigger,
            status="active",
            max_steps=data.max_steps,
            timeout_seconds=data.timeout_seconds,
            retry_on_failure=data.retry_on_failure,
            max_retries=data.max_retries,
            retry_delay_seconds=data.retry_delay_seconds,
            allow_concurrent=data.allow_concurrent,
            start_date=data.start_date,
            end_date=data.end_date,
            max_executions=data.max_executions,
            execution_count=0,
            last_run_at=None,
            next_run_at=next_run,
            tags=data.tags,
            created_at=row["created_at"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{action_id}", response_model=ScheduledActionResponse)
async def update_scheduled_action(
    action_id: int,
    data: ScheduledActionUpdate,
    db: DatabaseService = Depends(get_database_service),
):
    """Update a scheduled action."""
    try:
        updates = data.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")

        # Build dynamic update query
        set_clauses = []
        params = {"action_id": action_id}
        for key, value in updates.items():
            set_clauses.append(f"{key} = %({key})s")
            params[key] = value

        query = f"""
            UPDATE circle.scheduled_actions
            SET {', '.join(set_clauses)}, updated_at = NOW()
            WHERE id = %(action_id)s
        """
        db.execute(query, params)

        # Update scheduler cache
        scheduler = get_scheduler(db_service=db)
        scheduler.update_action(action_id, updates)

        return await get_scheduled_action(action_id, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{action_id}/pause")
async def pause_scheduled_action(
    action_id: int,
    db: DatabaseService = Depends(get_database_service),
):
    """Pause a scheduled action."""
    try:
        # Check if action exists and is active
        row = db.execute_one(
            "SELECT id FROM circle.scheduled_actions WHERE id = %(action_id)s AND status = 'active'",
            {"action_id": action_id},
        )
        if not row:
            raise HTTPException(status_code=404, detail="Action not found or not active")

        db.execute(
            "UPDATE circle.scheduled_actions SET status = 'paused', updated_at = NOW() WHERE id = %(action_id)s",
            {"action_id": action_id},
        )

        scheduler = get_scheduler(db_service=db)
        scheduler.pause_action(action_id)

        return {"status": "paused", "action_id": action_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{action_id}/resume")
async def resume_scheduled_action(
    action_id: int,
    db: DatabaseService = Depends(get_database_service),
):
    """Resume a paused scheduled action."""
    try:
        # Check if action exists and is paused
        row = db.execute_one(
            "SELECT id FROM circle.scheduled_actions WHERE id = %(action_id)s AND status = 'paused'",
            {"action_id": action_id},
        )
        if not row:
            raise HTTPException(status_code=404, detail="Action not found or not paused")

        db.execute(
            "UPDATE circle.scheduled_actions SET status = 'active', updated_at = NOW() WHERE id = %(action_id)s",
            {"action_id": action_id},
        )

        scheduler = get_scheduler(db_service=db)
        scheduler.resume_action(action_id)

        return {"status": "active", "action_id": action_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{action_id}/trigger")
async def trigger_scheduled_action(
    action_id: int,
    db: DatabaseService = Depends(get_database_service),
):
    """Manually trigger a scheduled action to run now."""
    try:
        scheduler = get_scheduler(db_service=db)
        success = scheduler.trigger_now(action_id)

        if not success:
            raise HTTPException(status_code=404, detail="Action not found")

        return {"status": "triggered", "action_id": action_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{action_id}")
async def delete_scheduled_action(
    action_id: int,
    db: DatabaseService = Depends(get_database_service),
):
    """Delete a scheduled action."""
    try:
        # Check if action exists
        row = db.execute_one(
            "SELECT id FROM circle.scheduled_actions WHERE id = %(action_id)s",
            {"action_id": action_id},
        )
        if not row:
            raise HTTPException(status_code=404, detail="Action not found")

        db.execute(
            "DELETE FROM circle.scheduled_actions WHERE id = %(action_id)s",
            {"action_id": action_id},
        )

        scheduler = get_scheduler(db_service=db)
        scheduler.delete_action(action_id)

        return {"status": "deleted", "action_id": action_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{action_id}/runs", response_model=List[ScheduledActionRunResponse])
async def get_scheduled_action_runs(
    action_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: DatabaseService = Depends(get_database_service),
):
    """Get execution history for a scheduled action."""
    try:
        rows = db.execute("""
            SELECT * FROM circle.scheduled_action_runs
            WHERE scheduled_action_id = %(action_id)s
            ORDER BY triggered_at DESC
            LIMIT %(limit)s OFFSET %(offset)s
        """, {"action_id": action_id, "limit": limit, "offset": offset})

        return [
            ScheduledActionRunResponse(
                id=row["id"],
                scheduled_action_id=row["scheduled_action_id"],
                background_task_id=row.get("background_task_id"),
                run_number=row["run_number"],
                triggered_at=row["triggered_at"],
                triggered_by=row.get("triggered_by", "scheduler"),
                status=row["status"],
                started_at=row.get("started_at"),
                completed_at=row.get("completed_at"),
                result_summary=row.get("result_summary"),
                error_message=row.get("error_message"),
                retry_count=row.get("retry_count", 0),
                duration_ms=row.get("duration_ms", 0),
                steps_executed=row.get("steps_executed", 0),
            )
            for row in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
