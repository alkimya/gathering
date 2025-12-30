"""
Tests for Event Bus system.

Test coverage:
- Event creation and filtering
- Subscribe/unsubscribe
- Publish and handler execution
- Concurrent handler execution
- Error isolation
- Event history
- Statistics
"""

import asyncio
import pytest
from datetime import datetime, timezone

from gathering.events import Event, EventType, EventBus, event_bus


@pytest.fixture
def bus():
    """Fresh event bus for each test."""
    bus = EventBus()
    bus.reset()  # Clear any existing state
    yield bus
    bus.reset()  # Cleanup


class TestEvent:
    """Test Event class."""

    def test_event_creation(self):
        """Test creating an event."""
        event = Event(
            type=EventType.TASK_COMPLETED,
            data={"task_id": 123},
            source_agent_id=1,
            circle_id=2,
        )

        assert event.type == EventType.TASK_COMPLETED
        assert event.data == {"task_id": 123}
        assert event.source_agent_id == 1
        assert event.circle_id == 2
        assert event.timestamp is not None
        assert event.id is not None

    def test_event_auto_timestamp(self):
        """Test that timestamp is auto-generated."""
        before = datetime.now(timezone.utc)
        event = Event(type=EventType.AGENT_STARTED)
        after = datetime.now(timezone.utc)

        assert before <= event.timestamp <= after

    def test_event_auto_id(self):
        """Test that ID is auto-generated and unique."""
        event1 = Event(type=EventType.TASK_CREATED)
        event2 = Event(type=EventType.TASK_CREATED)

        assert event1.id is not None
        assert event2.id is not None
        assert event1.id != event2.id

    def test_event_matches_filter(self):
        """Test event filtering."""
        event = Event(
            type=EventType.TASK_COMPLETED,
            source_agent_id=1,
            circle_id=2,
        )

        assert event.matches_filter(source_agent_id=1)
        assert event.matches_filter(circle_id=2)
        assert event.matches_filter(source_agent_id=1, circle_id=2)
        assert not event.matches_filter(source_agent_id=99)
        assert not event.matches_filter(circle_id=99)


