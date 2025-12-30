"""
WebSocket support for real-time updates.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field

from fastapi import WebSocket, WebSocketDisconnect


@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection."""
    websocket: WebSocket
    subscriptions: Set[str] = field(default_factory=set)
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class WebSocketManager:
    """
    Manages WebSocket connections and broadcasts events.

    Features:
    - Connection management
    - Topic-based subscriptions
    - Broadcast to all or specific clients
    - Event filtering
    """

    def __init__(self):
        self._connections: Dict[str, ConnectionInfo] = {}
        self._counter: int = 0
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> str:
        """
        Accept a WebSocket connection and return a connection ID.
        """
        await websocket.accept()

        async with self._lock:
            self._counter += 1
            conn_id = f"ws-{self._counter}"
            self._connections[conn_id] = ConnectionInfo(websocket=websocket)

        return conn_id

    async def disconnect(self, conn_id: str):
        """
        Disconnect a WebSocket connection.
        """
        async with self._lock:
            if conn_id in self._connections:
                del self._connections[conn_id]

    async def subscribe(self, conn_id: str, topics: List[str]):
        """
        Subscribe a connection to topics.

        Topics can be:
        - "agents" - All agent events
        - "agents:{id}" - Events for specific agent
        - "circles" - All circle events
        - "circles:{name}" - Events for specific circle
        - "conversations" - All conversation events
        - "tasks" - All task events
        """
        async with self._lock:
            if conn_id in self._connections:
                self._connections[conn_id].subscriptions.update(topics)

    async def unsubscribe(self, conn_id: str, topics: List[str]):
        """
        Unsubscribe a connection from topics.
        """
        async with self._lock:
            if conn_id in self._connections:
                self._connections[conn_id].subscriptions.difference_update(topics)

    def _matches_topic(self, subscriptions: Set[str], event_topics: List[str]) -> bool:
        """Check if any subscription matches the event topics."""
        for sub in subscriptions:
            for topic in event_topics:
                # Exact match
                if sub == topic:
                    return True
                # Wildcard match (e.g., "agents" matches "agents:1")
                if ":" in topic and sub == topic.split(":")[0]:
                    return True
        return False

    async def broadcast(
        self,
        event_type: str,
        data: dict,
        topics: Optional[List[str]] = None,
    ):
        """
        Broadcast an event to subscribed connections.

        Args:
            event_type: Type of event (e.g., "agent.chat", "task.created")
            data: Event data
            topics: Topics this event belongs to (for filtering)
        """
        message = json.dumps({
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        topics = topics or []
        disconnected = []

        async with self._lock:
            connections = list(self._connections.items())

        for conn_id, info in connections:
            # If no topics specified, send to all
            # Otherwise, check if connection is subscribed
            should_send = (
                not topics or
                not info.subscriptions or
                self._matches_topic(info.subscriptions, topics)
            )

            if should_send:
                try:
                    await info.websocket.send_text(message)
                except Exception:
                    disconnected.append(conn_id)

        # Clean up disconnected clients
        for conn_id in disconnected:
            await self.disconnect(conn_id)

    async def send_to(self, conn_id: str, event_type: str, data: dict):
        """
        Send an event to a specific connection.
        """
        async with self._lock:
            info = self._connections.get(conn_id)

        if info:
            message = json.dumps({
                "type": event_type,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            try:
                await info.websocket.send_text(message)
            except Exception:
                await self.disconnect(conn_id)

    @property
    def connection_count(self) -> int:
        """Number of active connections."""
        return len(self._connections)

    def get_connection_info(self, conn_id: str) -> Optional[dict]:
        """Get information about a connection."""
        info = self._connections.get(conn_id)
        if info:
            return {
                "id": conn_id,
                "subscriptions": list(info.subscriptions),
                "connected_at": info.connected_at.isoformat(),
            }
        return None


# Global WebSocket manager instance
ws_manager = WebSocketManager()


def get_ws_manager() -> WebSocketManager:
    """Get the global WebSocket manager."""
    return ws_manager


# =============================================================================
# Event Emitters (for integration with other modules)
# =============================================================================


async def emit_agent_event(agent_id: int, event_type: str, data: dict):
    """Emit an agent-related event."""
    await ws_manager.broadcast(
        event_type=f"agent.{event_type}",
        data={"agent_id": agent_id, **data},
        topics=["agents", f"agents:{agent_id}"],
    )


async def emit_circle_event(circle_name: str, event_type: str, data: dict):
    """Emit a circle-related event."""
    await ws_manager.broadcast(
        event_type=f"circle.{event_type}",
        data={"circle": circle_name, **data},
        topics=["circles", f"circles:{circle_name}"],
    )


async def emit_task_event(circle_name: str, task_id: int, event_type: str, data: dict):
    """Emit a task-related event."""
    await ws_manager.broadcast(
        event_type=f"task.{event_type}",
        data={"circle": circle_name, "task_id": task_id, **data},
        topics=["tasks", f"circles:{circle_name}"],
    )


async def emit_conversation_event(conv_id: str, event_type: str, data: dict):
    """Emit a conversation-related event."""
    await ws_manager.broadcast(
        event_type=f"conversation.{event_type}",
        data={"conversation_id": conv_id, **data},
        topics=["conversations", f"conversations:{conv_id}"],
    )
