"""
GatheRing Plugin System.

Allows extending GatheRing with custom tools, competencies, and capabilities.

This module provides:
- Plugin base class for creating plugins
- Plugin metadata for discovery and dependency management
- Plugin registry for managing loaded plugins

Example:
    from gathering.plugins import Plugin, PluginMetadata
    from gathering.core.tool_registry import ToolDefinition, ToolCategory
    from gathering.core.competency_registry import CompetencyDefinition, CompetencyCategory

    class MyPlugin(Plugin):
        @property
        def metadata(self) -> PluginMetadata:
            return PluginMetadata(
                id="my_plugin",
                name="My Plugin",
                version="1.0.0",
                description="Custom plugin",
                author="Your Name",
            )

        def register_tools(self):
            return [
                ToolDefinition(
                    name="my_tool",
                    description="Does something",
                    category=ToolCategory.CUSTOM,
                    function=self.my_function,
                    required_competencies=[],
                    parameters={},
                    returns={},
                )
            ]

        def register_competencies(self):
            return [
                CompetencyDefinition(
                    id="my_skill",
                    name="My Skill",
                    description="A custom skill",
                    category=CompetencyCategory.CUSTOM,
                )
            ]

        def my_function(self):
            return "Hello from plugin!"
"""

from gathering.plugins.base import Plugin, PluginMetadata, PluginStatus
from gathering.plugins.manager import PluginManager, plugin_manager

__all__ = [
    "Plugin",
    "PluginMetadata",
    "PluginStatus",
    "PluginManager",
    "plugin_manager",
]