class TestEventBus:
    """Test EventBus class."""

    def test_singleton(self):
        """Test that EventBus is a singleton."""
        bus1 = EventBus()
        bus2 = EventBus()
        assert bus1 is bus2

    def test_subscribe(self, bus):
        """Test subscribing to events."""
        called = []

        async def handler(event: Event):
            called.append(event)

        sub_id = bus.subscribe(EventType.TASK_COMPLETED, handler)

        assert sub_id is not None
        assert len(called) == 0

    def test_unsubscribe(self, bus):
        """Test unsubscribing."""
        async def handler(event: Event):
            pass

        sub_id = bus.subscribe(EventType.TASK_COMPLETED, handler)
        assert bus.unsubscribe(sub_id)
        assert not bus.unsubscribe(sub_id)  # Already removed

    @pytest.mark.asyncio
    async def test_publish_simple(self, bus):
        """Test publishing and receiving events."""
        received = []

        async def handler(event: Event):
            received.append(event)

        bus.subscribe(EventType.TASK_COMPLETED, handler)

        event = Event(
            type=EventType.TASK_COMPLETED,
            data={"task_id": 123},
        )

        await bus.publish(event)

        assert len(received) == 1
        assert received[0].type == EventType.TASK_COMPLETED
        assert received[0].data == {"task_id": 123}

    @pytest.mark.asyncio
    async def test_publish_multiple_handlers(self, bus):
        """Test that all subscribed handlers receive events."""
        calls = {"h1": 0, "h2": 0, "h3": 0}

        async def handler1(event: Event):
            calls["h1"] += 1

        async def handler2(event: Event):
            calls["h2"] += 1

        def handler3(event: Event):  # Sync handler
            calls["h3"] += 1

        bus.subscribe(EventType.TASK_COMPLETED, handler1)
        bus.subscribe(EventType.TASK_COMPLETED, handler2)
        bus.subscribe(EventType.TASK_COMPLETED, handler3)

        await bus.publish(Event(type=EventType.TASK_COMPLETED))

        assert calls["h1"] == 1
        assert calls["h2"] == 1
        assert calls["h3"] == 1

    @pytest.mark.asyncio
    async def test_publish_with_filter(self, bus):
        """Test publishing with subscriber filters."""
        received = []

        async def handler(event: Event):
            received.append(event)

        # Subscribe only to events from circle 1
        bus.subscribe(
            EventType.TASK_COMPLETED,
            handler,
            filter_fn=lambda e: e.circle_id == 1
        )

        # This should be received
        await bus.publish(Event(
            type=EventType.TASK_COMPLETED,
            circle_id=1,
        ))

        # This should NOT be received
        await bus.publish(Event(
            type=EventType.TASK_COMPLETED,
            circle_id=2,
        ))

        assert len(received) == 1
        assert received[0].circle_id == 1

    @pytest.mark.asyncio
    async def test_handler_error_isolation(self, bus):
        """Test that errors in one handler don't affect others."""
        calls = []

        async def good_handler(event: Event):
            calls.append("good")

        async def bad_handler(event: Event):
            raise ValueError("Handler error!")

        async def another_good_handler(event: Event):
            calls.append("another_good")

        bus.subscribe(EventType.TASK_COMPLETED, good_handler)
        bus.subscribe(EventType.TASK_COMPLETED, bad_handler)
        bus.subscribe(EventType.TASK_COMPLETED, another_good_handler)

        await bus.publish(Event(type=EventType.TASK_COMPLETED))

        # Both good handlers should have been called
        assert "good" in calls
        assert "another_good" in calls

        # Error should be tracked in stats
        stats = bus.get_stats()
        assert stats["handler_errors"] == 1

    @pytest.mark.asyncio
    async def test_concurrent_execution(self, bus):
        """Test that handlers run concurrently."""
        start_times = []
        end_times = []

        async def slow_handler(event: Event):
            start_times.append(asyncio.get_event_loop().time())
            await asyncio.sleep(0.1)
            end_times.append(asyncio.get_event_loop().time())

        # Subscribe 3 handlers
        bus.subscribe(EventType.TASK_COMPLETED, slow_handler)
        bus.subscribe(EventType.TASK_COMPLETED, slow_handler)
        bus.subscribe(EventType.TASK_COMPLETED, slow_handler)

        start = asyncio.get_event_loop().time()
        await bus.publish(Event(type=EventType.TASK_COMPLETED))
        duration = asyncio.get_event_loop().time() - start

        # If sequential: 3 * 0.1 = 0.3s
        # If concurrent: ~0.1s
        assert duration < 0.2  # Should be closer to 0.1 than 0.3

        # All handlers should have started before any finished
        assert len(start_times) == 3
        assert len(end_times) == 3
        assert max(start_times) < min(end_times)

    @pytest.mark.asyncio
    async def test_no_subscribers(self, bus):
        """Test publishing when no one is listening."""
        # Should not raise
        await bus.publish(Event(type=EventType.TASK_COMPLETED))

        stats = bus.get_stats()
        assert stats["events_published"] == 1
        assert stats["events_delivered"] == 0

    def test_event_history(self, bus):
        """Test event history tracking."""
        bus.clear_history()

        # Publish some events (synchronously for test simplicity)
        event1 = Event(type=EventType.TASK_CREATED, data={"id": 1})
        event2 = Event(type=EventType.TASK_COMPLETED, data={"id": 2})
        event3 = Event(type=EventType.TASK_FAILED, data={"id": 3})

        asyncio.run(bus.publish(event1))
        asyncio.run(bus.publish(event2))
        asyncio.run(bus.publish(event3))

        # Get all history
        history = bus.get_history()
        assert len(history) == 3
        assert history[0].data == {"id": 3}  # Most recent first
        assert history[2].data == {"id": 1}

        # Filter by type
        completed = bus.get_history(EventType.TASK_COMPLETED)
        assert len(completed) == 1
        assert completed[0].data == {"id": 2}

        # Limit
        limited = bus.get_history(limit=2)
        assert len(limited) == 2

    def test_event_history_with_filters(self, bus):
        """Test filtering event history."""
        bus.clear_history()

        asyncio.run(bus.publish(Event(
            type=EventType.TASK_COMPLETED,
            circle_id=1,
        )))
        asyncio.run(bus.publish(Event(
            type=EventType.TASK_COMPLETED,
            circle_id=2,
        )))
        asyncio.run(bus.publish(Event(
            type=EventType.TASK_FAILED,
            circle_id=1,
        )))

        # Filter by circle_id
        circle1 = bus.get_history(circle_id=1)
        assert len(circle1) == 2

        # Filter by type and circle_id
        circle1_completed = bus.get_history(
            EventType.TASK_COMPLETED,
            circle_id=1
        )
        assert len(circle1_completed) == 1

    def test_history_circular_buffer(self, bus):
        """Test that history is limited to max size."""
        bus.clear_history()
        bus._max_history = 10

        # Publish 20 events
        for i in range(20):
            asyncio.run(bus.publish(Event(
                type=EventType.TASK_CREATED,
                data={"id": i}
            )))

        history = bus.get_history()
        assert len(history) == 10
        # Should keep most recent
        assert history[0].data["id"] == 19
        assert history[9].data["id"] == 10

    def test_stats(self, bus):
        """Test statistics tracking."""
        bus.reset()

        async def handler(event: Event):
            pass

        bus.subscribe(EventType.TASK_COMPLETED, handler)
        bus.subscribe(EventType.TASK_FAILED, handler)

        asyncio.run(bus.publish(Event(type=EventType.TASK_COMPLETED)))
        asyncio.run(bus.publish(Event(type=EventType.TASK_COMPLETED)))

        stats = bus.get_stats()
        assert stats["events_published"] == 2
        assert stats["events_delivered"] == 2
        assert stats["active_subscribers"] == 2
        assert stats["handler_errors"] == 0


