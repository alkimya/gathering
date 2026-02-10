"""
Main FastAPI application for GatheRing.
"""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, status
from fastapi.middleware.cors import CORSMiddleware

from gathering.api.routers import (
    agents_router,
    auth_router,
    circles_router,
    conversations_router,
    dashboard_router,
    health_router,
    memories_router,
    models_router,
    background_tasks_router,
    scheduled_actions_router,
    goals_router,
    settings_router,
    projects_router,
    pipelines_router,
    websocket_router,
    workspace_router,
    lsp_router,
    plugins_router,
    tools_router,
)
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from gathering.api.middleware import (
    AuthenticationMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from asgi_correlation_id import CorrelationIdMiddleware
from gathering.core.config import get_settings
from gathering.core.logging import configure_logging
from gathering.api.websocket import ws_manager
from gathering.api.dependencies import get_database_service
from gathering.orchestration.background import get_background_executor
from gathering.orchestration.scheduler import get_scheduler
from gathering.api.auth import decode_token


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    settings = get_settings()

    # Configure structured logging (console renderer in debug mode, JSON in production)
    configure_logging(json_output=not settings.debug, log_level=settings.log_level)

    print("GatheRing API starting...")
    if settings.is_production:
        try:
            settings.require_production_ready()
            print("✓ Production configuration validated")
        except ValueError as e:
            print(f"❌ {e}")
            raise

    # Setup WebSocket broadcasting from Event Bus
    try:
        from gathering.websocket.integration import setup_websocket_broadcasting
        setup_websocket_broadcasting()
        print("WebSocket broadcasting enabled")
    except Exception as e:
        print(f"Warning: Could not setup WebSocket broadcasting: {e}")

    # Initialize background task executor and recover interrupted tasks
    try:
        db = get_database_service()
        executor = get_background_executor(db_service=db)
        recovered = await executor.recover_tasks()
        if recovered:
            print(f"Recovered {recovered} interrupted background tasks (now paused)")
    except Exception as e:
        print(f"Warning: Could not recover background tasks: {e}")

    # Initialize and start the scheduler
    try:
        db = get_database_service()
        scheduler = get_scheduler(db_service=db)
        await scheduler.start()
        print("Scheduler started")
    except Exception as e:
        print(f"Warning: Could not start scheduler: {e}")

    # Initialize async database pool
    try:
        from gathering.api.async_db import AsyncDatabaseService
        async_db = AsyncDatabaseService.get_instance()
        await async_db.startup()
        print("Async database pool opened")
    except Exception as e:
        print(f"Warning: Could not initialize async database pool: {e}")

    yield

    # Shutdown
    print("GatheRing API shutting down...")

    # Close async database pool
    try:
        from gathering.api.async_db import AsyncDatabaseService
        if AsyncDatabaseService._instance is not None:
            await AsyncDatabaseService.get_instance().shutdown()
            print("Async database pool closed")
    except Exception as e:
        print(f"Warning: Error during async database pool shutdown: {e}")

    # Stop the scheduler
    try:
        scheduler = get_scheduler()
        await scheduler.stop(timeout=10)
        print("Scheduler stopped")
    except Exception as e:
        print(f"Warning: Error during scheduler shutdown: {e}")

    # Gracefully shutdown background task executor
    try:
        executor = get_background_executor()
        await executor.shutdown(timeout=30)
        print("Background task executor shutdown complete")
    except Exception as e:
        print(f"Warning: Error during background executor shutdown: {e}")


def create_app(
    title: str = "GatheRing API",
    description: str = "Multi-agent collaboration framework REST API",
    version: str = "0.4.0",
    enable_cors: bool = True,
    cors_origins: Optional[list] = None,
    enable_websocket: bool = True,
    enable_auth: bool = True,
    enable_rate_limit: bool = True,
    enable_logging: bool = True,
) -> FastAPI:
    """
    Create and configure the FastAPI application.

    Args:
        title: API title
        description: API description
        version: API version
        enable_cors: Enable CORS middleware
        cors_origins: Allowed CORS origins (default: all)
        enable_websocket: Enable WebSocket endpoint
        enable_auth: Enable authentication middleware
        enable_rate_limit: Enable rate limiting middleware
        enable_logging: Enable request logging middleware

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title=title,
        description=description,
        version=version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS middleware - use settings-based origins or provided list
    if enable_cors:
        settings = get_settings()
        # Use provided origins, or settings origins, or restrictive default
        if cors_origins:
            origins = cors_origins
        elif settings.cors_origins:
            origins = settings.cors_origins_list
        else:
            # Restrictive default: only localhost for development
            origins = [
                "http://localhost:3000",
                "http://localhost:5000",
                "http://localhost:5173",  # Vite default
                "http://127.0.0.1:5173",
            ]

        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        )

    # Security middleware (order matters - first added is last executed)
    # Add security headers to all responses
    app.add_middleware(SecurityHeadersMiddleware)

    # Request logging (logs all requests with timing)
    if enable_logging:
        app.add_middleware(RequestLoggingMiddleware)

    # Rate limiting via slowapi (per-endpoint decorators)
    if enable_rate_limit:
        from gathering.api.rate_limit import limiter
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Authentication (protects all non-public endpoints)
    if enable_auth:
        app.add_middleware(AuthenticationMiddleware)

    # Correlation ID middleware (added last so it runs first in request lifecycle)
    app.add_middleware(CorrelationIdMiddleware)

    # Include routers
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(agents_router)
    app.include_router(circles_router)
    app.include_router(conversations_router)
    app.include_router(dashboard_router)
    app.include_router(memories_router)
    app.include_router(models_router)
    app.include_router(background_tasks_router)
    app.include_router(scheduled_actions_router)
    app.include_router(goals_router)
    app.include_router(settings_router)
    app.include_router(projects_router)
    app.include_router(pipelines_router)
    app.include_router(websocket_router)
    app.include_router(workspace_router)
    app.include_router(lsp_router)
    app.include_router(plugins_router)
    app.include_router(tools_router)

    # WebSocket endpoint
    if enable_websocket:
        async def _validate_ws_token(websocket: WebSocket, token: Optional[str]) -> bool:
            """Validate WebSocket token and close connection if invalid."""
            settings = get_settings()

            # Skip auth in development mode if auth is disabled
            if settings.disable_auth and settings.is_development:
                return True

            if not token:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return False

            token_data = decode_token(token)
            if not token_data:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return False

            return True

        @app.websocket("/ws")
        async def websocket_endpoint(
            websocket: WebSocket,
            token: Optional[str] = Query(None, description="JWT auth token"),
        ):
            """
            WebSocket endpoint for real-time updates.

            **Authentication**: Pass JWT token as query parameter: `/ws?token=<jwt>`

            After connecting, send JSON messages to subscribe to topics:
            ```json
            {"action": "subscribe", "topics": ["agents", "circles:my-circle"]}
            ```

            Events will be sent in the format:
            ```json
            {
                "type": "agent.chat",
                "data": {...},
                "timestamp": "2024-01-15T10:30:00Z"
            }
            ```
            """
            # Validate token before accepting connection
            if not await _validate_ws_token(websocket, token):
                return

            conn_id = await ws_manager.connect(websocket)

            try:
                # Send connection confirmation
                await ws_manager.send_to(conn_id, "connected", {
                    "connection_id": conn_id,
                    "message": "Connected to GatheRing WebSocket",
                })

                while True:
                    data = await websocket.receive_json()

                    action = data.get("action")

                    if action == "subscribe":
                        topics = data.get("topics", [])
                        await ws_manager.subscribe(conn_id, topics)
                        await ws_manager.send_to(conn_id, "subscribed", {
                            "topics": topics,
                        })

                    elif action == "unsubscribe":
                        topics = data.get("topics", [])
                        await ws_manager.unsubscribe(conn_id, topics)
                        await ws_manager.send_to(conn_id, "unsubscribed", {
                            "topics": topics,
                        })

                    elif action == "ping":
                        await ws_manager.send_to(conn_id, "pong", {})

                    elif action == "info":
                        info = ws_manager.get_connection_info(conn_id)
                        await ws_manager.send_to(conn_id, "info", info or {})

                    else:
                        await ws_manager.send_to(conn_id, "error", {
                            "message": f"Unknown action: {action}",
                        })

            except WebSocketDisconnect:
                await ws_manager.disconnect(conn_id)

        @app.websocket("/ws/terminal/{project_id}")
        async def terminal_websocket(
            websocket: WebSocket,
            project_id: int,
            token: Optional[str] = Query(None, description="JWT auth token"),
        ):
            """
            WebSocket endpoint for terminal sessions with real PTY.

            **Authentication**: Pass JWT token as query parameter: `/ws/terminal/{project_id}?token=<jwt>`

            Provides real-time terminal I/O for workspace projects.
            """
            import asyncio
            import json
            import os

            # Validate token before accepting connection
            if not await _validate_ws_token(websocket, token):
                return

            await websocket.accept()

            try:
                from gathering.workspace.terminal_manager import terminal_manager

                # Get project path (for now use cwd, later integrate with projects)
                project_path = os.getcwd()

                # Create unique session ID
                session_id = f"{project_id}-{id(websocket)}"

                # Create terminal session
                session = terminal_manager.create_session(project_path, session_id)

                async def read_output():
                    """Background task to read terminal output."""
                    while session.running:
                        data = await session.read()
                        if data:
                            await websocket.send_text(data.decode('utf-8', errors='ignore'))
                        await asyncio.sleep(0.01)

                # Start output reader
                output_task = asyncio.create_task(read_output())

                try:
                    while True:
                        # Receive input from client
                        message = await websocket.receive_text()
                        data = json.loads(message)

                        if data.get("type") == "input":
                            input_data = data.get("data", "")
                            await session.write(input_data)

                        elif data.get("type") == "resize":
                            rows = data.get("rows", 24)
                            cols = data.get("cols", 80)
                            session.resize(rows, cols)

                except WebSocketDisconnect:
                    pass
                finally:
                    # Cleanup
                    output_task.cancel()
                    terminal_manager.close_session(session_id)

            except ImportError:
                # Fallback to echo mode if PTY not available (Windows, etc.)
                print("PTY not available, using echo mode")
                try:
                    while True:
                        message = await websocket.receive_text()
                        data = json.loads(message)

                        if data.get("type") == "input":
                            input_data = data.get("data", "")
                            if input_data == "\r":
                                await websocket.send_text("\r\n$ ")
                            elif input_data == "\x7F":
                                await websocket.send_text("\b \b")
                            else:
                                await websocket.send_text(input_data)

                except WebSocketDisconnect:
                    pass

            except Exception as e:
                print(f"Terminal WebSocket error: {e}")
                import traceback
                traceback.print_exc()

    # Root endpoint
    @app.get("/")
    async def root():
        """API root - returns basic info."""
        return {
            "name": title,
            "version": version,
            "docs": "/docs",
            "health": "/health",
        }

    return app


# Default app instance - check settings for auth disable
_settings = get_settings()
_enable_auth = not _settings.disable_auth

if _settings.disable_auth and _settings.is_development:
    print("⚠️  Authentication DISABLED (DISABLE_AUTH=true)")

app = create_app(enable_auth=_enable_auth)


# =============================================================================
# API Documentation
# =============================================================================

# Add custom OpenAPI tags
app.openapi_tags = [
    {
        "name": "health",
        "description": "Health check and readiness endpoints",
    },
    {
        "name": "auth",
        "description": "Authentication - login, registration, and token management",
    },
    {
        "name": "agents",
        "description": "Agent management - create, chat, and manage agent state",
    },
    {
        "name": "circles",
        "description": "Circle orchestration - manage teams, tasks, and workflows",
    },
    {
        "name": "conversations",
        "description": "Agent conversations - collaborative discussions between agents",
    },
    {
        "name": "dashboard",
        "description": "Dashboard data - agents, providers, models for web UI (supports demo/DB toggle)",
    },
    {
        "name": "memories",
        "description": "Agent memories and knowledge base - RAG with semantic search",
    },
    {
        "name": "background-tasks",
        "description": "Background task execution - long-running autonomous agent tasks",
    },
    {
        "name": "scheduled-actions",
        "description": "Scheduled actions - cron-like scheduling for agent tasks",
    },
    {
        "name": "goals",
        "description": "Agent goals - hierarchical goal tracking with decomposition",
    },
    {
        "name": "settings",
        "description": "Application settings - API keys, database, environment configuration",
    },
    {
        "name": "projects",
        "description": "Project management - browse folders, create projects, assign agents to projects",
    },
    {
        "name": "pipelines",
        "description": "Automated workflows - multi-agent pipeline orchestration and execution",
    },
]
