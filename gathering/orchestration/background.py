"""
Background Task Execution for GatheRing.
Enables agents to run long-running autonomous tasks with checkpointing.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

from gathering.orchestration.events import EventBus, EventType

logger = logging.getLogger(__name__)


class BackgroundTaskStatus(Enum):
    """Status of a background task."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class TaskStep:
    """Record of a single step in task execution."""
    step_number: int
    action_type: str  # plan, execute, tool_call, memory_recall, memory_store, checkpoint, complete_check
    action_input: Optional[str] = None
    action_output: Optional[str] = None
    tool_name: Optional[str] = None
    tool_input: Optional[Dict] = None
    tool_output: Optional[Dict] = None
    tool_success: bool = True
    llm_model: Optional[str] = None
    tokens_input: int = 0
    tokens_output: int = 0
    duration_ms: int = 0
    success: bool = True
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step_number": self.step_number,
            "action_type": self.action_type,
            "action_input": self.action_input,
            "action_output": self.action_output,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "tool_output": self.tool_output,
            "tool_success": self.tool_success,
            "llm_model": self.llm_model,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class BackgroundTask:
    """A background task for autonomous execution."""
    id: int
    agent_id: int
    goal: str
    status: BackgroundTaskStatus = BackgroundTaskStatus.PENDING
    circle_id: Optional[int] = None
    goal_context: Dict[str, Any] = field(default_factory=dict)

    # Execution limits
    max_steps: int = 50
    timeout_seconds: int = 3600  # 1 hour
    checkpoint_interval: int = 5

    # Progress
    current_step: int = 0
    progress_percent: int = 0
    progress_summary: Optional[str] = None
    last_action: Optional[str] = None

    # Checkpointing
    checkpoint_data: Dict[str, Any] = field(default_factory=dict)
    last_checkpoint_at: Optional[datetime] = None

    # Results
    final_result: Optional[str] = None
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None

    # Metrics
    total_llm_calls: int = 0
    total_tokens_used: int = 0
    total_tool_calls: int = 0

    # Steps history (in-memory only, persisted separately)
    steps: List[TaskStep] = field(default_factory=list)

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None

    @property
    def is_active(self) -> bool:
        """Check if task is in an active state."""
        return self.status in (BackgroundTaskStatus.PENDING, BackgroundTaskStatus.RUNNING, BackgroundTaskStatus.PAUSED)

    @property
    def duration_seconds(self) -> int:
        """Get task duration in seconds."""
        if not self.started_at:
            return 0
        end_time = self.completed_at or datetime.now(timezone.utc)
        return int((end_time - self.started_at).total_seconds())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "goal": self.goal,
            "status": self.status.value,
            "circle_id": self.circle_id,
            "goal_context": self.goal_context,
            "max_steps": self.max_steps,
            "timeout_seconds": self.timeout_seconds,
            "checkpoint_interval": self.checkpoint_interval,
            "current_step": self.current_step,
            "progress_percent": self.progress_percent,
            "progress_summary": self.progress_summary,
            "last_action": self.last_action,
            "checkpoint_data": self.checkpoint_data,
            "last_checkpoint_at": self.last_checkpoint_at.isoformat() if self.last_checkpoint_at else None,
            "final_result": self.final_result,
            "artifacts": self.artifacts,
            "error_message": self.error_message,
            "total_llm_calls": self.total_llm_calls,
            "total_tokens_used": self.total_tokens_used,
            "total_tool_calls": self.total_tool_calls,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "paused_at": self.paused_at.isoformat() if self.paused_at else None,
            "duration_seconds": self.duration_seconds,
        }


