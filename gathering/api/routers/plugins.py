"""
Plugin Management API Router.

Provides REST API endpoints for managing GatheRing plugins:
- List available and loaded plugins
- Load/unload plugins
- Enable/disable plugins
- Get plugin information and health
- Create dynamic plugins (for agents)
- Discover plugins from directories
"""

from typing import List, Optional, Dict, Any
from pathlib import Path
from fastapi import APIRouter, HTTPException, status, Body
from starlette.requests import Request

from gathering.api.rate_limit import limiter, TIER_READ, TIER_WRITE
from pydantic import BaseModel, Field

from gathering.plugins import plugin_manager
from gathering.core.tool_registry import tool_registry, ToolCategory


router = APIRouter(prefix="/plugins", tags=["plugins"])


# =============================================================================
# Pydantic Models
# =============================================================================


class PluginInfo(BaseModel):
    """Plugin information response."""

    id: str
    name: str
    version: str
    description: str
    author: str = ""
    license: str = "MIT"
    homepage: str = ""
    tags: List[str] = []
    status: str
    error: Optional[str] = None
    tools_count: int = 0
    competencies_count: int = 0

    class Config:
        from_attributes = True


class PluginListResponse(BaseModel):
    """List of plugins response."""

    plugins: List[PluginInfo]
    total: int


class PluginLoadRequest(BaseModel):
    """Request to load a plugin."""

    plugin_id: str = Field(..., description="Plugin ID to load")
    config: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional plugin configuration"
    )


class PluginActionResponse(BaseModel):
    """Response for plugin actions."""

    success: bool
    message: str
    plugin_id: str


class PluginHealthResponse(BaseModel):
    """Plugin health check response."""

    plugin_id: str
    status: str
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ToolInfo(BaseModel):
    """Tool information."""

    name: str
    description: str
    category: str
    required_competencies: List[str] = []
    plugin_id: Optional[str] = None


class DynamicToolConfig(BaseModel):
    """Configuration for a dynamic tool."""

    name: str = Field(..., description="Unique tool name")
    description: str = Field(..., description="Tool description")
    category: str = Field(default="custom", description="Tool category")
    required_competencies: List[str] = Field(
        default=[], description="Required competencies"
    )
    parameters: Dict[str, Any] = Field(default={}, description="Parameter schema")
    returns: Dict[str, Any] = Field(default={}, description="Return type schema")
    code: str = Field(..., description="Python code for the tool function")


class DynamicCompetencyConfig(BaseModel):
    """Configuration for a dynamic competency."""

    id: str = Field(..., description="Unique competency ID")
    name: str = Field(..., description="Competency name")
    description: str = Field(default="", description="Competency description")
    category: str = Field(default="custom", description="Competency category")
    level: str = Field(default="intermediate", description="Skill level")
    prerequisites: List[str] = Field(default=[], description="Prerequisite competencies")
    capabilities: List[str] = Field(default=[], description="Capabilities provided")


class CreateDynamicPluginRequest(BaseModel):
    """Request to create a dynamic plugin."""

    plugin_id: str = Field(..., description="Unique plugin identifier")
    name: str = Field(..., description="Human-readable plugin name")
    description: str = Field(..., description="Plugin description")
    version: str = Field(default="1.0.0", description="Semantic version")
    author: str = Field(default="GatheRing Agent", description="Plugin author")
    tools: List[DynamicToolConfig] = Field(
        default=[], description="Tools to create"
    )
    competencies: List[DynamicCompetencyConfig] = Field(
        default=[], description="Competencies to register"
    )
    config: Optional[Dict[str, Any]] = Field(
        default=None, description="Plugin configuration"
    )


class DiscoverPluginsRequest(BaseModel):
    """Request to discover plugins in a directory."""

    directory: str = Field(..., description="Directory path to scan")


class DiscoveredPluginInfo(BaseModel):
    """Information about a discovered plugin."""

    plugin_id: str
    path: str


class DiscoverPluginsResponse(BaseModel):
    """Response from plugin discovery."""

    discovered: List[DiscoveredPluginInfo]
    total: int


