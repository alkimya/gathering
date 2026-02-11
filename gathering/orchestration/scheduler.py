"""
Scheduled Actions for GatheRing.
Enables cron-like scheduling for agent task execution.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set

from croniter import croniter

from gathering.orchestration.events import EventBus, EventType
from gathering.orchestration.background import (
    BackgroundTaskStatus,
    get_background_executor,
)

logger = logging.getLogger(__name__)

# Advisory lock namespace to prevent collision with other advisory lock users.
# pg_try_advisory_xact_lock(namespace, key) uses two int4 values.
SCHEDULER_LOCK_NAMESPACE = 1


class ScheduleType(Enum):
    """Type of schedule."""
    CRON = "cron"
    INTERVAL = "interval"
    ONCE = "once"
    EVENT = "event"


class ScheduledActionStatus(Enum):
    """Status of a scheduled action."""
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    EXPIRED = "expired"


@dataclass
class ScheduledAction:
    """Represents a scheduled action for an agent."""
    id: int
    agent_id: int
    name: str
    goal: str = ""
    schedule_type: ScheduleType = ScheduleType.CRON
    status: ScheduledActionStatus = ScheduledActionStatus.ACTIVE

    # Action dispatch
    action_type: str = "run_task"
    action_config: Dict[str, Any] = field(default_factory=dict)

    # Schedule configuration
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    event_trigger: Optional[str] = None

    # Optional circle
    circle_id: Optional[int] = None

    # Execution config
    max_steps: int = 50
    timeout_seconds: int = 3600
    retry_on_failure: bool = True
    max_retries: int = 3
    retry_delay_seconds: int = 300
    allow_concurrent: bool = False

    # Limits
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    max_executions: Optional[int] = None
    execution_count: int = 0

    # Tracking
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None

    # Metadata
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def calculate_next_run(self, from_time: Optional[datetime] = None) -> Optional[datetime]:
        """Calculate the next run time based on schedule type."""
        now = from_time or datetime.now(timezone.utc)

        if self.schedule_type == ScheduleType.CRON and self.cron_expression:
            try:
                cron = croniter(self.cron_expression, now)
                return cron.get_next(datetime)
            except Exception as e:
                logger.error(f"Invalid cron expression '{self.cron_expression}': {e}")
                return None

        elif self.schedule_type == ScheduleType.INTERVAL and self.interval_seconds:
            base = self.last_run_at or now
            return base + timedelta(seconds=self.interval_seconds)

        elif self.schedule_type == ScheduleType.ONCE:
            # next_run_at is set at creation time
            return self.next_run_at if self.next_run_at and self.next_run_at > now else None

        elif self.schedule_type == ScheduleType.EVENT:
            # Event-triggered, no scheduled time
            return None

        return None

    def should_run(self, now: Optional[datetime] = None) -> bool:
        """Check if this action should run now."""
        now = now or datetime.now(timezone.utc)

        # Check status
        if self.status != ScheduledActionStatus.ACTIVE:
            return False

        # Check date bounds
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False

        # Check execution limit
        if self.max_executions and self.execution_count >= self.max_executions:
            return False

        # Check scheduled time
        if self.schedule_type == ScheduleType.EVENT:
            return False  # Event-triggered only

        if self.next_run_at and now >= self.next_run_at:
            return True

        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "circle_id": self.circle_id,
            "name": self.name,
            "description": self.description,
            "goal": self.goal,
            "action_type": self.action_type,
            "action_config": self.action_config,
            "schedule_type": self.schedule_type.value,
            "cron_expression": self.cron_expression,
            "interval_seconds": self.interval_seconds,
            "event_trigger": self.event_trigger,
            "status": self.status.value,
            "max_steps": self.max_steps,
            "timeout_seconds": self.timeout_seconds,
            "retry_on_failure": self.retry_on_failure,
            "max_retries": self.max_retries,
            "retry_delay_seconds": self.retry_delay_seconds,
            "allow_concurrent": self.allow_concurrent,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "max_executions": self.max_executions,
            "execution_count": self.execution_count,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ScheduledActionRun:
    """Record of a scheduled action execution."""
    id: int
    scheduled_action_id: int
    background_task_id: Optional[int] = None
    run_number: int = 1
    triggered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    triggered_by: str = "scheduler"
    status: BackgroundTaskStatus = BackgroundTaskStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result_summary: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    duration_ms: int = 0
    steps_executed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "scheduled_action_id": self.scheduled_action_id,
            "background_task_id": self.background_task_id,
            "run_number": self.run_number,
            "triggered_at": self.triggered_at.isoformat(),
            "triggered_by": self.triggered_by,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result_summary": self.result_summary,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "duration_ms": self.duration_ms,
            "steps_executed": self.steps_executed,
        }


# ---------------------------------------------------------------------------
# Action type dispatchers
# ---------------------------------------------------------------------------
# Module-level async functions that handle each action_type.
# Dispatcher signature: async (action: ScheduledAction, context: dict) -> dict
# context contains: {"db": DatabaseService, "event_bus": EventBus}


async def _dispatch_run_task(
    action: ScheduledAction, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Dispatch run_task action via BackgroundTaskExecutor + AgentWrapper.

    This is the original scheduler behavior, extracted into a dispatcher.
    """
    db_service = context.get("db")

    executor = get_background_executor(db_service=db_service)

    from gathering.agents.wrapper import AgentWrapper
    agent = AgentWrapper(
        agent_id=action.agent_id,
        name=f"scheduled-{action.id}",
    )

    # Use goal from action_config if available, fall back to action.goal
    goal = action.action_config.get("goal", action.goal) or action.goal

    task_id = await executor.start_task(
        goal=goal,
        agent=agent,
        max_steps=action.action_config.get("max_steps", action.max_steps),
        timeout=timedelta(
            seconds=action.action_config.get("timeout_seconds", action.timeout_seconds)
        ),
        metadata={
            "scheduled_action_id": action.id,
            "action_type": "run_task",
        },
    )

    return {"task_id": task_id, "action_type": "run_task"}