class BackgroundTaskRunner:
    """
    Runs a single background task to completion.

    The execution loop:
    1. Recall relevant context from memory
    2. Plan the next action toward the goal
    3. Execute the planned action (may involve tools)
    4. Store important learnings in memory
    5. Checkpoint if interval reached
    6. Check if goal is complete
    7. Repeat until complete, max_steps, or timeout
    """

    def __init__(
        self,
        task: BackgroundTask,
        agent: Any,  # AgentWrapper - avoid circular import
        event_bus: Optional[EventBus] = None,
        db_service: Optional[Any] = None,
    ):
        self.task = task
        self.agent = agent
        self.event_bus = event_bus
        self.db = db_service
        self._stop_requested = False
        self._pause_requested = False

    def request_stop(self) -> None:
        """Request the runner to stop."""
        self._stop_requested = True

    def request_pause(self) -> None:
        """Request the runner to pause."""
        self._pause_requested = True

    async def run(self) -> BackgroundTask:
        """Execute the task until completion or interruption."""
        self.task.status = BackgroundTaskStatus.RUNNING
        self.task.started_at = datetime.now(timezone.utc)
        await self._emit_event(EventType.TASK_STARTED, {"task_id": self.task.id})

        start_time = datetime.now(timezone.utc)
        timeout = timedelta(seconds=self.task.timeout_seconds)

        try:
            while self.task.current_step < self.task.max_steps:
                # Check for stop/pause requests
                if self._stop_requested:
                    self.task.status = BackgroundTaskStatus.CANCELLED
                    self.task.completed_at = datetime.now(timezone.utc)
                    await self._emit_event(EventType.TASK_CANCELLED, {"task_id": self.task.id})
                    break

                if self._pause_requested:
                    self.task.status = BackgroundTaskStatus.PAUSED
                    self.task.paused_at = datetime.now(timezone.utc)
                    await self._checkpoint()
                    break

                # Check timeout
                if datetime.now(timezone.utc) - start_time > timeout:
                    self.task.status = BackgroundTaskStatus.TIMEOUT
                    self.task.error_message = f"Task exceeded timeout of {self.task.timeout_seconds} seconds"
                    self.task.completed_at = datetime.now(timezone.utc)
                    await self._emit_event(EventType.TASK_FAILED, {
                        "task_id": self.task.id,
                        "error": self.task.error_message,
                    })
                    break

                # Execute one step
                self.task.current_step += 1
                step_start = datetime.now(timezone.utc)

                try:
                    # Step 1: Recall relevant memories
                    await self._step_recall()

                    # Step 2: Plan next action
                    action = await self._step_plan()

                    # Step 3: Execute action
                    result = await self._step_execute(action)

                    # Step 4: Remember important findings
                    await self._step_remember(result)

                    # Step 5: Checkpoint if needed
                    if self.task.current_step % self.task.checkpoint_interval == 0:
                        await self._checkpoint()

                    # Step 6: Check if complete
                    is_complete = await self._check_complete(result)

                    # Emit progress event
                    await self._emit_event(EventType.TASK_PROGRESS, {
                        "task_id": self.task.id,
                        "step": self.task.current_step,
                        "progress_percent": self.task.progress_percent,
                        "last_action": self.task.last_action,
                    })

                    if is_complete:
                        self.task.status = BackgroundTaskStatus.COMPLETED
                        self.task.completed_at = datetime.now(timezone.utc)
                        self.task.final_result = result.get("summary", result.get("output", str(result)))
                        await self._emit_event(EventType.TASK_COMPLETED, {
                            "task_id": self.task.id,
                            "result": self.task.final_result,
                        })
                        break

                except Exception as e:
                    logger.error(f"Error in task {self.task.id} step {self.task.current_step}: {e}")
                    step = TaskStep(
                        step_number=self.task.current_step,
                        action_type="error",
                        success=False,
                        error_message=str(e),
                        duration_ms=int((datetime.now(timezone.utc) - step_start).total_seconds() * 1000),
                    )
                    self.task.steps.append(step)

                    # Don't fail immediately - allow retry on next iteration
                    # But if we've had too many errors, fail
                    error_count = sum(1 for s in self.task.steps if not s.success)
                    if error_count >= 5:
                        self.task.status = BackgroundTaskStatus.FAILED
                        self.task.error_message = f"Too many errors: {str(e)}"
                        self.task.completed_at = datetime.now(timezone.utc)
                        await self._emit_event(EventType.TASK_FAILED, {
                            "task_id": self.task.id,
                            "error": self.task.error_message,
                        })
                        break

            # Max steps reached without completion
            if self.task.status == BackgroundTaskStatus.RUNNING:
                self.task.status = BackgroundTaskStatus.FAILED
                self.task.error_message = f"Reached max steps ({self.task.max_steps}) without completing goal"
                self.task.completed_at = datetime.now(timezone.utc)
                await self._emit_event(EventType.TASK_FAILED, {
                    "task_id": self.task.id,
                    "error": self.task.error_message,
                })

        except Exception as e:
            logger.exception(f"Fatal error in task {self.task.id}: {e}")
            self.task.status = BackgroundTaskStatus.FAILED
            self.task.error_message = str(e)
            self.task.completed_at = datetime.now(timezone.utc)
            await self._emit_event(EventType.TASK_FAILED, {
                "task_id": self.task.id,
                "error": str(e),
            })

        # Persist final state
        await self._persist_task()

        return self.task

    async def _step_recall(self) -> List[str]:
        """Recall relevant memories for the task."""
        step_start = datetime.now(timezone.utc)

        try:
            memories = await self.agent.recall(
                query=f"{self.task.goal}\nCurrent progress: {self.task.progress_summary or 'Starting'}",
                limit=5,
            )

            step = TaskStep(
                step_number=self.task.current_step,
                action_type="memory_recall",
                action_input=self.task.goal,
                action_output=str(memories) if memories else "No relevant memories",
                duration_ms=int((datetime.now(timezone.utc) - step_start).total_seconds() * 1000),
            )
            self.task.steps.append(step)

            return memories

        except Exception as e:
            logger.warning(f"Memory recall failed: {e}")
            return []

    async def _step_plan(self) -> str:
        """Plan the next action."""
        step_start = datetime.now(timezone.utc)

        # Build planning prompt
        prompt = f"""You are working on a background task autonomously.

GOAL: {self.task.goal}

CONTEXT: {self.task.goal_context}

CURRENT PROGRESS:
- Step: {self.task.current_step}/{self.task.max_steps}
- Progress: {self.task.progress_percent}%
- Last action: {self.task.last_action or 'None yet'}
- Summary: {self.task.progress_summary or 'Just started'}

RECENT STEPS:
{self._format_recent_steps()}

Plan your next action to make progress toward the goal. Be specific and actionable.
If you believe the goal is complete, start your response with [COMPLETE].

Your next action:"""

        response = await self.agent.chat(prompt, include_memories=False, allow_tools=False)
        action = response.content

        step = TaskStep(
            step_number=self.task.current_step,
            action_type="plan",
            action_input=prompt[:500],  # Truncate for storage
            action_output=action,
            llm_model=self.agent.config.model,
            tokens_input=response.tokens_used // 2,  # Approximate split
            tokens_output=response.tokens_used // 2,
            duration_ms=response.duration_ms,
        )
        self.task.steps.append(step)

        self.task.total_llm_calls += 1
        self.task.total_tokens_used += response.tokens_used
        self.task.last_action = action[:200]

        return action

    async def _step_execute(self, action: str) -> Dict[str, Any]:
        """Execute the planned action."""
        step_start = datetime.now(timezone.utc)

        # Execute via agent (with tools enabled)
        prompt = f"""Execute this action for the background task:

ACTION: {action}

GOAL: {self.task.goal}

Use the tools available to you to complete this action. Report what you did and any results."""

        response = await self.agent.chat(prompt, include_memories=False, allow_tools=True)

        step = TaskStep(
            step_number=self.task.current_step,
            action_type="execute",
            action_input=action,
            action_output=response.content,
            llm_model=self.agent.config.model,
            tokens_input=response.tokens_used // 2,
            tokens_output=response.tokens_used // 2,
            duration_ms=response.duration_ms,
        )

        # Track tool calls
        if response.tool_calls:
            self.task.total_tool_calls += len(response.tool_calls)
            step.tool_name = response.tool_calls[0].get("name", "unknown") if response.tool_calls else None

        self.task.steps.append(step)
        self.task.total_llm_calls += 1
        self.task.total_tokens_used += response.tokens_used

        # Update progress estimate
        self.task.progress_percent = min(95, int((self.task.current_step / self.task.max_steps) * 100))

        return {
            "output": response.content,
            "tool_calls": response.tool_calls,
            "tool_results": response.tool_results,
        }

    async def _step_remember(self, result: Dict[str, Any]) -> None:
        """Store important learnings from this step."""
        output = result.get("output", "")

        # Only remember if there's substantial content
        if len(output) > 100:
            step_start = datetime.now(timezone.utc)

            summary = f"Background task progress (step {self.task.current_step}): {output[:500]}"
            await self.agent.remember(summary, memory_type="task_progress")

            step = TaskStep(
                step_number=self.task.current_step,
                action_type="memory_store",
                action_input=summary[:200],
                duration_ms=int((datetime.now(timezone.utc) - step_start).total_seconds() * 1000),
            )
            self.task.steps.append(step)

    async def _checkpoint(self) -> None:
        """Save checkpoint for recovery."""
        step_start = datetime.now(timezone.utc)

        self.task.checkpoint_data = {
            "step": self.task.current_step,
            "progress_percent": self.task.progress_percent,
            "progress_summary": self.task.progress_summary,
            "last_action": self.task.last_action,
            "recent_steps": [s.to_dict() for s in self.task.steps[-10:]],
        }
        self.task.last_checkpoint_at = datetime.now(timezone.utc)

        step = TaskStep(
            step_number=self.task.current_step,
            action_type="checkpoint",
            action_output=f"Checkpoint saved at step {self.task.current_step}",
            duration_ms=int((datetime.now(timezone.utc) - step_start).total_seconds() * 1000),
        )
        self.task.steps.append(step)

        # Persist to database if available
        await self._persist_task()

        await self._emit_event(EventType.TASK_PROGRESS, {
            "task_id": self.task.id,
            "checkpoint": True,
            "step": self.task.current_step,
        })

    async def _check_complete(self, result: Dict[str, Any]) -> bool:
        """Check if the goal is complete."""
        output = result.get("output", "")

        # Quick check for completion marker
        if "[COMPLETE]" in output.upper():
            return True

        # Ask the agent to evaluate completion
        step_start = datetime.now(timezone.utc)

        prompt = f"""Evaluate if the following goal has been achieved.

GOAL: {self.task.goal}

CURRENT STATE:
- Steps completed: {self.task.current_step}
- Progress: {self.task.progress_percent}%
- Last action result: {output[:1000]}

Has the goal been fully achieved? Reply with ONLY 'YES' or 'NO' followed by a brief explanation."""

        response = await self.agent.chat(prompt, include_memories=False, allow_tools=False)
        is_complete = response.content.strip().upper().startswith("YES")

        step = TaskStep(
            step_number=self.task.current_step,
            action_type="complete_check",
            action_input=f"Goal: {self.task.goal}",
            action_output=response.content,
            llm_model=self.agent.config.model,
            tokens_input=response.tokens_used // 2,
            tokens_output=response.tokens_used // 2,
            duration_ms=response.duration_ms,
        )
        self.task.steps.append(step)

        self.task.total_llm_calls += 1
        self.task.total_tokens_used += response.tokens_used

        # Update progress summary from evaluation
        if len(response.content) > 10:
            self.task.progress_summary = response.content[:500]

        return is_complete

    def _format_recent_steps(self) -> str:
        """Format recent steps for context."""
        recent = self.task.steps[-5:] if self.task.steps else []
        if not recent:
            return "No steps yet."

        lines = []
        for step in recent:
            if step.action_type == "execute":
                lines.append(f"- Step {step.step_number}: {step.action_input[:100]}")
                if step.action_output:
                    lines.append(f"  Result: {step.action_output[:200]}")
        return "\n".join(lines) if lines else "No execution steps yet."

    async def _emit_event(self, event_type: EventType, data: Dict[str, Any]) -> None:
        """Emit an event if event bus is available."""
        if self.event_bus:
            await self.event_bus.emit(
                event_type=event_type,
                data=data,
                source_agent_id=self.task.agent_id,
            )

    async def _persist_task(self) -> None:
        """Persist task state to database."""
        if not self.db:
            return

        try:
            # Update task in database
            self.db.execute("""
                UPDATE circle.background_tasks
                SET status = %(status)s,
                    current_step = %(current_step)s,
                    progress_percent = %(progress_percent)s,
                    progress_summary = %(progress_summary)s,
                    last_action = %(last_action)s,
                    checkpoint_data = %(checkpoint_data)s,
                    last_checkpoint_at = %(last_checkpoint_at)s,
                    final_result = %(final_result)s,
                    artifacts = %(artifacts)s,
                    error_message = %(error_message)s,
                    total_llm_calls = %(total_llm_calls)s,
                    total_tokens_used = %(total_tokens_used)s,
                    total_tool_calls = %(total_tool_calls)s,
                    started_at = %(started_at)s,
                    completed_at = %(completed_at)s,
                    paused_at = %(paused_at)s,
                    updated_at = NOW()
                WHERE id = %(id)s
            """, {
                'id': self.task.id,
                'status': self.task.status.value,
                'current_step': self.task.current_step,
                'progress_percent': self.task.progress_percent,
                'progress_summary': self.task.progress_summary,
                'last_action': self.task.last_action,
                'checkpoint_data': self.task.checkpoint_data,
                'last_checkpoint_at': self.task.last_checkpoint_at,
                'final_result': self.task.final_result,
                'artifacts': self.task.artifacts,
                'error_message': self.task.error_message,
                'total_llm_calls': self.task.total_llm_calls,
                'total_tokens_used': self.task.total_tokens_used,
                'total_tool_calls': self.task.total_tool_calls,
                'started_at': self.task.started_at,
                'completed_at': self.task.completed_at,
                'paused_at': self.task.paused_at,
            })

            # Persist recent steps
            for step in self.task.steps[-5:]:
                self.db.execute("""
                    INSERT INTO circle.background_task_steps (
                        task_id, step_number, action_type, action_input, action_output,
                        tool_name, tool_input, tool_output, tool_success,
                        llm_model, tokens_input, tokens_output, duration_ms,
                        success, error_message
                    ) VALUES (
                        %(task_id)s, %(step_number)s, %(action_type)s, %(action_input)s, %(action_output)s,
                        %(tool_name)s, %(tool_input)s, %(tool_output)s, %(tool_success)s,
                        %(llm_model)s, %(tokens_input)s, %(tokens_output)s, %(duration_ms)s,
                        %(success)s, %(error_message)s
                    )
                    ON CONFLICT DO NOTHING
                """, {
                    'task_id': self.task.id,
                    'step_number': step.step_number,
                    'action_type': step.action_type,
                    'action_input': step.action_input,
                    'action_output': step.action_output,
                    'tool_name': step.tool_name,
                    'tool_input': step.tool_input,
                    'tool_output': step.tool_output,
                    'tool_success': step.tool_success,
                    'llm_model': step.llm_model,
                    'tokens_input': step.tokens_input,
                    'tokens_output': step.tokens_output,
                    'duration_ms': step.duration_ms,
                    'success': step.success,
                    'error_message': step.error_message,
                })

        except Exception as e:
            logger.error(f"Failed to persist task {self.task.id}: {e}")


