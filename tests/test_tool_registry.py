"""
Tests for Tool Registry.

Covers:
- Tool registration/unregistration
- Tool discovery (by name, category, competency, plugin)
- Tool execution
- Error handling
- Statistics
"""

import pytest
from gathering.core.tool_registry import (
    ToolRegistry,
    ToolDefinition,
    ToolCategory,
    tool_registry,
)


class TestToolDefinition:
    """Test ToolDefinition dataclass."""

    def test_create_tool_definition(self):
        """Test creating a valid tool definition."""
        tool = ToolDefinition(
            name="test_tool",
            description="A test tool",
            category=ToolCategory.UTILITY,
            function=lambda x: x * 2,
            required_competencies=["math"],
            parameters={"type": "object"},
            returns={"type": "integer"},
            examples=["test_tool(5)"],
        )

        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.category == ToolCategory.UTILITY
        assert callable(tool.function)
        assert tool.required_competencies == ["math"]
        assert tool.plugin_id is None
        assert tool.async_function is False

    def test_tool_definition_validation(self):
        """Test tool definition validation."""
        # Empty name
        with pytest.raises(ValueError, match="name cannot be empty"):
            ToolDefinition(
                name="",
                description="Test",
                category=ToolCategory.UTILITY,
                function=lambda: None,
                required_competencies=[],
                parameters={},
                returns={},
            )

        # Empty description
        with pytest.raises(ValueError, match="description cannot be empty"):
            ToolDefinition(
                name="test",
                description="",
                category=ToolCategory.UTILITY,
                function=lambda: None,
                required_competencies=[],
                parameters={},
                returns={},
            )

        # Non-callable function
        with pytest.raises(ValueError, match="must be callable"):
            ToolDefinition(
                name="test",
                description="Test",
                category=ToolCategory.UTILITY,
                function="not_callable",  # type: ignore
                required_competencies=[],
                parameters={},
                returns={},
            )