class TestGlobalEventBus:
    """Test the global event_bus singleton."""

    def test_global_singleton(self):
        """Test that global event_bus is the same as EventBus()."""
        assert event_bus is EventBus()

    @pytest.mark.asyncio
    async def test_global_usage(self):
        """Test using the global event_bus."""
        event_bus.reset()
        received = []

        async def handler(event: Event):
            received.append(event)

        event_bus.subscribe(EventType.AGENT_STARTED, handler)
        await event_bus.publish(Event(type=EventType.AGENT_STARTED))

        assert len(received) == 1


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    @pytest.mark.asyncio
    async def test_agent_task_workflow(self, bus):
        """Test complete agent task workflow with events."""
        workflow = []

        async def on_task_created(event: Event):
            workflow.append(f"created:{event.data['task_id']}")

        async def on_task_assigned(event: Event):
            workflow.append(f"assigned:{event.data['task_id']}")

        async def on_task_completed(event: Event):
            workflow.append(f"completed:{event.data['task_id']}")

        bus.subscribe(EventType.TASK_CREATED, on_task_created)
        bus.subscribe(EventType.TASK_ASSIGNED, on_task_assigned)
        bus.subscribe(EventType.TASK_COMPLETED, on_task_completed)

        # Simulate workflow
        task_id = 123
        await bus.publish(Event(
            type=EventType.TASK_CREATED,
            data={"task_id": task_id}
        ))
        await bus.publish(Event(
            type=EventType.TASK_ASSIGNED,
            data={"task_id": task_id, "agent_id": 1}
        ))
        await bus.publish(Event(
            type=EventType.TASK_COMPLETED,
            data={"task_id": task_id, "result": "success"}
        ))

        assert workflow == [
            "created:123",
            "assigned:123",
            "completed:123",
        ]

    @pytest.mark.asyncio
    async def test_circle_coordination(self, bus):
        """Test circle members coordinating via events."""
        agent1_received = []
        agent2_received = []

        # Agent 1 listens to circle 5 events
        async def agent1_handler(event: Event):
            agent1_received.append(event.data)

        bus.subscribe(
            EventType.MEMORY_SHARED,
            agent1_handler,
            filter_fn=lambda e: e.circle_id == 5
        )

        # Agent 2 also listens to circle 5
        async def agent2_handler(event: Event):
            agent2_received.append(event.data)

        bus.subscribe(
            EventType.MEMORY_SHARED,
            agent2_handler,
            filter_fn=lambda e: e.circle_id == 5
        )

        # Agent 1 shares knowledge in circle 5
        await bus.publish(Event(
            type=EventType.MEMORY_SHARED,
            data={"content": "Use PostgreSQL for database"},
            source_agent_id=1,
            circle_id=5,
        ))

        # Both agents should receive
        assert len(agent1_received) == 1
        assert len(agent2_received) == 1

        # Event from different circle shouldn't be received
        await bus.publish(Event(
            type=EventType.MEMORY_SHARED,
            circle_id=999,
        ))

        assert len(agent1_received) == 1
        assert len(agent2_received) == 1