class PluginStatsResponse(BaseModel):
    """Plugin manager statistics."""

    available_plugins: int
    loaded_plugins: int
    enabled_plugins: int
    plugins_by_status: Dict[str, int]
    total_tools_from_plugins: int
    total_competencies_from_plugins: int


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=PluginListResponse)
@limiter.limit(TIER_READ)
async def list_plugins(
    request: Request,
    status_filter: Optional[str] = None,
    include_available: bool = True,
):
    """
    List all plugins.

    Args:
        status_filter: Filter by status (loaded, enabled, disabled, error)
        include_available: Include available but not loaded plugins
    """
    plugins = []

    # Add loaded plugins
    for plugin in plugin_manager.list_plugins():
        if status_filter and plugin.status.value != status_filter:
            continue

        info = plugin.get_info()
        plugins.append(PluginInfo(**info))

    # Add available but not loaded plugins
    if include_available:
        loaded_ids = {p.metadata.id for p in plugin_manager.list_plugins()}
        for plugin_id in plugin_manager.list_available_plugins():
            if plugin_id not in loaded_ids:
                plugins.append(
                    PluginInfo(
                        id=plugin_id,
                        name=plugin_id,
                        version="",
                        description="Available for loading",
                        status="available",
                    )
                )

    return PluginListResponse(plugins=plugins, total=len(plugins))


@router.get("/available", response_model=List[str])
@limiter.limit(TIER_READ)
async def list_available_plugins(request: Request):
    """List available plugin IDs that can be loaded."""
    return plugin_manager.list_available_plugins()


@router.get("/stats", response_model=PluginStatsResponse)
@limiter.limit(TIER_READ)
async def get_plugin_stats(request: Request):
    """Get plugin manager statistics."""
    return PluginStatsResponse(**plugin_manager.get_stats())


@router.get("/{plugin_id}", response_model=PluginInfo)
@limiter.limit(TIER_READ)
async def get_plugin(request: Request, plugin_id: str):
    """Get plugin information by ID."""
    plugin = plugin_manager.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin '{plugin_id}' not found or not loaded",
        )

    return PluginInfo(**plugin.get_info())


@router.get("/{plugin_id}/health", response_model=PluginHealthResponse)
@limiter.limit(TIER_READ)
async def check_plugin_health(request: Request, plugin_id: str):
    """Check plugin health."""
    plugin = plugin_manager.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin '{plugin_id}' not found or not loaded",
        )

    health = plugin.health_check()
    return PluginHealthResponse(
        plugin_id=plugin_id,
        status=health.get("status", "unknown"),
        error=health.get("error"),
        details=health,
    )


@router.get("/{plugin_id}/tools", response_model=List[ToolInfo])
@limiter.limit(TIER_READ)
async def get_plugin_tools(request: Request, plugin_id: str):
    """Get tools provided by a plugin."""
    plugin = plugin_manager.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin '{plugin_id}' not found or not loaded",
        )

    # Get tools from registry that belong to this plugin
    tools = tool_registry.list_by_plugin(plugin_id)
    return [
        ToolInfo(
            name=t.name,
            description=t.description,
            category=t.category.value,
            required_competencies=t.required_competencies,
            plugin_id=t.plugin_id,
        )
        for t in tools
    ]


@router.post("/load", response_model=PluginActionResponse)
@limiter.limit(TIER_WRITE)
async def load_plugin(request: Request, load_request: PluginLoadRequest):
    """
    Load a plugin.

    The plugin must be registered (either manually or via discovery).
    """
    try:
        plugin_manager.load_plugin(load_request.plugin_id, config=load_request.config)
        return PluginActionResponse(
            success=True,
            message=f"Plugin '{load_request.plugin_id}' loaded successfully",
            plugin_id=load_request.plugin_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load plugin: {e}",
        )


