"""
Tests for WebSocket module.

Covers:
- ConnectionManager
- Connection tracking
- Broadcasting
- Event integration
- Graceful error handling
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from gathering.websocket.manager import ConnectionManager, get_connection_manager
from gathering.websocket.integration import setup_websocket_broadcasting, DEFAULT_BROADCAST_EVENTS


class TestConnectionManager:
    """Test ConnectionManager class."""

    def test_initialization(self):
        """Test manager initialization."""
        manager = ConnectionManager()

        assert manager.active_connections == {}
        assert manager.total_connections == 0
        assert manager.total_messages_sent == 0
        assert manager.total_broadcasts == 0

    @pytest.mark.asyncio
    async def test_connect(self):
        """Test connecting a client."""
        manager = ConnectionManager()
        websocket = AsyncMock()
        websocket.accept = AsyncMock()

        await manager.connect(websocket, client_id="test-client")

        websocket.accept.assert_called_once()
        assert websocket in manager.active_connections
        assert manager.active_connections[websocket]["client_id"] == "test-client"
        assert manager.total_connections == 1

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test disconnecting a client."""
        manager = ConnectionManager()
        websocket = AsyncMock()
        websocket.accept = AsyncMock()

        # Connect then disconnect
        await manager.connect(websocket, client_id="test-client")
        await manager.disconnect(websocket)

        assert websocket not in manager.active_connections
        assert manager.total_connections == 1  # Counter doesn't decrease

    @pytest.mark.asyncio
    async def test_send_personal(self):
        """Test sending message to specific client."""
        manager = ConnectionManager()
        websocket = AsyncMock()
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()

        await manager.connect(websocket)

        message = {"type": "test", "data": "hello"}
        result = await manager.send_personal(message, websocket)

        assert result is True
        websocket.send_json.assert_called_once_with(message)
        assert manager.active_connections[websocket]["messages_sent"] == 1
        assert manager.total_messages_sent == 1

    @pytest.mark.asyncio
    async def test_send_personal_error_handling(self):
        """Test send_personal handles errors gracefully."""
        manager = ConnectionManager()
        websocket = AsyncMock()
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock(side_effect=Exception("Send failed"))

        await manager.connect(websocket)

        message = {"type": "test"}
        result = await manager.send_personal(message, websocket)

        assert result is False
        # Should auto-disconnect on error
        assert websocket not in manager.active_connections

    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_clients(self):
        """Test broadcasting to multiple clients."""
        manager = ConnectionManager()

        # Create 3 mock clients
        clients = []
        for i in range(3):
            ws = AsyncMock()
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            await manager.connect(ws, client_id=f"client-{i}")
            clients.append(ws)

        # Broadcast message
        message = {"type": "broadcast", "data": "hello all"}
        count = await manager.broadcast(message)

        # Verify all clients received message
        assert count == 3
        for ws in clients:
            ws.send_json.assert_called_once()
            # Verify message has timestamp
            call_args = ws.send_json.call_args[0][0]
            assert "timestamp" in call_args

    @pytest.mark.asyncio
    async def test_broadcast_with_no_clients(self):
        """Test broadcasting with no connected clients."""
        manager = ConnectionManager()

        message = {"type": "test"}
        count = await manager.broadcast(message)

        assert count == 0

    @pytest.mark.asyncio
    async def test_broadcast_handles_failed_sends(self):
        """Test broadcast handles some clients failing."""
        manager = ConnectionManager()

        # Client 1: success
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()
        await manager.connect(ws1, client_id="client-1")

        # Client 2: fails
        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock(side_effect=Exception("Failed"))
        await manager.connect(ws2, client_id="client-2")

        # Client 3: success
        ws3 = AsyncMock()
        ws3.accept = AsyncMock()
        ws3.send_json = AsyncMock()
        await manager.connect(ws3, client_id="client-3")

        # Broadcast
        message = {"type": "test"}
        count = await manager.broadcast(message)

        # Should succeed for 2 out of 3
        assert count == 2

        # All clients remain connected (broadcast doesn't auto-disconnect)
        # Failed sends just aren't counted in successful deliveries
        assert ws1 in manager.active_connections
        assert ws2 in manager.active_connections
        assert ws3 in manager.active_connections

    @pytest.mark.asyncio
    async def test_broadcast_event(self):
        """Test broadcast_event convenience method."""
        manager = ConnectionManager()
        websocket = AsyncMock()
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()

        await manager.connect(websocket)

        count = await manager.broadcast_event(
            "task.completed",
            {"task_id": 123, "status": "done"}
        )

        assert count == 1
        websocket.send_json.assert_called_once()

        # Verify message format
        call_args = websocket.send_json.call_args[0][0]
        assert call_args["type"] == "task.completed"
        assert call_args["data"]["task_id"] == 123
        assert "timestamp" in call_args

    def test_get_stats(self):
        """Test getting connection statistics."""
        manager = ConnectionManager()

        stats = manager.get_stats()

        assert stats["active_connections"] == 0
        assert stats["total_connections"] == 0
        assert stats["total_messages_sent"] == 0
        assert stats["total_broadcasts"] == 0
        assert stats["clients"] == []

    @pytest.mark.asyncio
    async def test_get_stats_with_connections(self):
        """Test stats with active connections."""
        manager = ConnectionManager()
        websocket = AsyncMock()
        websocket.accept = AsyncMock()

        await manager.connect(websocket, client_id="test-client")

        stats = manager.get_stats()

        assert stats["active_connections"] == 1
        assert stats["total_connections"] == 1
        assert len(stats["clients"]) == 1
        assert stats["clients"][0]["client_id"] == "test-client"

    def test_get_client_count(self):
        """Test getting active client count."""
        manager = ConnectionManager()

        assert manager.get_client_count() == 0

    @pytest.mark.asyncio
    async def test_ping_all(self):
        """Test pinging all clients."""
        manager = ConnectionManager()
        websocket = AsyncMock()
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()

        await manager.connect(websocket)

        count = await manager.ping_all()

        assert count == 1
        websocket.send_json.assert_called_once()

        # Verify ping message
        call_args = websocket.send_json.call_args[0][0]
        assert call_args["type"] == "ping"
        assert "timestamp" in call_args


