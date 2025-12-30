"""
Event Bus - Asynchronous event system for agent coordination.

Provides a lightweight, type-safe event bus for real-time communication
between agents, circles, and system components.
"""

from gathering.events.event_bus import (
    Event,
    EventType,
    EventBus,
    event_bus,
)

__all__ = [
    "Event",
    "EventType",
    "EventBus",
    "event_bus",
]
