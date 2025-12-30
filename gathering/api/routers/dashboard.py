"""
Dashboard endpoints - provides data for the web dashboard.

Uses USE_DEMO_DATA toggle to switch between demo and real database data.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from gathering.api.dependencies import get_data_service, DataService, use_demo_data


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/config")
async def get_dashboard_config() -> dict:
    """Get dashboard configuration including data source mode."""
    return {
        "demo_mode": use_demo_data(),
        "version": "0.1.1",
        "features": {
            "agents": True,
            "circles": True,
            "conversations": True,
            "memories": True,
        },
    }


@router.get("/agents")
async def list_dashboard_agents(
    data: DataService = Depends(get_data_service),
) -> dict:
    """List agents for dashboard display."""
    agents = data.get_agents()
    return {
        "agents": agents,
        "total": len(agents),
        "demo_mode": data.is_demo_mode,
    }


@router.get("/agents/{agent_id}")
async def get_dashboard_agent(
    agent_id: int,
    data: DataService = Depends(get_data_service),
) -> dict:
    """Get agent details for dashboard display."""
    agent = data.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )
    return {
        "agent": agent,
        "demo_mode": data.is_demo_mode,
    }


@router.get("/providers")
async def list_dashboard_providers(
    data: DataService = Depends(get_data_service),
) -> dict:
    """List LLM providers for dashboard display."""
    providers = data.get_providers()
    return {
        "providers": providers,
        "total": len(providers),
        "demo_mode": data.is_demo_mode,
    }


@router.get("/providers/{provider_id}")
async def get_dashboard_provider(
    provider_id: int,
    data: DataService = Depends(get_data_service),
) -> dict:
    """Get provider details for dashboard display."""
    provider = data.get_provider(provider_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider {provider_id} not found",
        )
    return {
        "provider": provider,
        "demo_mode": data.is_demo_mode,
    }


@router.get("/models")
async def list_dashboard_models(
    provider_id: Optional[int] = None,
    data: DataService = Depends(get_data_service),
) -> dict:
    """List models for dashboard display."""
    models = data.get_models(provider_id)
    return {
        "models": models,
        "total": len(models),
        "provider_id": provider_id,
        "demo_mode": data.is_demo_mode,
    }


@router.get("/models/{model_id}")
async def get_dashboard_model(
    model_id: int,
    data: DataService = Depends(get_data_service),
) -> dict:
    """Get model details for dashboard display."""
    model = data.get_model(model_id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found",
        )
    return {
        "model": model,
        "demo_mode": data.is_demo_mode,
    }


@router.get("/stats")
async def get_dashboard_stats(
    data: DataService = Depends(get_data_service),
) -> dict:
    """Get aggregated stats for dashboard."""
    agents = data.get_agents()
    providers = data.get_providers()
    models = data.get_models()
    circles = data.get_circles()

    # Calculate stats
    active_agents = sum(1 for a in agents if a.get("is_active", True))
    busy_agents = sum(1 for a in agents if a.get("status") == "busy")
    total_tasks = sum(a.get("tasks_completed", 0) for a in agents)
    total_reviews = sum(a.get("reviews_done", 0) for a in agents)

    active_circles = sum(1 for c in circles if c.get("status") == "running")
    total_circle_tasks = sum(c.get("task_count", 0) for c in circles)

    return {
        "agents": {
            "total": len(agents),
            "active": active_agents,
            "busy": busy_agents,
            "idle": active_agents - busy_agents,
        },
        "providers": {
            "total": len(providers),
        },
        "models": {
            "total": len(models),
        },
        "circles": {
            "total": len(circles),
            "active": active_circles,
            "total_tasks": total_circle_tasks,
        },
        "activity": {
            "tasks_completed": total_tasks,
            "reviews_done": total_reviews,
        },
        "demo_mode": data.is_demo_mode,
    }


@router.get("/circles")
async def list_dashboard_circles(
    is_active: Optional[bool] = None,
    data: DataService = Depends(get_data_service),
) -> dict:
    """List circles for dashboard display."""
    circles = data.get_circles(is_active)
    return {
        "circles": circles,
        "total": len(circles),
        "demo_mode": data.is_demo_mode,
    }


@router.get("/circles/{circle_id}")
async def get_dashboard_circle(
    circle_id: int,
    data: DataService = Depends(get_data_service),
) -> dict:
    """Get circle details for dashboard display."""
    circle = data.get_circle(circle_id)
    if not circle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circle {circle_id} not found",
        )
    return {
        "circle": circle,
        "demo_mode": data.is_demo_mode,
    }


@router.get("/circles/{circle_id}/members")
async def list_circle_members(
    circle_id: int,
    data: DataService = Depends(get_data_service),
) -> dict:
    """List members of a circle."""
    # Verify circle exists
    circle = data.get_circle(circle_id)
    if not circle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circle {circle_id} not found",
        )

    members = data.get_circle_members(circle_id)
    return {
        "circle_id": circle_id,
        "members": members,
        "total": len(members),
        "demo_mode": data.is_demo_mode,
    }


@router.get("/circles/{circle_id}/tasks")
async def list_circle_tasks(
    circle_id: int,
    status: Optional[str] = None,
    data: DataService = Depends(get_data_service),
) -> dict:
    """List tasks in a circle, optionally filtered by status."""
    # Verify circle exists
    circle = data.get_circle(circle_id)
    if not circle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circle {circle_id} not found",
        )

    tasks = data.get_circle_tasks(circle_id, status)
    return {
        "circle_id": circle_id,
        "tasks": tasks,
        "total": len(tasks),
        "status_filter": status,
        "demo_mode": data.is_demo_mode,
    }
