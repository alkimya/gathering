"""
Tests for gathering/agents/goals.py - Agent Goal Management.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from gathering.agents.goals import (
    GoalStatus,
    GoalPriority,
    Goal,
    GoalDependency,
    GoalActivity,
    GoalManager,
)
from gathering.orchestration.events import EventBus


class TestGoalStatus:
    """Test GoalStatus enum."""

    def test_all_statuses_exist(self):
        """Test all expected statuses exist."""
        statuses = [
            GoalStatus.PENDING,
            GoalStatus.ACTIVE,
            GoalStatus.BLOCKED,
            GoalStatus.PAUSED,
            GoalStatus.COMPLETED,
            GoalStatus.FAILED,
            GoalStatus.CANCELLED,
        ]
        assert len(statuses) == 7

    def test_status_values(self):
        """Test status enum values."""
        assert GoalStatus.PENDING.value == "pending"
        assert GoalStatus.ACTIVE.value == "active"
        assert GoalStatus.BLOCKED.value == "blocked"
        assert GoalStatus.PAUSED.value == "paused"
        assert GoalStatus.COMPLETED.value == "completed"
        assert GoalStatus.FAILED.value == "failed"
        assert GoalStatus.CANCELLED.value == "cancelled"


class TestGoalPriority:
    """Test GoalPriority enum."""

    def test_all_priorities_exist(self):
        """Test all expected priorities exist."""
        priorities = [
            GoalPriority.LOW,
            GoalPriority.MEDIUM,
            GoalPriority.HIGH,
            GoalPriority.CRITICAL,
        ]
        assert len(priorities) == 4

    def test_priority_values(self):
        """Test priority enum values."""
        assert GoalPriority.LOW.value == "low"
        assert GoalPriority.MEDIUM.value == "medium"
        assert GoalPriority.HIGH.value == "high"
        assert GoalPriority.CRITICAL.value == "critical"


class TestGoal:
    """Test Goal dataclass."""

    def test_minimal_creation(self):
        """Test creating a minimal goal."""
        goal = Goal(
            id=1,
            agent_id=100,
            title="Test Goal",
            description="A test goal",
        )
        assert goal.id == 1
        assert goal.agent_id == 100
        assert goal.title == "Test Goal"
        assert goal.description == "A test goal"
        assert goal.status == GoalStatus.PENDING
        assert goal.priority == GoalPriority.MEDIUM
        assert goal.progress_percent == 0
        assert goal.parent_id is None
        assert goal.depth == 0

    def test_full_creation(self):
        """Test creating a goal with all fields."""
        deadline = datetime.now(timezone.utc) + timedelta(days=7)
        goal = Goal(
            id=2,
            agent_id=200,
            title="Complex Goal",
            description="A complex goal with many fields",
            status=GoalStatus.ACTIVE,
            priority=GoalPriority.HIGH,
            progress_percent=50,
            parent_id=1,
            depth=1,
            circle_id=10,
            success_criteria="All tests pass",
            context={"key": "value"},
            status_message="In progress",
            deadline=deadline,
            estimated_hours=Decimal("8.5"),
            actual_hours=Decimal("4.0"),
            is_decomposed=True,
            decomposition_strategy="sequential",
            max_subgoals=3,
            background_task_id=5,
            attempts=1,
            max_attempts=3,
            result_summary=None,
            artifacts=[{"type": "file", "path": "/tmp/result.json"}],
            tags=["important", "urgent"],
            metadata={"priority_reason": "deadline approaching"},
            created_by="user-123",
        )
        assert goal.status == GoalStatus.ACTIVE
        assert goal.priority == GoalPriority.HIGH
        assert goal.progress_percent == 50
        assert goal.parent_id == 1
        assert goal.circle_id == 10
        assert goal.estimated_hours == Decimal("8.5")
        assert goal.is_decomposed is True
        assert len(goal.artifacts) == 1
        assert len(goal.tags) == 2

    def test_is_blocked_true(self):
        """Test is_blocked returns True when blocking_count > 0."""
        goal = Goal(
            id=1,
            agent_id=1,
            title="Blocked Goal",
            description="A blocked goal",
            blocking_count=2,
        )
        assert goal.is_blocked() is True

    def test_is_blocked_false(self):
        """Test is_blocked returns False when blocking_count == 0."""
        goal = Goal(
            id=1,
            agent_id=1,
            title="Unblocked Goal",
            description="An unblocked goal",
            blocking_count=0,
        )
        assert goal.is_blocked() is False

    def test_can_start_true(self):
        """Test can_start returns True when conditions are met."""
        goal = Goal(
            id=1,
            agent_id=1,
            title="Ready Goal",
            description="A ready goal",
            status=GoalStatus.PENDING,
            blocking_count=0,
            attempts=0,
            max_attempts=3,
        )
        assert goal.can_start() is True

    def test_can_start_false_not_pending(self):
        """Test can_start returns False when status is not PENDING."""
        goal = Goal(
            id=1,
            agent_id=1,
            title="Active Goal",
            description="An active goal",
            status=GoalStatus.ACTIVE,
        )
        assert goal.can_start() is False

    def test_can_start_false_blocked(self):
        """Test can_start returns False when goal is blocked."""
        goal = Goal(
            id=1,
            agent_id=1,
            title="Blocked Goal",
            description="A blocked goal",
            status=GoalStatus.PENDING,
            blocking_count=1,
        )
        assert goal.can_start() is False

    def test_can_start_false_max_attempts(self):
        """Test can_start returns False when max attempts reached."""
        goal = Goal(
            id=1,
            agent_id=1,
            title="Exhausted Goal",
            description="A goal with max attempts",
            status=GoalStatus.PENDING,
            blocking_count=0,
            attempts=3,
            max_attempts=3,
        )
        assert goal.can_start() is False

    def test_to_dict(self):
        """Test converting goal to dictionary."""
        now = datetime.now(timezone.utc)
        goal = Goal(
            id=1,
            agent_id=100,
            title="Test Goal",
            description="Test description",
            status=GoalStatus.ACTIVE,
            priority=GoalPriority.HIGH,
            progress_percent=25,
            created_at=now,
        )
        d = goal.to_dict()
        assert d["id"] == 1
        assert d["agent_id"] == 100
        assert d["title"] == "Test Goal"
        assert d["description"] == "Test description"
        assert d["status"] == "active"
        assert d["priority"] == "high"
        assert d["progress_percent"] == 25
        assert "created_at" in d

    def test_to_dict_with_timestamps(self):
        """Test to_dict with various timestamps."""
        now = datetime.now(timezone.utc)
        deadline = now + timedelta(days=7)
        goal = Goal(
            id=1,
            agent_id=1,
            title="Test",
            description="Test",
            deadline=deadline,
            estimated_hours=Decimal("4.5"),
            started_at=now,
            completed_at=now,
        )
        d = goal.to_dict()
        assert d["deadline"] is not None
        assert d["estimated_hours"] == 4.5
        assert d["started_at"] is not None
        assert d["completed_at"] is not None

    def test_to_dict_null_timestamps(self):
        """Test to_dict with null optional timestamps."""
        goal = Goal(
            id=1,
            agent_id=1,
            title="Test",
            description="Test",
        )
        d = goal.to_dict()
        assert d["deadline"] is None
        assert d["started_at"] is None
        assert d["completed_at"] is None
        assert d["estimated_hours"] is None


class TestGoalDependency:
    """Test GoalDependency dataclass."""

    def test_creation(self):
        """Test creating a goal dependency."""
        dep = GoalDependency(
            id=1,
            goal_id=10,
            depends_on_id=5,
        )
        assert dep.id == 1
        assert dep.goal_id == 10
        assert dep.depends_on_id == 5
        assert dep.dependency_type == "blocks"
        assert dep.created_at is not None

    def test_custom_dependency_type(self):
        """Test custom dependency type."""
        dep = GoalDependency(
            id=1,
            goal_id=10,
            depends_on_id=5,
            dependency_type="requires",
        )
        assert dep.dependency_type == "requires"


class TestGoalActivity:
    """Test GoalActivity dataclass."""

    def test_minimal_creation(self):
        """Test creating a minimal activity."""
        activity = GoalActivity(
            id=1,
            goal_id=10,
            activity_type="status_change",
        )
        assert activity.id == 1
        assert activity.goal_id == 10
        assert activity.activity_type == "status_change"
        assert activity.description is None
        assert activity.tokens_used == 0
        assert activity.duration_ms == 0

    def test_full_creation(self):
        """Test creating a full activity."""
        activity = GoalActivity(
            id=1,
            goal_id=10,
            activity_type="progress_update",
            description="Updated progress to 50%",
            old_value="25",
            new_value="50",
            actor_type="agent",
            actor_id=100,
            tokens_used=500,
            duration_ms=1500,
        )
        assert activity.description == "Updated progress to 50%"
        assert activity.old_value == "25"
        assert activity.new_value == "50"
        assert activity.actor_type == "agent"
        assert activity.actor_id == 100
        assert activity.tokens_used == 500
        assert activity.duration_ms == 1500


class TestGoalManager:
    """Test GoalManager class."""

    def test_creation_without_db(self):
        """Test creating a goal manager without database."""
        manager = GoalManager()
        assert manager.db_service is None
        assert manager.event_bus is not None

    def test_creation_with_event_bus(self):
        """Test creating a goal manager with custom event bus."""
        event_bus = EventBus()
        manager = GoalManager(event_bus=event_bus)
        assert manager.event_bus is event_bus

    def test_creation_with_db(self):
        """Test creating a goal manager with database."""

        class MockDB:
            pass

        db = MockDB()
        manager = GoalManager(db_service=db)
        assert manager.db_service is db
