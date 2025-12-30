"""
WebSocket router for real-time dashboard updates.

Provides:
- /ws/dashboard - Real-time event stream
- Event broadcasting from Event Bus
- Connection management
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Optional

from gathering.websocket import get_connection_manager
from gathering.events import event_bus, Event, EventType

router = APIRouter()


@router.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket, client_id: Optional[str] = None):
    """
    WebSocket endpoint for real-time dashboard updates.

    Clients connect to this endpoint to receive real-time events:
    - Agent task completions
    - Tool executions
    - Memory updates
    - Circle activity
    - System events

    Usage (JavaScript):
        const ws = new WebSocket('ws://localhost:8000/ws/dashboard?client_id=dashboard-1');

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('Event received:', data);
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        ws.onclose = () => {
            console.log('WebSocket closed');
        };

    Message format:
        {
            "type": "agent.task.completed",
            "data": {...},
            "timestamp": "2025-01-15T10:30:00Z"
        }

    Args:
        websocket: WebSocket connection
        client_id: Optional client identifier for tracking
    """
    manager = get_connection_manager()

    # Accept connection
    await manager.connect(websocket, client_id=client_id)

    try:
        # Send welcome message
        await manager.send_personal(
            {
                "type": "connection.established",
                "data": {
                    "client_id": client_id or f"client_{id(websocket)}",
                    "message": "Connected to GatheRing dashboard",
                },
            },
            websocket,
        )

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Receive messages from client (optional - for bidirectional comm)
                data = await websocket.receive_json()

                # Handle client messages (ping, subscribe filters, etc.)
                if data.get("type") == "ping":
                    await manager.send_personal(
                        {"type": "pong", "timestamp": data.get("timestamp")},
                        websocket,
                    )

                # Add more client message handling here as needed

            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"[WebSocket] Error receiving message: {e}")
                break

    finally:
        # Clean up on disconnect
        await manager.disconnect(websocket)


@router.get("/ws/stats")
async def websocket_stats():
    """
    Get WebSocket connection statistics.

    Returns:
        Connection stats including active connections and message counts.
    """
    manager = get_connection_manager()
    return manager.get_stats()
