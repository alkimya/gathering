"""
Scheduler dispatch, crash recovery, and deduplication tests.

Covers: ACTION_DISPATCHERS dispatch table, crash recovery with deduplication,
race condition fix, and ScheduledAction dataclass fields.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gathering.orchestration.scheduler import (
    ACTION_DISPATCHERS,
    Scheduler,
    ScheduledAction,
    ScheduledActionStatus,
    ScheduleType,
    _dispatch_call_api,
    _dispatch_execute_pipeline,
    _dispatch_send_notification,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_action(**overrides) -> ScheduledAction:
    """Factory returning a ScheduledAction with sensible defaults."""
    defaults = dict(
        id=1,
        agent_id=1,
        name="test",
        goal="test goal",
        schedule_type=ScheduleType.CRON,
        status=ScheduledActionStatus.ACTIVE,
        cron_expression="0 * * * *",
        action_type="run_task",
        action_config={},
    )
    defaults.update(overrides)
    return ScheduledAction(**defaults)


class MockDBService:
    """Mock database service that records calls and returns configurable responses."""

    def __init__(self):
        self.execute_calls: list = []
        self.execute_one_calls: list = []
        self._execute_return: list = []
        self._execute_one_return = None

    def execute(self, query, params=None):
        self.execute_calls.append((query, params))
        return self._execute_return

    def execute_one(self, query, params=None):
        self.execute_one_calls.append((query, params))
        return self._execute_one_return


def make_mock_event_bus() -> AsyncMock:
    """Create a mock EventBus with async emit."""
    bus = AsyncMock()
    bus.emit = AsyncMock()
    bus.subscribe = MagicMock()
    return bus


# ---------------------------------------------------------------------------
# Test: ACTION_DISPATCHERS registration
# ---------------------------------------------------------------------------


class TestActionDispatchers:
    """Verify the dispatch table is correctly populated."""

    def test_action_dispatchers_registered(self):
        """ACTION_DISPATCHERS has keys for all 4 action types."""
        expected_types = {"run_task", "execute_pipeline", "send_notification", "call_api"}
        assert set(ACTION_DISPATCHERS.keys()) == expected_types

    def test_dispatchers_are_callable(self):
        """Each dispatcher value must be a callable coroutine function."""
        for action_type, handler in ACTION_DISPATCHERS.items():
            assert callable(handler), f"Dispatcher for '{action_type}' is not callable"
            assert asyncio.iscoroutinefunction(handler), (
                f"Dispatcher for '{action_type}' is not async"
            )


# ---------------------------------------------------------------------------
# Test: Dispatch execute_pipeline
# ---------------------------------------------------------------------------


class TestDispatchExecutePipeline:
    """Test the execute_pipeline dispatcher."""

    @pytest.mark.asyncio
    async def test_dispatch_execute_pipeline(self):
        """Verify PipelineExecutor is instantiated and execute() called."""
        action = make_action(
            action_type="execute_pipeline",
            action_config={"pipeline_id": "42"},
        )

        mock_db = MockDBService()
        # Return pipeline definition row
        mock_db._execute_one_return = {
            "id": 42,
            "name": "test-pipeline",
            "definition": {"nodes": [], "edges": []},
        }

        mock_executor_instance = MagicMock()
        mock_executor_instance.execute = AsyncMock(return_value={"status": "completed"})

        # PipelineExecutor is imported lazily inside the function, patch at source
        with patch(
            "gathering.orchestration.pipeline.executor.PipelineExecutor",
            return_value=mock_executor_instance,
        ) as MockPE:
            context = {"db": mock_db, "event_bus": make_mock_event_bus()}
            result = await _dispatch_execute_pipeline(action, context)

        # Verify PipelineExecutor was called with correct pipeline_id
        MockPE.assert_called_once()
        call_kwargs = MockPE.call_args
        assert call_kwargs.kwargs.get("pipeline_id") == 42
        mock_executor_instance.execute.assert_awaited_once()
        assert result["action_type"] == "execute_pipeline"
        assert result["status"] == "completed"


# ---------------------------------------------------------------------------
# Test: Dispatch send_notification
# ---------------------------------------------------------------------------


class TestDispatchSendNotification:
    """Test the send_notification dispatcher."""

    @pytest.mark.asyncio
    async def test_dispatch_send_notification(self):
        """Verify NotificationsSkill.execute is called with action_config."""
        action = make_action(
            action_type="send_notification",
            action_config={
                "message": "hello",
                "channel": "email",
                "tool_name": "notify_webhook",
                "tool_input": {"message": "hello"},
            },
        )

        mock_skill_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.message = "Notification sent"
        mock_skill_instance.execute.return_value = mock_response

        # NotificationsSkill is imported lazily inside the function
        with patch(
            "gathering.skills.notifications.sender.NotificationsSkill",
            return_value=mock_skill_instance,
        ):
            context = {"db": None, "event_bus": make_mock_event_bus()}
            result = await _dispatch_send_notification(action, context)

        mock_skill_instance.execute.assert_called_once()
        assert result["action_type"] == "send_notification"
        assert result["success"] is True


# ---------------------------------------------------------------------------
# Test: Dispatch call_api
# ---------------------------------------------------------------------------


class TestDispatchCallApi:
    """Test the call_api dispatcher."""

    @pytest.mark.asyncio
    async def test_dispatch_call_api(self):
        """Verify HTTPSkill.execute is called with action_config."""
        action = make_action(
            action_type="call_api",
            action_config={
                "url": "https://example.com",
                "method": "GET",
                "tool_name": "http_get",
                "tool_input": {"url": "https://example.com"},
            },
        )

        mock_skill_instance = MagicMock()
        mock_skill_instance.execute.return_value = {"status_code": 200, "body": "ok"}

        # HTTPSkill is imported lazily inside the function
        with patch(
            "gathering.skills.http.client.HTTPSkill",
            return_value=mock_skill_instance,
        ):
            context = {"db": None, "event_bus": make_mock_event_bus()}
            result = await _dispatch_call_api(action, context)

        mock_skill_instance.execute.assert_called_once()
        assert result["action_type"] == "call_api"


# ---------------------------------------------------------------------------
# Test: Dispatch unknown type
# ---------------------------------------------------------------------------


class TestDispatchUnknown:
    """Test handling of unknown action types."""

    @pytest.mark.asyncio
    async def test_dispatch_unknown_type_logs_error(self):
        """Unknown action_type does not crash; emits failure event."""
        action = make_action(action_type="unknown_thing")
        mock_db = MockDBService()
        mock_db._execute_one_return = None  # No run record created
        event_bus = make_mock_event_bus()

        scheduler = Scheduler(db_service=mock_db, event_bus=event_bus)

        # Manually add action to scheduler
        scheduler._actions[action.id] = action

        # Execute the action through the scheduler's dispatch path
        await scheduler._execute_action(action, triggered_by="test")

        # Verify failure event was emitted (SCHEDULED_ACTION_FAILED)
        fail_calls = [
            call
            for call in event_bus.emit.call_args_list
            if len(call.args) >= 1
            and hasattr(call.args[0], "value")
            and "failed" in call.args[0].value
        ]
        assert len(fail_calls) > 0, "Expected SCHEDULED_ACTION_FAILED event to be emitted"


# ---------------------------------------------------------------------------
# Test: Crash recovery
# ---------------------------------------------------------------------------


class TestCrashRecovery:
    """Test _recover_missed_runs with deduplication."""

    @pytest.mark.asyncio
    async def test_recover_missed_runs_executes_missed(self):
        """Missed run (no prior record) triggers recovery execution."""
        mock_db = MockDBService()
        # No existing runs for the missed window
        mock_db._execute_return = []
        # For run record creation
        mock_db._execute_one_return = {
            "id": 100,
            "scheduled_action_id": 1,
            "run_number": 1,
            "triggered_by": "recovery",
            "triggered_at": datetime.now(timezone.utc),
        }

        event_bus = make_mock_event_bus()
        scheduler = Scheduler(db_service=mock_db, event_bus=event_bus)

        # Create action with next_run_at in the past
        action = make_action(
            next_run_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        scheduler._actions[action.id] = action

        # Mock _execute_action to capture calls
        scheduler._execute_action = AsyncMock()

        await scheduler._recover_missed_runs()

        scheduler._execute_action.assert_awaited_once()
        call_kwargs = scheduler._execute_action.call_args
        assert call_kwargs.kwargs.get("triggered_by") == "recovery" or (
            len(call_kwargs.args) >= 2 and call_kwargs.args[1] == "recovery"
        )

    @pytest.mark.asyncio
    async def test_recover_missed_runs_skips_already_completed(self):
        """Completed run for missed window skips re-execution."""
        mock_db = MockDBService()
        # Return existing run record (completed)
        mock_db._execute_return = [{"id": 50, "status": "completed"}]

        event_bus = make_mock_event_bus()
        scheduler = Scheduler(db_service=mock_db, event_bus=event_bus)

        action = make_action(
            next_run_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        scheduler._actions[action.id] = action

        scheduler._execute_action = AsyncMock()
        # _persist_action writes to DB -- mock it
        scheduler._persist_action = AsyncMock()

        await scheduler._recover_missed_runs()

        scheduler._execute_action.assert_not_awaited()
        # next_run_at should be advanced
        scheduler._persist_action.assert_awaited()

    @pytest.mark.asyncio
    async def test_recover_missed_runs_skips_running(self):
        """Running run for missed window skips re-execution."""
        mock_db = MockDBService()
        mock_db._execute_return = [{"id": 51, "status": "running"}]

        event_bus = make_mock_event_bus()
        scheduler = Scheduler(db_service=mock_db, event_bus=event_bus)

        action = make_action(
            next_run_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        scheduler._actions[action.id] = action

        scheduler._execute_action = AsyncMock()
        scheduler._persist_action = AsyncMock()

        await scheduler._recover_missed_runs()

        scheduler._execute_action.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_recover_missed_runs_ignores_future_actions(self):
        """Actions with next_run_at in the future are not recovered."""
        mock_db = MockDBService()
        event_bus = make_mock_event_bus()
        scheduler = Scheduler(db_service=mock_db, event_bus=event_bus)

        action = make_action(
            next_run_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        scheduler._actions[action.id] = action

        scheduler._execute_action = AsyncMock()

        await scheduler._recover_missed_runs()

        scheduler._execute_action.assert_not_awaited()


# ---------------------------------------------------------------------------
# Test: Race condition fix
# ---------------------------------------------------------------------------


class TestRaceConditionFix:
    """Verify _running_actions is populated before asyncio.create_task."""

    @pytest.mark.asyncio
    async def test_race_condition_fixed(self):
        """action.id must be in _running_actions when create_task is called."""
        mock_db = MockDBService()
        event_bus = make_mock_event_bus()
        scheduler = Scheduler(db_service=mock_db, event_bus=event_bus)

        action = make_action(
            next_run_at=datetime.now(timezone.utc) - timedelta(seconds=10),
        )
        scheduler._actions[action.id] = action

        # Track the state of _running_actions at the time create_task is called
        captured_running_at_create_task = []

        original_create_task = asyncio.create_task

        def capturing_create_task(coro, **kwargs):
            # Record the running_actions state at the moment create_task is called
            captured_running_at_create_task.append(frozenset(scheduler._running_actions))
            # Cancel the coro so it doesn't actually run
            task = original_create_task(coro, **kwargs)
            task.cancel()
            return task

        with patch("gathering.orchestration.scheduler.asyncio.create_task", side_effect=capturing_create_task):
            await scheduler._check_and_execute_due_actions()

        # Verify action.id was in _running_actions at the time create_task was called
        assert len(captured_running_at_create_task) > 0, "create_task was never called"
        assert action.id in captured_running_at_create_task[0], (
            "_running_actions did not contain action.id before create_task"
        )


# ---------------------------------------------------------------------------
# Test: ScheduledAction dataclass
# ---------------------------------------------------------------------------


class TestScheduledActionDataclass:
    """Verify ScheduledAction has the expected fields."""

    def test_scheduled_action_dataclass_has_action_type(self):
        """ScheduledAction can be created with action_type and action_config."""
        action = ScheduledAction(
            id=1,
            agent_id=1,
            name="test",
            action_type="execute_pipeline",
            action_config={"pipeline_id": "42"},
        )
        assert action.action_type == "execute_pipeline"
        assert action.action_config == {"pipeline_id": "42"}

    def test_scheduled_action_defaults(self):
        """Defaults are correct for action_type and action_config."""
        action = ScheduledAction(id=1, agent_id=1, name="test")
        assert action.action_type == "run_task"
        assert action.action_config == {}
        assert action.goal == ""
