"""
Event system for GatheRing orchestration.
Provides pub/sub communication between agents.
"""

import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from uuid import uuid4

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of events in the Gathering Circle."""

    # Lifecycle events
    AGENT_JOINED = "agent.joined"
    AGENT_LEFT = "agent.left"
    AGENT_READY = "agent.ready"
    AGENT_BUSY = "agent.busy"

    # Task events
    TASK_CREATED = "task.created"
    TASK_OFFERED = "task.offered"
    TASK_CLAIMED = "task.claimed"
    TASK_REFUSED = "task.refused"
    TASK_STARTED = "task.started"
    TASK_PROGRESS = "task.progress"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_BLOCKED = "task.blocked"
    TASK_CANCELLED = "task.cancelled"

    # Review events
    REVIEW_REQUESTED = "review.requested"
    REVIEW_STARTED = "review.started"
    REVIEW_COMPLETED = "review.completed"
    REVIEW_APPROVED = "review.approved"
    REVIEW_CHANGES_REQUESTED = "review.changes_requested"
    REVIEW_REJECTED = "review.rejected"

    # Communication events
    MESSAGE_SENT = "message.sent"
    MENTION_RECEIVED = "mention.received"
    BROADCAST = "broadcast"

    # Conflict events
    CONFLICT_DETECTED = "conflict.detected"
    CONFLICT_RESOLVED = "conflict.resolved"

    # Escalation events
    ESCALATION_CREATED = "escalation.created"
    ESCALATION_RESOLVED = "escalation.resolved"

    # System events
    CIRCLE_STARTED = "circle.started"
    CIRCLE_STOPPED = "circle.stopped"
    ERROR = "error"

    # Background task events
    BACKGROUND_TASK_CREATED = "background_task.created"
    BACKGROUND_TASK_STARTED = "background_task.started"
    BACKGROUND_TASK_STEP = "background_task.step"
    BACKGROUND_TASK_CHECKPOINT = "background_task.checkpoint"
    BACKGROUND_TASK_COMPLETED = "background_task.completed"
    BACKGROUND_TASK_FAILED = "background_task.failed"
    BACKGROUND_TASK_CANCELLED = "background_task.cancelled"
    BACKGROUND_TASK_PAUSED = "background_task.paused"
    BACKGROUND_TASK_RESUMED = "background_task.resumed"

    # Scheduled action events
    SCHEDULED_ACTION_CREATED = "scheduled_action.created"
    SCHEDULED_ACTION_UPDATED = "scheduled_action.updated"
    SCHEDULED_ACTION_DELETED = "scheduled_action.deleted"
    SCHEDULED_ACTION_TRIGGERED = "scheduled_action.triggered"
    SCHEDULED_ACTION_STARTED = "scheduled_action.started"
    SCHEDULED_ACTION_COMPLETED = "scheduled_action.completed"
    SCHEDULED_ACTION_FAILED = "scheduled_action.failed"
    SCHEDULED_ACTION_PAUSED = "scheduled_action.paused"
    SCHEDULED_ACTION_RESUMED = "scheduled_action.resumed"
    SCHEDULED_ACTION_SCHEDULER_STARTED = "scheduled_action.scheduler_started"
    SCHEDULED_ACTION_SCHEDULER_STOPPED = "scheduled_action.scheduler_stopped"

    # Pipeline execution events
    PIPELINE_RUN_STARTED = "pipeline_run.started"
    PIPELINE_RUN_COMPLETED = "pipeline_run.completed"
    PIPELINE_RUN_FAILED = "pipeline_run.failed"
    PIPELINE_RUN_CANCELLED = "pipeline_run.cancelled"
    PIPELINE_RUN_TIMEOUT = "pipeline_run.timeout"
    PIPELINE_NODE_STARTED = "pipeline_node.started"
    PIPELINE_NODE_COMPLETED = "pipeline_node.completed"
    PIPELINE_NODE_FAILED = "pipeline_node.failed"
    PIPELINE_NODE_SKIPPED = "pipeline_node.skipped"
    PIPELINE_NODE_RETRYING = "pipeline_node.retrying"


@dataclass
class Event:
    """An event in the Gathering Circle."""

    type: EventType
    data: Dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_agent_id: Optional[int] = None
    target_agent_id: Optional[int] = None
    correlation_id: Optional[str] = None  # For tracking related events

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "source_agent_id": self.source_agent_id,
            "target_agent_id": self.target_agent_id,
            "correlation_id": self.correlation_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create event from dictionary."""
        return cls(
            id=data.get("id", str(uuid4())),
            type=EventType(data["type"]),
            data=data.get("data", {}),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(timezone.utc),
            source_agent_id=data.get("source_agent_id"),
            target_agent_id=data.get("target_agent_id"),
            correlation_id=data.get("correlation_id"),
        )