class TestToolRegistry:
    """Test ToolRegistry class."""

    def setup_method(self):
        """Setup for each test - create fresh registry."""
        self.registry = ToolRegistry()

    def test_register_tool(self):
        """Test registering a tool."""
        tool = ToolDefinition(
            name="add",
            description="Add two numbers",
            category=ToolCategory.UTILITY,
            function=lambda a, b: a + b,
            required_competencies=["math"],
            parameters={"type": "object"},
            returns={"type": "number"},
        )

        self.registry.register(tool)

        assert self.registry.has("add")
        retrieved = self.registry.get("add")
        assert retrieved is not None
        assert retrieved.name == "add"

    def test_register_duplicate_tool(self):
        """Test registering tool with duplicate name fails."""
        tool1 = ToolDefinition(
            name="duplicate",
            description="First",
            category=ToolCategory.UTILITY,
            function=lambda: 1,
            required_competencies=[],
            parameters={},
            returns={},
        )

        tool2 = ToolDefinition(
            name="duplicate",
            description="Second",
            category=ToolCategory.UTILITY,
            function=lambda: 2,
            required_competencies=[],
            parameters={},
            returns={},
        )

        self.registry.register(tool1)

        with pytest.raises(ValueError, match="already registered"):
            self.registry.register(tool2)

    def test_unregister_tool(self):
        """Test unregistering a tool."""
        tool = ToolDefinition(
            name="temp",
            description="Temporary tool",
            category=ToolCategory.UTILITY,
            function=lambda: None,
            required_competencies=[],
            parameters={},
            returns={},
        )

        self.registry.register(tool)
        assert self.registry.has("temp")

        result = self.registry.unregister("temp")
        assert result is True
        assert not self.registry.has("temp")

    def test_unregister_nonexistent_tool(self):
        """Test unregistering non-existent tool."""
        result = self.registry.unregister("nonexistent")
        assert result is False

    def test_get_tool(self):
        """Test getting a tool."""
        tool = ToolDefinition(
            name="getter_test",
            description="Test getting",
            category=ToolCategory.UTILITY,
            function=lambda: "result",
            required_competencies=[],
            parameters={},
            returns={},
        )

        self.registry.register(tool)

        retrieved = self.registry.get("getter_test")
        assert retrieved is not None
        assert retrieved.name == "getter_test"

        # Non-existent
        assert self.registry.get("nonexistent") is None

    def test_list_all_tools(self):
        """Test listing all tools."""
        tools = [
            ToolDefinition(
                name=f"tool{i}",
                description=f"Tool {i}",
                category=ToolCategory.UTILITY,
                function=lambda: i,
                required_competencies=[],
                parameters={},
                returns={},
            )
            for i in range(5)
        ]

        for tool in tools:
            self.registry.register(tool)

        all_tools = self.registry.list_all()
        assert len(all_tools) == 5
        assert set(t.name for t in all_tools) == {"tool0", "tool1", "tool2", "tool3", "tool4"}

    def test_list_by_category(self):
        """Test listing tools by category."""
        # Create tools in different categories
        image_tool = ToolDefinition(
            name="generate_image",
            description="Generate image",
            category=ToolCategory.IMAGE,
            function=lambda: "image",
            required_competencies=[],
            parameters={},
            returns={},
        )

        finance_tool = ToolDefinition(
            name="calculate_returns",
            description="Calculate returns",
            category=ToolCategory.FINANCE,
            function=lambda: 0.1,
            required_competencies=[],
            parameters={},
            returns={},
        )

        utility_tool = ToolDefinition(
            name="utility",
            description="Utility function",
            category=ToolCategory.UTILITY,
            function=lambda: None,
            required_competencies=[],
            parameters={},
            returns={},
        )

        self.registry.register(image_tool)
        self.registry.register(finance_tool)
        self.registry.register(utility_tool)

        # List by category
        image_tools = self.registry.list_by_category(ToolCategory.IMAGE)
        assert len(image_tools) == 1
        assert image_tools[0].name == "generate_image"

        finance_tools = self.registry.list_by_category(ToolCategory.FINANCE)
        assert len(finance_tools) == 1
        assert finance_tools[0].name == "calculate_returns"

        # Empty category
        cad_tools = self.registry.list_by_category(ToolCategory.CAD)
        assert len(cad_tools) == 0

    def test_list_by_competency(self):
        """Test listing tools by competency."""
        python_tool = ToolDefinition(
            name="run_python",
            description="Run Python code",
            category=ToolCategory.CODE_EXECUTION,
            function=lambda: None,
            required_competencies=["python", "code_execution"],
            parameters={},
            returns={},
        )

        design_tool = ToolDefinition(
            name="edit_image",
            description="Edit image",
            category=ToolCategory.IMAGE,
            function=lambda: None,
            required_competencies=["image_editing", "design"],
            parameters={},
            returns={},
        )

        self.registry.register(python_tool)
        self.registry.register(design_tool)

        # List by competency
        python_tools = self.registry.list_by_competency("python")
        assert len(python_tools) == 1
        assert python_tools[0].name == "run_python"

        design_tools = self.registry.list_by_competency("design")
        assert len(design_tools) == 1
        assert design_tools[0].name == "edit_image"

        # Non-existent competency
        finance_tools = self.registry.list_by_competency("finance")
        assert len(finance_tools) == 0

    def test_list_by_plugin(self):
        """Test listing tools by plugin."""
        core_tool = ToolDefinition(
            name="core_tool",
            description="Core tool",
            category=ToolCategory.UTILITY,
            function=lambda: None,
            required_competencies=[],
            parameters={},
            returns={},
            plugin_id=None,  # Core tool
        )

        design_tool = ToolDefinition(
            name="design_tool",
            description="Design tool",
            category=ToolCategory.IMAGE,
            function=lambda: None,
            required_competencies=[],
            parameters={},
            returns={},
            plugin_id="design",
        )

        finance_tool = ToolDefinition(
            name="finance_tool",
            description="Finance tool",
            category=ToolCategory.FINANCE,
            function=lambda: None,
            required_competencies=[],
            parameters={},
            returns={},
            plugin_id="finance",
        )

        self.registry.register(core_tool)
        self.registry.register(design_tool)
        self.registry.register(finance_tool)

        # List by plugin
        design_tools = self.registry.list_by_plugin("design")
        assert len(design_tools) == 1
        assert design_tools[0].name == "design_tool"

        finance_tools = self.registry.list_by_plugin("finance")
        assert len(finance_tools) == 1
        assert finance_tools[0].name == "finance_tool"

        # Non-existent plugin
        other_tools = self.registry.list_by_plugin("other")
        assert len(other_tools) == 0

    def test_execute_tool(self):
        """Test executing a tool."""
        def multiply(a: int, b: int) -> int:
            return a * b

        tool = ToolDefinition(
            name="multiply",
            description="Multiply two numbers",
            category=ToolCategory.UTILITY,
            function=multiply,
            required_competencies=["math"],
            parameters={},
            returns={},
        )

        self.registry.register(tool)

        result = self.registry.execute("multiply", a=3, b=4)
        assert result == 12

    def test_execute_nonexistent_tool(self):
        """Test executing non-existent tool fails."""
        with pytest.raises(ValueError, match="not found in registry"):
            self.registry.execute("nonexistent")

    def test_execute_tool_with_error(self):
        """Test tool execution error handling."""
        def failing_function():
            raise RuntimeError("Tool failed!")

        tool = ToolDefinition(
            name="failing_tool",
            description="A failing tool",
            category=ToolCategory.UTILITY,
            function=failing_function,
            required_competencies=[],
            parameters={},
            returns={},
        )

        self.registry.register(tool)

        with pytest.raises(Exception, match="Error executing tool 'failing_tool'"):
            self.registry.execute("failing_tool")

    def test_get_categories(self):
        """Test getting list of used categories."""
        assert len(self.registry.get_categories()) == 0

        # Add tools in different categories
        self.registry.register(ToolDefinition(
            name="t1",
            description="T1",
            category=ToolCategory.IMAGE,
            function=lambda: None,
            required_competencies=[],
            parameters={},
            returns={},
        ))

        self.registry.register(ToolDefinition(
            name="t2",
            description="T2",
            category=ToolCategory.FINANCE,
            function=lambda: None,
            required_competencies=[],
            parameters={},
            returns={},
        ))

        categories = self.registry.get_categories()
        assert len(categories) == 2
        assert ToolCategory.IMAGE in categories
        assert ToolCategory.FINANCE in categories

    def test_get_competencies(self):
        """Test getting list of used competencies."""
        assert len(self.registry.get_competencies()) == 0

        # Add tools with competencies
        self.registry.register(ToolDefinition(
            name="t1",
            description="T1",
            category=ToolCategory.UTILITY,
            function=lambda: None,
            required_competencies=["python", "testing"],
            parameters={},
            returns={},
        ))

        self.registry.register(ToolDefinition(
            name="t2",
            description="T2",
            category=ToolCategory.UTILITY,
            function=lambda: None,
            required_competencies=["javascript"],
            parameters={},
            returns={},
        ))

        competencies = self.registry.get_competencies()
        assert len(competencies) == 3
        assert "python" in competencies
        assert "testing" in competencies
        assert "javascript" in competencies

    def test_get_stats(self):
        """Test getting registry statistics."""
        # Empty registry
        stats = self.registry.get_stats()
        assert stats["total_tools"] == 0
        assert stats["categories"] == 0
        assert stats["competencies"] == 0
        assert stats["plugins"] == 0

        # Add some tools
        self.registry.register(ToolDefinition(
            name="t1",
            description="T1",
            category=ToolCategory.IMAGE,
            function=lambda: None,
            required_competencies=["image_editing"],
            parameters={},
            returns={},
            plugin_id="design",
        ))

        self.registry.register(ToolDefinition(
            name="t2",
            description="T2",
            category=ToolCategory.IMAGE,
            function=lambda: None,
            required_competencies=["ai_generation"],
            parameters={},
            returns={},
            plugin_id="design",
        ))

        self.registry.register(ToolDefinition(
            name="t3",
            description="T3",
            category=ToolCategory.FINANCE,
            function=lambda: None,
            required_competencies=["financial_analysis"],
            parameters={},
            returns={},
            plugin_id="finance",
        ))

        stats = self.registry.get_stats()
        assert stats["total_tools"] == 3
        assert stats["categories"] == 2
        assert stats["competencies"] == 3
        assert stats["plugins"] == 2  # design + finance
        assert stats["tools_by_category"]["image"] == 2
        assert stats["tools_by_category"]["finance"] == 1

    def test_clear_registry(self):
        """Test clearing all tools from registry."""
        # Add some tools
        for i in range(5):
            self.registry.register(ToolDefinition(
                name=f"tool{i}",
                description=f"Tool {i}",
                category=ToolCategory.UTILITY,
                function=lambda: None,
                required_competencies=[],
                parameters={},
                returns={},
            ))

        assert len(self.registry.list_all()) == 5

        # Clear
        self.registry.clear()

        assert len(self.registry.list_all()) == 0
        assert len(self.registry.get_categories()) == 0
        assert len(self.registry.get_competencies()) == 0


