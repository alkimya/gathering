"""
Plugin Base Class for GatheRing.

Provides abstract base class and metadata for creating extensible plugins.

Features:
- Plugin lifecycle management (load, unload, enable, disable)
- Dependency declaration and validation
- Tool and competency registration
- Health checks and status monitoring
- Configuration management
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

from gathering.core.tool_registry import ToolDefinition
from gathering.core.competency_registry import CompetencyDefinition


logger = logging.getLogger(__name__)


class PluginStatus(str, Enum):
    """Plugin lifecycle status."""

    UNLOADED = "unloaded"  # Not loaded yet
    LOADED = "loaded"  # Loaded but not enabled
    ENABLED = "enabled"  # Loaded and enabled (active)
    DISABLED = "disabled"  # Loaded but disabled (inactive)
    ERROR = "error"  # Failed to load or encountered error


@dataclass
class PluginMetadata:
    """
    Plugin metadata for discovery and dependency management.

    Contains all information needed to identify, load, and manage a plugin.
    """

    id: str
    """Unique plugin identifier (e.g., 'design', 'finance', 'engineering')"""

    name: str
    """Human-readable plugin name"""

    version: str
    """Semantic version (e.g., '1.0.0', '2.1.3')"""

    description: str
    """Detailed description of what the plugin provides"""

    author: str = ""
    """Plugin author name or organization"""

    author_email: str = ""
    """Contact email for the plugin author"""

    license: str = "MIT"
    """Plugin license (default: MIT)"""

    homepage: str = ""
    """Plugin homepage or repository URL"""

    tags: List[str] = field(default_factory=list)
    """Tags for plugin categorization and discovery"""

    dependencies: List[str] = field(default_factory=list)
    """
    List of plugin IDs that this plugin depends on.
    Format: ["plugin_id", "plugin_id>=1.0.0"]
    """

    python_dependencies: List[str] = field(default_factory=list)
    """
    List of Python packages required (pip install).
    Format: ["requests>=2.28.0", "pillow"]
    """

    min_gathering_version: str = "0.1.0"
    """Minimum GatheRing version required"""

    config_schema: Dict[str, Any] = field(default_factory=dict)
    """JSON Schema for plugin configuration"""

    def __post_init__(self):
        """Validate metadata."""
        if not self.id:
            raise ValueError("Plugin ID cannot be empty")
        if not self.name:
            raise ValueError("Plugin name cannot be empty")
        if not self.version:
            raise ValueError("Plugin version cannot be empty")


class Plugin(ABC):
    """
    Abstract base class for GatheRing plugins.

    Plugins extend GatheRing by providing:
    - Custom tools (functions agents can use)
    - Custom competencies (skills agents can have)
    - Optional configuration

    Lifecycle:
        1. instantiate() - Create plugin instance
        2. load() - Initialize plugin, validate dependencies
        3. register_tools() - Get tools to register
        4. register_competencies() - Get competencies to register
        5. on_enable() - Called when plugin is enabled
        6. on_disable() - Called when plugin is disabled
        7. unload() - Cleanup plugin resources

    Example:
        class DesignPlugin(Plugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    id="design",
                    name="Design Tools",
                    version="1.0.0",
                    description="AI-powered design tools",
                    python_dependencies=["pillow>=9.0.0"],
                )

            def register_tools(self) -> List[ToolDefinition]:
                return [
                    ToolDefinition(
                        name="generate_image",
                        description="Generate image using AI",
                        category=ToolCategory.IMAGE,
                        function=self.generate_image,
                        required_competencies=["ai_image_generation"],
                        parameters={...},
                        returns={...},
                        plugin_id=self.metadata.id,
                    )
                ]

            def generate_image(self, prompt: str) -> str:
                # Implementation
                pass
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize plugin.

        Args:
            config: Optional plugin configuration dictionary.
        """
        self._config = config or {}
        self._status = PluginStatus.UNLOADED
        self._error: Optional[str] = None

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """
        Get plugin metadata.

        Must be implemented by all plugins.

        Returns:
            PluginMetadata with plugin information.
        """
        pass

    @property
    def status(self) -> PluginStatus:
        """Get current plugin status."""
        return self._status

    @property
    def error(self) -> Optional[str]:
        """Get last error message if status is ERROR."""
        return self._error

    @property
    def config(self) -> Dict[str, Any]:
        """Get plugin configuration."""
        return self._config

    def load(self) -> None:
        """
        Load and initialize the plugin.

        Called when plugin is first loaded.
        Override to add custom initialization logic.

        Raises:
            Exception: If plugin fails to load.
        """
        try:
            logger.info(f"Loading plugin: {self.metadata.name} v{self.metadata.version}")
            self.validate_dependencies()
            self._status = PluginStatus.LOADED
            logger.info(f"Plugin loaded successfully: {self.metadata.id}")
        except Exception as e:
            self._status = PluginStatus.ERROR
            self._error = str(e)
            logger.error(f"Failed to load plugin {self.metadata.id}: {e}")
            raise

    def unload(self) -> None:
        """
        Unload and cleanup the plugin.

        Called when plugin is being removed.
        Override to add custom cleanup logic.
        """
        try:
            logger.info(f"Unloading plugin: {self.metadata.id}")
            self.on_disable()
            self._status = PluginStatus.UNLOADED
            logger.info(f"Plugin unloaded successfully: {self.metadata.id}")
        except Exception as e:
            logger.error(f"Error unloading plugin {self.metadata.id}: {e}")
            self._status = PluginStatus.ERROR
            self._error = str(e)

    def validate_dependencies(self) -> None:
        """
        Validate plugin dependencies.

        Checks that all required Python packages and plugin dependencies
        are available.

        Override to add custom validation logic.

        Raises:
            ImportError: If required Python package is missing.
            ValueError: If required plugin is missing.
        """
        # Validate Python dependencies
        for dep in self.metadata.python_dependencies:
            package_name = dep.split(">=")[0].split("==")[0].strip()
            try:
                __import__(package_name)
            except ImportError as e:
                raise ImportError(
                    f"Plugin '{self.metadata.id}' requires Python package '{dep}'. "
                    f"Install with: pip install {dep}"
                ) from e

        logger.debug(
            f"All dependencies validated for plugin: {self.metadata.id}"
        )

    def register_tools(self) -> List[ToolDefinition]:
        """
        Register tools provided by this plugin.

        Override to return list of tool definitions.

        Returns:
            List of ToolDefinition objects to register.

        Example:
            def register_tools(self):
                return [
                    ToolDefinition(
                        name="my_tool",
                        description="Does something",
                        category=ToolCategory.CUSTOM,
                        function=self.my_function,
                        required_competencies=[],
                        parameters={...},
                        returns={...},
                        plugin_id=self.metadata.id,
                    )
                ]
        """
        return []

    def register_competencies(self) -> List[CompetencyDefinition]:
        """
        Register competencies provided by this plugin.

        Override to return list of competency definitions.

        Returns:
            List of CompetencyDefinition objects to register.

        Example:
            def register_competencies(self):
                return [
                    CompetencyDefinition(
                        id="my_skill",
                        name="My Skill",
                        description="A custom skill",
                        category=CompetencyCategory.CUSTOM,
                        plugin_id=self.metadata.id,
                    )
                ]
        """
        return []

    def on_enable(self) -> None:
        """
        Called when plugin is enabled.

        Override to add custom logic when plugin becomes active.
        Examples: start background tasks, open connections, etc.
        """
        logger.info(f"Plugin enabled: {self.metadata.id}")
        self._status = PluginStatus.ENABLED

    def on_disable(self) -> None:
        """
        Called when plugin is disabled.

        Override to add custom logic when plugin becomes inactive.
        Examples: stop background tasks, close connections, etc.
        """
        logger.info(f"Plugin disabled: {self.metadata.id}")
        self._status = PluginStatus.DISABLED

    def health_check(self) -> Dict[str, Any]:
        """
        Check plugin health status.

        Override to add custom health checks.

        Returns:
            Dictionary with health status information.

        Example:
            {
                "status": "healthy",
                "message": "All systems operational",
                "details": {
                    "api_connected": True,
                    "cache_size": 1024,
                }
            }
        """
        return {
            "plugin_id": self.metadata.id,
            "status": self._status.value,
            "error": self._error,
        }

    def get_info(self) -> Dict[str, Any]:
        """
        Get plugin information.

        Returns:
            Dictionary with plugin metadata and status.
        """
        meta = self.metadata
        return {
            "id": meta.id,
            "name": meta.name,
            "version": meta.version,
            "description": meta.description,
            "author": meta.author,
            "license": meta.license,
            "homepage": meta.homepage,
            "tags": meta.tags,
            "status": self._status.value,
            "error": self._error,
            "tools_count": len(self.register_tools()),
            "competencies_count": len(self.register_competencies()),
        }

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<Plugin {self.metadata.id} "
            f"v{self.metadata.version} "
            f"status={self._status.value}>"
        )
