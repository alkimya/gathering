"""
API Middleware for GatheRing.
Includes authentication enforcement, rate limiting, and request logging.
"""

import time
import logging
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from gathering.api.auth import decode_token, log_auth_event
from gathering.api.dependencies import DatabaseService


logger = logging.getLogger("gathering.api")


# =============================================================================
# Public Endpoints (no authentication required)
# =============================================================================

PUBLIC_PATHS = {
    # Health checks
    "/",
    "/health",
    "/health/ready",
    "/health/live",
    # Authentication
    "/auth/login",
    "/auth/login/json",
    "/auth/register",
    # Documentation
    "/docs",
    "/redoc",
    "/openapi.json",
}

PUBLIC_PREFIXES = {
    "/docs",
    "/redoc",
}


def is_public_path(path: str) -> bool:
    """Check if a path is public (no auth required)."""
    # Exact matches
    if path in PUBLIC_PATHS:
        return True

    # Prefix matches
    for prefix in PUBLIC_PREFIXES:
        if path.startswith(prefix):
            return True

    return False


# =============================================================================
# Authentication Middleware
# =============================================================================


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce authentication on protected endpoints.

    Public endpoints (health, auth, docs) are excluded.
    All other endpoints require a valid JWT token.
    WebSocket connections are handled separately.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # Skip auth for WebSocket connections (handled separately in endpoint)
        if path == "/ws":
            return await call_next(request)

        # Skip auth for public paths
        if is_public_path(path):
            return await call_next(request)

        # Skip auth for OPTIONS (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            try:
                db = DatabaseService.get_instance()
                log_auth_event(
                    db, "auth_missing_token",
                    ip_address=request.client.host if request.client else None,
                    message=f"Missing auth token for {path}",
                )
            except Exception:
                pass  # Don't block request processing for audit logging failures
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing authentication token"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Validate Bearer token format
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            try:
                db = DatabaseService.get_instance()
                log_auth_event(
                    db, "auth_invalid_token",
                    ip_address=request.client.host if request.client else None,
                    message=f"Invalid auth header format for {path}",
                )
            except Exception:
                pass
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid authentication header format"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = parts[1]

        # Decode and validate token
        token_data = decode_token(token)
        if token_data is None:
            try:
                db = DatabaseService.get_instance()
                log_auth_event(
                    db, "auth_invalid_token",
                    ip_address=request.client.host if request.client else None,
                    message=f"Invalid or expired token for {path}",
                )
            except Exception:
                pass
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or expired token"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Store user info in request state for use in endpoints
        request.state.user = token_data

        return await call_next(request)


# =============================================================================
# Rate Limiting Middleware
# =============================================================================


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware.

    Limits requests per IP address based on configuration.
    Uses a sliding window approach.
    """

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_size = 60  # 1 minute window
        self.requests: dict[str, list[float]] = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        # Check for proxy headers
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct connection
        if request.client:
            return request.client.host

        return "unknown"

    def _cleanup_old_requests(self, ip: str, now: float) -> None:
        """Remove requests outside the current window."""
        cutoff = now - self.window_size
        self.requests[ip] = [t for t in self.requests[ip] if t > cutoff]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for WebSocket connections
        if request.url.path == "/ws":
            return await call_next(request)

        # Skip rate limiting for health checks
        if request.url.path.startswith("/health"):
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        now = time.time()

        # Clean up old requests
        self._cleanup_old_requests(client_ip, now)

        # Check rate limit
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            retry_after = int(self.window_size - (now - self.requests[client_ip][0]))
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        # Record this request
        self.requests[client_ip].append(now)

        # Add rate limit headers to response
        response = await call_next(request)

        remaining = self.requests_per_minute - len(self.requests[client_ip])
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Reset"] = str(int(now + self.window_size))

        return response


# =============================================================================
# Request Logging Middleware
# =============================================================================


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging API requests.

    Logs request details, response status, and timing.
    Sensitive data (tokens, passwords) is redacted.
    WebSocket connections are not logged here.
    """

    SENSITIVE_HEADERS = {"authorization", "cookie", "x-api-key"}
    SENSITIVE_PATHS = {"/auth/login", "/auth/register"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for WebSocket connections (too noisy)
        if request.url.path == "/ws":
            return await call_next(request)

        start_time = time.time()
        request_id = request.headers.get("X-Request-ID", f"req_{int(start_time * 1000)}")

        # Log request
        client_ip = self._get_client_ip(request)
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"from {client_ip}"
        )

        # Process request
        try:
            response = await call_next(request)
        except (ValueError, TypeError, AttributeError, RuntimeError, OSError) as e:
            duration = (time.time() - start_time) * 1000
            logger.error(
                f"[{request_id}] {request.method} {request.url.path} "
                f"ERROR: {type(e).__name__}: {str(e)} ({duration:.2f}ms)"
            )
            raise
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.exception(
                f"[{request_id}] {request.method} {request.url.path} "
                f"UNEXPECTED ERROR ({duration:.2f}ms)"
            )
            raise

        # Log response
        duration = (time.time() - start_time) * 1000
        log_level = logging.INFO if response.status_code < 400 else logging.WARNING

        logger.log(
            log_level,
            f"[{request_id}] {request.method} {request.url.path} "
            f"-> {response.status_code} ({duration:.2f}ms)"
        )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        if request.client:
            return request.client.host

        return "unknown"


# =============================================================================
# Security Headers Middleware
# =============================================================================


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Implements OWASP security headers best practices.
    """

    def __init__(self, app, enable_hsts: bool = True):
        """
        Initialize security headers middleware.

        Args:
            app: FastAPI application
            enable_hsts: Enable HSTS header (disable for local development)
        """
        super().__init__(app)
        self.enable_hsts = enable_hsts

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip for WebSocket connections
        if request.url.path == "/ws":
            return await call_next(request)

        response = await call_next(request)

        # =================================================================
        # Basic Security Headers
        # =================================================================
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # =================================================================
        # Content-Security-Policy (CSP)
        # =================================================================
        # Restrictive CSP for API responses
        # More permissive for docs pages (Swagger/ReDoc)
        if request.url.path.startswith(("/docs", "/redoc")):
            # Allow Swagger/ReDoc to work
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https://fastapi.tiangolo.com; "
                "font-src 'self' https://cdn.jsdelivr.net; "
                "connect-src 'self'"
            )
        else:
            # Strict CSP for API endpoints
            csp = (
                "default-src 'none'; "
                "frame-ancestors 'none'; "
                "form-action 'none'"
            )
        response.headers["Content-Security-Policy"] = csp

        # =================================================================
        # HTTP Strict Transport Security (HSTS)
        # =================================================================
        # Only add HSTS in production (when enabled)
        # max-age=31536000 = 1 year
        if self.enable_hsts:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # =================================================================
        # Permissions-Policy (formerly Feature-Policy)
        # =================================================================
        # Disable sensitive browser features
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        )

        # =================================================================
        # Cross-Origin Policies
        # =================================================================
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

        # =================================================================
        # Cache Control for API responses
        # =================================================================
        if not request.url.path.startswith("/docs"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"

        return response
