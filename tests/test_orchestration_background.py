"""
Tests for gathering/orchestration/background.py - Background task models.
"""

import pytest
from datetime import datetime, timezone, timedelta

from gathering.orchestration.background import (
    BackgroundTaskStatus,
    TaskStep,
    BackgroundTask,
    BackgroundTaskRunner,
    BackgroundTaskExecutor,
    get_background_executor,
)


class TestBackgroundTaskStatus:
    """Test BackgroundTaskStatus enum."""

    def test_all_statuses_exist(self):
        """Test all expected statuses exist."""
        statuses = [
            BackgroundTaskStatus.PENDING,
            BackgroundTaskStatus.RUNNING,
            BackgroundTaskStatus.PAUSED,
            BackgroundTaskStatus.COMPLETED,
            BackgroundTaskStatus.FAILED,
            BackgroundTaskStatus.CANCELLED,
            BackgroundTaskStatus.TIMEOUT,
        ]
        assert len(statuses) == 7

    def test_status_values(self):
        """Test status enum values."""
        assert BackgroundTaskStatus.PENDING.value == "pending"
        assert BackgroundTaskStatus.RUNNING.value == "running"
        assert BackgroundTaskStatus.PAUSED.value == "paused"
        assert BackgroundTaskStatus.COMPLETED.value == "completed"
        assert BackgroundTaskStatus.FAILED.value == "failed"
        assert BackgroundTaskStatus.CANCELLED.value == "cancelled"
        assert BackgroundTaskStatus.TIMEOUT.value == "timeout"


class TestTaskStep:
    """Test TaskStep dataclass."""

    def test_minimal_creation(self):
        """Test creating a minimal task step."""
        step = TaskStep(step_number=1, action_type="plan")
        assert step.step_number == 1
        assert step.action_type == "plan"
        assert step.action_input is None
        assert step.action_output is None
        assert step.tool_name is None
        assert step.success is True
        assert step.error_message is None

    def test_full_creation(self):
        """Test creating a task step with all fields."""
        now = datetime.now(timezone.utc)
        step = TaskStep(
            step_number=5,
            action_type="execute",
            action_input="Write code",
            action_output="Code written successfully",
            tool_name="code_executor",
            tool_input={"code": "print('hello')"},
            tool_output={"result": "hello"},
            tool_success=True,
            llm_model="gpt-4",
            tokens_input=100,
            tokens_output=50,
            duration_ms=1500,
            success=True,
            error_message=None,
            created_at=now,
        )
        assert step.step_number == 5
        assert step.action_type == "execute"
        assert step.tool_name == "code_executor"
        assert step.tokens_input == 100
        assert step.tokens_output == 50
        assert step.duration_ms == 1500

    def test_to_dict(self):
        """Test converting task step to dictionary."""
        step = TaskStep(
            step_number=1,
            action_type="plan",
            action_input="Test input",
            action_output="Test output",
            tool_name="calculator",
            tokens_input=50,
            tokens_output=25,
            duration_ms=500,
        )
        d = step.to_dict()
        assert d["step_number"] == 1
        assert d["action_type"] == "plan"
        assert d["action_input"] == "Test input"
        assert d["action_output"] == "Test output"
        assert d["tool_name"] == "calculator"
        assert d["tokens_input"] == 50
        assert d["tokens_output"] == 25
        assert d["duration_ms"] == 500
        assert d["success"] is True
        assert "created_at" in d

    def test_error_step(self):
        """Test creating an error step."""
        step = TaskStep(
            step_number=3,
            action_type="error",
            success=False,
            error_message="Something went wrong",
        )
        assert step.success is False
        assert step.error_message == "Something went wrong"


