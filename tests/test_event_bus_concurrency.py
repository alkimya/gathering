"""
Concurrency tests for the Event Bus.

Proves PERF-04 (batching/dedup under load) and TEST-04 (concurrency correctness):
- Parallel handler execution without data corruption
- Rapid-fire publishing without unbounded task spawning
- Event ordering preservation per handler
- Deduplication of identical rapid-fire events
- Dedup pass-through for semantically distinct events
- Semaphore-based concurrency limiting
- Error isolation under concurrent execution
"""

import asyncio
import pytest

from gathering.events import Event, EventType, EventBus


@pytest.fixture(autouse=True)
def reset_event_bus():
    """Fresh event bus for each test."""
    bus = EventBus()
    bus.reset()
    yield bus
    bus.reset()


@pytest.mark.asyncio
async def test_parallel_handlers_no_race_condition(reset_event_bus):
    """Concurrent handlers execute without data corruption.

    10 handlers each increment a shared counter under asyncio.Lock.
    All handlers must run exactly once per published event.
    """
    bus = reset_event_bus
    counter = {"value": 0}
    lock = asyncio.Lock()

    async def counting_handler(event: Event):
        async with lock:
            counter["value"] += 1

    # Subscribe 10 handlers
    for _ in range(10):
        bus.subscribe(EventType.TASK_COMPLETED, counting_handler)

    await bus.publish(Event(
        type=EventType.TASK_COMPLETED,
        data={"test": "parallel"},
    ))

    assert counter["value"] == 10, (
        f"Expected 10 handler invocations, got {counter['value']}"
    )


@pytest.mark.asyncio
async def test_rapid_fire_does_not_exhaust_memory(reset_event_bus):
    """Rapid-fire publishing handles load without spawning unbounded tasks.

    Publishes 200 events with unique data rapidly with dedup disabled.
    All events must be delivered and no asyncio tasks should leak.
    """
    bus = reset_event_bus
    bus.configure(dedup_enabled=False)
    received = []

    async def collector_handler(event: Event):
        received.append(event.data["seq"])

    bus.subscribe(EventType.TASK_COMPLETED, collector_handler)

    # Snapshot tasks before
    tasks_before = len(asyncio.all_tasks())

    # Publish 200 events rapidly with unique data
    for i in range(200):
        await bus.publish(Event(
            type=EventType.TASK_COMPLETED,
            data={"seq": i},
        ))

    assert len(received) == 200, (
        f"Expected 200 events delivered, got {len(received)}"
    )

    # Check no leaked tasks (allow small margin for test infrastructure)
    tasks_after = len(asyncio.all_tasks())
    assert tasks_after <= tasks_before + 5, (
        f"Task leak detected: {tasks_before} before, {tasks_after} after"
    )


@pytest.mark.asyncio
async def test_event_ordering_preserved(reset_event_bus):
    """Per-handler event ordering is maintained under sequential publish.

    Events published in sequence must be delivered in the same order
    to each handler.
    """
    bus = reset_event_bus
    bus.configure(dedup_enabled=False)
    order = []

    async def order_handler(event: Event):
        order.append(event.data["seq"])

    bus.subscribe(EventType.TASK_COMPLETED, order_handler)

    for i in range(50):
        await bus.publish(Event(
            type=EventType.TASK_COMPLETED,
            data={"seq": i},
        ))

    assert order == list(range(50)), (
        f"Event ordering broken: expected 0..49, got {order[:10]}..."
    )