class TestGlobalToolRegistry:
    """Test global tool registry instance."""

    def setup_method(self):
        """Clear global registry before each test."""
        tool_registry.clear()

    def teardown_method(self):
        """Clear global registry after each test."""
        tool_registry.clear()

    def test_global_registry_singleton(self):
        """Test that tool_registry is a singleton."""
        from gathering.core.tool_registry import tool_registry as registry2
        assert tool_registry is registry2

    def test_register_to_global_registry(self):
        """Test registering tool to global registry."""
        tool = ToolDefinition(
            name="global_tool",
            description="A global tool",
            category=ToolCategory.UTILITY,
            function=lambda: "result",
            required_competencies=[],
            parameters={},
            returns={},
        )

        tool_registry.register(tool)

        assert tool_registry.has("global_tool")
        retrieved = tool_registry.get("global_tool")
        assert retrieved is not None
        assert retrieved.name == "global_tool"

    def test_convenience_functions(self):
        """Test convenience functions for global registry."""
        from gathering.core.tool_registry import register_tool, get_tool, execute_tool

        tool = ToolDefinition(
            name="convenience_test",
            description="Test convenience",
            category=ToolCategory.UTILITY,
            function=lambda x: x + 1,
            required_competencies=[],
            parameters={},
            returns={},
        )

        # Register
        register_tool(tool)
        assert tool_registry.has("convenience_test")

        # Get
        retrieved = get_tool("convenience_test")
        assert retrieved is not None
        assert retrieved.name == "convenience_test"

        # Execute
        result = execute_tool("convenience_test", x=5)
        assert result == 6


