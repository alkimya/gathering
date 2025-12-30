"""
Tests for API middleware.
Tests authentication, rate limiting, logging, and security headers.
"""

import os
import time
import pytest
from unittest.mock import patch

from fastapi.testclient import TestClient

from gathering.api.auth import get_password_hash, create_access_token
from gathering.api.middleware import is_public_path


# =============================================================================
# Public Path Tests
# =============================================================================


class TestPublicPaths:
    """Tests for public path detection."""

    def test_health_is_public(self):
        """Test that health endpoints are public."""
        assert is_public_path("/health") is True
        assert is_public_path("/health/ready") is True
        assert is_public_path("/health/live") is True

    def test_auth_login_is_public(self):
        """Test that auth login endpoints are public."""
        assert is_public_path("/auth/login") is True
        assert is_public_path("/auth/login/json") is True
        assert is_public_path("/auth/register") is True

    def test_docs_is_public(self):
        """Test that documentation endpoints are public."""
        assert is_public_path("/docs") is True
        assert is_public_path("/redoc") is True
        assert is_public_path("/openapi.json") is True

    def test_root_is_public(self):
        """Test that root endpoint is public."""
        assert is_public_path("/") is True

    def test_agents_is_protected(self):
        """Test that agents endpoints are protected."""
        assert is_public_path("/agents") is False
        assert is_public_path("/agents/1") is False

    def test_circles_is_protected(self):
        """Test that circles endpoints are protected."""
        assert is_public_path("/circles") is False

    def test_settings_is_protected(self):
        """Test that settings endpoints are protected."""
        assert is_public_path("/settings") is False


# =============================================================================
# Authentication Middleware Tests
# =============================================================================


