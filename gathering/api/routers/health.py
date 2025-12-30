"""
Health check endpoints.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends

from gathering.api.schemas import HealthResponse
from gathering.api.dependencies import (
    get_agent_registry,
    get_circle_registry,
    AgentRegistry,
    CircleRegistry,
)

router = APIRouter(prefix="/health", tags=["health"])

# Track startup time
_startup_time = datetime.now(timezone.utc)


@router.get("", response_model=HealthResponse)
async def health_check(
    agent_registry: AgentRegistry = Depends(get_agent_registry),
    circle_registry: CircleRegistry = Depends(get_circle_registry),
) -> HealthResponse:
    """
    Health check endpoint.

    Returns the current status of the API including:
    - Version information
    - Uptime
    - Agent and circle counts
    - Active task count
    """
    uptime = (datetime.now(timezone.utc) - _startup_time).total_seconds()

    # Count active tasks across all circles
    active_tasks = 0
    for circle in circle_registry.list_all():
        active_tasks += len([
            t for t in circle.tasks.values()
            if t.status.value in ("assigned", "in_progress", "in_review")
        ])

    return HealthResponse(
        status="healthy",
        version="0.4.0",
        uptime_seconds=uptime,
        agents_count=agent_registry.count(),
        circles_count=circle_registry.count(),
        active_tasks=active_tasks,
    )


@router.get("/ready")
async def readiness_check():
    """Readiness probe for Kubernetes."""
    return {"ready": True}


@router.get("/live")
async def liveness_check():
    """Liveness probe for Kubernetes."""
    return {"alive": True}