async def _dispatch_execute_pipeline(
    action: ScheduledAction, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Dispatch execute_pipeline action via PipelineExecutor."""
    from gathering.orchestration.pipeline.executor import PipelineExecutor, PipelineRunManager
    from gathering.orchestration.pipeline.models import PipelineDefinition

    db_service = context.get("db")
    event_bus = context.get("event_bus")

    pipeline_id = action.action_config.get("pipeline_id") or action.metadata.get("pipeline_id")
    if not pipeline_id:
        return {"error": "No pipeline_id in action_config", "action_type": "execute_pipeline"}

    # Load pipeline definition from DB
    if not db_service:
        return {"error": "No database service available", "action_type": "execute_pipeline"}

    try:
        row = db_service.execute_one(
            """
            SELECT id, name, definition
            FROM circle.pipelines
            WHERE id = %(pipeline_id)s
            """,
            {"pipeline_id": int(pipeline_id)},
        )
    except Exception as e:
        logger.error("Failed to load pipeline %s: %s", pipeline_id, e)
        return {"error": f"Failed to load pipeline: {e}", "action_type": "execute_pipeline"}

    if not row:
        return {"error": f"Pipeline {pipeline_id} not found", "action_type": "execute_pipeline"}

    # Parse definition
    definition_data = row.get("definition", {})
    if isinstance(definition_data, str):
        definition_data = json.loads(definition_data)
    definition = PipelineDefinition(**definition_data)

    # Create a run record for the pipeline
    try:
        run_row = db_service.execute_one(
            """
            INSERT INTO circle.pipeline_runs (pipeline_id, status, trigger_data)
            VALUES (%(pipeline_id)s, 'running', %(trigger_data)s::jsonb)
            RETURNING id
            """,
            {
                "pipeline_id": int(pipeline_id),
                "trigger_data": json.dumps(action.action_config),
            },
        )
        run_id = run_row["id"] if run_row else 0
    except Exception as e:
        logger.warning("Failed to create pipeline run record: %s", e)
        run_id = 0

    executor = PipelineExecutor(
        pipeline_id=int(pipeline_id),
        definition=definition,
        db=db_service,
        event_bus=event_bus,
    )

    try:
        result = await executor.execute(
            run_id=run_id,
            trigger_data=action.action_config,
        )
    except Exception as e:
        logger.error("Pipeline %s execution failed: %s", pipeline_id, e)
        return {"error": str(e), "action_type": "execute_pipeline", "pipeline_id": pipeline_id}

    return {
        "action_type": "execute_pipeline",
        "pipeline_id": pipeline_id,
        "run_id": run_id,
        "status": result.get("status", "unknown"),
    }


async def _dispatch_send_notification(
    action: ScheduledAction, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Dispatch send_notification action via NotificationsSkill."""
    try:
        from gathering.skills.notifications.sender import NotificationsSkill
    except ImportError:
        logger.warning("NotificationsSkill not available, cannot dispatch send_notification")
        return {"error": "NotificationsSkill not loadable", "action_type": "send_notification"}

    try:
        skill = NotificationsSkill(config=action.action_config.get("skill_config"))
        tool_name = action.action_config.get("tool_name", "notify_webhook")
        tool_input = action.action_config.get("tool_input", action.action_config)
        result = skill.execute(tool_name, tool_input)
        logger.info(
            "Notification dispatched for action %s: %s",
            action.id,
            getattr(result, "message", str(result)),
        )
        # SkillResponse has .success and .message attributes
        if hasattr(result, "success"):
            return {
                "action_type": "send_notification",
                "success": result.success,
                "message": result.message,
            }
        return {"action_type": "send_notification", "result": str(result)}
    except Exception as e:
        logger.error("send_notification failed for action %s: %s", action.id, e)
        return {"error": str(e), "action_type": "send_notification"}


async def _dispatch_call_api(
    action: ScheduledAction, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Dispatch call_api action via HTTPSkill."""
    try:
        from gathering.skills.http.client import HTTPSkill
    except ImportError:
        logger.warning("HTTPSkill not available, cannot dispatch call_api")
        return {"error": "HTTPSkill not loadable", "action_type": "call_api"}

    try:
        skill = HTTPSkill()
        tool_name = action.action_config.get("tool_name", "http_get")
        tool_input = action.action_config.get("tool_input", action.action_config)
        result = skill.execute(tool_name, tool_input)
        logger.info("API call dispatched for action %s", action.id)
        if isinstance(result, dict):
            return {"action_type": "call_api", **result}
        return {"action_type": "call_api", "result": str(result)}
    except Exception as e:
        logger.error("call_api failed for action %s: %s", action.id, e)
        return {"error": str(e), "action_type": "call_api"}


# Dispatch table mapping action_type strings to async handler functions
ACTION_DISPATCHERS: Dict[str, Callable[..., Coroutine]] = {
    "run_task": _dispatch_run_task,
    "execute_pipeline": _dispatch_execute_pipeline,
    "send_notification": _dispatch_send_notification,
    "call_api": _dispatch_call_api,
}


class Scheduler:
    """
    Scheduler for running scheduled actions.

    Features:
    - Cron-based scheduling
    - Interval-based scheduling
    - One-time scheduled execution
    - Event-triggered execution
    - Concurrent execution control
    - Retry on failure
    - Crash recovery with deduplication
    """

    def __init__(
        self,
        db_service: Any = None,
        event_bus: Optional[EventBus] = None,
        check_interval: int = 60,
        async_db: Optional[Any] = None,
    ):
        """
        Initialize the scheduler.

        Args:
            db_service: Database service for persistence
            event_bus: Event bus for publishing events
            check_interval: How often to check for due actions (seconds)
            async_db: Optional AsyncDatabaseService for advisory lock coordination.
                      When provided, enables multi-instance coordination via
                      PostgreSQL advisory locks. When None (default), single-instance
                      mode -- all locks are implicitly acquired.
        """
        self.db_service = db_service
        self.event_bus = event_bus or EventBus()
        self.check_interval = check_interval
        self._async_db = async_db

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._actions: Dict[int, ScheduledAction] = {}
        self._running_actions: Set[int] = set()  # Actions currently executing
        self._event_subscriptions: Dict[str, Set[int]] = {}  # event_name -> action_ids
        self._lock = asyncio.Lock()

        # Subscribe to events for event-triggered actions
        self._setup_event_handlers()

    def _setup_event_handlers(self):
        """Setup handlers for event-triggered schedules."""
        # We'll subscribe to all events and filter by event_trigger
        async def handle_event(event: Dict[str, Any]):
            event_type = event.get("type")
            if event_type:
                await self._trigger_event_actions(event_type, event)

        self.event_bus.subscribe("*", handle_event)

    async def _trigger_event_actions(self, event_type: str, event_data: Dict[str, Any]):
        """Trigger actions that listen for this event."""
        action_ids = self._event_subscriptions.get(event_type, set())
        for action_id in action_ids:
            action = self._actions.get(action_id)
            if action and action.status == ScheduledActionStatus.ACTIVE:
                await self._execute_action(action, triggered_by="event")

    async def start(self):
        """Start the scheduler."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        await self._load_actions()
        await self._recover_missed_runs()
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Scheduler started")

        await self.event_bus.emit(EventType.SCHEDULED_ACTION_SCHEDULER_STARTED, {
            "action_count": len(self._actions),
        })

    async def stop(self, timeout: int = 30):
        """Stop the scheduler gracefully."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await asyncio.wait_for(self._task, timeout=timeout)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

        logger.info("Scheduler stopped")
        await self.event_bus.emit(EventType.SCHEDULED_ACTION_SCHEDULER_STOPPED, {})

    async def _load_actions(self):
        """Load active scheduled actions from database."""
        if not self.db_service:
            logger.warning("No database service, skipping action load")
            return

        try:
            # Use sync picopg interface
            rows = self.db_service.execute("""
                SELECT * FROM circle.scheduled_actions
                WHERE status IN ('active', 'paused')
            """)

            async with self._lock:
                for row in rows:
                    action = self._row_to_action(row)
                    self._actions[action.id] = action

                    # Register event triggers
                    if action.schedule_type == ScheduleType.EVENT and action.event_trigger:
                        if action.event_trigger not in self._event_subscriptions:
                            self._event_subscriptions[action.event_trigger] = set()
                        self._event_subscriptions[action.event_trigger].add(action.id)

            logger.info(f"Loaded {len(self._actions)} scheduled actions")
        except Exception as e:
            logger.error(f"Failed to load scheduled actions: {e}")

    def _row_to_action(self, row) -> ScheduledAction:
        """Convert database row to ScheduledAction.

        Handles both the current DB schema (action_type, action_config) and
        legacy rows that may only have goal/metadata fields.
        """
        # Read action_config -- may be a dict (from JSONB) or a string
        raw_config = row.get("action_config", {})
        if isinstance(raw_config, str):
            try:
                raw_config = json.loads(raw_config)
            except (json.JSONDecodeError, TypeError):
                raw_config = {}
        if raw_config is None:
            raw_config = {}

        return ScheduledAction(
            id=row["id"],
            agent_id=row["agent_id"],
            circle_id=row.get("circle_id"),
            name=row["name"],
            description=row.get("description"),
            goal=row.get("goal", ""),
            action_type=row.get("action_type", "run_task"),
            action_config=raw_config,
            schedule_type=ScheduleType(row["schedule_type"]),
            cron_expression=row.get("cron_expression"),
            interval_seconds=row.get("interval_seconds"),
            event_trigger=row.get("event_trigger"),
            status=ScheduledActionStatus(row["status"]),
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
            tags=row.get("tags", []),
            metadata=row.get("metadata", {}),
            created_at=row.get("created_at", datetime.now(timezone.utc)),
        )

    async def _recover_missed_runs(self):
        """Detect and recover missed runs after crash/restart.

        For each ACTIVE action whose next_run_at is in the past:
        - Check scheduled_action_runs for an existing run in the missed window.
        - If a run exists (completed/running/pending), skip and advance next_run_at.
        - If no run exists, execute as a recovery run.

        Wrapped in try/except to never prevent scheduler startup.
        """
        try:
            now = datetime.now(timezone.utc)
            for action in list(self._actions.values()):
                if action.status != ScheduledActionStatus.ACTIVE:
                    continue
                if not action.next_run_at or action.next_run_at >= now:
                    continue

                # Check for existing runs in the missed window
                has_existing_run = False
                if self.db_service:
                    try:
                        window_start = action.next_run_at - timedelta(seconds=60)
                        rows = self.db_service.execute(
                            """
                            SELECT id FROM circle.scheduled_action_runs
                            WHERE scheduled_action_id = %(action_id)s
                              AND triggered_at >= %(window_start)s
                              AND status IN ('completed', 'running', 'pending')
                            LIMIT 1
                            """,
                            {
                                "action_id": action.id,
                                "window_start": window_start,
                            },
                        )
                        has_existing_run = bool(rows)
                    except Exception as e:
                        logger.warning(
                            "Failed to check missed runs for action %s: %s",
                            action.id, e,
                        )

                if has_existing_run:
                    logger.info(
                        "Action %s already has run for missed window, skipping",
                        action.id,
                    )
                    action.next_run_at = action.calculate_next_run()
                    await self._persist_action(action)
                else:
                    logger.info(
                        "Action %s missed, executing recovery run",
                        action.id,
                    )
                    await self._execute_action(action, triggered_by="recovery")
        except Exception as e:
            logger.error("Crash recovery failed (non-fatal): %s", e)

    async def _run_loop(self):
        """Main scheduler loop."""
        while self._running:
            try:
                await self._check_and_execute_due_actions()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(self.check_interval)

    async def _check_and_execute_due_actions(self):
        """Check for due actions and execute them."""
        now = datetime.now(timezone.utc)

        async with self._lock:
            for action in list(self._actions.values()):
                if action.should_run(now):
                    # Check concurrent execution
                    if not action.allow_concurrent and action.id in self._running_actions:
                        logger.debug(f"Action {action.id} already running, skipping")
                        continue

                    # Add to running set BEFORE creating the task to prevent
                    # race condition where duplicate tasks could be created
                    # between the check above and _execute_action's lock acquisition.
                    self._running_actions.add(action.id)
                    asyncio.create_task(self._execute_action(action))

    async def _try_acquire_action_lock(self, action_id: int) -> bool:
        """Try to acquire a transaction-scoped advisory lock for a scheduled action.

        Uses pg_try_advisory_xact_lock(namespace, action_id) which:
        - Returns True if lock acquired, False if another session holds it
        - Auto-releases on transaction COMMIT/ROLLBACK (no leaked locks)
        - Is non-blocking (returns immediately, never waits)

        Returns True (proceed) if:
        - Lock acquired successfully
        - No async_db available (single-instance mode, always proceed)

        Returns False (skip) if:
        - Another instance holds the lock
        - DB error during lock attempt (fail-closed for safety)
        """
        if self._async_db is None:
            return True

        try:
            async with self._async_db._pool.connection() as conn:
                async with conn.transaction():
                    cur = await conn.execute(
                        "SELECT pg_try_advisory_xact_lock(%s, %s) AS acquired",
                        [SCHEDULER_LOCK_NAMESPACE, action_id],
                    )
                    row = await cur.fetchone()
                    if row is None:
                        logger.warning(
                            "Advisory lock query returned no rows for action %s, skipping",
                            action_id,
                        )
                        return False
                    return row[0]
        except Exception:
            logger.warning(
                "Failed to acquire advisory lock for action %s, skipping (fail-closed)",
                action_id,
                exc_info=True,
            )
            return False

    async def _execute_action(self, action: ScheduledAction, triggered_by: str = "scheduler"):
        """Execute a scheduled action using the dispatch table."""
        action_id = action.id

        # Advisory lock gate: in multi-instance mode, only one instance
        # should execute each action. Check before any other logic.
        lock_acquired = await self._try_acquire_action_lock(action_id)
        if not lock_acquired:
            logger.debug("Action %s locked by another instance, skipping", action_id)
            # Remove from _running_actions since we won't execute
            async with self._lock:
                self._running_actions.discard(action_id)
            return

        async with self._lock:
            if not action.allow_concurrent and action_id in self._running_actions:
                # Already marked by _check_and_execute_due_actions -- skip double-check
                # unless this was called from outside the check loop (event, manual, recovery)
                pass
            else:
                self._running_actions.add(action_id)

        try:
            logger.info(f"Executing scheduled action {action_id}: {action.name}")

            # Create run record
            run = await self._create_run_record(action, triggered_by)

            # Publish event
            await self.event_bus.emit(EventType.SCHEDULED_ACTION_TRIGGERED, {
                "action_id": action_id,
                "action_name": action.name,
                "run_id": run.id if run else None,
                "triggered_by": triggered_by,
            })

            # Determine action type and dispatch
            action_type = action.action_type or "run_task"
            handler = ACTION_DISPATCHERS.get(action_type)

            if handler is None:
                error_msg = f"Unknown action_type '{action_type}' for action {action_id}"
                logger.error(error_msg)
                await self.event_bus.emit(EventType.SCHEDULED_ACTION_FAILED, {
                    "action_id": action_id,
                    "error": error_msg,
                })
                return

            # Build context for dispatcher
            dispatch_context = {
                "db": self.db_service,
                "event_bus": self.event_bus,
            }

            result = await handler(action, dispatch_context)

            # Update run with result info
            if run and result:
                task_id = result.get("task_id")
                if task_id:
                    await self._update_run_task(run.id, task_id)

            # Update action's next run time
            action.last_run_at = datetime.now(timezone.utc)
            action.next_run_at = action.calculate_next_run()
            action.execution_count += 1
            await self._persist_action(action)

            await self.event_bus.emit(EventType.SCHEDULED_ACTION_STARTED, {
                "action_id": action_id,
                "action_type": action_type,
                "run_id": run.id if run else None,
                "result": result,
            })

        except Exception as e:
            logger.error(f"Failed to execute action {action_id}: {e}")
            await self.event_bus.emit(EventType.SCHEDULED_ACTION_FAILED, {
                "action_id": action_id,
                "error": str(e),
            })

            # Handle retry logic
            if action.retry_on_failure:
                await self._schedule_retry(action)

        finally:
            async with self._lock:
                self._running_actions.discard(action_id)

    async def _create_run_record(
        self, action: ScheduledAction, triggered_by: str
    ) -> Optional[ScheduledActionRun]:
        """Create a run record in the database."""
        if not self.db_service:
            return None

        try:
            # Use sync picopg interface with named params
            row = self.db_service.execute_one("""
                INSERT INTO circle.scheduled_action_runs
                (scheduled_action_id, run_number, triggered_by, status)
                VALUES (%(action_id)s, %(run_number)s, %(triggered_by)s, 'pending')
                RETURNING *
            """, {
                'action_id': action.id,
                'run_number': action.execution_count + 1,
                'triggered_by': triggered_by,
            })

            if row:
                return ScheduledActionRun(
                    id=row["id"],
                    scheduled_action_id=row["scheduled_action_id"],
                    run_number=row["run_number"],
                    triggered_by=row["triggered_by"],
                    triggered_at=row["triggered_at"],
                )
            return None
        except Exception as e:
            logger.error(f"Failed to create run record: {e}")
            return None

    async def _update_run_task(self, run_id: int, task_id: int):
        """Update run record with background task ID."""
        if not self.db_service:
            return

        try:
            self.db_service.execute("""
                UPDATE circle.scheduled_action_runs
                SET background_task_id = %(task_id)s, status = 'running', started_at = NOW()
                WHERE id = %(run_id)s
            """, {'task_id': task_id, 'run_id': run_id})
        except Exception as e:
            logger.error(f"Failed to update run task: {e}")

    async def _persist_action(self, action: ScheduledAction):
        """Persist action state to database."""
        if not self.db_service:
            return

        try:
            self.db_service.execute("""
                UPDATE circle.scheduled_actions
                SET
                    execution_count = %(execution_count)s,
                    last_run_at = %(last_run_at)s,
                    next_run_at = %(next_run_at)s,
                    status = %(status)s,
                    updated_at = NOW()
                WHERE id = %(id)s
            """, {
                'execution_count': action.execution_count,
                'last_run_at': action.last_run_at,
                'next_run_at': action.next_run_at,
                'status': action.status.value,
                'id': action.id,
            })
        except Exception as e:
            logger.error(f"Failed to persist action: {e}")

    async def _schedule_retry(self, action: ScheduledAction):
        """Schedule a retry for a failed action."""
        # Simple retry: schedule for retry_delay_seconds from now
        action.next_run_at = datetime.now(timezone.utc) + timedelta(
            seconds=action.retry_delay_seconds
        )
        await self._persist_action(action)

    # Public API

    async def add_action(self, action: ScheduledAction) -> int:
        """Add a new scheduled action."""
        # Calculate initial next_run
        if action.schedule_type != ScheduleType.EVENT:
            action.next_run_at = action.calculate_next_run()

        # Persist to database
        if self.db_service:
            action.id = await self._insert_action(action)

        async with self._lock:
            self._actions[action.id] = action

            # Register event trigger
            if action.schedule_type == ScheduleType.EVENT and action.event_trigger:
                if action.event_trigger not in self._event_subscriptions:
                    self._event_subscriptions[action.event_trigger] = set()
                self._event_subscriptions[action.event_trigger].add(action.id)

        await self.event_bus.emit(EventType.SCHEDULED_ACTION_CREATED, {
            "action_id": action.id,
            "action_name": action.name,
            "schedule_type": action.schedule_type.value,
        })

        return action.id

    async def _insert_action(self, action: ScheduledAction) -> int:
        """Insert action into database."""
        row = self.db_service.execute_one("""
            INSERT INTO circle.scheduled_actions
            (agent_id, circle_id, name, description, action_type, action_config,
             schedule_type, cron_expression, interval_seconds,
             retry_on_failure, max_retries, retry_delay_seconds,
             max_executions, next_run_at)
            VALUES (%(agent_id)s, %(circle_id)s, %(name)s, %(description)s,
                    %(action_type)s, %(action_config)s::jsonb,
                    %(schedule_type)s, %(cron_expression)s, %(interval_seconds)s,
                    %(retry_on_failure)s, %(max_retries)s, %(retry_delay_seconds)s,
                    %(max_executions)s, %(next_run_at)s)
            RETURNING id
        """, {
            'agent_id': action.agent_id,
            'circle_id': action.circle_id,
            'name': action.name,
            'description': action.description,
            'action_type': action.action_type,
            'action_config': json.dumps(action.action_config) if action.action_config else '{}',
            'schedule_type': action.schedule_type.value,
            'cron_expression': action.cron_expression,
            'interval_seconds': action.interval_seconds,
            'retry_on_failure': action.retry_on_failure,
            'max_retries': action.max_retries,
            'retry_delay_seconds': action.retry_delay_seconds,
            'max_executions': action.max_executions,
            'next_run_at': action.next_run_at,
        })
        return row["id"]

    async def update_action(self, action_id: int, updates: Dict[str, Any]) -> bool:
        """Update a scheduled action."""
        async with self._lock:
            action = self._actions.get(action_id)
            if not action:
                return False

            for key, value in updates.items():
                if hasattr(action, key):
                    setattr(action, key, value)

            # Recalculate next_run if schedule changed
            if any(k in updates for k in ["cron_expression", "interval_seconds", "schedule_type"]):
                action.next_run_at = action.calculate_next_run()

        await self._persist_action(action)
        await self.event_bus.emit(EventType.SCHEDULED_ACTION_UPDATED, {
            "action_id": action_id,
            "updates": list(updates.keys()),
        })

        return True

    async def pause_action(self, action_id: int) -> bool:
        """Pause a scheduled action."""
        async with self._lock:
            action = self._actions.get(action_id)
            if not action:
                return False
            action.status = ScheduledActionStatus.PAUSED

        await self._persist_action(action)
        await self.event_bus.emit(EventType.SCHEDULED_ACTION_PAUSED, {
            "action_id": action_id,
        })

        return True

    async def resume_action(self, action_id: int) -> bool:
        """Resume a paused scheduled action."""
        async with self._lock:
            action = self._actions.get(action_id)
            if not action:
                return False
            action.status = ScheduledActionStatus.ACTIVE
            action.next_run_at = action.calculate_next_run()

        await self._persist_action(action)
        await self.event_bus.emit(EventType.SCHEDULED_ACTION_RESUMED, {
            "action_id": action_id,
        })

        return True

    async def delete_action(self, action_id: int) -> bool:
        """Delete a scheduled action."""
        async with self._lock:
            action = self._actions.pop(action_id, None)
            if not action:
                return False

            # Remove from event subscriptions
            if action.event_trigger and action.event_trigger in self._event_subscriptions:
                self._event_subscriptions[action.event_trigger].discard(action_id)

        if self.db_service:
            try:
                self.db_service.execute(
                    "DELETE FROM circle.scheduled_actions WHERE id = %(id)s",
                    {'id': action_id},
                )
            except Exception as e:
                logger.error(f"Failed to delete action: {e}")

        await self.event_bus.emit(EventType.SCHEDULED_ACTION_DELETED, {
            "action_id": action_id,
        })

        return True

    async def trigger_now(self, action_id: int) -> bool:
        """Manually trigger an action to run immediately."""
        async with self._lock:
            action = self._actions.get(action_id)
            if not action:
                return False

        await self._execute_action(action, triggered_by="manual")
        return True

    async def get_action(self, action_id: int) -> Optional[ScheduledAction]:
        """Get a scheduled action by ID."""
        return self._actions.get(action_id)

    async def list_actions(
        self,
        status: Optional[ScheduledActionStatus] = None,
        agent_id: Optional[int] = None,
    ) -> List[ScheduledAction]:
        """List scheduled actions with optional filtering."""
        actions = list(self._actions.values())

        if status:
            actions = [a for a in actions if a.status == status]
        if agent_id:
            actions = [a for a in actions if a.agent_id == agent_id]

        return actions

    async def get_runs(
        self,
        action_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> List[ScheduledActionRun]:
        """Get execution history for an action."""
        if not self.db_service:
            return []

        try:
            rows = self.db_service.execute("""
                SELECT * FROM circle.scheduled_action_runs
                WHERE scheduled_action_id = %(action_id)s
                ORDER BY triggered_at DESC
                LIMIT %(limit)s OFFSET %(offset)s
            """, {'action_id': action_id, 'limit': limit, 'offset': offset})

            return [
                ScheduledActionRun(
                    id=row["id"],
                    scheduled_action_id=row["scheduled_action_id"],
                    background_task_id=row.get("background_task_id"),
                    run_number=row["run_number"],
                    triggered_at=row["triggered_at"],
                    triggered_by=row.get("triggered_by", "scheduler"),
                    status=BackgroundTaskStatus(row["status"]),
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
            logger.error(f"Failed to get runs: {e}")
            return []


# Singleton instance
_scheduler: Optional[Scheduler] = None


def get_scheduler(
    db_service: Any = None,
    event_bus: Optional[EventBus] = None,
    check_interval: int = 60,
    async_db: Optional[Any] = None,
) -> Scheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler(
            db_service=db_service,
            event_bus=event_bus,
            check_interval=check_interval,
            async_db=async_db,
        )
    return _scheduler
