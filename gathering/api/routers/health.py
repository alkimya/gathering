"""
Health check endpoints.
"""

import os
import psutil
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends

from gathering.api.schemas import (
    HealthResponse,
    SystemMetricsResponse,
    CpuMetrics,
    MemoryMetrics,
    DiskMetrics,
    LoadAverage,
    HealthChecksResponse,
    ServiceHealth,
)
from gathering.api.dependencies import (
    get_agent_registry,
    get_circle_registry,
    get_database_service,
    AgentRegistry,
    CircleRegistry,
    DatabaseService,
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
        version="0.4.0",  # Sync with CHANGELOG.md
        uptime_seconds=uptime,
        agents_count=agent_registry.count(),
        circles_count=circle_registry.count(),
        active_tasks=active_tasks,
    )


@router.get("/system", response_model=SystemMetricsResponse)
async def get_system_metrics() -> SystemMetricsResponse:
    """
    Get system metrics (CPU, memory, disk, load).

    Returns real-time system metrics from the host machine.
    """
    # CPU metrics
    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_count = psutil.cpu_count() or 1
    cpu_freq = psutil.cpu_freq()
    cpu_freq_mhz = cpu_freq.current if cpu_freq else None

    # Memory metrics
    mem = psutil.virtual_memory()
    memory = MemoryMetrics(
        total_gb=round(mem.total / (1024 ** 3), 2),
        available_gb=round(mem.available / (1024 ** 3), 2),
        used_gb=round(mem.used / (1024 ** 3), 2),
        percent=mem.percent,
    )

    # Disk metrics (root partition)
    disk = psutil.disk_usage("/")
    disk_metrics = DiskMetrics(
        total_gb=round(disk.total / (1024 ** 3), 2),
        used_gb=round(disk.used / (1024 ** 3), 2),
        free_gb=round(disk.free / (1024 ** 3), 2),
        percent=disk.percent,
    )

    # Load average (Unix only)
    try:
        load = os.getloadavg()
        load_avg = LoadAverage(**{
            "1min": round(load[0], 2),
            "5min": round(load[1], 2),
            "15min": round(load[2], 2),
        })
    except (AttributeError, OSError):
        # Windows doesn't have getloadavg
        load_avg = LoadAverage(**{"1min": 0.0, "5min": 0.0, "15min": 0.0})

    # Uptime
    uptime = (datetime.now(timezone.utc) - _startup_time).total_seconds()

    return SystemMetricsResponse(
        cpu=CpuMetrics(
            percent=cpu_percent,
            count=cpu_count,
            frequency_mhz=cpu_freq_mhz,
        ),
        memory=memory,
        disk=disk_metrics,
        load_average=load_avg,
        uptime_seconds=uptime,
    )


@router.get("/checks", response_model=HealthChecksResponse)
async def get_health_checks(
    agent_registry: AgentRegistry = Depends(get_agent_registry),
    circle_registry: CircleRegistry = Depends(get_circle_registry),
    db_service: DatabaseService = Depends(get_database_service),
) -> HealthChecksResponse:
    """
    Get detailed health checks for all services.

    Checks:
    - API Server
    - Database connection
    - Memory usage
    - Disk space
    """
    now = datetime.now(timezone.utc)
    checks = []

    # API Server check (always healthy if we get here)
    checks.append(ServiceHealth(
        name="API Server",
        status="healthy",
        message="Responding normally",
        last_check=now,
    ))

    # Database check
    db_status = "healthy"
    db_message = "PostgreSQL connected"
    try:
        # Use sync query for health check
        result = db_service.fetch_one("SELECT 1 as ok")
        if not result:
            db_status = "warning"
            db_message = "Query returned no result"
    except Exception as e:
        db_status = "critical"
        db_message = f"Connection failed: {str(e)[:50]}"

    checks.append(ServiceHealth(
        name="Database",
        status=db_status,
        message=db_message,
        last_check=now,
    ))

    # Memory check
    mem = psutil.virtual_memory()
    mem_status = "healthy"
    if mem.percent >= 90:
        mem_status = "critical"
    elif mem.percent >= 70:
        mem_status = "warning"

    checks.append(ServiceHealth(
        name="Memory Usage",
        status=mem_status,
        value=f"{mem.percent:.1f}%",
        message="Above 70% threshold" if mem_status != "healthy" else "Normal",
        last_check=now,
    ))

    # Disk check
    disk = psutil.disk_usage("/")
    disk_status = "healthy"
    if disk.percent >= 90:
        disk_status = "critical"
    elif disk.percent >= 80:
        disk_status = "warning"

    checks.append(ServiceHealth(
        name="Disk Space",
        status=disk_status,
        value=f"{disk.percent:.1f}%",
        message="Sufficient space" if disk_status == "healthy" else "Low disk space",
        last_check=now,
    ))

    # Agents check
    agent_count = agent_registry.count()
    checks.append(ServiceHealth(
        name="Agents",
        status="healthy" if agent_count > 0 else "warning",
        value=str(agent_count),
        message=f"{agent_count} agent(s) registered",
        last_check=now,
    ))

    # Circles check
    circle_count = circle_registry.count()
    running_circles = len([c for c in circle_registry.list_all() if c.status.value == "running"])
    checks.append(ServiceHealth(
        name="Circles",
        status="healthy",
        value=f"{running_circles}/{circle_count}",
        message=f"{running_circles} running, {circle_count} total",
        last_check=now,
    ))

    # Determine overall status
    statuses = [c.status for c in checks]
    if "critical" in statuses:
        overall = "critical"
    elif "warning" in statuses:
        overall = "warning"
    else:
        overall = "healthy"

    return HealthChecksResponse(
        checks=checks,
        overall_status=overall,
    )


@router.get("/ready")
async def readiness_check():
    """Readiness probe for Kubernetes."""
    return {"ready": True}


@router.get("/live")
async def liveness_check():
    """Liveness probe for Kubernetes."""
    return {"alive": True}