class TestGlobalConnectionManager:
    """Test global connection manager singleton."""

    def test_get_connection_manager(self):
        """Test getting global manager instance."""
        manager1 = get_connection_manager()
        manager2 = get_connection_manager()

        # Should return same instance
        assert manager1 is manager2

    def test_manager_is_connection_manager(self):
        """Test manager is correct type."""
        manager = get_connection_manager()

        assert isinstance(manager, ConnectionManager)


class TestWebSocketIntegration:
    """Test Event Bus integration."""

    def test_default_broadcast_events(self):
        """Test DEFAULT_BROADCAST_EVENTS is defined."""
        assert isinstance(DEFAULT_BROADCAST_EVENTS, list)
        assert len(DEFAULT_BROADCAST_EVENTS) > 0

    def test_setup_websocket_broadcasting(self):
        """Test setting up broadcasting."""
        # Just verify it doesn't crash
        setup_websocket_broadcasting()

        # Should have subscribed to events
        # (Event bus will have subscribers)


class TestGracefulDegradation:
    """Test graceful degradation without FastAPI."""

    @patch("gathering.websocket.manager.FASTAPI_AVAILABLE", False)
    def test_manager_without_fastapi(self):
        """Test manager can be created without FastAPI."""
        manager = ConnectionManager()

        assert manager is not None
        assert manager.active_connections == {}


class TestConcurrentConnections:
    """Test handling many concurrent connections."""

    @pytest.mark.asyncio
    async def test_many_concurrent_connections(self):
        """Test handling 100 concurrent connections."""
        manager = ConnectionManager()

        # Create 100 clients
        clients = []
        for i in range(100):
            ws = AsyncMock()
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            await manager.connect(ws, client_id=f"client-{i}")
            clients.append(ws)

        assert manager.get_client_count() == 100

        # Broadcast to all
        message = {"type": "test", "data": "hello"}
        count = await manager.broadcast(message)

        assert count == 100

        # All clients received message
        for ws in clients:
            ws.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_disconnect(self):
        """Test concurrent disconnections."""
        manager = ConnectionManager()

        # Create 10 clients
        clients = []
        for i in range(10):
            ws = AsyncMock()
            ws.accept = AsyncMock()
            await manager.connect(ws, client_id=f"client-{i}")
            clients.append(ws)

        # Disconnect all
        for ws in clients:
            await manager.disconnect(ws)

        assert manager.get_client_count() == 0
        assert manager.total_connections == 10  # Total doesn't decrease
