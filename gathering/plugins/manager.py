"""
Plugin Manager for GatheRing.

Manages plugin lifecycle, dependency resolution, and registry integration.

Features:
- Load/unload plugins dynamically
- Validate plugin dependencies
- Register tools and competencies from plugins
- Enable/disable plugins
- Query plugin status and information
"""

from typing import Dict, List, Optional, Type, Any
import logging

from gathering.plugins.base import Plugin, PluginStatus, PluginMetadata
from gathering.core.tool_registry import tool_registry, ToolDefinition
from gathering.core.competency_registry import (
    competency_registry,
    CompetencyDefinition,
)


logger = logging.getLogger(__name__)


class PluginManager:
    """
    Plugin manager for loading and managing GatheRing plugins.

    Handles plugin lifecycle, dependency resolution, and integration
    with tool and competency registries.

    Thread-safe for concurrent access.

    Example:
        # Create manager
        manager = PluginManager()

        # Register plugin class
        manager.register_plugin_class("design", DesignPlugin)

        # Load plugin
        manager.load_plugin("design", config={...})

        # Enable plugin
        manager.enable_plugin("design")

        # Query
        info = manager.get_plugin_info("design")
        all_plugins = manager.list_plugins()

        # Unload
        manager.unload_plugin("design")
    """

    def __init__(
        self,
        tool_registry=tool_registry,
        competency_registry=competency_registry,
    ):
        """
        Initialize plugin manager.

        Args:
            tool_registry: Tool registry instance (default: global).
            competency_registry: Competency registry instance (default: global).
        """
        self._tool_registry = tool_registry
        self._competency_registry = competency_registry

        # Plugin storage
        self._plugin_classes: Dict[str, Type[Plugin]] = {}
        self._plugins: Dict[str, Plugin] = {}
        self._plugin_tools: Dict[str, List[str]] = {}  # plugin_id -> tool names
        self._plugin_competencies: Dict[str, List[str]] = {}  # plugin_id -> comp ids

    def register_plugin_class(
        self, plugin_id: str, plugin_class: Type[Plugin]
    ) -> None:
        """
        Register a plugin class for loading.

        Args:
            plugin_id: Unique plugin identifier.
            plugin_class: Plugin class (subclass of Plugin).

        Raises:
            ValueError: If plugin_id already registered.
            TypeError: If plugin_class is not a Plugin subclass.

        Example:
            >>> manager.register_plugin_class("design", DesignPlugin)
        """
        if plugin_id in self._plugin_classes:
            raise ValueError(
                f"Plugin class '{plugin_id}' already registered. "
                f"Unregister first to replace it."
            )

        if not issubclass(plugin_class, Plugin):
            raise TypeError(f"plugin_class must be a subclass of Plugin")

        self._plugin_classes[plugin_id] = plugin_class
        logger.info(f"Plugin class registered: {plugin_id}")

    def unregister_plugin_class(self, plugin_id: str) -> bool:
        """
        Unregister a plugin class.

        Args:
            plugin_id: Plugin identifier.

        Returns:
            True if plugin class was removed, False if it didn't exist.

        Raises:
            ValueError: If plugin is currently loaded.

        Example:
            >>> manager.unregister_plugin_class("design")
            True
        """
        if plugin_id not in self._plugin_classes:
            return False

        if plugin_id in self._plugins:
            raise ValueError(
                f"Cannot unregister plugin class '{plugin_id}': "
                f"plugin is currently loaded. Unload it first."
            )

        del self._plugin_classes[plugin_id]
        logger.info(f"Plugin class unregistered: {plugin_id}")
        return True

    def load_plugin(
        self, plugin_id: str, config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Load and initialize a plugin.

        Args:
            plugin_id: Plugin identifier.
            config: Optional plugin configuration.

        Raises:
            ValueError: If plugin not registered or already loaded.
            Exception: If plugin fails to load.

        Example:
            >>> manager.load_plugin("design", config={"api_key": "..."})
        """
        if plugin_id not in self._plugin_classes:
            raise ValueError(
                f"Plugin '{plugin_id}' not registered. "
                f"Register plugin class first with register_plugin_class()."
            )

        if plugin_id in self._plugins:
            raise ValueError(f"Plugin '{plugin_id}' already loaded")

        # Instantiate plugin
        plugin_class = self._plugin_classes[plugin_id]
        plugin = plugin_class(config=config)

        # Validate plugin ID matches
        if plugin.metadata.id != plugin_id:
            raise ValueError(
                f"Plugin metadata ID '{plugin.metadata.id}' "
                f"doesn't match registered ID '{plugin_id}'"
            )

        # Validate plugin dependencies
        self._validate_plugin_dependencies(plugin)

        # Load plugin
        plugin.load()

        # Register tools
        tools = plugin.register_tools()
        for tool in tools:
            # Ensure plugin_id is set
            if tool.plugin_id != plugin_id:
                tool.plugin_id = plugin_id

            self._tool_registry.register(tool)

            # Track tools
            if plugin_id not in self._plugin_tools:
                self._plugin_tools[plugin_id] = []
            self._plugin_tools[plugin_id].append(tool.name)

        logger.info(f"Registered {len(tools)} tools from plugin: {plugin_id}")

        # Register competencies
        competencies = plugin.register_competencies()
        for comp in competencies:
            # Ensure plugin_id is set
            if comp.plugin_id != plugin_id:
                comp.plugin_id = plugin_id

            self._competency_registry.register(comp)

            # Track competencies
            if plugin_id not in self._plugin_competencies:
                self._plugin_competencies[plugin_id] = []
            self._plugin_competencies[plugin_id].append(comp.id)

        logger.info(
            f"Registered {len(competencies)} competencies from plugin: {plugin_id}"
        )

        # Store plugin
        self._plugins[plugin_id] = plugin

        logger.info(
            f"Plugin loaded successfully: {plugin.metadata.name} v{plugin.metadata.version}"
        )

    def unload_plugin(self, plugin_id: str) -> None:
        """
        Unload a plugin and cleanup resources.

        Args:
            plugin_id: Plugin identifier.

        Raises:
            ValueError: If plugin not loaded or other plugins depend on it.

        Example:
            >>> manager.unload_plugin("design")
        """
        if plugin_id not in self._plugins:
            raise ValueError(f"Plugin '{plugin_id}' is not loaded")

        # Check if other plugins depend on this one
        dependents = self._get_dependent_plugins(plugin_id)
        if dependents:
            raise ValueError(
                f"Cannot unload plugin '{plugin_id}': "
                f"plugins {dependents} depend on it"
            )

        plugin = self._plugins[plugin_id]

        # Unregister competencies (must be done before tools)
        # Unregister in reverse dependency order (dependents first)
        comp_ids = self._plugin_competencies.get(plugin_id, [])

        # Build dependency graph and find order
        remaining = set(comp_ids)
        unregistered = []

        while remaining:
            # Find competencies with no dependents in remaining set
            can_unregister = []
            for comp_id in remaining:
                dependents = self._competency_registry.get_dependents(comp_id)
                # Only unregister if no remaining competencies depend on it
                if not any(dep in remaining for dep in dependents):
                    can_unregister.append(comp_id)

            # If we can't unregister anything, there's a cycle or external dependency
            if not can_unregister:
                # Force unregister remaining (log warnings)
                can_unregister = list(remaining)

            # Unregister this batch
            for comp_id in can_unregister:
                try:
                    self._competency_registry.unregister(comp_id)
                    unregistered.append(comp_id)
                except Exception as e:
                    logger.warning(
                        f"Failed to unregister competency '{comp_id}': {e}"
                    )
                remaining.discard(comp_id)

        # Unregister tools
        tool_names = self._plugin_tools.get(plugin_id, [])
        for tool_name in tool_names:
            try:
                self._tool_registry.unregister(tool_name)
            except Exception as e:
                logger.warning(f"Failed to unregister tool '{tool_name}': {e}")

        # Unload plugin
        plugin.unload()

        # Cleanup
        del self._plugins[plugin_id]
        if plugin_id in self._plugin_tools:
            del self._plugin_tools[plugin_id]
        if plugin_id in self._plugin_competencies:
            del self._plugin_competencies[plugin_id]

        logger.info(f"Plugin unloaded: {plugin_id}")

    def enable_plugin(self, plugin_id: str) -> None:
        """
        Enable a loaded plugin.

        Args:
            plugin_id: Plugin identifier.

        Raises:
            ValueError: If plugin not loaded.

        Example:
            >>> manager.enable_plugin("design")
        """
        plugin = self._get_plugin(plugin_id)
        plugin.on_enable()
        logger.info(f"Plugin enabled: {plugin_id}")

    def disable_plugin(self, plugin_id: str) -> None:
        """
        Disable a loaded plugin.

        Args:
            plugin_id: Plugin identifier.

        Raises:
            ValueError: If plugin not loaded.

        Example:
            >>> manager.disable_plugin("design")
        """
        plugin = self._get_plugin(plugin_id)
        plugin.on_disable()
        logger.info(f"Plugin disabled: {plugin_id}")

    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """
        Get loaded plugin instance.

        Args:
            plugin_id: Plugin identifier.

        Returns:
            Plugin instance or None if not loaded.

        Example:
            >>> plugin = manager.get_plugin("design")
            >>> if plugin:
            ...     print(plugin.metadata.name)
        """
        return self._plugins.get(plugin_id)

    def has_plugin(self, plugin_id: str) -> bool:
        """
        Check if plugin is loaded.

        Args:
            plugin_id: Plugin identifier.

        Returns:
            True if plugin is loaded.

        Example:
            >>> if manager.has_plugin("design"):
            ...     print("Design plugin is available")
        """
        return plugin_id in self._plugins

    def list_plugins(
        self, status: Optional[PluginStatus] = None
    ) -> List[Plugin]:
        """
        List loaded plugins.

        Args:
            status: Optional filter by status.

        Returns:
            List of plugin instances.

        Example:
            >>> all_plugins = manager.list_plugins()
            >>> enabled = manager.list_plugins(status=PluginStatus.ENABLED)
        """
        plugins = list(self._plugins.values())

        if status:
            plugins = [p for p in plugins if p.status == status]

        return plugins

    def list_available_plugins(self) -> List[str]:
        """
        List available plugin classes that can be loaded.

        Returns:
            List of plugin IDs.

        Example:
            >>> available = manager.list_available_plugins()
            >>> print(f"Can load: {available}")
        """
        return list(self._plugin_classes.keys())

    def get_plugin_info(self, plugin_id: str) -> Dict[str, Any]:
        """
        Get plugin information.

        Args:
            plugin_id: Plugin identifier.

        Returns:
            Dictionary with plugin info.

        Raises:
            ValueError: If plugin not loaded.

        Example:
            >>> info = manager.get_plugin_info("design")
            >>> print(info["version"])
        """
        plugin = self._get_plugin(plugin_id)
        return plugin.get_info()

    def health_check(self, plugin_id: str) -> Dict[str, Any]:
        """
        Check plugin health.

        Args:
            plugin_id: Plugin identifier.

        Returns:
            Dictionary with health status.

        Raises:
            ValueError: If plugin not loaded.

        Example:
            >>> health = manager.health_check("design")
            >>> print(health["status"])
        """
        plugin = self._get_plugin(plugin_id)
        return plugin.health_check()

    def health_check_all(self) -> Dict[str, Any]:
        """
        Check health of all loaded plugins.

        Returns:
            Dictionary mapping plugin IDs to health status.

        Example:
            >>> health = manager.health_check_all()
            >>> for plugin_id, status in health.items():
            ...     print(f"{plugin_id}: {status['status']}")
        """
        return {
            plugin_id: plugin.health_check()
            for plugin_id, plugin in self._plugins.items()
        }

    def get_stats(self) -> Dict[str, Any]:
        """
        Get plugin manager statistics.

        Returns:
            Dictionary with statistics.

        Example:
            >>> stats = manager.get_stats()
            >>> print(f"Loaded plugins: {stats['loaded_plugins']}")
        """
        return {
            "available_plugins": len(self._plugin_classes),
            "loaded_plugins": len(self._plugins),
            "enabled_plugins": len(
                [p for p in self._plugins.values() if p.status == PluginStatus.ENABLED]
            ),
            "plugins_by_status": {
                status.value: len(
                    [p for p in self._plugins.values() if p.status == status]
                )
                for status in PluginStatus
            },
            "total_tools_from_plugins": sum(
                len(tools) for tools in self._plugin_tools.values()
            ),
            "total_competencies_from_plugins": sum(
                len(comps) for comps in self._plugin_competencies.values()
            ),
        }

    def _get_plugin(self, plugin_id: str) -> Plugin:
        """Get plugin or raise error."""
        if plugin_id not in self._plugins:
            raise ValueError(f"Plugin '{plugin_id}' is not loaded")
        return self._plugins[plugin_id]

    def _validate_plugin_dependencies(self, plugin: Plugin) -> None:
        """
        Validate plugin dependencies are satisfied.

        Args:
            plugin: Plugin instance to validate.

        Raises:
            ValueError: If dependencies are not satisfied.
        """
        for dep in plugin.metadata.dependencies:
            # Parse dependency (e.g., "plugin_id>=1.0.0" or "plugin_id")
            dep_id = dep.split(">=")[0].split("==")[0].strip()

            if dep_id not in self._plugins:
                raise ValueError(
                    f"Plugin '{plugin.metadata.id}' requires plugin '{dep_id}' "
                    f"which is not loaded. Load '{dep_id}' first."
                )

    def _get_dependent_plugins(self, plugin_id: str) -> List[str]:
        """
        Get plugins that depend on the specified plugin.

        Args:
            plugin_id: Plugin identifier.

        Returns:
            List of plugin IDs that depend on this plugin.
        """
        dependents = []
        for other_id, other_plugin in self._plugins.items():
            if other_id == plugin_id:
                continue

            for dep in other_plugin.metadata.dependencies:
                dep_id = dep.split(">=")[0].split("==")[0].strip()
                if dep_id == plugin_id:
                    dependents.append(other_id)
                    break

        return dependents


# Global plugin manager instance
plugin_manager = PluginManager()


# Convenience functions for global manager
def load_plugin(plugin_id: str, config: Optional[Dict[str, Any]] = None) -> None:
    """Load plugin in global manager."""
    plugin_manager.load_plugin(plugin_id, config)


def unload_plugin(plugin_id: str) -> None:
    """Unload plugin from global manager."""
    plugin_manager.unload_plugin(plugin_id)


def get_plugin(plugin_id: str) -> Optional[Plugin]:
    """Get plugin from global manager."""
    return plugin_manager.get_plugin(plugin_id)
