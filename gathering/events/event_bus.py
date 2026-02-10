"""
Event Bus - Lightweight asynchronous event system.

The Event Bus enables decoupled communication between components:
- Agents can publish events when completing tasks
- Circle members can subscribe to circle events
- Memory system can broadcast shared knowledge
- Dashboard can receive real-time updates

Design principles:
- Simple: Subscribe, publish, done
- Fast: Async concurrent execution
- Type-safe: Enum-based event types
- Testable: Easy to mock and verify
- Reliable: Exception isolation per handler
- Resilient: Backpressure via semaphore, deduplication within configurable window
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from collections import defaultdict, deque


class EventType(str, Enum):
    """
    Event types in the GatheRing system.

    Organized by domain for clarity:
    - agent.*: Agent lifecycle and actions
    - memory.*: Knowledge sharing
    - circle.*: Circle coordination
    - conversation.*: Inter-agent communication
    - task.*: Task management
    """

    # Agent events
    AGENT_STARTED = "agent.started"
    AGENT_STOPPED = "agent.stopped"
    AGENT_TASK_ASSIGNED = "agent.task.assigned"
    AGENT_TASK_COMPLETED = "agent.task.completed"
    AGENT_TASK_FAILED = "agent.task.failed"
    AGENT_TOOL_EXECUTED = "agent.tool.executed"

    # Memory events
    MEMORY_CREATED = "memory.created"
    MEMORY_SHARED = "memory.shared"  # Scope: circle/project
    MEMORY_RECALLED = "memory.recalled"

    # Circle events
    CIRCLE_CREATED = "circle.created"
    CIRCLE_STARTED = "circle.started"
    CIRCLE_STOPPED = "circle.stopped"
    CIRCLE_MEMBER_ADDED = "circle.member.added"
    CIRCLE_MEMBER_REMOVED = "circle.member.removed"

    # Task events
    TASK_CREATED = "task.created"
    TASK_ASSIGNED = "task.assigned"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CONFLICT_DETECTED = "task.conflict.detected"

    # Conversation events
    CONVERSATION_MESSAGE = "conversation.message"
    CONVERSATION_TURN_COMPLETE = "conversation.turn.complete"

    # System events
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"


@dataclass
class Event:
    """
    An event in the system.

    Events are immutable records of things that happened.
    They carry just enough data for subscribers to react.

    Attributes:
        type: Event type (enum)
        data: Event-specific payload
        source_agent_id: Agent that triggered the event (optional)
        circle_id: Circle context (optional)
        timestamp: When the event occurred (auto-set)
        id: Unique event ID (auto-generated)
    """

    type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    source_agent_id: Optional[int] = None
    circle_id: Optional[int] = None
    project_id: Optional[int] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: Optional[str] = None

    def __post_init__(self):
        """Generate unique ID if not provided."""
        if self.id is None:
            # Simple ID: timestamp + type
            ts = int(self.timestamp.timestamp() * 1000000)
            self.id = f"{self.type.value}:{ts}"

    def matches_filter(self, **filters) -> bool:
        """
        Check if event matches filter criteria.

        Args:
            **filters: Key-value pairs to match (e.g., circle_id=1)

        Returns:
            True if all filters match

        Examples:
            event.matches_filter(circle_id=1)
            event.matches_filter(source_agent_id=2, circle_id=1)
        """
        for key, value in filters.items():
            if getattr(self, key, None) != value:
                return False
        return True


class EventBus:
    """
    Asynchronous event bus for decoupled communication.

    The event bus is a singleton that manages subscriptions and
    event delivery. Handlers run concurrently and errors are isolated.

    Usage:
        # Subscribe
        async def on_task_complete(event: Event):
            print(f"Task {event.data['task_id']} completed!")

        event_bus.subscribe(EventType.TASK_COMPLETED, on_task_complete)

        # Publish
        await event_bus.publish(Event(
            type=EventType.TASK_COMPLETED,
            data={"task_id": 123, "result": "success"},
            source_agent_id=1,
        ))

    Thread safety:
        The event bus is designed for asyncio (single-threaded).
        For multi-process scenarios, use external message queue (Redis, RabbitMQ).
    """

    _instance: Optional["EventBus"] = None

    def __new__(cls):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize event bus (called only once due to singleton)."""
        if self._initialized:
            return

        # Subscribers: EventType -> List of (handler, filter_fn)
        self._subscribers: Dict[EventType, List[Dict[str, Any]]] = defaultdict(list)

        # Event history using deque for O(1) append and automatic size limiting
        self._max_history = 1000
        self._event_history: deque = deque(maxlen=self._max_history)

        # Backpressure: semaphore limits concurrent handler execution
        self._max_concurrent_handlers: int = 100
        self._handler_semaphore = asyncio.Semaphore(self._max_concurrent_handlers)

        # Deduplication: suppress identical events within a time window
        # Disabled by default for backward compatibility; enable via configure()
        self._dedup_window: float = 1.0  # seconds
        self._seen_events: Dict[str, float] = {}  # dedup_key -> monotonic timestamp
        self._dedup_enabled: bool = False

        # Statistics
        self._stats = {
            "events_published": 0,
            "events_delivered": 0,
            "events_deduplicated": 0,
            "handler_errors": 0,
        }

        self._initialized = True

    def configure(
        self,
        max_concurrent_handlers: Optional[int] = None,
        dedup_window: Optional[float] = None,
        dedup_enabled: Optional[bool] = None,
    ) -> None:
        """
        Configure event bus parameters.

        Args:
            max_concurrent_handlers: Max concurrent handler tasks (default 100)
            dedup_window: Deduplication window in seconds (default 1.0)
            dedup_enabled: Enable/disable deduplication (default True)
        """
        if max_concurrent_handlers is not None:
            self._max_concurrent_handlers = max_concurrent_handlers
            self._handler_semaphore = asyncio.Semaphore(max_concurrent_handlers)
        if dedup_window is not None:
            self._dedup_window = dedup_window
        if dedup_enabled is not None:
            self._dedup_enabled = dedup_enabled

    def _dedup_key(self, event: Event) -> str:
        """Compute deduplication key for an event.

        Includes type, source, circle, and a hash of data for specificity.
        Events with different data will have different keys and will not
        be deduplicated against each other.
        """
        data_hash = hash(frozenset(
            (k, str(v)) for k, v in sorted(event.data.items())
        )) if event.data else 0
        return f"{event.type.value}:{event.source_agent_id}:{event.circle_id}:{data_hash}"

    def _prune_seen_events(self) -> None:
        """Remove expired entries from dedup cache to prevent memory growth."""
        now = time.monotonic()
        expired = [
            k for k, ts in self._seen_events.items()
            if (now - ts) > self._dedup_window * 2
        ]
        for k in expired:
            del self._seen_events[k]

    def subscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], Any],
        filter_fn: Optional[Callable[[Event], bool]] = None,
        name: Optional[str] = None,
    ) -> str:
        """
        Subscribe to an event type.

        Args:
            event_type: Type of event to listen for
            handler: Async function called when event occurs
            filter_fn: Optional function to filter events (return True to receive)
            name: Optional handler name (for debugging)

        Returns:
            Subscription ID (for unsubscribe)

        Examples:
            # Subscribe to all task completions
            event_bus.subscribe(
                EventType.TASK_COMPLETED,
                on_task_complete
            )

            # Subscribe only to tasks in circle 1
            event_bus.subscribe(
                EventType.TASK_COMPLETED,
                on_my_circle_task,
                filter_fn=lambda e: e.circle_id == 1
            )
        """
        # Generate subscription ID
        sub_id = f"{event_type.value}:{len(self._subscribers[event_type])}"

        self._subscribers[event_type].append({
            "id": sub_id,
            "handler": handler,
            "filter": filter_fn,
            "name": name or handler.__name__,
        })

        return sub_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe a handler.

        Args:
            subscription_id: ID returned by subscribe()

        Returns:
            True if found and removed
        """
        event_type_str, _ = subscription_id.split(":", 1)
        event_type = EventType(event_type_str)

        subscribers = self._subscribers.get(event_type, [])
        for i, sub in enumerate(subscribers):
            if sub["id"] == subscription_id:
                subscribers.pop(i)
                return True
        return False

    async def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribers.

        Handlers are executed concurrently with semaphore-based backpressure.
        Errors in one handler don't affect others. Identical events within
        the dedup window are suppressed.

        Args:
            event: Event to publish

        Examples:
            await event_bus.publish(Event(
                type=EventType.TASK_COMPLETED,
                data={"task_id": 123},
                source_agent_id=1,
            ))
        """
        # Deduplication check (before recording in history)
        if self._dedup_enabled:
            dedup_key = self._dedup_key(event)
            now = time.monotonic()
            if dedup_key in self._seen_events:
                if (now - self._seen_events[dedup_key]) < self._dedup_window:
                    self._stats["events_deduplicated"] += 1
                    return  # Duplicate within window, skip
            self._seen_events[dedup_key] = now
            # Periodic cleanup (every 1000 events)
            if self._stats["events_published"] % 1000 == 0:
                self._prune_seen_events()

        # Record event in history (deque handles size limit automatically)
        self._event_history.append(event)

        self._stats["events_published"] += 1

        # Get subscribers for this event type
        subscribers = self._subscribers.get(event.type, [])
        if not subscribers:
            return

        # Collect handlers that pass filter
        tasks = []
        for sub in subscribers:
            # Apply filter if present
            if sub["filter"] and not sub["filter"](event):
                continue

            # Wrap handler to catch exceptions (with semaphore backpressure)
            tasks.append(self._safe_invoke(sub["handler"], event, sub["name"]))

        # Execute all handlers concurrently (bounded by semaphore)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            self._stats["events_delivered"] += len(tasks)

    async def _safe_invoke(self, handler: Callable, event: Event, handler_name: str) -> None:
        """
        Invoke handler with exception isolation and semaphore backpressure.

        The handler_semaphore limits the number of concurrently executing
        handlers, preventing unbounded task spawning under rapid-fire events.

        Args:
            handler: Handler function
            event: Event to pass
            handler_name: Handler name for error logging
        """
        async with self._handler_semaphore:
            try:
                result = handler(event)
                # Handle both sync and async handlers
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                self._stats["handler_errors"] += 1
                # Log error but don't propagate
                # In production, use proper logging
                print(f"[EventBus] Error in handler '{handler_name}': {e}")

    def get_history(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 100,
        **filters
    ) -> List[Event]:
        """
        Get recent event history.

        Args:
            event_type: Filter by event type
            limit: Maximum events to return
            **filters: Additional filters (e.g., circle_id=1)

        Returns:
            List of events, most recent first

        Examples:
            # Get last 10 task completions
            events = event_bus.get_history(
                EventType.TASK_COMPLETED,
                limit=10
            )

            # Get circle 1 events
            events = event_bus.get_history(circle_id=1)
        """
        # Convert deque to list for slicing operations
        events = list(self._event_history)

        # Filter by type
        if event_type:
            events = [e for e in events if e.type == event_type]

        # Filter by attributes
        if filters:
            events = [e for e in events if e.matches_filter(**filters)]

        # Return most recent first
        return list(reversed(events[-limit:]))

    def get_stats(self) -> Dict[str, Any]:
        """
        Get event bus statistics.

        Returns:
            Dict with counts and metrics
        """
        return {
            **self._stats,
            "active_subscribers": sum(len(subs) for subs in self._subscribers.values()),
            "history_size": len(self._event_history),
        }

    def clear_history(self) -> None:
        """Clear event history (useful for testing)."""
        self._event_history.clear()

    def reset(self) -> None:
        """Reset event bus (useful for testing)."""
        self._subscribers.clear()
        self._event_history.clear()
        self._seen_events.clear()
        self._handler_semaphore = asyncio.Semaphore(self._max_concurrent_handlers)
        self._stats = {
            "events_published": 0,
            "events_delivered": 0,
            "events_deduplicated": 0,
            "handler_errors": 0,
        }


# Global singleton instance
event_bus = EventBus()