# Type alias for event handlers
EventHandler = Callable[[Event], Any]
AsyncEventHandler = Callable[[Event], Any]  # Can be sync or async


class EventBus:
    """
    Central event bus for the Gathering Circle.

    Supports:
    - Sync and async handlers
    - Wildcard subscriptions
    - Event filtering
    - Event history
    """

    def __init__(self, history_size: int = 1000):
        self._handlers: Dict[EventType, List[AsyncEventHandler]] = {}
        self._wildcard_handlers: List[AsyncEventHandler] = []
        self._history: List[Event] = []
        self._history_size = history_size
        self._lock = asyncio.Lock()

    def subscribe(
        self,
        event_type: Optional[EventType],
        handler: AsyncEventHandler,
    ) -> Callable[[], None]:
        """
        Subscribe to events.

        Args:
            event_type: Type to subscribe to (None for all events)
            handler: Handler function (sync or async)

        Returns:
            Unsubscribe function
        """
        if event_type is None:
            self._wildcard_handlers.append(handler)
            return lambda: self._wildcard_handlers.remove(handler)
        else:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)
            return lambda: self._handlers[event_type].remove(handler)

    def on(self, event_type: Optional[EventType] = None):
        """Decorator for subscribing to events."""
        def decorator(handler: AsyncEventHandler):
            self.subscribe(event_type, handler)
            return handler
        return decorator

    async def emit(
        self,
        event_type: EventType,
        data: Dict[str, Any],
        source_agent_id: Optional[int] = None,
        target_agent_id: Optional[int] = None,
        correlation_id: Optional[str] = None,
    ) -> Event:
        """
        Emit an event.

        Args:
            event_type: Type of event
            data: Event data
            source_agent_id: ID of agent emitting event
            target_agent_id: ID of target agent (if directed)
            correlation_id: ID for tracking related events

        Returns:
            The emitted event
        """
        event = Event(
            type=event_type,
            data=data,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            correlation_id=correlation_id,
        )

        # Store in history
        async with self._lock:
            self._history.append(event)
            if len(self._history) > self._history_size:
                self._history = self._history[-self._history_size:]

        # Call handlers
        handlers = self._handlers.get(event_type, []) + self._wildcard_handlers

        for handler in handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")

        logger.debug(f"Event emitted: {event_type.value} from agent {source_agent_id}")
        return event

    def emit_sync(
        self,
        event_type: EventType,
        data: Dict[str, Any],
        **kwargs,
    ) -> Event:
        """
        Emit an event synchronously.
        Creates a new event loop if needed.
        """
        try:
            asyncio.get_running_loop()
            # If we're in an async context, schedule the coroutine
            asyncio.ensure_future(self.emit(event_type, data, **kwargs))
            # Return a placeholder event
            return Event(type=event_type, data=data, **kwargs)
        except RuntimeError:
            # No running loop, create one
            return asyncio.run(self.emit(event_type, data, **kwargs))

    def get_history(
        self,
        event_type: Optional[EventType] = None,
        agent_id: Optional[int] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Event]:
        """
        Get event history with optional filters.

        Args:
            event_type: Filter by event type
            agent_id: Filter by source or target agent
            since: Filter events after this time
            limit: Maximum events to return

        Returns:
            List of matching events
        """
        events: List[Event] = list(self._history)

        if event_type:
            events = [e for e in events if e.type == event_type]

        if agent_id:
            events = [
                e for e in events
                if e.source_agent_id == agent_id or e.target_agent_id == agent_id
            ]

        if since:
            events = [e for e in events if e.timestamp >= since]

        return events[-limit:]

    def clear_history(self) -> None:
        """Clear event history."""
        self._history.clear()