@router.post("/{plugin_id}/unload", response_model=PluginActionResponse)
@limiter.limit(TIER_WRITE)
async def unload_plugin(request: Request, plugin_id: str):
    """Unload a plugin."""
    try:
        plugin_manager.unload_plugin(plugin_id)
        return PluginActionResponse(
            success=True,
            message=f"Plugin '{plugin_id}' unloaded successfully",
            plugin_id=plugin_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{plugin_id}/enable", response_model=PluginActionResponse)
@limiter.limit(TIER_WRITE)
async def enable_plugin(request: Request, plugin_id: str):
    """Enable a loaded plugin."""
    try:
        plugin_manager.enable_plugin(plugin_id)
        return PluginActionResponse(
            success=True,
            message=f"Plugin '{plugin_id}' enabled successfully",
            plugin_id=plugin_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{plugin_id}/disable", response_model=PluginActionResponse)
@limiter.limit(TIER_WRITE)
async def disable_plugin(request: Request, plugin_id: str):
    """Disable a loaded plugin."""
    try:
        plugin_manager.disable_plugin(plugin_id)
        return PluginActionResponse(
            success=True,
            message=f"Plugin '{plugin_id}' disabled successfully",
            plugin_id=plugin_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/discover", response_model=DiscoverPluginsResponse)
@limiter.limit(TIER_WRITE)
async def discover_plugins(request: Request, discover_request: DiscoverPluginsRequest):
    """
    Discover plugins in a directory.

    Scans the directory for Python files containing Plugin classes.
    Discovered plugins are registered but not loaded.
    """
    try:
        path = Path(discover_request.directory)
        if not path.exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Directory does not exist: {discover_request.directory}",
            )

        # Add directory and discover
        plugin_manager.add_plugin_directory(path)
        discovered = plugin_manager.discover_plugins(path)

        return DiscoverPluginsResponse(
            discovered=[
                DiscoveredPluginInfo(plugin_id=pid, path=str(p))
                for pid, p in discovered.items()
            ],
            total=len(discovered),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Discovery failed: {e}",
        )


@router.post("/dynamic", response_model=PluginInfo)
@limiter.limit(TIER_WRITE)
async def create_dynamic_plugin(request: Request, create_request: CreateDynamicPluginRequest):
    """
    Create a dynamic plugin at runtime.

    This allows agents to extend GatheRing with new tools and competencies
    without writing plugin files.

    WARNING: The 'code' field in tools allows arbitrary Python code execution.
    Only use in trusted environments.
    """
    try:
        # Convert tool configs to the format expected by create_dynamic_plugin
        tools = []
        for tool_config in create_request.tools:
            # Compile the code to create the function
            # WARNING: This executes arbitrary code
            local_vars: Dict[str, Any] = {}
            exec(tool_config.code, {"__builtins__": __builtins__}, local_vars)

            # Find the function (should be the first callable)
            func = None
            for name, value in local_vars.items():
                if callable(value) and not name.startswith("_"):
                    func = value
                    break

            if not func:
                raise ValueError(f"No function found in tool '{tool_config.name}' code")

            # Get category
            try:
                category = ToolCategory(tool_config.category)
            except ValueError:
                category = ToolCategory.CUSTOM

            tools.append({
                "name": tool_config.name,
                "description": tool_config.description,
                "function": func,
                "category": category,
                "required_competencies": tool_config.required_competencies,
                "parameters": tool_config.parameters,
                "returns": tool_config.returns,
            })

        # Convert competency configs
        competencies = [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "category": c.category,
                "level": c.level,
                "prerequisites": c.prerequisites,
                "capabilities": c.capabilities,
            }
            for c in create_request.competencies
        ]

        # Create the plugin
        plugin = plugin_manager.create_dynamic_plugin(
            plugin_id=create_request.plugin_id,
            name=create_request.name,
            description=create_request.description,
            version=create_request.version,
            author=create_request.author,
            tools=tools,
            competencies=competencies,
            config=create_request.config,
        )

        return PluginInfo(**plugin.get_info())

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create dynamic plugin: {e}",
        )


@router.post("/{plugin_id}/save", response_model=PluginActionResponse)
@limiter.limit(TIER_WRITE)
async def save_dynamic_plugin(
    request: Request,
    plugin_id: str,
    output_path: str = Body(..., embed=True),
):
    """
    Save a dynamically created plugin to a file.

    This persists the plugin so it can be discovered and loaded in future sessions.
    """
    try:
        saved_path = plugin_manager.save_dynamic_plugin(plugin_id, Path(output_path))
        return PluginActionResponse(
            success=True,
            message=f"Plugin saved to {saved_path}",
            plugin_id=plugin_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save plugin: {e}",
        )


@router.get("/health/all", response_model=Dict[str, PluginHealthResponse])
@limiter.limit(TIER_READ)
async def check_all_plugin_health(request: Request):
    """Check health of all loaded plugins."""
    health_map = plugin_manager.health_check_all()
    return {
        plugin_id: PluginHealthResponse(
            plugin_id=plugin_id,
            status=health.get("status", "unknown"),
            error=health.get("error"),
            details=health,
        )
        for plugin_id, health in health_map.items()
    }
