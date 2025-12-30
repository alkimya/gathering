"""
Tests for the Gathering Circle orchestration system.
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from gathering.orchestration import (
    GatheringCircle,
    AgentHandle,
    CircleTask,
    CircleStatus,
    Facilitator,
    EventBus,
    EventType,
    Event,
    Conflict,
    ConflictType,
    AgentMetrics,
)


class TestEventBus:
    """Tests for the EventBus."""

    @pytest.fixture
    def event_bus(self):
        return EventBus()

    @pytest.mark.asyncio
    async def test_emit_and_subscribe(self, event_bus):
        """Test basic emit and subscribe."""
        received_events = []

        async def handler(event: Event):
            received_events.append(event)

        event_bus.subscribe(EventType.TASK_CREATED, handler)

        await event_bus.emit(
            EventType.TASK_CREATED,
            {"task_id": 1, "title": "Test task"},
        )

        assert len(received_events) == 1
        assert received_events[0].type == EventType.TASK_CREATED
        assert received_events[0].data["task_id"] == 1

    @pytest.mark.asyncio
    async def test_wildcard_subscription(self, event_bus):
        """Test wildcard (all events) subscription."""
        received_events = []

        async def handler(event: Event):
            received_events.append(event)

        event_bus.subscribe(None, handler)  # Subscribe to all

        await event_bus.emit(EventType.TASK_CREATED, {"id": 1})
        await event_bus.emit(EventType.AGENT_JOINED, {"id": 2})

        assert len(received_events) == 2

    @pytest.mark.asyncio
    async def test_unsubscribe(self, event_bus):
        """Test unsubscribe functionality."""
        received_events = []

        async def handler(event: Event):
            received_events.append(event)

        unsubscribe = event_bus.subscribe(EventType.TASK_CREATED, handler)
        await event_bus.emit(EventType.TASK_CREATED, {"id": 1})

        unsubscribe()
        await event_bus.emit(EventType.TASK_CREATED, {"id": 2})

        assert len(received_events) == 1

    @pytest.mark.asyncio
    async def test_event_history(self, event_bus):
        """Test event history."""
        await event_bus.emit(EventType.TASK_CREATED, {"id": 1})
        await event_bus.emit(EventType.TASK_CREATED, {"id": 2})
        await event_bus.emit(EventType.AGENT_JOINED, {"id": 3})

        history = event_bus.get_history()
        assert len(history) == 3

        task_history = event_bus.get_history(event_type=EventType.TASK_CREATED)
        assert len(task_history) == 2

    @pytest.mark.asyncio
    async def test_sync_handler(self, event_bus):
        """Test that sync handlers work."""
        received = []

        def sync_handler(event: Event):
            received.append(event)

        event_bus.subscribe(EventType.TASK_CREATED, sync_handler)
        await event_bus.emit(EventType.TASK_CREATED, {"id": 1})

        assert len(received) == 1


class TestFacilitator:
    """Tests for the Facilitator."""

    @pytest.fixture
    def facilitator(self):
        event_bus = EventBus()
        return Facilitator(event_bus)

    def test_register_agent(self, facilitator):
        """Test agent registration."""
        facilitator.register_agent(
            agent_id=1,
            name="Claude",
            competencies=["python", "architecture"],
            can_review=["code"],
        )

        active = facilitator.get_active_agents()
        assert len(active) == 1
        assert active[0]["name"] == "Claude"

    def test_unregister_agent(self, facilitator):
        """Test agent unregistration."""
        facilitator.register_agent(1, "Claude", ["python"])
        facilitator.unregister_agent(1)

        active = facilitator.get_active_agents()
        assert len(active) == 0

    @pytest.mark.asyncio
    async def test_route_task(self, facilitator):
        """Test task routing."""
        facilitator.register_agent(
            agent_id=1,
            name="Claude",
            competencies=["python", "api"],
        )
        facilitator.register_agent(
            agent_id=2,
            name="DeepSeek",
            competencies=["python", "testing"],
        )

        # Route a python task - both agents qualify
        agent_id = await facilitator.route_task(
            task_id=100,
            title="Write Python code",
            required_competencies=["python"],
        )

        assert agent_id in [1, 2]

    @pytest.mark.asyncio
    async def test_route_task_no_match(self, facilitator):
        """Test routing when no agent matches."""
        facilitator.register_agent(
            agent_id=1,
            name="Claude",
            competencies=["python"],
        )

        agent_id = await facilitator.route_task(
            task_id=100,
            title="Write Rust code",
            required_competencies=["rust"],
        )

        assert agent_id is None

    @pytest.mark.asyncio
    async def test_route_with_excluded_agents(self, facilitator):
        """Test routing with excluded agents."""
        facilitator.register_agent(1, "Claude", ["python"])
        facilitator.register_agent(2, "DeepSeek", ["python"])

        agent_id = await facilitator.route_task(
            task_id=100,
            title="Python task",
            required_competencies=["python"],
            excluded_agents=[1],
        )

        assert agent_id == 2

    def test_file_collision_detection(self, facilitator):
        """Test file collision conflict detection."""
        facilitator.register_agent(1, "Claude", ["python"])
        facilitator.register_agent(2, "DeepSeek", ["python"])

        # First agent accesses file
        conflict1 = facilitator.register_file_access("src/main.py", 1)
        assert conflict1 is None

        # Second agent tries to access same file
        conflict2 = facilitator.register_file_access("src/main.py", 2)
        assert conflict2 is not None
        assert conflict2.type == ConflictType.FILE_COLLISION
        assert set(conflict2.agent_ids) == {1, 2}

    def test_file_release(self, facilitator):
        """Test file release."""
        facilitator.register_agent(1, "Claude", ["python"])
        facilitator.register_agent(2, "DeepSeek", ["python"])

        facilitator.register_file_access("src/main.py", 1)
        facilitator.release_file("src/main.py", 1)

        # Now second agent can access
        conflict = facilitator.register_file_access("src/main.py", 2)
        assert conflict is None

    def test_agent_metrics(self, facilitator):
        """Test agent metrics tracking."""
        facilitator.register_agent(1, "Claude", ["python"])

        metrics = facilitator.get_agent_metrics(1)
        assert metrics is not None
        assert metrics.tasks_completed == 0
        assert metrics.current_workload == 0


class TestGatheringCircle:
    """Tests for the GatheringCircle."""

    @pytest.fixture
    def circle(self):
        return GatheringCircle(name="test-circle", auto_route=False)

    @pytest.fixture
    def circle_with_agents(self, circle):
        circle.add_agent(AgentHandle(
            id=1,
            name="Claude",
            provider="anthropic",
            model="claude-3-opus",
            competencies=["python", "architecture"],
            can_review=["code", "architecture"],
        ))
        circle.add_agent(AgentHandle(
            id=2,
            name="DeepSeek",
            provider="deepseek",
            model="deepseek-coder",
            competencies=["python", "testing"],
            can_review=["code"],
        ))
        return circle

    @pytest.mark.asyncio
    async def test_circle_lifecycle(self, circle):
        """Test circle start and stop."""
        assert circle.status == CircleStatus.INITIALIZING

        await circle.start()
        assert circle.status == CircleStatus.RUNNING

        await circle.stop()
        assert circle.status == CircleStatus.STOPPED

    def test_add_agent(self, circle):
        """Test adding an agent."""
        agent = AgentHandle(
            id=1,
            name="Claude",
            provider="anthropic",
            model="claude-3-opus",
            competencies=["python"],
            can_review=["code"],
        )
        circle.add_agent(agent)

        assert circle.get_agent(1) is not None
        assert len(circle.get_agents()) == 1

    def test_remove_agent(self, circle_with_agents):
        """Test removing an agent."""
        circle_with_agents.remove_agent(1)

        agent = circle_with_agents.get_agent(1)
        assert agent.is_active is False

    @pytest.mark.asyncio
    async def test_create_task(self, circle_with_agents):
        """Test task creation."""
        await circle_with_agents.start()

        task_id = await circle_with_agents.create_task(
            title="Test task",
            description="A test task",
            required_competencies=["python"],
        )

        task = circle_with_agents.get_task(task_id)
        assert task is not None
        assert task.title == "Test task"
        assert task.status == "pending"

    @pytest.mark.asyncio
    async def test_claim_task(self, circle_with_agents):
        """Test claiming a task."""
        await circle_with_agents.start()

        task_id = await circle_with_agents.create_task(
            title="Test task",
            description="A test task",
            required_competencies=["python"],
        )

        success = await circle_with_agents.claim_task(task_id, agent_id=1)
        assert success is True

        task = circle_with_agents.get_task(task_id)
        assert task.status == "in_progress"
        assert task.assigned_agent_id == 1

    @pytest.mark.asyncio
    async def test_submit_task(self, circle_with_agents):
        """Test submitting task work."""
        circle = circle_with_agents
        circle.require_review = False  # Skip review for this test
        await circle.start()

        task_id = await circle.create_task(
            title="Test task",
            description="A test task",
            required_competencies=["python"],
        )

        await circle.claim_task(task_id, agent_id=1)

        await circle.submit_task(
            task_id=task_id,
            agent_id=1,
            result="Task completed successfully",
            artifacts=["src/feature.py"],
        )

        task = circle.get_task(task_id)
        assert task.status == "completed"
        assert task.result == "Task completed successfully"

    @pytest.mark.asyncio
    async def test_submit_task_with_review(self, circle_with_agents):
        """Test submitting task triggers review."""
        circle = circle_with_agents
        circle.require_review = True
        await circle.start()

        task_id = await circle.create_task(
            title="Test task",
            description="A test task",
            required_competencies=["python"],
        )

        await circle.claim_task(task_id, agent_id=1)

        await circle.submit_task(
            task_id=task_id,
            agent_id=1,
            result="Task completed",
        )

        task = circle.get_task(task_id)
        assert task.status == "review"

    @pytest.mark.asyncio
    async def test_review_approved(self, circle_with_agents):
        """Test review approval."""
        circle = circle_with_agents
        circle.require_review = True
        await circle.start()

        task_id = await circle.create_task(
            title="Test task",
            description="A test task",
            required_competencies=["python"],
        )

        await circle.claim_task(task_id, agent_id=1)
        await circle.submit_task(task_id, agent_id=1, result="Done")

        await circle.submit_review(
            task_id=task_id,
            reviewer_id=2,
            status="approved",
            score=90,
            feedback="Great work!",
        )

        task = circle.get_task(task_id)
        assert task.status == "completed"

    @pytest.mark.asyncio
    async def test_review_changes_requested(self, circle_with_agents):
        """Test review with changes requested."""
        circle = circle_with_agents
        circle.require_review = True
        await circle.start()

        task_id = await circle.create_task(
            title="Test task",
            description="A test task",
            required_competencies=["python"],
        )

        await circle.claim_task(task_id, agent_id=1)
        await circle.submit_task(task_id, agent_id=1, result="Done")

        await circle.submit_review(
            task_id=task_id,
            reviewer_id=2,
            status="changes_requested",
            score=60,
            feedback="Needs improvement",
            changes=["Fix bug in line 42"],
        )

        task = circle.get_task(task_id)
        assert task.status == "in_progress"
        assert task.iteration == 2

    @pytest.mark.asyncio
    async def test_escalation(self, circle_with_agents):
        """Test escalation to human."""
        circle = circle_with_agents
        circle.require_review = True
        await circle.start()

        escalation_received = []

        async def handle_escalation(data):
            escalation_received.append(data)

        circle.on_escalation(handle_escalation)

        task_id = await circle.create_task(
            title="Test task",
            description="A test task",
            required_competencies=["python"],
        )

        await circle.claim_task(task_id, agent_id=1)
        await circle.submit_task(task_id, agent_id=1, result="Done")

        await circle.submit_review(
            task_id=task_id,
            reviewer_id=2,
            status="rejected",
            score=20,
            feedback="Completely wrong approach",
        )

        # Give async handlers time to run
        await asyncio.sleep(0.1)

        assert len(escalation_received) == 1
        assert "rejected" in escalation_received[0]["reason"].lower()

    @pytest.mark.asyncio
    async def test_send_message(self, circle_with_agents):
        """Test sending messages with mentions."""
        circle = circle_with_agents
        await circle.start()

        mention_events = []

        @circle.event_bus.on(EventType.MENTION_RECEIVED)
        async def on_mention(event):
            mention_events.append(event)

        await circle.send_message(
            from_agent_id=1,
            content="Hey @DeepSeek, can you review this?",
            mentions=[2],
        )

        assert len(mention_events) == 1
        assert mention_events[0].data["mentioned_agent_id"] == 2

    def test_circle_status(self, circle_with_agents):
        """Test getting circle status."""
        status = circle_with_agents.get_circle_status()

        assert status["name"] == "test-circle"
        assert status["agents"]["total"] == 2
        assert status["tasks"]["total"] == 0

    def test_agent_workload(self, circle_with_agents):
        """Test getting agent workload."""
        workload = circle_with_agents.get_agent_workload()

        assert 1 in workload
        assert 2 in workload
        assert workload[1]["name"] == "Claude"
        assert workload[2]["name"] == "DeepSeek"


class TestAgentHandle:
    """Tests for AgentHandle."""

    def test_agent_handle_creation(self):
        """Test creating an agent handle."""
        agent = AgentHandle(
            id=1,
            name="Claude",
            provider="anthropic",
            model="claude-3-opus",
            competencies=["python", "architecture"],
            can_review=["code"],
            persona="You are a helpful assistant.",
        )

        assert agent.id == 1
        assert agent.name == "Claude"
        assert agent.is_active is True
        assert agent.current_task_id is None

    @pytest.mark.asyncio
    async def test_agent_with_callbacks(self):
        """Test agent handle with callbacks."""
        accept_called = []
        execute_called = []

        async def accept_task(task_data):
            accept_called.append(task_data)
            return True

        async def execute_task(task_data):
            execute_called.append(task_data)
            return {"result": "Done"}

        agent = AgentHandle(
            id=1,
            name="Claude",
            provider="anthropic",
            model="claude-3-opus",
            competencies=["python"],
            can_review=["code"],
            accept_task=accept_task,
            execute_task=execute_task,
        )

        # Test accept callback
        result = await agent.accept_task({"task_id": 1})
        assert result is True
        assert len(accept_called) == 1


class TestCircleTask:
    """Tests for CircleTask."""

    def test_task_creation(self):
        """Test creating a task."""
        task = CircleTask(
            id=1,
            title="Test task",
            description="A test task",
            required_competencies=["python"],
            priority=3,
        )

        assert task.id == 1
        assert task.status == "pending"
        assert task.iteration == 1
        assert task.created_at is not None


class TestAgentMetrics:
    """Tests for AgentMetrics."""

    def test_availability_score(self):
        """Test availability score calculation."""
        metrics = AgentMetrics()

        # No workload = full availability
        assert metrics.calculate_availability_score() == 1.0

        # Some workload
        metrics.current_workload = 2
        assert metrics.calculate_availability_score() == 0.6

        # Max workload
        metrics.current_workload = 5
        assert metrics.calculate_availability_score() == 0.0

        # Over max
        metrics.current_workload = 10
        assert metrics.calculate_availability_score() == 0.0
