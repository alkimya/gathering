"""
Agent Tools API endpoints.
Manages skills/tools assigned to agents.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from starlette.requests import Request

from gathering.api.rate_limit import limiter, TIER_READ, TIER_WRITE
from pydantic import BaseModel, Field

from gathering.api.dependencies import get_database_service, DatabaseService
from gathering.skills.registry import SkillRegistry


# =============================================================================
# Pydantic Schemas
# =============================================================================

class SkillInfo(BaseModel):
    """Skill information."""
    id: int
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    category: str = "general"
    required_permissions: List[str] = Field(default_factory=list)
    is_dangerous: bool = False
    is_enabled: bool = True
    version: str = "1.0.0"
    tools_count: int = 0


class AgentToolInfo(BaseModel):
    """Tool assignment for an agent."""
    skill_id: int
    skill_name: str
    skill_display_name: Optional[str] = None
    skill_category: str
    required_permissions: List[str] = Field(default_factory=list)
    is_dangerous: bool = False
    is_enabled: bool = False
    usage_count: int = 0
    last_used_at: Optional[str] = None


class AgentToolsResponse(BaseModel):
    """Response with all tools for an agent."""
    agent_id: int
    agent_name: str
    tools: List[AgentToolInfo]
    enabled_count: int
    total_count: int


class ToolToggleRequest(BaseModel):
    """Request to enable/disable a tool."""
    is_enabled: bool


class BulkToolsRequest(BaseModel):
    """Request to bulk enable/disable tools."""
    skill_names: List[str]
    is_enabled: bool


# =============================================================================
# Router
# =============================================================================

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("/skills", response_model=List[SkillInfo])
@limiter.limit(TIER_READ)
async def list_skills(
    request: Request,
    category: Optional[str] = None,
    db: DatabaseService = Depends(get_database_service),
):
    """List all available skills."""
    if category:
        query = """
            SELECT id, name, display_name, description, category,
                   required_permissions, is_dangerous, is_enabled, version
            FROM agent.skills
            WHERE is_enabled = true AND category = %(category)s
            ORDER BY category, name
        """
        rows = db.fetch_all(query, {'category': category})
    else:
        query = """
            SELECT id, name, display_name, description, category,
                   required_permissions, is_dangerous, is_enabled, version
            FROM agent.skills
            WHERE is_enabled = true
            ORDER BY category, name
        """
        rows = db.fetch_all(query)

    skills = []
    for row in rows:
        # Get tools count from registry
        tools_count = 0
        try:
            skill_info = SkillRegistry.get_skill_info(row["name"])
            tools_count = skill_info.get("tools_count", 0)
        except (ValueError, Exception):
            pass

        skills.append(SkillInfo(
            id=row["id"],
            name=row["name"],
            display_name=row.get("display_name"),
            description=row.get("description"),
            category=row.get("category", "general"),
            required_permissions=row.get("required_permissions", []),
            is_dangerous=row.get("is_dangerous", False),
            is_enabled=row.get("is_enabled", True),
            version=row.get("version", "1.0.0"),
            tools_count=tools_count,
        ))

    return skills


@router.get("/skills/categories")
@limiter.limit(TIER_READ)
async def list_skill_categories(request: Request, db: DatabaseService = Depends(get_database_service)):
    """List all skill categories with counts."""
    rows = db.fetch_all("""
        SELECT category, COUNT(*) as count
        FROM agent.skills
        WHERE is_enabled = true
        GROUP BY category
        ORDER BY category
    """)

    return {row["category"]: row["count"] for row in rows}


@router.get("/agents/{agent_id}", response_model=AgentToolsResponse)
@limiter.limit(TIER_READ)
async def get_agent_tools(
    request: Request,
    agent_id: int,
    db: DatabaseService = Depends(get_database_service),
):
    """Get all tools for an agent with enabled/disabled status."""
    # Check agent exists
    agent = db.fetch_one(
        "SELECT id, name FROM agent.agents WHERE id = %(agent_id)s",
        {'agent_id': agent_id}
    )
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    # Get all tools with status
    rows = db.fetch_all("""
        SELECT
            s.id AS skill_id,
            s.name AS skill_name,
            s.display_name AS skill_display_name,
            s.category AS skill_category,
            s.required_permissions,
            s.is_dangerous,
            COALESCE(at.is_enabled, false) AS is_enabled,
            COALESCE(at.usage_count, 0) AS usage_count,
            at.last_used_at
        FROM agent.skills s
        LEFT JOIN agent.agent_tools at ON at.skill_id = s.id AND at.agent_id = %(agent_id)s
        WHERE s.is_enabled = true
        ORDER BY s.category, s.name
    """, {'agent_id': agent_id})

    tools = []
    enabled_count = 0
    for row in rows:
        is_enabled = row.get("is_enabled", False)
        if is_enabled:
            enabled_count += 1

        tools.append(AgentToolInfo(
            skill_id=row["skill_id"],
            skill_name=row["skill_name"],
            skill_display_name=row.get("skill_display_name"),
            skill_category=row.get("skill_category", "general"),
            required_permissions=row.get("required_permissions", []),
            is_dangerous=row.get("is_dangerous", False),
            is_enabled=is_enabled,
            usage_count=row.get("usage_count", 0),
            last_used_at=row.get("last_used_at").isoformat() if row.get("last_used_at") else None,
        ))

    return AgentToolsResponse(
        agent_id=agent_id,
        agent_name=agent["name"],
        tools=tools,
        enabled_count=enabled_count,
        total_count=len(tools),
    )


@router.patch("/agents/{agent_id}/skills/{skill_name}")
@limiter.limit(TIER_WRITE)
async def toggle_agent_tool(
    request: Request,
    agent_id: int,
    skill_name: str,
    toggle_request: ToolToggleRequest,
    db: DatabaseService = Depends(get_database_service),
):
    """Enable or disable a tool for an agent."""
    # Check agent exists
    agent = db.fetch_one(
        "SELECT id FROM agent.agents WHERE id = %(agent_id)s",
        {'agent_id': agent_id}
    )
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    # Get skill
    skill = db.fetch_one(
        "SELECT id, name, is_dangerous FROM agent.skills WHERE name = %(skill_name)s",
        {'skill_name': skill_name}
    )
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

    # Upsert agent_tool
    db.execute("""
        INSERT INTO agent.agent_tools (agent_id, skill_id, is_enabled)
        VALUES (%(agent_id)s, %(skill_id)s, %(is_enabled)s)
        ON CONFLICT (agent_id, skill_id)
        DO UPDATE SET is_enabled = %(is_enabled)s, updated_at = NOW()
    """, {'agent_id': agent_id, 'skill_id': skill["id"], 'is_enabled': toggle_request.is_enabled})

    return {
        "agent_id": agent_id,
        "skill_name": skill_name,
        "is_enabled": toggle_request.is_enabled,
        "message": f"Tool '{skill_name}' {'enabled' if toggle_request.is_enabled else 'disabled'} for agent {agent_id}",
    }


@router.post("/agents/{agent_id}/skills/bulk")
@limiter.limit(TIER_WRITE)
async def bulk_toggle_tools(
    request: Request,
    agent_id: int,
    bulk_request: BulkToolsRequest,
    db: DatabaseService = Depends(get_database_service),
):
    """Bulk enable or disable multiple tools for an agent."""
    # Check agent exists
    agent = db.fetch_one(
        "SELECT id FROM agent.agents WHERE id = %(agent_id)s",
        {'agent_id': agent_id}
    )
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    updated = 0
    for skill_name in bulk_request.skill_names:
        skill = db.fetch_one(
            "SELECT id FROM agent.skills WHERE name = %(skill_name)s",
            {'skill_name': skill_name}
        )
        if skill:
            db.execute("""
                INSERT INTO agent.agent_tools (agent_id, skill_id, is_enabled)
                VALUES (%(agent_id)s, %(skill_id)s, %(is_enabled)s)
                ON CONFLICT (agent_id, skill_id)
                DO UPDATE SET is_enabled = %(is_enabled)s, updated_at = NOW()
            """, {'agent_id': agent_id, 'skill_id': skill["id"], 'is_enabled': bulk_request.is_enabled})
            updated += 1

    return {
        "agent_id": agent_id,
        "updated_count": updated,
        "is_enabled": bulk_request.is_enabled,
        "message": f"{updated} tools {'enabled' if bulk_request.is_enabled else 'disabled'}",
    }


@router.post("/agents/{agent_id}/skills/enable-all")
@limiter.limit(TIER_WRITE)
async def enable_all_tools(
    request: Request,
    agent_id: int,
    category: Optional[str] = None,
    db: DatabaseService = Depends(get_database_service),
):
    """Enable all tools (optionally by category) for an agent."""
    # Check agent exists
    agent = db.fetch_one(
        "SELECT id FROM agent.agents WHERE id = %(agent_id)s",
        {'agent_id': agent_id}
    )
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    # Get skills to enable
    if category:
        skills = db.fetch_all(
            "SELECT id, name FROM agent.skills WHERE is_enabled = true AND category = %(category)s",
            {'category': category}
        )
    else:
        skills = db.fetch_all("SELECT id, name FROM agent.skills WHERE is_enabled = true")

    for skill in skills:
        db.execute("""
            INSERT INTO agent.agent_tools (agent_id, skill_id, is_enabled)
            VALUES (%(agent_id)s, %(skill_id)s, true)
            ON CONFLICT (agent_id, skill_id)
            DO UPDATE SET is_enabled = true, updated_at = NOW()
        """, {'agent_id': agent_id, 'skill_id': skill["id"]})

    return {
        "agent_id": agent_id,
        "enabled_count": len(skills),
        "category": category,
        "message": f"Enabled {len(skills)} tools" + (f" in category '{category}'" if category else ""),
    }


@router.post("/agents/{agent_id}/skills/disable-all")
@limiter.limit(TIER_WRITE)
async def disable_all_tools(
    request: Request,
    agent_id: int,
    category: Optional[str] = None,
    db: DatabaseService = Depends(get_database_service),
):
    """Disable all tools (optionally by category) for an agent."""
    if category:
        db.execute("""
            UPDATE agent.agent_tools at
            SET is_enabled = false, updated_at = NOW()
            FROM agent.skills s
            WHERE at.skill_id = s.id
              AND at.agent_id = %(agent_id)s
              AND s.category = %(category)s
        """, {'agent_id': agent_id, 'category': category})
    else:
        db.execute("""
            UPDATE agent.agent_tools
            SET is_enabled = false, updated_at = NOW()
            WHERE agent_id = %(agent_id)s
        """, {'agent_id': agent_id})

    return {
        "agent_id": agent_id,
        "category": category,
        "message": "Disabled all tools" + (f" in category '{category}'" if category else ""),
    }


@router.get("/agents/{agent_id}/enabled")
@limiter.limit(TIER_READ)
async def get_enabled_tool_names(
    request: Request,
    agent_id: int,
    db: DatabaseService = Depends(get_database_service),
):
    """Get list of enabled tool names for an agent (for agent chat context)."""
    rows = db.fetch_all("""
        SELECT s.name
        FROM agent.agent_tools at
        JOIN agent.skills s ON s.id = at.skill_id
        WHERE at.agent_id = %(agent_id)s
          AND at.is_enabled = true
          AND s.is_enabled = true
        ORDER BY s.name
    """, {'agent_id': agent_id})

    return {
        "agent_id": agent_id,
        "enabled_skills": [row["name"] for row in rows],
    }


# Export router
tools_router = router
