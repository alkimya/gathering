"""
Advisory lock coordination tests for Scheduler.

Covers: single-instance bypass, fail-closed on DB error, exactly-once
execution under concurrency, cleanup on lock skip, and normal execution
with advisory lock acquired.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gathering.orchestration.scheduler import (
    ACTION_DISPATCHERS,
    SCHEDULER_LOCK_NAMESPACE,
    Scheduler,
    ScheduledAction,
    ScheduledActionStatus,
    ScheduleType,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_action(**overrides) -> ScheduledAction:
    """Factory returning a ScheduledAction with sensible defaults."""
    defaults = dict(
        id=42,
        agent_id=1,
        name="test-action",
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
# Test 1: No async_db = always returns True (single-instance mode)
# ---------------------------------------------------------------------------


class TestAdvisoryLockNoAsyncDB:
    """Advisory lock with no async_db always proceeds."""

    @pytest.mark.asyncio
    async def test_try_acquire_lock_no_async_db_returns_true(self):
        """Scheduler with async_db=None always acquires the lock."""
        scheduler = Scheduler(
            db_service=None,
            event_bus=make_mock_event_bus(),
            async_db=None,
        )
        result = await scheduler._try_acquire_action_lock(42)
        assert result is True


# ---------------------------------------------------------------------------
# Test 2: DB error = fail-closed (returns False)
# ---------------------------------------------------------------------------


class TestAdvisoryLockDBError:
    """Advisory lock returns False on DB error (fail-closed)."""

    @pytest.mark.asyncio
    async def test_try_acquire_lock_db_error_returns_false(self):
        """DB error during lock attempt returns False (skip execution)."""
        mock_async_db = MagicMock()
        # Make _pool.connection() raise an exception
        mock_async_db._pool.connection.side_effect = Exception("Connection failed")

        scheduler = Scheduler(
            db_service=None,
            event_bus=make_mock_event_bus(),
            async_db=mock_async_db,
        )
        result = await scheduler._try_acquire_action_lock(42)
        assert result is False


# ---------------------------------------------------------------------------
# Test 3: Exactly-once execution under concurrency
# ---------------------------------------------------------------------------


class TestAdvisoryLockPreventsDoubleExecution:
    """Two concurrent _execute_action calls for same action execute once."""

    @pytest.mark.asyncio
    async def test_advisory_lock_prevents_duplicate_execution(self):
        """With lock returning True then False, dispatcher is called once."""
        mock_db = MockDBService()
        # For run record creation
        mock_db._execute_one_return = {
            "id": 100,
            "scheduled_action_id": 42,
            "run_number": 1,
            "triggered_by": "scheduler",
            "triggered_at": datetime.now(timezone.utc),
        }
        event_bus = make_mock_event_bus()
        scheduler = Scheduler(db_service=mock_db, event_bus=event_bus)

        action = make_action(id=42, action_type="run_task")
        scheduler._actions[action.id] = action
        # Pre-add to _running_actions as _check_and_execute_due_actions would
        scheduler._running_actions.add(action.id)

        # Track dispatcher calls
        dispatch_calls = []

        async def mock_run_task(action, context):
            dispatch_calls.append(action.id)
            return {"task_id": 1, "action_type": "run_task"}

        # Lock: first call True, second call False
        lock_results = iter([True, False])

        async def mock_lock(action_id):
            return next(lock_results)

        with patch.object(scheduler, "_try_acquire_action_lock", side_effect=mock_lock):
            with patch.dict(ACTION_DISPATCHERS, {"run_task": mock_run_task}):
                await asyncio.gather(
                    scheduler._execute_action(action),
                    scheduler._execute_action(action),
                )

        assert len(dispatch_calls) == 1, (
            f"Expected exactly 1 dispatch call, got {len(dispatch_calls)}"
        )


# ---------------------------------------------------------------------------
# Test 4: Lock skip removes from _running_actions
# ---------------------------------------------------------------------------


class TestLockSkipCleansUp:
    """When advisory lock returns False, action_id is removed from _running_actions."""

    @pytest.mark.asyncio
    async def test_lock_skip_removes_from_running_actions(self):
        """Failed lock acquisition removes action from _running_actions set."""
        event_bus = make_mock_event_bus()
        scheduler = Scheduler(db_service=None, event_bus=event_bus)

        action = make_action(id=42)
        scheduler._running_actions.add(action.id)

        # Mock lock to return False
        with patch.object(
            scheduler,
            "_try_acquire_action_lock",
            new_callable=AsyncMock,
            return_value=False,
        ):
            await scheduler._execute_action(action)

        assert action.id not in scheduler._running_actions, (
            "action_id should be removed from _running_actions after lock skip"
        )


# ---------------------------------------------------------------------------
# Test 5: Lock success proceeds with normal execution
# ---------------------------------------------------------------------------


class TestLockSuccessProceeds:
    """When advisory lock returns True, execution proceeds normally."""

    @pytest.mark.asyncio
    async def test_execute_action_with_lock_success_proceeds(self):
        """Lock success allows normal dispatch and increments execution_count."""
        mock_db = MockDBService()
        mock_db._execute_one_return = {
            "id": 200,
            "scheduled_action_id": 42,
            "run_number": 1,
            "triggered_by": "scheduler",
            "triggered_at": datetime.now(timezone.utc),
        }
        event_bus = make_mock_event_bus()
        scheduler = Scheduler(db_service=mock_db, event_bus=event_bus)

        action = make_action(id=42, action_type="run_task", execution_count=0)
        scheduler._actions[action.id] = action

        dispatch_called = []

        async def mock_run_task(action, context):
            dispatch_called.append(action.id)
            return {"task_id": 1, "action_type": "run_task"}

        with patch.object(
            scheduler,
            "_try_acquire_action_lock",
            new_callable=AsyncMock,
            return_value=True,
        ):
            with patch.dict(ACTION_DISPATCHERS, {"run_task": mock_run_task}):
                await scheduler._execute_action(action)

        assert len(dispatch_called) == 1, "Dispatcher should be called once"
        assert action.execution_count == 1, "execution_count should be incremented"
