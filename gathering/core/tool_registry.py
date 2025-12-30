"""
Dynamic Tool Registry for GatheRing.

Allows registration and discovery of tools at runtime,
enabling plugin system and extensibility.

Features:
- Type-safe tool definitions
- Category-based indexing
- Competency-based filtering
- Dynamic registration/unregistration
- Tool execution with validation

Usage:
    from gathering.core.tool_registry import tool_registry, ToolDefinition, ToolCategory

    # Register a tool
    tool_registry.register(ToolDefinition(
        name="generate_image",
        description="Generate image using AI",
        category=ToolCategory.IMAGE,
        function=my_function,
        required_competencies=["ai_image_generation"],
        parameters={...},
        returns={...},
    ))

    # Get tool
    tool = tool_registry.get("generate_image")

    # Execute tool
    result = tool_registry.execute("generate_image", prompt="A sunset")

    # List tools by category
    image_tools = tool_registry.list_by_category(ToolCategory.IMAGE)
"""

from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum


class ToolCategory(str, Enum):
    """Tool categories for organization and discovery."""

    # File & System
    FILE_SYSTEM = "filesystem"
    VERSION_CONTROL = "version_control"

    # Development
    CODE_EXECUTION = "code_execution"
    TESTING = "testing"
    DEBUGGING = "debugging"

    # AI & ML
    LLM = "llm"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"

    # Data
    DATA_ANALYSIS = "data_analysis"
    DATABASE = "database"

    # Business
    FINANCE = "finance"
    ACCOUNTING = "accounting"

    # Engineering
    CAD = "cad"
    SIMULATION = "simulation"
    IOT = "iot"

    # Web & Network
    WEB = "web"
    API = "api"

    # Other
    CUSTOM = "custom"
    UTILITY = "utility"


@dataclass
class ToolDefinition:
    """
    Tool definition with metadata.

    A tool is a function that agents can call to perform actions.
    """

    name: str
    """Unique tool name (e.g., 'generate_image', 'git_commit')"""

    description: str
    """Human-readable description of what the tool does"""

    category: ToolCategory
    """Tool category for organization"""

    function: Callable
    """The actual function to execute"""

    required_competencies: List[str]
    """Competencies needed to use this tool effectively"""

    parameters: Dict[str, Any]
    """JSON Schema describing function parameters"""

    returns: Dict[str, Any]
    """JSON Schema describing return value"""

    examples: List[str] = field(default_factory=list)
    """Example usage strings for documentation"""

    plugin_id: Optional[str] = None
    """ID of plugin that provided this tool (None for core)"""

    async_function: bool = False
    """Whether the function is async (default: False)"""

    requires_context: bool = False
    """Whether the function needs agent context (default: False)"""

    def __post_init__(self):
        """Validate tool definition."""
        if not self.name:
            raise ValueError("Tool name cannot be empty")
        if not self.description:
            raise ValueError("Tool description cannot be empty")
        if not callable(self.function):
            raise ValueError("Tool function must be callable")