class TestToolRegistryCleanup:
    """Test registry cleanup when tools are removed."""

    def setup_method(self):
        """Create fresh registry."""
        self.registry = ToolRegistry()

    def test_unregister_cleans_category_index(self):
        """Test that unregistering removes from category index."""
        tool = ToolDefinition(
            name="test",
            description="Test",
            category=ToolCategory.IMAGE,
            function=lambda: None,
            required_competencies=[],
            parameters={},
            returns={},
        )

        self.registry.register(tool)
        assert ToolCategory.IMAGE in self.registry.get_categories()

        self.registry.unregister("test")
        assert ToolCategory.IMAGE not in self.registry.get_categories()

    def test_unregister_cleans_competency_index(self):
        """Test that unregistering removes from competency index."""
        tool = ToolDefinition(
            name="test",
            description="Test",
            category=ToolCategory.UTILITY,
            function=lambda: None,
            required_competencies=["python", "testing"],
            parameters={},
            returns={},
        )

        self.registry.register(tool)
        assert "python" in self.registry.get_competencies()
        assert "testing" in self.registry.get_competencies()

        self.registry.unregister("test")
        assert "python" not in self.registry.get_competencies()
        assert "testing" not in self.registry.get_competencies()

    def test_partial_cleanup_with_shared_category(self):
        """Test cleanup when multiple tools share a category."""
        tool1 = ToolDefinition(
            name="tool1",
            description="Tool 1",
            category=ToolCategory.IMAGE,
            function=lambda: None,
            required_competencies=[],
            parameters={},
            returns={},
        )

        tool2 = ToolDefinition(
            name="tool2",
            description="Tool 2",
            category=ToolCategory.IMAGE,
            function=lambda: None,
            required_competencies=[],
            parameters={},
            returns={},
        )

        self.registry.register(tool1)
        self.registry.register(tool2)

        # Remove one tool
        self.registry.unregister("tool1")

        # Category should still exist (tool2 still uses it)
        assert ToolCategory.IMAGE in self.registry.get_categories()
        assert len(self.registry.list_by_category(ToolCategory.IMAGE)) == 1

        # Remove second tool
        self.registry.unregister("tool2")

        # Now category should be removed
        assert ToolCategory.IMAGE not in self.registry.get_categories()
