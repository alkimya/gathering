"""
Graceful shutdown tests for GatheRing.

Proves:
- /health/ready returns 200 during normal operation
- /health/ready returns 503 during shutdown with reason 'shutting_down'
- Shutdown sequence executes subsystems in correct order
- set_shutting_down() is idempotent (no crash on double-call)
- reset_shutting_down() restores readiness to 200
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
from fastapi.testclient import TestClient

from gathering.api.main import create_app
from gathering.api.routers.health import (
    set_shutting_down,
    reset_shutting_down,
)
from gathering.api.dependencies import reset_registries


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_state():
    """Reset shutdown flag and registries before/after each test."""
    reset_shutting_down()
    reset_registries()
    yield
    reset_shutting_down()
    reset_registries()


@pytest.fixture
def app():
    """Create a test app with auth and rate limiting disabled."""
    return create_app(
        enable_websocket=False,
        enable_auth=False,
        enable_rate_limit=False,
        enable_logging=False,
    )


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGracefulShutdown:
    """Tests for graceful shutdown readiness probe behavior."""

    def test_readiness_probe_returns_200_normally(self, client):
        """GET /health/ready returns 200 and {"ready": True} during normal operation."""
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True

    def test_readiness_probe_returns_503_during_shutdown(self, client):
        """GET /health/ready returns 503 with shutdown reason after set_shutting_down()."""
        set_shutting_down()

        response = client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["ready"] is False
        assert data["reason"] == "shutting_down"

    def test_shutdown_sequence_order(self):
        """Verify lifespan shutdown calls subsystems in correct order.

        Expected order:
        1. set_shutting_down()
        2. asyncio.sleep(3)  -- LB drain pause
        3. scheduler.stop(timeout=10)
        4. asyncio.sleep(2)  -- in-flight task drain
        5. executor.shutdown(timeout=30)
        6. async_db.shutdown()
        """
        call_order = []

        # -- Mock startup subsystems to prevent real initialization --

        mock_ws_setup = MagicMock()

        mock_db_service = MagicMock()

        mock_executor = MagicMock()
        mock_executor.recover_tasks = AsyncMock(return_value=0)
        mock_executor.shutdown = AsyncMock(
            side_effect=lambda **kwargs: call_order.append("executor_shutdown")
        )

        mock_scheduler = MagicMock()
        mock_scheduler.start = AsyncMock()
        mock_scheduler.stop = AsyncMock(
            side_effect=lambda **kwargs: call_order.append("scheduler_stop")
        )

        mock_async_db_instance = MagicMock()
        mock_async_db_instance.startup = AsyncMock()
        mock_async_db_instance.shutdown = AsyncMock(
            side_effect=lambda: call_order.append("async_db_shutdown")
        )

        mock_async_db_cls = MagicMock()
        mock_async_db_cls.get_instance.return_value = mock_async_db_instance
        mock_async_db_cls._instance = mock_async_db_instance

        # Save reference to real set_shutting_down BEFORE patching
        from gathering.api.routers import health as _health_module
        real_set_shutting_down = _health_module.set_shutting_down

        def mock_set_shutting_down():
            real_set_shutting_down()
            call_order.append("set_shutting_down")

        async def mock_sleep(seconds):
            call_order.append(f"sleep({int(seconds)})")

        with patch(
            "gathering.api.main.get_database_service", return_value=mock_db_service
        ), patch(
            "gathering.api.main.get_scheduler", return_value=mock_scheduler
        ), patch(
            "gathering.api.main.get_background_executor", return_value=mock_executor
        ), patch(
            "gathering.websocket.integration.setup_websocket_broadcasting",
            mock_ws_setup,
        ), patch(
            "gathering.api.main.asyncio.sleep", side_effect=mock_sleep
        ), patch(
            "gathering.api.routers.health.set_shutting_down",
            side_effect=mock_set_shutting_down,
        ), patch(
            "gathering.api.async_db.AsyncDatabaseService", mock_async_db_cls
        ):
            app = create_app(
                enable_websocket=False,
                enable_auth=False,
                enable_rate_limit=False,
                enable_logging=False,
            )

            # Enter and exit lifespan to trigger startup + shutdown
            with TestClient(app):
                # Startup happened; clear any startup-related calls
                call_order.clear()

            # After exiting the context manager, shutdown has run
            assert call_order == [
                "set_shutting_down",
                "sleep(3)",
                "scheduler_stop",
                "sleep(2)",
                "executor_shutdown",
                "async_db_shutdown",
            ]

    def test_set_shutting_down_is_idempotent(self, client):
        """Calling set_shutting_down() twice does not crash; /health/ready stays 503."""
        set_shutting_down()
        set_shutting_down()  # second call -- no error

        response = client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["ready"] is False
        assert data["reason"] == "shutting_down"

    def test_reset_shutting_down_restores_readiness(self, client):
        """After set_shutting_down() -> reset_shutting_down(), /health/ready returns 200."""
        # Start normal
        response = client.get("/health/ready")
        assert response.status_code == 200

        # Trigger shutdown
        set_shutting_down()
        response = client.get("/health/ready")
        assert response.status_code == 503

        # Reset
        reset_shutting_down()
        response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.json()["ready"] is True
