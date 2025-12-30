"""
Tests for Plugin System.

Tests plugin base class, plugin manager, and plugin lifecycle.
"""

import pytest
from gathering.plugins import Plugin, PluginMetadata, PluginStatus, PluginManager
from gathering.core.tool_registry import (
    ToolRegistry,
    ToolDefinition,
    ToolCategory,
)
from gathering.core.competency_registry import (
    CompetencyRegistry,
    CompetencyDefinition,
    CompetencyCategory,
    CompetencyLevel,
)


# ============================================================================
# Test Plugins
# ============================================================================


class BasicPlugin(Plugin):
    """Basic test plugin."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="basic",
            name="Basic Plugin",
            version="1.0.0",
            description="A basic test plugin",
        )


class ToolPlugin(Plugin):
    """Plugin that provides tools."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="tool_plugin",
            name="Tool Plugin",
            version="1.0.0",
            description="Provides test tools",
        )

    def add_numbers(self, a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    def register_tools(self):
        return [
            ToolDefinition(
                name="add",
                description="Add two numbers",
                category=ToolCategory.UTILITY,
                function=self.add_numbers,
                required_competencies=[],
                parameters={"type": "object"},
                returns={"type": "number"},
                plugin_id=self.metadata.id,
            )
        ]


class CompetencyPlugin(Plugin):
    """Plugin that provides competencies."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="competency_plugin",
            name="Competency Plugin",
            version="1.0.0",
            description="Provides test competencies",
        )

    def register_competencies(self):
        return [
            CompetencyDefinition(
                id="test_skill",
                name="Test Skill",
                description="A test skill",
                category=CompetencyCategory.CUSTOM,
                level=CompetencyLevel.INTERMEDIATE,
                plugin_id=self.metadata.id,
            )
        ]


class FullPlugin(Plugin):
    """Plugin that provides both tools and competencies."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="full_plugin",
            name="Full Plugin",
            version="1.0.0",
            description="Provides both tools and competencies",
            tags=["test", "full"],
        )

    def multiply(self, a: int, b: int) -> int:
        """Multiply two numbers."""
        return a * b

    def register_tools(self):
        return [
            ToolDefinition(
                name="multiply",
                description="Multiply two numbers",
                category=ToolCategory.UTILITY,
                function=self.multiply,
                required_competencies=["math"],
                parameters={"type": "object"},
                returns={"type": "number"},
                plugin_id=self.metadata.id,
            )
        ]

    def register_competencies(self):
        return [
            CompetencyDefinition(
                id="math",
                name="Mathematics",
                description="Math skills",
                category=CompetencyCategory.CUSTOM,
                plugin_id=self.metadata.id,
            )
        ]


class DependentPlugin(Plugin):
    """Plugin that depends on another plugin."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="dependent",
            name="Dependent Plugin",
            version="1.0.0",
            description="Depends on full_plugin",
            dependencies=["full_plugin"],
        )


class PythonDependencyPlugin(Plugin):
    """Plugin that requires Python packages."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="python_dep",
            name="Python Dependency Plugin",
            version="1.0.0",
            description="Requires Python packages",
            python_dependencies=["json"],  # Built-in, always available
        )