class TestBackgroundTask:
    """Test BackgroundTask dataclass."""

    def test_minimal_creation(self):
        """Test creating a minimal background task."""
        task = BackgroundTask(
            id=1,
            agent_id=100,
            goal="Analyze data",
        )
        assert task.id == 1
        assert task.agent_id == 100
        assert task.goal == "Analyze data"
        assert task.status == BackgroundTaskStatus.PENDING
        assert task.max_steps == 50
        assert task.timeout_seconds == 3600
        assert task.checkpoint_interval == 5
        assert task.current_step == 0
        assert task.progress_percent == 0
        assert task.steps == []

    def test_full_creation(self):
        """Test creating a task with all fields."""
        task = BackgroundTask(
            id=2,
            agent_id=200,
            goal="Complex analysis",
            status=BackgroundTaskStatus.RUNNING,
            circle_id=10,
            goal_context={"key": "value"},
            max_steps=100,
            timeout_seconds=7200,
            checkpoint_interval=10,
            current_step=25,
            progress_percent=50,
            progress_summary="Halfway done",
            last_action="Processed data",
            checkpoint_data={"state": "active"},
            final_result=None,
            artifacts=[{"type": "file", "path": "/tmp/result.json"}],
            total_llm_calls=10,
            total_tokens_used=5000,
            total_tool_calls=5,
        )
        assert task.circle_id == 10
        assert task.max_steps == 100
        assert task.progress_percent == 50
        assert task.total_llm_calls == 10
        assert len(task.artifacts) == 1

    def test_is_active_pending(self):
        """Test is_active for pending task."""
        task = BackgroundTask(id=1, agent_id=1, goal="test")
        task.status = BackgroundTaskStatus.PENDING
        assert task.is_active is True

    def test_is_active_running(self):
        """Test is_active for running task."""
        task = BackgroundTask(id=1, agent_id=1, goal="test")
        task.status = BackgroundTaskStatus.RUNNING
        assert task.is_active is True

    def test_is_active_paused(self):
        """Test is_active for paused task."""
        task = BackgroundTask(id=1, agent_id=1, goal="test")
        task.status = BackgroundTaskStatus.PAUSED
        assert task.is_active is True

    def test_is_active_completed(self):
        """Test is_active for completed task."""
        task = BackgroundTask(id=1, agent_id=1, goal="test")
        task.status = BackgroundTaskStatus.COMPLETED
        assert task.is_active is False

    def test_is_active_failed(self):
        """Test is_active for failed task."""
        task = BackgroundTask(id=1, agent_id=1, goal="test")
        task.status = BackgroundTaskStatus.FAILED
        assert task.is_active is False

    def test_is_active_cancelled(self):
        """Test is_active for cancelled task."""
        task = BackgroundTask(id=1, agent_id=1, goal="test")
        task.status = BackgroundTaskStatus.CANCELLED
        assert task.is_active is False

    def test_is_active_timeout(self):
        """Test is_active for timed out task."""
        task = BackgroundTask(id=1, agent_id=1, goal="test")
        task.status = BackgroundTaskStatus.TIMEOUT
        assert task.is_active is False

    def test_duration_seconds_not_started(self):
        """Test duration when task hasn't started."""
        task = BackgroundTask(id=1, agent_id=1, goal="test")
        assert task.duration_seconds == 0

    def test_duration_seconds_running(self):
        """Test duration while task is running."""
        task = BackgroundTask(id=1, agent_id=1, goal="test")
        task.started_at = datetime.now(timezone.utc) - timedelta(seconds=60)
        # Should be approximately 60 seconds
        duration = task.duration_seconds
        assert 59 <= duration <= 61

    def test_duration_seconds_completed(self):
        """Test duration after task completed."""
        start = datetime.now(timezone.utc) - timedelta(seconds=120)
        end = datetime.now(timezone.utc) - timedelta(seconds=20)
        task = BackgroundTask(id=1, agent_id=1, goal="test")
        task.started_at = start
        task.completed_at = end
        # Should be exactly 100 seconds
        assert task.duration_seconds == 100

    def test_to_dict(self):
        """Test converting task to dictionary."""
        task = BackgroundTask(
            id=1,
            agent_id=100,
            goal="Test goal",
            status=BackgroundTaskStatus.RUNNING,
            current_step=5,
            progress_percent=25,
        )
        d = task.to_dict()
        assert d["id"] == 1
        assert d["agent_id"] == 100
        assert d["goal"] == "Test goal"
        assert d["status"] == "running"
        assert d["current_step"] == 5
        assert d["progress_percent"] == 25
        assert "created_at" in d
        assert "duration_seconds" in d

    def test_to_dict_with_timestamps(self):
        """Test to_dict with various timestamps."""
        now = datetime.now(timezone.utc)
        task = BackgroundTask(
            id=1,
            agent_id=1,
            goal="test",
            started_at=now,
            completed_at=now,
            paused_at=now,
            last_checkpoint_at=now,
        )
        d = task.to_dict()
        assert d["started_at"] is not None
        assert d["completed_at"] is not None
        assert d["paused_at"] is not None
        assert d["last_checkpoint_at"] is not None


