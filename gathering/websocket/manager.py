"""
WebSocket Connection Manager.

Manages WebSocket connections for real-time dashboard updates.
Non-blocking, async-first, supports multiple concurrent connections.
"""

import asyncio
import json
from typing import Dict, Set, Optional, Any, List
from datetime import datetime, timezone

try:
    from fastapi import WebSocket, WebSocketDisconnect
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    WebSocket = None
    WebSocketDisconnect = None


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates.

    Features:
    - Multiple concurrent connections
    - Broadcasting to all clients
    - Graceful disconnect handling
    - JSON message serialization
    - Connection tracking and stats

    Example:
        manager = ConnectionManager()

        # Accept connection
        await manager.connect(websocket)

        # Broadcast to all
        await manager.broadcast({"type": "task.completed", "task_id": 123})

        # Send to specific client
        await manager.send_personal(message, websocket)

        # Disconnect
        await manager.disconnect(websocket)
    """

    def __init__(self):
        """Initialize connection manager."""
        # Active connections: WebSocket -> connection info
        self.active_connections: Dict[WebSocket, Dict[str, Any]] = {}

        # Connection stats
        self.total_connections = 0
        self.total_messages_sent = 0
        self.total_broadcasts = 0

    async def connect(self, websocket: WebSocket, client_id: Optional[str] = None) -> None:
        """
        Accept a new WebSocket connection.

        Args:
            websocket: WebSocket instance.
            client_id: Optional client identifier.
        """
        if not FASTAPI_AVAILABLE:
            raise RuntimeError("FastAPI not available")

        await websocket.accept()

        # Store connection info
        self.active_connections[websocket] = {
            "client_id": client_id or f"client_{id(websocket)}",
            "connected_at": datetime.now(timezone.utc),
            "messages_received": 0,
            "messages_sent": 0,
        }

        self.total_connections += 1

        print(f"[WebSocket] Client connected: {self.active_connections[websocket]['client_id']}")
        print(f"[WebSocket] Active connections: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket) -> None:
        """
        Disconnect a WebSocket client.

        Args:
            websocket: WebSocket to disconnect.
        """
        if websocket in self.active_connections:
            client_info = self.active_connections[websocket]
            client_id = client_info["client_id"]

            del self.active_connections[websocket]

            print(f"[WebSocket] Client disconnected: {client_id}")
            print(f"[WebSocket] Active connections: {len(self.active_connections)}")

    async def send_personal(self, message: Dict[str, Any], websocket: WebSocket) -> bool:
        """
        Send message to a specific client.

        Args:
            message: Message dict to send.
            websocket: Target WebSocket.

        Returns:
            True if sent successfully.
        """
        try:
            await websocket.send_json(message)

            # Update stats
            if websocket in self.active_connections:
                self.active_connections[websocket]["messages_sent"] += 1
                self.total_messages_sent += 1

            return True
        except Exception as e:
            print(f"[WebSocket] Error sending to client: {e}")
            # Auto-disconnect on error
            await self.disconnect(websocket)
            return False

    async def broadcast(self, message: Dict[str, Any]) -> int:
        """
        Broadcast message to all connected clients.

        Args:
            message: Message dict to broadcast.

        Returns:
            Number of clients that received the message.
        """
        if not self.active_connections:
            return 0

        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.now(timezone.utc).isoformat()

        successful = 0
        disconnected = []

        # Send to all clients concurrently
        tasks = []
        for websocket in list(self.active_connections.keys()):
            tasks.append(self._send_with_error_handling(websocket, message))

        # Wait for all sends to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successes and collect disconnected clients
        for websocket, result in zip(list(self.active_connections.keys()), results):
            if result is True:
                successful += 1
            elif isinstance(result, Exception):
                disconnected.append(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            await self.disconnect(websocket)

        self.total_broadcasts += 1

        return successful

    async def _send_with_error_handling(
        self,
        websocket: WebSocket,
        message: Dict[str, Any],
    ) -> bool:
        """
        Send message with error handling.

        Args:
            websocket: Target WebSocket.
            message: Message to send.

        Returns:
            True if successful, False otherwise.
        """
        try:
            await websocket.send_json(message)

            # Update stats
            if websocket in self.active_connections:
                self.active_connections[websocket]["messages_sent"] += 1
                self.total_messages_sent += 1

            return True
        except Exception as e:
            print(f"[WebSocket] Send error: {e}")
            return False

    async def broadcast_event(self, event_type: str, data: Dict[str, Any]) -> int:
        """
        Broadcast an event to all clients.

        Convenience method that wraps data in standard event format.

        Args:
            event_type: Event type (e.g., "task.completed").
            data: Event data.

        Returns:
            Number of clients that received the event.
        """
        message = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return await self.broadcast(message)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get connection statistics.

        Returns:
            Dict with connection stats.
        """
        return {
            "active_connections": len(self.active_connections),
            "total_connections": self.total_connections,
            "total_messages_sent": self.total_messages_sent,
            "total_broadcasts": self.total_broadcasts,
            "clients": [
                {
                    "client_id": info["client_id"],
                    "connected_at": info["connected_at"].isoformat(),
                    "messages_sent": info["messages_sent"],
                    "messages_received": info["messages_received"],
                }
                for info in self.active_connections.values()
            ],
        }

    def get_client_count(self) -> int:
        """Get number of active connections."""
        return len(self.active_connections)

    async def ping_all(self) -> int:
        """
        Send ping to all clients (keepalive).

        Returns:
            Number of clients still connected.
        """
        return await self.broadcast({"type": "ping", "timestamp": datetime.now(timezone.utc).isoformat()})


# Global connection manager instance
_connection_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """
    Get global connection manager instance.

    Returns:
        ConnectionManager singleton.
    """
    global _connection_manager

    if _connection_manager is None:
        _connection_manager = ConnectionManager()

    return _connection_manager


# Alias for backwards compatibility
WebSocketManager = ConnectionManager
