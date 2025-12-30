"""
GatheRing REST API Module.

FastAPI-based REST API for the GatheRing multi-agent framework.

Features:
- Agent management (CRUD, chat, status)
- Circle orchestration (create, start, stop, tasks)
- Agent conversations (collaborate, transcripts)
- Real-time updates via WebSocket
- Event streaming via SSE

Usage:
    # Run the API server
    uvicorn gathering.api:app --reload

    # Or programmatically
    from gathering.api import app, create_app

    # Custom configuration
    app = create_app(
        title="My GatheRing API",
        enable_websocket=True,
    )
"""

from gathering.api.main import app, create_app
from gathering.api.dependencies import (
    get_circle,
    get_memory_service,
    get_agent_registry,
)

__all__ = [
    "app",
    "create_app",
    "get_circle",
    "get_memory_service",
    "get_agent_registry",
]