class TestAuthenticationMiddleware:
    """Tests for authentication middleware."""

    @pytest.fixture
    def client(self):
        """Create test client with auth enabled."""
        from gathering.api.main import create_app
        app = create_app(
            enable_cors=False,
            enable_auth=True,
            enable_rate_limit=False,
            enable_logging=False,
        )
        return TestClient(app)

    @pytest.fixture
    def client_no_auth(self):
        """Create test client without auth."""
        from gathering.api.main import create_app
        app = create_app(
            enable_cors=False,
            enable_auth=False,
            enable_rate_limit=False,
            enable_logging=False,
        )
        return TestClient(app)

    def test_public_endpoint_without_token(self, client):
        """Test that public endpoints work without token."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_protected_endpoint_without_token(self, client):
        """Test that protected endpoints require token."""
        response = client.get("/agents")
        assert response.status_code == 401
        assert "Missing authentication token" in response.json()["detail"]

    def test_protected_endpoint_with_invalid_token(self, client):
        """Test that invalid tokens are rejected."""
        response = client.get(
            "/agents",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401
        assert "Invalid or expired token" in response.json()["detail"]

    def test_protected_endpoint_with_valid_token(self, client):
        """Test that valid tokens are accepted."""
        token = create_access_token({"sub": "user123", "role": "user"})
        response = client.get(
            "/agents",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Should not be 401 - the endpoint itself may return other errors
        assert response.status_code != 401

    def test_invalid_auth_header_format(self, client):
        """Test that invalid auth header format is rejected."""
        # Missing Bearer prefix
        response = client.get(
            "/agents",
            headers={"Authorization": "token123"},
        )
        assert response.status_code == 401
        assert "Invalid authentication header format" in response.json()["detail"]

    def test_auth_disabled(self, client_no_auth):
        """Test that auth can be disabled."""
        response = client_no_auth.get("/agents")
        # Should not be 401 when auth is disabled
        assert response.status_code != 401


# =============================================================================
# Rate Limiting Middleware Tests
# =============================================================================


class TestRateLimitMiddleware:
    """Tests for rate limiting middleware."""

    @pytest.fixture
    def client(self):
        """Create test client with rate limiting (low limit for testing)."""
        from gathering.api.main import create_app
        from gathering.api.middleware import RateLimitMiddleware

        app = create_app(
            enable_cors=False,
            enable_auth=False,
            enable_rate_limit=False,  # We'll add our own
            enable_logging=False,
        )
        # Add rate limiter with very low limit for testing
        app.add_middleware(RateLimitMiddleware, requests_per_minute=5)
        return TestClient(app)

    def test_rate_limit_headers(self, client):
        """Test that rate limit headers are added."""
        response = client.get("/")
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    def test_rate_limit_decrements(self, client):
        """Test that remaining count decrements."""
        response1 = client.get("/")
        remaining1 = int(response1.headers["X-RateLimit-Remaining"])

        response2 = client.get("/")
        remaining2 = int(response2.headers["X-RateLimit-Remaining"])

        assert remaining2 < remaining1

    def test_rate_limit_exceeded(self, client):
        """Test that rate limit is enforced."""
        # Make requests until limit is exceeded
        for i in range(6):
            response = client.get("/")
            if response.status_code == 429:
                break

        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["detail"]
        assert "Retry-After" in response.headers

    def test_health_bypasses_rate_limit(self, client):
        """Test that health checks bypass rate limit."""
        # Exhaust rate limit on other endpoint
        for _ in range(10):
            client.get("/")

        # Health should still work
        response = client.get("/health")
        assert response.status_code == 200


# =============================================================================
# Security Headers Middleware Tests
# =============================================================================


class TestSecurityHeadersMiddleware:
    """Tests for security headers middleware."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from gathering.api.main import create_app
        app = create_app(
            enable_cors=False,
            enable_auth=False,
            enable_rate_limit=False,
            enable_logging=False,
        )
        return TestClient(app)

    def test_content_type_options_header(self, client):
        """Test X-Content-Type-Options header."""
        response = client.get("/")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_frame_options_header(self, client):
        """Test X-Frame-Options header."""
        response = client.get("/")
        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_xss_protection_header(self, client):
        """Test X-XSS-Protection header."""
        response = client.get("/")
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"

    def test_referrer_policy_header(self, client):
        """Test Referrer-Policy header."""
        response = client.get("/")
        assert "strict-origin" in response.headers.get("Referrer-Policy", "")

    def test_cache_control_header(self, client):
        """Test Cache-Control header for API endpoints."""
        response = client.get("/health")
        assert "no-store" in response.headers.get("Cache-Control", "")


# =============================================================================
# Integration Tests
# =============================================================================


class TestMiddlewareIntegration:
    """Integration tests for middleware stack."""

    @pytest.fixture
    def client(self):
        """Create test client with all middleware enabled."""
        from gathering.api.main import create_app
        app = create_app(
            enable_cors=False,
            enable_auth=True,
            enable_rate_limit=True,
            enable_logging=True,
        )
        return TestClient(app)

    def test_full_auth_flow(self, client):
        """Test complete authentication flow."""
        admin_email = "admin@test.com"
        admin_password = "admin123"
        admin_hash = get_password_hash(admin_password)

        with patch.dict(os.environ, {
            "ADMIN_EMAIL": admin_email,
            "ADMIN_PASSWORD_HASH": admin_hash,
        }):
            # Login
            login_response = client.post(
                "/auth/login",
                data={"username": admin_email, "password": admin_password},
            )
            assert login_response.status_code == 200
            token = login_response.json()["access_token"]

            # Access protected endpoint
            protected_response = client.get(
                "/agents",
                headers={"Authorization": f"Bearer {token}"},
            )
            # Should have security headers
            assert "X-Content-Type-Options" in protected_response.headers
            # Should have rate limit headers
            assert "X-RateLimit-Limit" in protected_response.headers

    def test_request_id_header(self, client):
        """Test that request ID is added to response."""
        token = create_access_token({"sub": "user123", "role": "user"})
        response = client.get(
            "/health",
            headers={"X-Request-ID": "test-request-123"},
        )
        assert response.headers.get("X-Request-ID") == "test-request-123"