class EventFilter:
    """Filter for selecting events."""

    def __init__(
        self,
        event_types: Optional[Set[EventType]] = None,
        source_agents: Optional[Set[int]] = None,
        target_agents: Optional[Set[int]] = None,
        data_match: Optional[Dict[str, Any]] = None,
    ):
        self.event_types = event_types
        self.source_agents = source_agents
        self.target_agents = target_agents
        self.data_match = data_match or {}

    def matches(self, event: Event) -> bool:
        """Check if event matches filter."""
        if self.event_types and event.type not in self.event_types:
            return False

        if self.source_agents and event.source_agent_id not in self.source_agents:
            return False

        if self.target_agents and event.target_agent_id not in self.target_agents:
            return False

        for key, value in self.data_match.items():
            if event.data.get(key) != value:
                return False

        return True


class AgentEventMixin:
    """
    Mixin for agents to handle events.
    Add to agent class to enable event handling.
    """

    def __init__(self):
        self._event_handlers: Dict[EventType, List[AsyncEventHandler]] = {}
        self._event_bus: Optional[EventBus] = None

    def set_event_bus(self, bus: EventBus) -> None:
        """Set the event bus for this agent."""
        self._event_bus = bus

    def on_event(self, event_type: EventType):
        """Decorator for registering event handlers."""
        def decorator(handler: AsyncEventHandler):
            if event_type not in self._event_handlers:
                self._event_handlers[event_type] = []
            self._event_handlers[event_type].append(handler)
            return handler
        return decorator

    async def handle_event(self, event: Event) -> None:
        """Handle an incoming event."""
        handlers = self._event_handlers.get(event.type, [])
        for handler in handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Error handling event {event.type}: {e}")

    async def emit(
        self,
        event_type: EventType,
        data: Dict[str, Any],
        target_agent_id: Optional[int] = None,
    ) -> Optional[Event]:
        """Emit an event from this agent."""
        if not self._event_bus:
            logger.warning("No event bus set, cannot emit event")
            return None

        return await self._event_bus.emit(
            event_type=event_type,
            data=data,
            source_agent_id=getattr(self, "id", None),
            target_agent_id=target_agent_id,
        )


# Convenience functions for common events

def task_created_event(
    task_id: int,
    title: str,
    required_competencies: List[str],
    priority: int = 5,
) -> tuple[EventType, Dict[str, Any]]:
    """Create a task.created event payload."""
    return EventType.TASK_CREATED, {
        "task_id": task_id,
        "title": title,
        "required_competencies": required_competencies,
        "priority": priority,
    }


def task_completed_event(
    task_id: int,
    agent_id: int,
    result: str,
    artifacts: Optional[List[str]] = None,
) -> tuple[EventType, Dict[str, Any]]:
    """Create a task.completed event payload."""
    return EventType.TASK_COMPLETED, {
        "task_id": task_id,
        "agent_id": agent_id,
        "result": result,
        "artifacts": artifacts or [],
    }


def review_requested_event(
    task_id: int,
    author_id: int,
    work: str,
    review_type: str = "quality",
    suggested_reviewer_id: Optional[int] = None,
) -> tuple[EventType, Dict[str, Any]]:
    """Create a review.requested event payload."""
    return EventType.REVIEW_REQUESTED, {
        "task_id": task_id,
        "author_id": author_id,
        "work": work,
        "review_type": review_type,
        "suggested_reviewer_id": suggested_reviewer_id,
    }


def mention_event(
    message_id: int,
    mentioned_agent_id: int,
    mentioner_id: int,
    message_content: str,
) -> tuple[EventType, Dict[str, Any]]:
    """Create a mention.received event payload."""
    return EventType.MENTION_RECEIVED, {
        "message_id": message_id,
        "mentioned_agent_id": mentioned_agent_id,
        "mentioner_id": mentioner_id,
        "message_content": message_content,
    }


def conflict_detected_event(
    conflict_type: str,
    agent_ids: List[int],
    resource: str,
    description: str,
) -> tuple[EventType, Dict[str, Any]]:
    """Create a conflict.detected event payload."""
    return EventType.CONFLICT_DETECTED, {
        "conflict_type": conflict_type,
        "agent_ids": agent_ids,
        "resource": resource,
        "description": description,
    }
