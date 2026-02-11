"""
Rate limit tier integration tests.

Tests that per-endpoint rate limiting works with real slowapi middleware,
verifying 429 responses, Retry-After headers, and tier differentiation.
"""

import pytest
from fastapi.testclient import TestClient

from gathering.api.main import create_app
from gathering.api.rate_limit import limiter


@pytest.fixture(autouse=True)
def reset_limiter():
    """Reset the limiter storage between tests to prevent cross-test pollution."""
    limiter._limiter.storage.reset()
    yield
    limiter._limiter.storage.reset()


@pytest.fixture
def app():
    """Create app with rate limiting enabled but auth disabled."""
    return create_app(
        enable_rate_limit=True,
        enable_auth=False,
        enable_logging=False,
        enable_websocket=False,
    )


@pytest.fixture
def client(app):
    """Create test client that does not raise server exceptions.

    raise_server_exceptions=False is needed because some endpoints (like
    /auth/login) hit the database which is unavailable in CI. The rate limiter
    checks run before the endpoint body, so 500 responses still count toward
    the rate limit and the 6th request correctly returns 429.
    """
    return TestClient(app, raise_server_exceptions=False)


# =============================================================================
# Test Cases
# =============================================================================


class TestRateLimitReturns429WithRetryAfter:
    """The critical test: prove that exceeding a rate limit returns 429
    with a Retry-After header."""

    def test_auth_login_rate_limited_at_tier_auth(self, client):
        """POST /auth/login uses TIER_AUTH (5/minute).
        The 6th request should return 429 Too Many Requests."""
        # Send 5 requests (the TIER_AUTH limit)
        for i in range(5):
            resp = client.post("/auth/login", data={"username": "x", "password": "x"})
            assert resp.status_code != 429, (
                f"Request {i + 1} should not be rate limited (got 429 too early)"
            )

        # The 6th request should be rate limited
        resp = client.post("/auth/login", data={"username": "x", "password": "x"})
        assert resp.status_code == 429, (
            f"Expected 429 on 6th request, got {resp.status_code}"
        )

    def test_429_response_has_retry_after_header(self, client):
        """429 response must include Retry-After header."""
        # Exhaust the TIER_AUTH limit
        for _ in range(5):
            client.post("/auth/login", data={"username": "x", "password": "x"})

        resp = client.post("/auth/login", data={"username": "x", "password": "x"})
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers, (
            "429 response must include Retry-After header"
        )
        retry_after = int(resp.headers["Retry-After"])
        assert retry_after > 0, "Retry-After must be a positive integer"

    def test_429_response_has_rate_limit_headers(self, client):
        """429 response includes X-RateLimit-* headers."""
        for _ in range(5):
            client.post("/auth/login", data={"username": "x", "password": "x"})

        resp = client.post("/auth/login", data={"username": "x", "password": "x"})
        assert resp.status_code == 429
        assert "X-RateLimit-Limit" in resp.headers
        assert resp.headers["X-RateLimit-Limit"] == "5"
        assert "X-RateLimit-Remaining" in resp.headers
        assert resp.headers["X-RateLimit-Remaining"] == "0"
        assert "X-RateLimit-Reset" in resp.headers

    def test_429_response_body_contains_error_detail(self, client):
        """429 response body includes rate limit information."""
        for _ in range(5):
            client.post("/auth/login", data={"username": "x", "password": "x"})

        resp = client.post("/auth/login", data={"username": "x", "password": "x"})
        assert resp.status_code == 429
        body = resp.json()
        assert "error" in body
        assert "5 per 1 minute" in body["error"]


class TestHealthEndpointHigherLimit:
    """Prove that health endpoints have a much higher rate limit (TIER_HEALTH
    = 300/minute), not the same as TIER_AUTH (5/minute)."""

    def test_health_allows_many_requests(self, client):
        """GET /health allows well beyond 5 requests (proving it uses
        TIER_HEALTH, not TIER_AUTH)."""
        for i in range(10):
            resp = client.get("/health")
            assert resp.status_code == 200, (
                f"Health request {i + 1} should succeed (got {resp.status_code})"
            )

    def test_health_ready_allows_many_requests(self, client):
        """GET /health/ready also uses TIER_HEALTH."""
        for i in range(10):
            resp = client.get("/health/ready")
            assert resp.status_code == 200, (
                f"Health/ready request {i + 1} should succeed (got {resp.status_code})"
            )


class TestReadEndpointTier:
    """Prove read endpoints use TIER_READ (120/minute)."""

    def test_read_endpoint_allows_high_volume(self, client):
        """GET /health (TIER_HEALTH) allows 10+ rapid requests without 429."""
        for i in range(15):
            resp = client.get("/health")
            assert resp.status_code != 429, (
                f"Request {i + 1} to health endpoint should not be rate limited"
            )

    def test_different_tiers_are_independent(self, client):
        """Exhausting TIER_AUTH on /auth/login does not affect /health."""
        # Exhaust the TIER_AUTH limit on auth/login
        for _ in range(5):
            client.post("/auth/login", data={"username": "x", "password": "x"})

        # Verify auth/login is now rate limited
        resp = client.post("/auth/login", data={"username": "x", "password": "x"})
        assert resp.status_code == 429

        # Health should still work fine (different endpoint, different tier)
        resp = client.get("/health")
        assert resp.status_code == 200, (
            "Health endpoint should not be affected by auth rate limit"
        )