@pytest.mark.asyncio
async def test_deduplication_suppresses_identical_events(reset_event_bus):
    """Deduplication suppresses truly identical rapid-fire events.

    Publishing the same event (same type, data, source) 10 times rapidly
    should deliver only the first one within the dedup window.
    """
    bus = reset_event_bus
    bus.configure(dedup_enabled=True)
    received = []

    async def dedup_handler(event: Event):
        received.append(event)

    bus.subscribe(EventType.TASK_COMPLETED, dedup_handler)

    # Publish the SAME event 10 times rapidly
    for _ in range(10):
        await bus.publish(Event(
            type=EventType.TASK_COMPLETED,
            data={"action": "save"},
            source_agent_id=1,
            circle_id=1,
        ))

    assert len(received) == 1, (
        f"Expected 1 delivery (9 deduped), got {len(received)}"
    )

    # Verify stats track deduplication
    stats = bus.get_stats()
    assert stats["events_deduplicated"] == 9, (
        f"Expected 9 deduped events, got {stats['events_deduplicated']}"
    )


@pytest.mark.asyncio
async def test_dedup_allows_distinct_events(reset_event_bus):
    """Dedup does not suppress semantically different events.

    Events with different data payloads should all be delivered
    even when dedup is enabled.
    """
    bus = reset_event_bus
    bus.configure(dedup_enabled=True)
    received = []

    async def distinct_handler(event: Event):
        received.append(event.data["id"])

    bus.subscribe(EventType.TASK_COMPLETED, distinct_handler)

    # Publish 10 events with DIFFERENT data
    for i in range(10):
        await bus.publish(Event(
            type=EventType.TASK_COMPLETED,
            data={"id": i},
        ))

    assert len(received) == 10, (
        f"Expected 10 distinct events delivered, got {len(received)}"
    )
    assert received == list(range(10)), (
        f"Expected ids 0..9, got {received}"
    )


@pytest.mark.asyncio
async def test_semaphore_limits_concurrent_handlers(reset_event_bus):
    """Semaphore backpressure limits concurrent handler execution.

    With max_concurrent_handlers=3 and 10 handlers, at most 3 should
    execute simultaneously.
    """
    bus = reset_event_bus
    bus.configure(max_concurrent_handlers=3)

    current_concurrent = {"value": 0}
    max_concurrent = {"value": 0}
    lock = asyncio.Lock()

    async def tracked_handler(event: Event):
        async with lock:
            current_concurrent["value"] += 1
            if current_concurrent["value"] > max_concurrent["value"]:
                max_concurrent["value"] = current_concurrent["value"]
        # Simulate work to allow concurrency overlap
        await asyncio.sleep(0.01)
        async with lock:
            current_concurrent["value"] -= 1

    # Subscribe 10 handlers
    for _ in range(10):
        bus.subscribe(EventType.TASK_COMPLETED, tracked_handler)

    await bus.publish(Event(
        type=EventType.TASK_COMPLETED,
        data={"test": "semaphore"},
    ))

    assert max_concurrent["value"] <= 3, (
        f"Semaphore violated: max concurrent was {max_concurrent['value']}, limit is 3"
    )
    assert max_concurrent["value"] >= 1, (
        "At least one handler must have executed"
    )


@pytest.mark.asyncio
async def test_handler_error_does_not_block_others(reset_event_bus):
    """Error in one handler does not block other handlers from executing.

    One handler raises an exception; two others must still complete.
    """
    bus = reset_event_bus
    results = []

    async def error_handler(event: Event):
        raise RuntimeError("Intentional test error")

    async def good_handler_a(event: Event):
        results.append("a")

    async def good_handler_b(event: Event):
        results.append("b")

    bus.subscribe(EventType.TASK_COMPLETED, error_handler)
    bus.subscribe(EventType.TASK_COMPLETED, good_handler_a)
    bus.subscribe(EventType.TASK_COMPLETED, good_handler_b)

    await bus.publish(Event(
        type=EventType.TASK_COMPLETED,
        data={"test": "error_isolation"},
    ))

    assert len(results) == 2, (
        f"Expected 2 successful handlers, got {len(results)}"
    )
    assert "a" in results and "b" in results, (
        f"Expected both 'a' and 'b' in results, got {results}"
    )

    # Verify error was tracked
    stats = bus.get_stats()
    assert stats["handler_errors"] == 1
