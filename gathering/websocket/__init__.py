"""
WebSocket - Real-time communication for GatheRing dashboard.

Provides:
- WebSocket connection management
- Event broadcasting to connected clients
- Dashboard real-time updates
"""

from gathering.websocket.manager import (
    WebSocketManager,
    ConnectionManager,
    get_connection_manager,
)

__all__ = [
    "WebSocketManager",
    "ConnectionManager",
    "get_connection_manager",
]
