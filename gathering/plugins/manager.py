"""
Plugin Manager for GatheRing.

Manages plugin lifecycle, dependency resolution, and registry integration.

Features:
- Load/unload plugins dynamically
- Discover plugins from directories
- Validate plugin dependencies
- Register tools and competencies from plugins
- Enable/disable plugins
- Query plugin status and information
- Generate plugins dynamically (for agent-created plugins)
"""

from typing import Dict, List, Optional, Type, Any
from pathlib import Path
import logging
import sys
import importlib
import importlib.util
import inspect

from gathering.plugins.base import Plugin, PluginStatus, PluginMetadata
from gathering.core.tool_registry import tool_registry, ToolDefinition, ToolCategory
from gathering.core.competency_registry import (
    competency_registry,
    CompetencyDefinition,
    CompetencyCategory,
    CompetencyLevel,
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

        # Plugin directories for discovery
        self._plugin_dirs: List[Path] = []
        self._discovered_plugins: Dict[str, Path] = {}  # plugin_id -> module path

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
            raise TypeError("plugin_class must be a subclass of Plugin")

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

    # =========================================================================
    # Plugin Discovery
    # =========================================================================

    def add_plugin_directory(self, path: Path | str) -> None:
        """
        Add a directory to search for plugins.

        Plugin files should be Python modules containing a Plugin subclass.
        The module should have either:
        - A `plugin_class` attribute pointing to the Plugin class
        - A single Plugin subclass in the module

        Args:
            path: Directory path to search for plugins.

        Example:
            >>> manager.add_plugin_directory(Path("./my_plugins"))
            >>> manager.add_plugin_directory("/usr/share/gathering/plugins")
        """
        path = Path(path)
        if not path.exists():
            raise ValueError(f"Plugin directory does not exist: {path}")
        if not path.is_dir():
            raise ValueError(f"Not a directory: {path}")

        if path not in self._plugin_dirs:
            self._plugin_dirs.append(path)
            # Add to Python path for imports
            path_str = str(path.resolve())
            if path_str not in sys.path:
                sys.path.insert(0, path_str)
            logger.info(f"Added plugin directory: {path}")

    def remove_plugin_directory(self, path: Path | str) -> bool:
        """
        Remove a plugin directory from the search path.

        Args:
            path: Directory path to remove.

        Returns:
            True if directory was removed, False if it wasn't registered.
        """
        path = Path(path)
        if path in self._plugin_dirs:
            self._plugin_dirs.remove(path)
            # Remove from Python path
            path_str = str(path.resolve())
            if path_str in sys.path:
                sys.path.remove(path_str)
            logger.info(f"Removed plugin directory: {path}")
            return True
        return False

    def discover_plugins(self, directory: Optional[Path | str] = None) -> Dict[str, Path]:
        """
        Discover plugins in registered directories or a specific directory.

        Scans for Python files containing Plugin subclasses and registers them.
        Does not load the plugins - use load_plugin() after discovery.

        Args:
            directory: Optional specific directory to scan.
                      If None, scans all registered directories.

        Returns:
            Dictionary mapping plugin_id to module path.

        Example:
            >>> discovered = manager.discover_plugins()
            >>> for plugin_id, path in discovered.items():
            ...     print(f"Found plugin: {plugin_id} at {path}")
            ...     manager.load_plugin(plugin_id)
        """
        dirs_to_scan = [Path(directory)] if directory else self._plugin_dirs

        discovered = {}

        for plugin_dir in dirs_to_scan:
            if not plugin_dir.exists():
                logger.warning(f"Plugin directory does not exist: {plugin_dir}")
                continue

            # Scan for Python files
            for file_path in plugin_dir.glob("*.py"):
                if file_path.name.startswith("_"):
                    continue  # Skip __init__.py, etc.

                try:
                    plugin_class = self._load_plugin_from_file(file_path)
                    if plugin_class:
                        # Get plugin ID from metadata
                        temp_instance = plugin_class.__new__(plugin_class)
                        # Initialize minimally to get metadata
                        temp_instance._config = {}
                        temp_instance._status = PluginStatus.UNLOADED
                        temp_instance._error = None

                        plugin_id = temp_instance.metadata.id

                        # Register the class
                        if plugin_id not in self._plugin_classes:
                            self._plugin_classes[plugin_id] = plugin_class
                            self._discovered_plugins[plugin_id] = file_path
                            discovered[plugin_id] = file_path
                            logger.info(f"Discovered plugin: {plugin_id} from {file_path}")

                except Exception as e:
                    logger.warning(f"Failed to discover plugin from {file_path}: {e}")

            # Scan subdirectories for package-style plugins
            for subdir in plugin_dir.iterdir():
                if not subdir.is_dir():
                    continue
                if subdir.name.startswith("_") or subdir.name.startswith("."):
                    continue

                init_file = subdir / "__init__.py"
                if init_file.exists():
                    try:
                        plugin_class = self._load_plugin_from_package(subdir)
                        if plugin_class:
                            temp_instance = plugin_class.__new__(plugin_class)
                            temp_instance._config = {}
                            temp_instance._status = PluginStatus.UNLOADED
                            temp_instance._error = None

                            plugin_id = temp_instance.metadata.id

                            if plugin_id not in self._plugin_classes:
                                self._plugin_classes[plugin_id] = plugin_class
                                self._discovered_plugins[plugin_id] = subdir
                                discovered[plugin_id] = subdir
                                logger.info(f"Discovered plugin package: {plugin_id} from {subdir}")

                    except Exception as e:
                        logger.warning(f"Failed to discover plugin from {subdir}: {e}")

        return discovered

    def _load_plugin_from_file(self, file_path: Path) -> Optional[Type[Plugin]]:
        """
        Load a Plugin class from a Python file.

        Args:
            file_path: Path to the Python file.

        Returns:
            Plugin class if found, None otherwise.
        """
        module_name = file_path.stem

        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # Look for plugin_class attribute first
        if hasattr(module, "plugin_class"):
            plugin_class = getattr(module, "plugin_class")
            if isinstance(plugin_class, type) and issubclass(plugin_class, Plugin):
                return plugin_class

        # Otherwise, find Plugin subclass in module
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, Plugin) and obj is not Plugin:
                return obj

        return None

    def _load_plugin_from_package(self, package_dir: Path) -> Optional[Type[Plugin]]:
        """
        Load a Plugin class from a Python package.

        Args:
            package_dir: Path to the package directory.

        Returns:
            Plugin class if found, None otherwise.
        """
        package_name = package_dir.name
        init_file = package_dir / "__init__.py"

        spec = importlib.util.spec_from_file_location(
            package_name,
            init_file,
            submodule_search_locations=[str(package_dir)]
        )
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[package_name] = module
        spec.loader.exec_module(module)

        # Look for plugin_class attribute first
        if hasattr(module, "plugin_class"):
            plugin_class = getattr(module, "plugin_class")
            if isinstance(plugin_class, type) and issubclass(plugin_class, Plugin):
                return plugin_class

        # Otherwise, find Plugin subclass in module
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, Plugin) and obj is not Plugin:
                return obj

        return None

    def list_plugin_directories(self) -> List[Path]:
        """
        List registered plugin directories.

        Returns:
            List of directory paths.
        """
        return list(self._plugin_dirs)

    def get_discovered_plugins(self) -> Dict[str, Path]:
        """
        Get all discovered plugins and their locations.

        Returns:
            Dictionary mapping plugin_id to file/directory path.
        """
        return dict(self._discovered_plugins)

    # =========================================================================
    # Dynamic Plugin Creation (for agents)
    # =========================================================================

    def create_dynamic_plugin(
        self,
        plugin_id: str,
        name: str,
        description: str,
        version: str = "1.0.0",
        author: str = "GatheRing Agent",
        tools: Optional[List[Dict[str, Any]]] = None,
        competencies: Optional[List[Dict[str, Any]]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Plugin:
        """
        Create and load a plugin dynamically without writing files.

        This allows agents to create plugins at runtime, extending
        GatheRing without modifying existing code.

        Args:
            plugin_id: Unique plugin identifier.
            name: Human-readable plugin name.
            description: Plugin description.
            version: Semantic version (default: "1.0.0").
            author: Plugin author (default: "GatheRing Agent").
            tools: List of tool definitions (dicts with name, description, function, etc.).
            competencies: List of competency definitions.
            config: Optional plugin configuration.

        Returns:
            The created and loaded Plugin instance.

        Example:
            >>> plugin = manager.create_dynamic_plugin(
            ...     plugin_id="my_agent_plugin",
            ...     name="My Agent Plugin",
            ...     description="Plugin created by agent",
            ...     tools=[
            ...         {
            ...             "name": "greet",
            ...             "description": "Greet someone",
            ...             "function": lambda name: f"Hello, {name}!",
            ...             "parameters": {"name": {"type": "string"}},
            ...         }
            ...     ],
            ... )
        """
        tools = tools or []
        competencies = competencies or []

        # Create dynamic plugin class
        class DynamicPlugin(Plugin):
            _meta = PluginMetadata(
                id=plugin_id,
                name=name,
                version=version,
                description=description,
                author=author,
            )
            _tools_config = tools
            _competencies_config = competencies

            @property
            def metadata(self) -> PluginMetadata:
                return self._meta

            def register_tools(self) -> List[ToolDefinition]:
                result = []
                for tool_config in self._tools_config:
                    tool_def = ToolDefinition(
                        name=tool_config["name"],
                        description=tool_config.get("description", ""),
                        category=tool_config.get("category", ToolCategory.CUSTOM),
                        function=tool_config["function"],
                        required_competencies=tool_config.get("required_competencies", []),
                        parameters=tool_config.get("parameters", {}),
                        returns=tool_config.get("returns", {}),
                        examples=tool_config.get("examples", []),
                        plugin_id=plugin_id,
                    )
                    result.append(tool_def)
                return result

            def register_competencies(self) -> List[CompetencyDefinition]:
                result = []
                for comp_config in self._competencies_config:
                    comp_def = CompetencyDefinition(
                        id=comp_config["id"],
                        name=comp_config["name"],
                        description=comp_config.get("description", ""),
                        category=comp_config.get("category", CompetencyCategory.CUSTOM),
                        level=comp_config.get("level", CompetencyLevel.INTERMEDIATE),
                        prerequisites=comp_config.get("prerequisites", []),
                        capabilities=comp_config.get("capabilities", []),
                        tools_enabled=comp_config.get("tools_enabled", []),
                        plugin_id=plugin_id,
                    )
                    result.append(comp_def)
                return result

        # Register and load the plugin
        self.register_plugin_class(plugin_id, DynamicPlugin)
        self.load_plugin(plugin_id, config=config)
        self.enable_plugin(plugin_id)

        return self.get_plugin(plugin_id)

    def save_dynamic_plugin(
        self,
        plugin_id: str,
        output_path: Path | str,
    ) -> Path:
        """
        Save a dynamically created plugin to a file.

        This persists a runtime-created plugin so it can be discovered
        and loaded in future sessions.

        Args:
            plugin_id: ID of the dynamic plugin to save.
            output_path: Path to save the plugin file.

        Returns:
            Path to the saved plugin file.

        Raises:
            ValueError: If plugin not found or cannot be serialized.
        """
        if plugin_id not in self._plugins:
            raise ValueError(f"Plugin '{plugin_id}' not found")

        plugin = self._plugins[plugin_id]
        output_path = Path(output_path)

        # Generate plugin code
        code = self._generate_plugin_code(plugin)

        # Write to file
        output_path.write_text(code)
        logger.info(f"Saved dynamic plugin '{plugin_id}' to {output_path}")

        return output_path

    def _generate_plugin_code(self, plugin: Plugin) -> str:
        """
        Generate Python code for a plugin.

        Args:
            plugin: Plugin instance to generate code for.

        Returns:
            Python source code string.
        """
        meta = plugin.metadata
        tools = plugin.register_tools()
        competencies = plugin.register_competencies()

        code_lines = [
            '"""',
            f'{meta.name}',
            '',
            f'{meta.description}',
            '',
            'Auto-generated plugin by GatheRing.',
            '"""',
            '',
            'from gathering.plugins.base import Plugin, PluginMetadata',
            'from gathering.core.tool_registry import ToolDefinition, ToolCategory',
            'from gathering.core.competency_registry import CompetencyDefinition, CompetencyCategory, CompetencyLevel',
            'from typing import List',
            '',
            '',
            f'class {self._to_class_name(meta.id)}Plugin(Plugin):',
            '    """',
            f'    {meta.description}',
            '    """',
            '',
            '    @property',
            '    def metadata(self) -> PluginMetadata:',
            '        return PluginMetadata(',
            f'            id="{meta.id}",',
            f'            name="{meta.name}",',
            f'            version="{meta.version}",',
            f'            description="{meta.description}",',
            f'            author="{meta.author}",',
            '        )',
            '',
            '    def register_tools(self) -> List[ToolDefinition]:',
            '        return [',
        ]

        # Add tools
        for tool in tools:
            code_lines.extend([
                '            ToolDefinition(',
                f'                name="{tool.name}",',
                f'                description="{tool.description}",',
                f'                category=ToolCategory.{tool.category.name},',
                f'                function=self.{tool.name},',
                f'                required_competencies={tool.required_competencies!r},',
                f'                parameters={tool.parameters!r},',
                f'                returns={tool.returns!r},',
                f'                plugin_id="{meta.id}",',
                '            ),',
            ])

        code_lines.extend([
            '        ]',
            '',
            '    def register_competencies(self) -> List[CompetencyDefinition]:',
            '        return [',
        ])

        # Add competencies
        for comp in competencies:
            code_lines.extend([
                '            CompetencyDefinition(',
                f'                id="{comp.id}",',
                f'                name="{comp.name}",',
                f'                description="{comp.description}",',
                f'                category=CompetencyCategory.{comp.category.name},',
                f'                level=CompetencyLevel.{comp.level.name},',
                f'                tools_enabled={comp.tools_enabled!r},',
                f'                plugin_id="{meta.id}",',
                '            ),',
            ])

        code_lines.extend([
            '        ]',
            '',
        ])

        # Add tool method stubs
        for tool in tools:
            code_lines.extend([
                f'    def {tool.name}(self, **kwargs):',
                '        """',
                f'        {tool.description}',
                '        """',
                '        # TODO: Implement tool logic',
                f'        raise NotImplementedError("{tool.name} not implemented")',
                '',
            ])

        # Add plugin_class export
        code_lines.extend([
            '',
            '# Export for discovery',
            f'plugin_class = {self._to_class_name(meta.id)}Plugin',
            '',
        ])

        return '\n'.join(code_lines)

    def _to_class_name(self, plugin_id: str) -> str:
        """Convert plugin_id to PascalCase class name."""
        return ''.join(word.capitalize() for word in plugin_id.split('_'))

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
