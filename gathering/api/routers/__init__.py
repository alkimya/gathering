"""
API Routers for GatheRing.
"""

from gathering.api.routers.agents import router as agents_router
from gathering.api.routers.auth import router as auth_router
from gathering.api.routers.circles import router as circles_router
from gathering.api.routers.conversations import router as conversations_router
from gathering.api.routers.dashboard import router as dashboard_router
from gathering.api.routers.health import router as health_router
from gathering.api.routers.memories import router as memories_router
from gathering.api.routers.models import models_router
from gathering.api.routers.background_tasks import background_tasks_router
from gathering.api.routers.scheduled_actions import router as scheduled_actions_router
from gathering.api.routers.goals import goals_router
from gathering.api.routers.settings import settings_router
from gathering.api.routers.projects import router as projects_router
from gathering.api.routers.pipelines import pipelines_router
from gathering.api.routers.websocket import router as websocket_router
from gathering.api.routers.workspace import router as workspace_router
from gathering.api.routers.lsp import router as lsp_router

__all__ = [
    "agents_router",
    "auth_router",
    "circles_router",
    "conversations_router",
    "dashboard_router",
    "health_router",
    "memories_router",
    "models_router",
    "background_tasks_router",
    "scheduled_actions_router",
    "goals_router",
    "settings_router",
    "projects_router",
    "pipelines_router",
    "websocket_router",
    "workspace_router",
    "lsp_router",
]
