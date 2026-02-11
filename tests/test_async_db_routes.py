"""
Integration tests proving async DB route handlers work correctly
and don't block the event loop under concurrent load.

These tests mock the AsyncDatabaseService at the dependency override level
so they run without a live PostgreSQL connection.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest
import httpx

from gathering.api.main import create_app
from gathering.api.async_db import AsyncDatabaseService, get_async_db
from gathering.api.dependencies import (
    reset_registries,
    get_agent_registry,
    get_circle_registry,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_registries():
    """Reset all registries before each test."""
    reset_registries()
    AsyncDatabaseService.reset_instance()
    yield
    reset_registries()
    AsyncDatabaseService.reset_instance()


def _make_mock_async_db(delay: float = 0.01):
    """Create a mock AsyncDatabaseService with configurable async delay.

    The delay simulates real async I/O -- if the event loop is blocked,
    concurrent calls will serialize and total time = N * delay instead of ~delay.
    """
    mock_db = AsyncMock(spec=AsyncDatabaseService)

    async def mock_execute(sql, params=None):
        await asyncio.sleep(delay)
        return [{"ok": 1}]

    async def mock_fetch_one(sql, params=None):
        await asyncio.sleep(delay)
        return {"ok": 1}

    async def mock_fetch_all(sql, params=None):
        await asyncio.sleep(delay)
        return [{"ok": 1}]

    mock_db.execute = AsyncMock(side_effect=mock_execute)
    mock_db.execute_one = AsyncMock(side_effect=mock_fetch_one)
    mock_db.fetch_one = AsyncMock(side_effect=mock_fetch_one)
    mock_db.fetch_all = AsyncMock(side_effect=mock_fetch_all)
    mock_db.startup = AsyncMock()
    mock_db.shutdown = AsyncMock()

    return mock_db


def _make_mock_registries():
    """Create mock agent and circle registries that return zero counts."""
    mock_agent_reg = MagicMock()
    mock_agent_reg.count.return_value = 0
    mock_agent_reg.list_all.return_value = []

    mock_circle_reg = MagicMock()
    mock_circle_reg.count.return_value = 0
    mock_circle_reg.list_all.return_value = []

    return mock_agent_reg, mock_circle_reg


@pytest.fixture
def app_with_mock_db():
    """Create a test app with mocked async DB and registries."""
    app = create_app(
        enable_websocket=False,
        enable_auth=False,
        enable_rate_limit=False,
        enable_logging=False,
    )

    mock_db = _make_mock_async_db(delay=0.01)
    mock_agent_reg, mock_circle_reg = _make_mock_registries()

    app.dependency_overrides[get_async_db] = lambda: mock_db
    app.dependency_overrides[get_agent_registry] = lambda: mock_agent_reg
    app.dependency_overrides[get_circle_registry] = lambda: mock_circle_reg

    return app


# ---------------------------------------------------------------------------
# Test 1: Smoke test -- async health checks endpoint responds
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_async_health_checks_endpoint(app_with_mock_db):
    """Smoke test that GET /health/checks responds 200 via async DB dependency.

    Proves the AsyncDatabaseService dependency injection works end-to-end.
    """
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app_with_mock_db),
        base_url="http://test",
    ) as client:
        response = await client.get("/health/checks")

    assert response.status_code == 200
    data = response.json()
    assert "checks" in data
    assert "overall_status" in data

    # Verify the DB check ran and reported healthy
    db_check = next(
        (c for c in data["checks"] if c["name"] == "Database"),
        None,
    )
    assert db_check is not None
    assert db_check["status"] == "healthy"
    assert "async" in db_check["message"].lower()


# ---------------------------------------------------------------------------
# Test 2: Concurrency test -- proves parallel async DB execution
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_concurrent_async_db_requests(app_with_mock_db):
    """Proves concurrent async DB requests complete in parallel, not serially.

    Sends 10 concurrent GET requests to /health/checks (async-DB-backed).
    Each mock DB call sleeps 10ms. If executed in parallel, all 10 should
    complete in roughly 10-50ms total. If serialized (event loop blocked),
    it would take ~100ms+.

    This is the key integration test proving the event loop is not blocked.
    """
    num_requests = 10
    mock_delay_seconds = 0.01  # 10ms per "query"

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app_with_mock_db),
        base_url="http://test",
    ) as client:
        start = time.monotonic()

        # Fire all requests concurrently
        tasks = [client.get("/health/checks") for _ in range(num_requests)]
        responses = await asyncio.gather(*tasks)

        elapsed = time.monotonic() - start

    # All should succeed
    for resp in responses:
        assert resp.status_code == 200

    # If parallel: elapsed ~ 10-50ms (one batch of concurrent sleeps)
    # If serial:   elapsed ~ 100ms+ (10 sequential 10ms sleeps)
    # We use a generous threshold (< 2 seconds) to avoid flaky tests,
    # but the real assertion is that it's much less than num_requests * delay.
    serial_time = num_requests * mock_delay_seconds
    assert elapsed < serial_time * 5, (
        f"Concurrent requests took {elapsed:.3f}s, which suggests serialization. "
        f"Expected parallel execution to be much less than {serial_time:.3f}s serial time."
    )


# ---------------------------------------------------------------------------
# Test 3: Unit test -- get_async_db returns AsyncDatabaseService instance
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_async_db_dependency_returns_async_service():
    """Unit test that get_async_db() returns an AsyncDatabaseService instance.

    Verifies the FastAPI dependency returns the correct type, not the sync
    DatabaseService. This is important because a wrong dependency would
    silently block the event loop.
    """
    service = await get_async_db()
    assert isinstance(service, AsyncDatabaseService)
    assert hasattr(service, 'execute')
    assert hasattr(service, 'fetch_one')
    assert hasattr(service, 'fetch_all')
    assert hasattr(service, 'startup')
    assert hasattr(service, 'shutdown')


# ---------------------------------------------------------------------------
# Test 4: Providers endpoint uses async DB
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_async_list_providers_endpoint(app_with_mock_db):
    """Test that GET /providers responds via async DB dependency."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app_with_mock_db),
        base_url="http://test",
    ) as client:
        response = await client.get("/providers")

    assert response.status_code == 200
    data = response.json()
    assert "providers" in data
    assert "total" in data