class BackgroundTaskExecutor:
    """
    Manages execution of all background tasks.

    Singleton that handles:
    - Starting new tasks
    - Pausing/resuming tasks
    - Cancelling tasks
    - Recovering tasks after restart
    - Graceful shutdown
    """

    _instance: Optional['BackgroundTaskExecutor'] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        db_service: Optional[Any] = None,
        max_concurrent: int = 5,
    ):
        if self._initialized:
            return

        self.event_bus = event_bus
        self.db = db_service
        self.max_concurrent = max_concurrent

        self._tasks: Dict[int, BackgroundTask] = {}
        self._runners: Dict[int, BackgroundTaskRunner] = {}
        self._asyncio_tasks: Dict[int, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        self._next_id = 1

        self._initialized = True

    async def start_task(
        self,
        agent: Any,  # AgentWrapper
        goal: str,
        circle_id: Optional[int] = None,
        goal_context: Optional[Dict[str, Any]] = None,
        max_steps: int = 50,
        timeout_seconds: int = 3600,
        checkpoint_interval: int = 5,
    ) -> int:
        """
        Start a new background task.

        Args:
            agent: The agent to execute the task
            goal: What the task should accomplish
            circle_id: Optional circle context
            goal_context: Additional context for the goal
            max_steps: Maximum steps before failure
            timeout_seconds: Maximum time before timeout
            checkpoint_interval: Steps between checkpoints

        Returns:
            Task ID
        """
        async with self._lock:
            # Check concurrent limit
            running_count = sum(1 for t in self._tasks.values() if t.status == BackgroundTaskStatus.RUNNING)
            if running_count >= self.max_concurrent:
                raise RuntimeError(f"Maximum concurrent tasks ({self.max_concurrent}) reached")

            # Create task
            task_id = await self._create_task_in_db(
                agent_id=agent.agent_id,
                goal=goal,
                circle_id=circle_id,
                goal_context=goal_context or {},
                max_steps=max_steps,
                timeout_seconds=timeout_seconds,
                checkpoint_interval=checkpoint_interval,
            )

            task = BackgroundTask(
                id=task_id,
                agent_id=agent.agent_id,
                goal=goal,
                circle_id=circle_id,
                goal_context=goal_context or {},
                max_steps=max_steps,
                timeout_seconds=timeout_seconds,
                checkpoint_interval=checkpoint_interval,
            )

            self._tasks[task_id] = task

            # Create runner
            runner = BackgroundTaskRunner(
                task=task,
                agent=agent,
                event_bus=self.event_bus,
                db_service=self.db,
            )
            self._runners[task_id] = runner

            # Start execution
            asyncio_task = asyncio.create_task(runner.run())
            self._asyncio_tasks[task_id] = asyncio_task

            # Emit event
            if self.event_bus:
                await self.event_bus.emit(
                    EventType.TASK_CREATED,
                    {
                        "task_id": task_id,
                        "agent_id": agent.agent_id,
                        "goal": goal,
                    },
                    source_agent_id=agent.agent_id,
                )

            logger.info(f"Started background task {task_id} for agent {agent.agent_id}: {goal[:50]}...")

            return task_id

    async def pause_task(self, task_id: int) -> bool:
        """Pause a running task."""
        runner = self._runners.get(task_id)
        if not runner:
            return False

        task = self._tasks.get(task_id)
        if not task or task.status != BackgroundTaskStatus.RUNNING:
            return False

        runner.request_pause()
        logger.info(f"Requested pause for task {task_id}")
        return True

    async def resume_task(self, task_id: int, agent: Any) -> bool:
        """Resume a paused task."""
        task = self._tasks.get(task_id)
        if not task or task.status != BackgroundTaskStatus.PAUSED:
            return False

        async with self._lock:
            task.status = BackgroundTaskStatus.RUNNING
            task.paused_at = None

            # Create new runner
            runner = BackgroundTaskRunner(
                task=task,
                agent=agent,
                event_bus=self.event_bus,
                db_service=self.db,
            )
            self._runners[task_id] = runner

            # Start execution
            asyncio_task = asyncio.create_task(runner.run())
            self._asyncio_tasks[task_id] = asyncio_task

            logger.info(f"Resumed task {task_id}")
            return True

    async def cancel_task(self, task_id: int) -> bool:
        """Cancel a task."""
        runner = self._runners.get(task_id)
        if not runner:
            # Task might not be running, just update status
            task = self._tasks.get(task_id)
            if task and task.is_active:
                task.status = BackgroundTaskStatus.CANCELLED
                task.completed_at = datetime.now(timezone.utc)
                await self._update_task_status_in_db(task_id, "cancelled")
                return True
            return False

        runner.request_stop()

        # Also cancel the asyncio task
        asyncio_task = self._asyncio_tasks.get(task_id)
        if asyncio_task and not asyncio_task.done():
            asyncio_task.cancel()

        logger.info(f"Requested cancellation for task {task_id}")
        return True

    async def get_status(self, task_id: int) -> Optional[BackgroundTask]:
        """Get task status."""
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        status: Optional[BackgroundTaskStatus] = None,
        agent_id: Optional[int] = None,
    ) -> List[BackgroundTask]:
        """List tasks with optional filters."""
        tasks = list(self._tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]

        if agent_id:
            tasks = [t for t in tasks if t.agent_id == agent_id]

        return tasks

    async def recover_tasks(self) -> int:
        """
        Recover interrupted tasks after restart.

        Returns number of tasks recovered.
        """
        if not self.db:
            return 0

        # Find tasks that were running or paused
        rows = self.db.execute("""
            SELECT * FROM circle.background_tasks
            WHERE status IN ('running', 'paused')
            ORDER BY created_at
        """)

        recovered = 0
        for row in rows:
            task = BackgroundTask(
                id=row['id'],
                agent_id=row['agent_id'],
                goal=row['goal'],
                status=BackgroundTaskStatus(row['status']),
                circle_id=row.get('circle_id'),
                goal_context=row.get('goal_context', {}),
                max_steps=row.get('max_steps', 50),
                timeout_seconds=row.get('timeout_seconds', 3600),
                checkpoint_interval=row.get('checkpoint_interval', 5),
                current_step=row.get('current_step', 0),
                progress_percent=row.get('progress_percent', 0),
                progress_summary=row.get('progress_summary'),
                last_action=row.get('last_action'),
                checkpoint_data=row.get('checkpoint_data', {}),
            )

            # Mark as paused (needs manual resume with agent)
            task.status = BackgroundTaskStatus.PAUSED
            task.paused_at = datetime.now(timezone.utc)
            self._tasks[task.id] = task

            await self._update_task_status_in_db(task.id, "paused")
            recovered += 1

            logger.info(f"Recovered task {task.id} (now paused, needs manual resume)")

        return recovered

    async def shutdown(self, timeout: float = 30) -> None:
        """
        Graceful shutdown - pause all running tasks.

        Args:
            timeout: Maximum seconds to wait for tasks to pause
        """
        logger.info("Shutting down background task executor...")

        # Request all runners to pause
        for runner in self._runners.values():
            runner.request_pause()

        # Wait for tasks to pause
        if self._asyncio_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._asyncio_tasks.values(), return_exceptions=True),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                logger.warning(f"Shutdown timeout - cancelling remaining tasks")
                for asyncio_task in self._asyncio_tasks.values():
                    if not asyncio_task.done():
                        asyncio_task.cancel()

        logger.info("Background task executor shutdown complete")

    async def _create_task_in_db(
        self,
        agent_id: int,
        goal: str,
        circle_id: Optional[int],
        goal_context: Dict,
        max_steps: int,
        timeout_seconds: int,
        checkpoint_interval: int,
    ) -> int:
        """Create task in database and return ID."""
        if not self.db:
            # In-memory fallback
            task_id = self._next_id
            self._next_id += 1
            return task_id

        result = self.db.execute_one("""
            INSERT INTO circle.background_tasks (
                agent_id, circle_id, goal, goal_context,
                max_steps, timeout_seconds, checkpoint_interval
            ) VALUES (
                %(agent_id)s, %(circle_id)s, %(goal)s, %(goal_context)s,
                %(max_steps)s, %(timeout_seconds)s, %(checkpoint_interval)s
            )
            RETURNING id
        """, {
            'agent_id': agent_id,
            'circle_id': circle_id,
            'goal': goal,
            'goal_context': goal_context,
            'max_steps': max_steps,
            'timeout_seconds': timeout_seconds,
            'checkpoint_interval': checkpoint_interval,
        })

        return result['id']

    async def _update_task_status_in_db(self, task_id: int, status: str) -> None:
        """Update task status in database."""
        if not self.db:
            return

        self.db.execute(
            "UPDATE circle.background_tasks SET status = %(status)s, updated_at = NOW() WHERE id = %(id)s",
            {'id': task_id, 'status': status}
        )


# Singleton accessor
_executor: Optional[BackgroundTaskExecutor] = None


def get_background_executor(
    event_bus: Optional[EventBus] = None,
    db_service: Optional[Any] = None,
) -> BackgroundTaskExecutor:
    """Get or create the background task executor singleton."""
    global _executor
    if _executor is None:
        _executor = BackgroundTaskExecutor(event_bus=event_bus, db_service=db_service)
    return _executor