class MissingDependencyPlugin(Plugin):
    """Plugin with missing Python dependency."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="missing_dep",
            name="Missing Dependency Plugin",
            version="1.0.0",
            description="Has missing dependency",
            python_dependencies=["nonexistent_package_xyz"],
        )


# ============================================================================
# Tests
# ============================================================================


class TestPluginMetadata:
    """Test PluginMetadata dataclass."""

    def test_create_metadata(self):
        """Test creating valid metadata."""
        meta = PluginMetadata(
            id="test",
            name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            license="MIT",
            tags=["test", "demo"],
        )

        assert meta.id == "test"
        assert meta.name == "Test Plugin"
        assert meta.version == "1.0.0"
        assert "test" in meta.tags

    def test_metadata_validation(self):
        """Test metadata validation."""
        # Empty ID
        with pytest.raises(ValueError, match="ID cannot be empty"):
            PluginMetadata(
                id="",
                name="Test",
                version="1.0.0",
                description="Test",
            )

        # Empty name
        with pytest.raises(ValueError, match="name cannot be empty"):
            PluginMetadata(
                id="test",
                name="",
                version="1.0.0",
                description="Test",
            )

        # Empty version
        with pytest.raises(ValueError, match="version cannot be empty"):
            PluginMetadata(
                id="test",
                name="Test",
                version="",
                description="Test",
            )


class TestPlugin:
    """Test Plugin base class."""

    def test_plugin_initialization(self):
        """Test plugin initialization."""
        plugin = BasicPlugin()
        assert plugin.status == PluginStatus.UNLOADED
        assert plugin.error is None
        assert plugin.config == {}

    def test_plugin_with_config(self):
        """Test plugin with configuration."""
        config = {"api_key": "test123", "timeout": 30}
        plugin = BasicPlugin(config=config)
        assert plugin.config == config

    def test_plugin_load(self):
        """Test loading a plugin."""
        plugin = BasicPlugin()
        plugin.load()
        assert plugin.status == PluginStatus.LOADED

    def test_plugin_unload(self):
        """Test unloading a plugin."""
        plugin = BasicPlugin()
        plugin.load()
        plugin.unload()
        assert plugin.status == PluginStatus.UNLOADED

    def test_plugin_enable_disable(self):
        """Test enabling and disabling plugin."""
        plugin = BasicPlugin()
        plugin.load()

        plugin.on_enable()
        assert plugin.status == PluginStatus.ENABLED

        plugin.on_disable()
        assert plugin.status == PluginStatus.DISABLED

    def test_plugin_health_check(self):
        """Test plugin health check."""
        plugin = BasicPlugin()
        health = plugin.health_check()
        assert health["plugin_id"] == "basic"
        assert health["status"] == PluginStatus.UNLOADED.value

    def test_plugin_get_info(self):
        """Test getting plugin info."""
        plugin = BasicPlugin()
        info = plugin.get_info()
        assert info["id"] == "basic"
        assert info["name"] == "Basic Plugin"
        assert info["version"] == "1.0.0"
        assert info["status"] == PluginStatus.UNLOADED.value

    def test_plugin_validate_dependencies(self):
        """Test dependency validation."""
        # Should pass with built-in package
        plugin = PythonDependencyPlugin()
        plugin.validate_dependencies()  # Should not raise

    def test_plugin_missing_dependency(self):
        """Test plugin with missing dependency."""
        plugin = MissingDependencyPlugin()
        with pytest.raises(ImportError, match="requires Python package"):
            plugin.load()

    def test_plugin_repr(self):
        """Test string representation."""
        plugin = BasicPlugin()
        repr_str = repr(plugin)
        assert "basic" in repr_str
        assert "1.0.0" in repr_str


class TestPluginManager:
    """Test PluginManager class."""

    def setup_method(self):
        """Setup test manager with isolated registries."""
        self.tool_registry = ToolRegistry()
        self.competency_registry = CompetencyRegistry()
        self.manager = PluginManager(
            tool_registry=self.tool_registry,
            competency_registry=self.competency_registry,
        )

    def test_register_plugin_class(self):
        """Test registering a plugin class."""
        self.manager.register_plugin_class("basic", BasicPlugin)
        assert "basic" in self.manager.list_available_plugins()

    def test_register_duplicate_plugin_class(self):
        """Test registering duplicate plugin class raises error."""
        self.manager.register_plugin_class("basic", BasicPlugin)
        with pytest.raises(ValueError, match="already registered"):
            self.manager.register_plugin_class("basic", BasicPlugin)

    def test_register_invalid_plugin_class(self):
        """Test registering non-Plugin class raises error."""
        with pytest.raises(TypeError, match="must be a subclass"):
            self.manager.register_plugin_class("invalid", dict)

    def test_unregister_plugin_class(self):
        """Test unregistering plugin class."""
        self.manager.register_plugin_class("basic", BasicPlugin)
        result = self.manager.unregister_plugin_class("basic")
        assert result is True
        assert "basic" not in self.manager.list_available_plugins()

    def test_unregister_nonexistent_plugin_class(self):
        """Test unregistering nonexistent plugin class."""
        result = self.manager.unregister_plugin_class("nonexistent")
        assert result is False

    def test_unregister_loaded_plugin_class(self):
        """Test unregistering loaded plugin raises error."""
        self.manager.register_plugin_class("basic", BasicPlugin)
        self.manager.load_plugin("basic")
        with pytest.raises(ValueError, match="currently loaded"):
            self.manager.unregister_plugin_class("basic")

    def test_load_plugin(self):
        """Test loading a plugin."""
        self.manager.register_plugin_class("basic", BasicPlugin)
        self.manager.load_plugin("basic")
        assert self.manager.has_plugin("basic")

    def test_load_unregistered_plugin(self):
        """Test loading unregistered plugin raises error."""
        with pytest.raises(ValueError, match="not registered"):
            self.manager.load_plugin("nonexistent")

    def test_load_duplicate_plugin(self):
        """Test loading already loaded plugin raises error."""
        self.manager.register_plugin_class("basic", BasicPlugin)
        self.manager.load_plugin("basic")
        with pytest.raises(ValueError, match="already loaded"):
            self.manager.load_plugin("basic")

    def test_load_plugin_with_tools(self):
        """Test loading plugin that provides tools."""
        self.manager.register_plugin_class("tool_plugin", ToolPlugin)
        self.manager.load_plugin("tool_plugin")

        # Check tool was registered
        assert self.tool_registry.has("add")
        tool = self.tool_registry.get("add")
        assert tool.plugin_id == "tool_plugin"

    def test_load_plugin_with_competencies(self):
        """Test loading plugin that provides competencies."""
        self.manager.register_plugin_class("competency_plugin", CompetencyPlugin)
        self.manager.load_plugin("competency_plugin")

        # Check competency was registered
        assert self.competency_registry.has("test_skill")
        comp = self.competency_registry.get("test_skill")
        assert comp.plugin_id == "competency_plugin"

    def test_load_full_plugin(self):
        """Test loading plugin with both tools and competencies."""
        self.manager.register_plugin_class("full_plugin", FullPlugin)
        self.manager.load_plugin("full_plugin")

        # Check both were registered
        assert self.tool_registry.has("multiply")
        assert self.competency_registry.has("math")

    def test_unload_plugin(self):
        """Test unloading a plugin."""
        self.manager.register_plugin_class("basic", BasicPlugin)
        self.manager.load_plugin("basic")
        self.manager.unload_plugin("basic")
        assert not self.manager.has_plugin("basic")

    def test_unload_nonexistent_plugin(self):
        """Test unloading nonexistent plugin raises error."""
        with pytest.raises(ValueError, match="not loaded"):
            self.manager.unload_plugin("nonexistent")

    def test_unload_plugin_removes_tools(self):
        """Test unloading plugin removes its tools."""
        self.manager.register_plugin_class("tool_plugin", ToolPlugin)
        self.manager.load_plugin("tool_plugin")
        assert self.tool_registry.has("add")

        self.manager.unload_plugin("tool_plugin")
        assert not self.tool_registry.has("add")

    def test_unload_plugin_removes_competencies(self):
        """Test unloading plugin removes its competencies."""
        self.manager.register_plugin_class("competency_plugin", CompetencyPlugin)
        self.manager.load_plugin("competency_plugin")
        assert self.competency_registry.has("test_skill")

        self.manager.unload_plugin("competency_plugin")
        assert not self.competency_registry.has("test_skill")

    def test_enable_plugin(self):
        """Test enabling a plugin."""
        self.manager.register_plugin_class("basic", BasicPlugin)
        self.manager.load_plugin("basic")
        self.manager.enable_plugin("basic")

        plugin = self.manager.get_plugin("basic")
        assert plugin.status == PluginStatus.ENABLED

    def test_disable_plugin(self):
        """Test disabling a plugin."""
        self.manager.register_plugin_class("basic", BasicPlugin)
        self.manager.load_plugin("basic")
        self.manager.enable_plugin("basic")
        self.manager.disable_plugin("basic")

        plugin = self.manager.get_plugin("basic")
        assert plugin.status == PluginStatus.DISABLED

    def test_get_plugin(self):
        """Test getting plugin instance."""
        self.manager.register_plugin_class("basic", BasicPlugin)
        self.manager.load_plugin("basic")

        plugin = self.manager.get_plugin("basic")
        assert plugin is not None
        assert plugin.metadata.id == "basic"

    def test_get_nonexistent_plugin(self):
        """Test getting nonexistent plugin returns None."""
        plugin = self.manager.get_plugin("nonexistent")
        assert plugin is None

    def test_list_plugins(self):
        """Test listing loaded plugins."""
        self.manager.register_plugin_class("basic", BasicPlugin)
        self.manager.register_plugin_class("tool_plugin", ToolPlugin)
        self.manager.load_plugin("basic")
        self.manager.load_plugin("tool_plugin")

        plugins = self.manager.list_plugins()
        assert len(plugins) == 2

    def test_list_plugins_by_status(self):
        """Test listing plugins filtered by status."""
        self.manager.register_plugin_class("basic", BasicPlugin)
        self.manager.load_plugin("basic")
        self.manager.enable_plugin("basic")

        enabled = self.manager.list_plugins(status=PluginStatus.ENABLED)
        assert len(enabled) == 1
        assert enabled[0].metadata.id == "basic"

    def test_get_plugin_info(self):
        """Test getting plugin info."""
        self.manager.register_plugin_class("full_plugin", FullPlugin)
        self.manager.load_plugin("full_plugin")

        info = self.manager.get_plugin_info("full_plugin")
        assert info["id"] == "full_plugin"
        assert info["tools_count"] == 1
        assert info["competencies_count"] == 1

    def test_health_check(self):
        """Test plugin health check."""
        self.manager.register_plugin_class("basic", BasicPlugin)
        self.manager.load_plugin("basic")

        health = self.manager.health_check("basic")
        assert health["plugin_id"] == "basic"
        assert health["status"] == PluginStatus.LOADED.value

    def test_health_check_all(self):
        """Test checking health of all plugins."""
        self.manager.register_plugin_class("basic", BasicPlugin)
        self.manager.register_plugin_class("tool_plugin", ToolPlugin)
        self.manager.load_plugin("basic")
        self.manager.load_plugin("tool_plugin")

        health = self.manager.health_check_all()
        assert len(health) == 2
        assert "basic" in health
        assert "tool_plugin" in health

    def test_get_stats(self):
        """Test getting manager statistics."""
        self.manager.register_plugin_class("basic", BasicPlugin)
        self.manager.register_plugin_class("full_plugin", FullPlugin)
        self.manager.load_plugin("full_plugin")
        self.manager.enable_plugin("full_plugin")

        stats = self.manager.get_stats()
        assert stats["available_plugins"] == 2
        assert stats["loaded_plugins"] == 1
        assert stats["enabled_plugins"] == 1
        assert stats["total_tools_from_plugins"] == 1
        assert stats["total_competencies_from_plugins"] == 1

    def test_plugin_dependencies(self):
        """Test plugin dependencies."""
        # Load dependency first
        self.manager.register_plugin_class("full_plugin", FullPlugin)
        self.manager.load_plugin("full_plugin")

        # Load dependent plugin
        self.manager.register_plugin_class("dependent", DependentPlugin)
        self.manager.load_plugin("dependent")

        assert self.manager.has_plugin("dependent")

    def test_plugin_missing_dependency(self):
        """Test loading plugin with missing dependency raises error."""
        self.manager.register_plugin_class("dependent", DependentPlugin)

        with pytest.raises(ValueError, match="requires plugin"):
            self.manager.load_plugin("dependent")

    def test_unload_plugin_with_dependents(self):
        """Test unloading plugin that others depend on raises error."""
        # Load both plugins
        self.manager.register_plugin_class("full_plugin", FullPlugin)
        self.manager.register_plugin_class("dependent", DependentPlugin)
        self.manager.load_plugin("full_plugin")
        self.manager.load_plugin("dependent")

        # Try to unload full_plugin
        with pytest.raises(ValueError, match="depend on it"):
            self.manager.unload_plugin("full_plugin")

    def test_unload_dependent_first(self):
        """Test unloading dependent plugin first allows unloading dependency."""
        # Load both
        self.manager.register_plugin_class("full_plugin", FullPlugin)
        self.manager.register_plugin_class("dependent", DependentPlugin)
        self.manager.load_plugin("full_plugin")
        self.manager.load_plugin("dependent")

        # Unload dependent first
        self.manager.unload_plugin("dependent")

        # Now can unload full_plugin
        self.manager.unload_plugin("full_plugin")
        assert not self.manager.has_plugin("full_plugin")


class TestPluginToolIntegration:
    """Test integration between plugins and tools."""

    def setup_method(self):
        """Setup test manager with isolated registries."""
        self.tool_registry = ToolRegistry()
        self.competency_registry = CompetencyRegistry()
        self.manager = PluginManager(
            tool_registry=self.tool_registry,
            competency_registry=self.competency_registry,
        )

    def test_execute_tool_from_plugin(self):
        """Test executing a tool provided by a plugin."""
        self.manager.register_plugin_class("tool_plugin", ToolPlugin)
        self.manager.load_plugin("tool_plugin")

        # Execute tool
        result = self.tool_registry.execute("add", a=5, b=3)
        assert result == 8

    def test_plugin_tools_have_plugin_id(self):
        """Test that tools from plugins have correct plugin_id."""
        self.manager.register_plugin_class("tool_plugin", ToolPlugin)
        self.manager.load_plugin("tool_plugin")

        tool = self.tool_registry.get("add")
        assert tool.plugin_id == "tool_plugin"

    def test_list_tools_by_plugin(self):
        """Test listing tools from a specific plugin."""
        self.manager.register_plugin_class("tool_plugin", ToolPlugin)
        self.manager.load_plugin("tool_plugin")

        tools = self.tool_registry.list_by_plugin("tool_plugin")
        assert len(tools) == 1
        assert tools[0].name == "add"


class TestGlobalPluginManager:
    """Test global plugin manager instance."""

    def test_global_manager_singleton(self):
        """Test that global manager is a singleton."""
        from gathering.plugins.manager import plugin_manager as manager2
        from gathering.plugins import plugin_manager

        assert plugin_manager is manager2