class ToolRegistry:
    """
    Dynamic tool registry.

    Manages registration, discovery, and execution of tools.
    Thread-safe for concurrent access.
    """

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._tools_by_category: Dict[ToolCategory, List[str]] = {}
        self._tools_by_competency: Dict[str, List[str]] = {}

    def register(self, tool: ToolDefinition) -> None:
        """
        Register a tool.

        Args:
            tool: Tool definition to register.

        Raises:
            ValueError: If tool name already exists.

        Example:
            >>> tool = ToolDefinition(
            ...     name="my_tool",
            ...     description="Does something",
            ...     category=ToolCategory.UTILITY,
            ...     function=lambda: "result",
            ...     required_competencies=[],
            ...     parameters={},
            ...     returns={},
            ... )
            >>> tool_registry.register(tool)
        """
        # Validate
        if tool.name in self._tools:
            raise ValueError(
                f"Tool '{tool.name}' already registered. "
                f"Use unregister() first to replace it."
            )

        # Store tool
        self._tools[tool.name] = tool

        # Index by category
        if tool.category not in self._tools_by_category:
            self._tools_by_category[tool.category] = []
        self._tools_by_category[tool.category].append(tool.name)

        # Index by competencies
        for comp in tool.required_competencies:
            if comp not in self._tools_by_competency:
                self._tools_by_competency[comp] = []
            self._tools_by_competency[comp].append(tool.name)

    def unregister(self, name: str) -> bool:
        """
        Unregister a tool.

        Args:
            name: Tool name to unregister.

        Returns:
            True if tool was removed, False if it didn't exist.

        Example:
            >>> tool_registry.unregister("my_tool")
            True
        """
        if name not in self._tools:
            return False

        tool = self._tools[name]

        # Remove from category index
        if tool.category in self._tools_by_category:
            try:
                self._tools_by_category[tool.category].remove(name)
                # Clean up empty categories
                if not self._tools_by_category[tool.category]:
                    del self._tools_by_category[tool.category]
            except ValueError:
                pass

        # Remove from competency index
        for comp in tool.required_competencies:
            if comp in self._tools_by_competency:
                try:
                    self._tools_by_competency[comp].remove(name)
                    # Clean up empty competencies
                    if not self._tools_by_competency[comp]:
                        del self._tools_by_competency[comp]
                except ValueError:
                    pass

        # Remove tool
        del self._tools[name]
        return True

    def get(self, name: str) -> Optional[ToolDefinition]:
        """
        Get tool by name.

        Args:
            name: Tool name.

        Returns:
            Tool definition or None if not found.

        Example:
            >>> tool = tool_registry.get("my_tool")
            >>> if tool:
            ...     print(tool.description)
        """
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        """
        Check if tool exists.

        Args:
            name: Tool name.

        Returns:
            True if tool is registered.

        Example:
            >>> if tool_registry.has("my_tool"):
            ...     print("Tool exists")
        """
        return name in self._tools

    def list_all(self) -> List[ToolDefinition]:
        """
        List all registered tools.

        Returns:
            List of all tool definitions.

        Example:
            >>> for tool in tool_registry.list_all():
            ...     print(f"{tool.name}: {tool.description}")
        """
        return list(self._tools.values())

    def list_by_category(self, category: ToolCategory) -> List[ToolDefinition]:
        """
        List tools in a category.

        Args:
            category: Tool category.

        Returns:
            List of tools in the category.

        Example:
            >>> image_tools = tool_registry.list_by_category(ToolCategory.IMAGE)
            >>> print(f"Found {len(image_tools)} image tools")
        """
        tool_names = self._tools_by_category.get(category, [])
        return [self._tools[name] for name in tool_names]

    def list_by_competency(self, competency: str) -> List[ToolDefinition]:
        """
        List tools that require a competency.

        Args:
            competency: Competency ID (e.g., 'python', 'image_editing').

        Returns:
            List of tools requiring that competency.

        Example:
            >>> python_tools = tool_registry.list_by_competency("python")
            >>> for tool in python_tools:
            ...     print(tool.name)
        """
        tool_names = self._tools_by_competency.get(competency, [])
        return [self._tools[name] for name in tool_names]

    def list_by_plugin(self, plugin_id: str) -> List[ToolDefinition]:
        """
        List tools provided by a plugin.

        Args:
            plugin_id: Plugin ID.

        Returns:
            List of tools from that plugin.

        Example:
            >>> design_tools = tool_registry.list_by_plugin("design")
            >>> print(f"Design plugin provides {len(design_tools)} tools")
        """
        return [tool for tool in self._tools.values() if tool.plugin_id == plugin_id]

    def execute(self, name: str, **kwargs) -> Any:
        """
        Execute a tool.

        Args:
            name: Tool name.
            **kwargs: Tool arguments.

        Returns:
            Tool execution result.

        Raises:
            ValueError: If tool not found.
            Exception: If tool execution fails.

        Example:
            >>> result = tool_registry.execute("my_tool", arg1="value")
        """
        tool = self.get(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found in registry")

        # Execute function
        # TODO: Add parameter validation against JSON schema
        # TODO: Handle async functions
        try:
            return tool.function(**kwargs)
        except Exception as e:
            raise Exception(
                f"Error executing tool '{name}': {e}"
            ) from e

    def get_categories(self) -> List[ToolCategory]:
        """
        Get list of categories with registered tools.

        Returns:
            List of categories that have at least one tool.

        Example:
            >>> categories = tool_registry.get_categories()
            >>> print(f"Tools available in {len(categories)} categories")
        """
        return list(self._tools_by_category.keys())

    def get_competencies(self) -> List[str]:
        """
        Get list of competencies used by registered tools.

        Returns:
            List of competency IDs.

        Example:
            >>> competencies = tool_registry.get_competencies()
            >>> for comp in competencies:
            ...     tools = tool_registry.list_by_competency(comp)
            ...     print(f"{comp}: {len(tools)} tools")
        """
        return list(self._tools_by_competency.keys())

    def get_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics.

        Returns:
            Dictionary with statistics.

        Example:
            >>> stats = tool_registry.get_stats()
            >>> print(f"Total tools: {stats['total_tools']}")
        """
        return {
            "total_tools": len(self._tools),
            "categories": len(self._tools_by_category),
            "competencies": len(self._tools_by_competency),
            "tools_by_category": {
                cat.value: len(tools)
                for cat, tools in self._tools_by_category.items()
            },
            "plugins": len(set(
                tool.plugin_id for tool in self._tools.values()
                if tool.plugin_id
            )),
        }

    def clear(self) -> None:
        """
        Clear all registered tools.

        Use with caution! This removes all tools from the registry.

        Example:
            >>> tool_registry.clear()
            >>> assert len(tool_registry.list_all()) == 0
        """
        self._tools.clear()
        self._tools_by_category.clear()
        self._tools_by_competency.clear()


# Global tool registry instance
tool_registry = ToolRegistry()


# Convenience functions for global registry
def register_tool(tool: ToolDefinition) -> None:
    """Register a tool in the global registry."""
    tool_registry.register(tool)


def get_tool(name: str) -> Optional[ToolDefinition]:
    """Get tool from global registry."""
    return tool_registry.get(name)


def execute_tool(name: str, **kwargs) -> Any:
    """Execute tool from global registry."""
    return tool_registry.execute(name, **kwargs)
