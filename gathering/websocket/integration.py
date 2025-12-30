"""
Event Bus integration for WebSocket broadcasting.

Automatically forwards Event Bus events to WebSocket clients.
"""

from typing import List, Optional

from gathering.events import event_bus, Event, EventType
from gathering.websocket import get_connection_manager


# Events to broadcast to WebSocket clients
DEFAULT_BROADCAST_EVENTS = [
    EventType.AGENT_STARTED,
    EventType.AGENT_TASK_COMPLETED,
    EventType.AGENT_TOOL_EXECUTED,
    EventType.MEMORY_CREATED,
    EventType.MEMORY_SHARED,
    EventType.CIRCLE_CREATED,
    EventType.CIRCLE_MEMBER_ADDED,
    EventType.TASK_CREATED,
    EventType.TASK_STARTED,
    EventType.TASK_COMPLETED,
    EventType.TASK_FAILED,
    EventType.TASK_CONFLICT_DETECTED,
    EventType.CONVERSATION_MESSAGE,
]


async def _broadcast_event_to_websocket(event: Event) -> None:
    """
    Event handler that broadcasts events to WebSocket clients.

    Args:
        event: Event to broadcast.
    """
    manager = get_connection_manager()

    # Only broadcast if we have active connections
    if manager.get_client_count() == 0:
        return

    # Prepare event data for WebSocket
    ws_message = {
        "type": event.type.value if hasattr(event.type, "value") else str(event.type),
        "data": event.data,
        "source_agent_id": event.source_agent_id,
        "circle_id": event.circle_id,
        "project_id": event.project_id,
        "event_id": event.id,
        "timestamp": event.timestamp.isoformat() if event.timestamp else None,
    }

    # Broadcast to all connected clients
    await manager.broadcast(ws_message)


def setup_websocket_broadcasting(
    event_types: Optional[List[EventType]] = None,
) -> None:
    """
    Setup automatic broadcasting of Event Bus events to WebSocket clients.

    Call this during app startup to enable real-time dashboard updates.

    Args:
        event_types: List of event types to broadcast (defaults to DEFAULT_BROADCAST_EVENTS).

    Example:
        # In main.py or api.py startup
        from gathering.websocket.integration import setup_websocket_broadcasting

        @app.on_event("startup")
        async def startup():
            setup_websocket_broadcasting()
    """
    events_to_broadcast = event_types or DEFAULT_BROADCAST_EVENTS

    # Subscribe to all specified events
    for event_type in events_to_broadcast:
        event_bus.subscribe(event_type, _broadcast_event_to_websocket)

    print(f"[WebSocket] Broadcasting enabled for {len(events_to_broadcast)} event types")


def setup_custom_broadcasting(event_type: EventType, filter_fn=None) -> None:
    """
    Setup custom event broadcasting with optional filtering.

    Args:
        event_type: Event type to broadcast.
        filter_fn: Optional filter function (event -> bool).

    Example:
        # Only broadcast task events for circle_id == 1
        setup_custom_broadcasting(
            EventType.TASK_COMPLETED,
            filter_fn=lambda e: e.circle_id == 1
        )
    """
    event_bus.subscribe(event_type, _broadcast_event_to_websocket, filter_fn=filter_fn)

    print(f"[WebSocket] Custom broadcasting enabled for {event_type}")