class TestBackgroundTaskRunner:
    """Test BackgroundTaskRunner class."""

    def test_creation(self):
        """Test creating a task runner."""
        task = BackgroundTask(id=1, agent_id=1, goal="test")

        class MockAgent:
            agent_id = 1

        runner = BackgroundTaskRunner(task=task, agent=MockAgent())
        assert runner.task is task
        assert runner._stop_requested is False
        assert runner._pause_requested is False

    def test_request_stop(self):
        """Test requesting stop."""
        task = BackgroundTask(id=1, agent_id=1, goal="test")

        class MockAgent:
            agent_id = 1

        runner = BackgroundTaskRunner(task=task, agent=MockAgent())
        assert runner._stop_requested is False
        runner.request_stop()
        assert runner._stop_requested is True

    def test_request_pause(self):
        """Test requesting pause."""
        task = BackgroundTask(id=1, agent_id=1, goal="test")

        class MockAgent:
            agent_id = 1

        runner = BackgroundTaskRunner(task=task, agent=MockAgent())
        assert runner._pause_requested is False
        runner.request_pause()
        assert runner._pause_requested is True

    def test_format_recent_steps_empty(self):
        """Test formatting recent steps when empty."""
        task = BackgroundTask(id=1, agent_id=1, goal="test")

        class MockAgent:
            agent_id = 1

        runner = BackgroundTaskRunner(task=task, agent=MockAgent())
        result = runner._format_recent_steps()
        assert result == "No steps yet."

    def test_format_recent_steps_with_data(self):
        """Test formatting recent steps with data."""
        task = BackgroundTask(id=1, agent_id=1, goal="test")
        task.steps = [
            TaskStep(step_number=1, action_type="execute", action_input="Action 1", action_output="Result 1"),
            TaskStep(step_number=2, action_type="execute", action_input="Action 2", action_output="Result 2"),
        ]

        class MockAgent:
            agent_id = 1

        runner = BackgroundTaskRunner(task=task, agent=MockAgent())
        result = runner._format_recent_steps()
        assert "Step 1" in result
        assert "Step 2" in result
        assert "Action 1" in result

    def test_format_recent_steps_non_execute(self):
        """Test formatting when no execute steps."""
        task = BackgroundTask(id=1, agent_id=1, goal="test")
        task.steps = [
            TaskStep(step_number=1, action_type="plan", action_input="Plan 1"),
            TaskStep(step_number=2, action_type="memory_recall", action_input="Recall"),
        ]

        class MockAgent:
            agent_id = 1

        runner = BackgroundTaskRunner(task=task, agent=MockAgent())
        result = runner._format_recent_steps()
        # Non-execute steps are not formatted
        assert result == "No execution steps yet."


class TestBackgroundTaskExecutor:
    """Test BackgroundTaskExecutor class."""

    def test_singleton_pattern(self):
        """Test that executor is a singleton."""
        # Reset singleton for testing
        BackgroundTaskExecutor._instance = None

        exec1 = BackgroundTaskExecutor()
        exec2 = BackgroundTaskExecutor()
        assert exec1 is exec2

    def test_creation_with_params(self):
        """Test creating executor with parameters."""
        # Reset singleton
        BackgroundTaskExecutor._instance = None

        executor = BackgroundTaskExecutor(max_concurrent=10)
        assert executor.max_concurrent == 10
        assert executor.event_bus is None
        assert executor.db is None

    def test_get_status_not_found(self):
        """Test getting status of non-existent task."""
        import asyncio

        # Reset singleton
        BackgroundTaskExecutor._instance = None

        executor = BackgroundTaskExecutor()
        result = asyncio.run(executor.get_status(999))
        assert result is None

    def test_list_tasks_empty(self):
        """Test listing tasks when empty."""
        # Reset singleton
        BackgroundTaskExecutor._instance = None

        executor = BackgroundTaskExecutor()
        tasks = executor.list_tasks()
        assert tasks == []

    def test_list_tasks_with_filter(self):
        """Test listing tasks with status filter."""
        # Reset singleton
        BackgroundTaskExecutor._instance = None

        executor = BackgroundTaskExecutor()

        # Add some tasks directly
        task1 = BackgroundTask(id=1, agent_id=1, goal="task1", status=BackgroundTaskStatus.RUNNING)
        task2 = BackgroundTask(id=2, agent_id=1, goal="task2", status=BackgroundTaskStatus.COMPLETED)
        task3 = BackgroundTask(id=3, agent_id=2, goal="task3", status=BackgroundTaskStatus.RUNNING)

        executor._tasks = {1: task1, 2: task2, 3: task3}

        # Filter by status
        running_tasks = executor.list_tasks(status=BackgroundTaskStatus.RUNNING)
        assert len(running_tasks) == 2

        completed_tasks = executor.list_tasks(status=BackgroundTaskStatus.COMPLETED)
        assert len(completed_tasks) == 1

        # Filter by agent_id
        agent1_tasks = executor.list_tasks(agent_id=1)
        assert len(agent1_tasks) == 2

        agent2_tasks = executor.list_tasks(agent_id=2)
        assert len(agent2_tasks) == 1


class TestGetBackgroundExecutor:
    """Test get_background_executor function."""

    def test_get_executor(self):
        """Test getting the executor singleton."""
        # Reset module-level singleton
        import gathering.orchestration.background as bg

        bg._executor = None
        BackgroundTaskExecutor._instance = None

        executor = get_background_executor()
        assert isinstance(executor, BackgroundTaskExecutor)

    def test_get_executor_reuses_instance(self):
        """Test that get_background_executor reuses instance."""
        import gathering.orchestration.background as bg

        bg._executor = None
        BackgroundTaskExecutor._instance = None

        exec1 = get_background_executor()
        exec2 = get_background_executor()
        assert exec1 is exec2
