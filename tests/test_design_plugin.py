"""
Tests for Design Plugin example.

Demonstrates how plugins work in practice.
"""

import pytest
from gathering.plugins.examples import DesignPlugin
from gathering.plugins import PluginManager
from gathering.core.tool_registry import ToolRegistry
from gathering.core.competency_registry import CompetencyRegistry


class TestDesignPlugin:
    """Test the Design Plugin example."""

    def setup_method(self):
        """Setup test environment with isolated registries."""
        self.tool_registry = ToolRegistry()
        self.competency_registry = CompetencyRegistry()
        self.manager = PluginManager(
            tool_registry=self.tool_registry,
            competency_registry=self.competency_registry,
        )

    def test_plugin_metadata(self):
        """Test plugin metadata."""
        plugin = DesignPlugin()
        meta = plugin.metadata

        assert meta.id == "design"
        assert meta.name == "Design & Image Tools"
        assert meta.version == "1.0.0"
        assert "design" in meta.tags
        assert "image" in meta.tags

    def test_plugin_tools(self):
        """Test plugin provides correct tools."""
        plugin = DesignPlugin()
        tools = plugin.register_tools()

        assert len(tools) == 3
        tool_names = [t.name for t in tools]
        assert "generate_image" in tool_names
        assert "create_color_palette" in tool_names
        assert "create_ui_mockup" in tool_names

    def test_plugin_competencies(self):
        """Test plugin provides correct competencies."""
        plugin = DesignPlugin()
        competencies = plugin.register_competencies()

        assert len(competencies) == 4
        comp_ids = [c.id for c in competencies]
        assert "color_theory" in comp_ids
        assert "ui_design" in comp_ids
        assert "wireframing" in comp_ids
        assert "ai_image_generation" in comp_ids

    def test_load_plugin(self):
        """Test loading the plugin."""
        self.manager.register_plugin_class("design", DesignPlugin)
        self.manager.load_plugin("design")

        assert self.manager.has_plugin("design")

    def test_plugin_registers_tools(self):
        """Test plugin registers tools correctly."""
        self.manager.register_plugin_class("design", DesignPlugin)
        self.manager.load_plugin("design")

        # Check tools are registered
        assert self.tool_registry.has("generate_image")
        assert self.tool_registry.has("create_color_palette")
        assert self.tool_registry.has("create_ui_mockup")

        # Check tool metadata
        tool = self.tool_registry.get("generate_image")
        assert tool.plugin_id == "design"
        assert "ai_image_generation" in tool.required_competencies

    def test_plugin_registers_competencies(self):
        """Test plugin registers competencies correctly."""
        self.manager.register_plugin_class("design", DesignPlugin)
        self.manager.load_plugin("design")

        # Check competencies are registered
        assert self.competency_registry.has("color_theory")
        assert self.competency_registry.has("ui_design")

        # Check competency metadata
        comp = self.competency_registry.get("ui_design")
        assert comp.plugin_id == "design"
        assert "color_theory" in comp.prerequisites

    def test_competency_prerequisites(self):
        """Test competency prerequisite chain."""
        self.manager.register_plugin_class("design", DesignPlugin)
        self.manager.load_plugin("design")

        # Get learning path
        path = self.competency_registry.get_learning_path("wireframing")

        # wireframing requires ui_design, which requires color_theory
        assert "color_theory" in path
        assert "ui_design" in path
        assert "wireframing" in path

        # Verify order
        assert path.index("color_theory") < path.index("ui_design")
        assert path.index("ui_design") < path.index("wireframing")

    def test_execute_generate_image(self):
        """Test executing the generate_image tool."""
        self.manager.register_plugin_class("design", DesignPlugin)
        self.manager.load_plugin("design")

        result = self.tool_registry.execute(
            "generate_image",
            prompt="A sunset over mountains",
            style="realistic",
        )

        assert "image_url" in result
        assert result["prompt"] == "A sunset over mountains"
        assert result["style"] == "realistic"

    def test_execute_create_color_palette(self):
        """Test executing the create_color_palette tool."""
        self.manager.register_plugin_class("design", DesignPlugin)
        self.manager.load_plugin("design")

        result = self.tool_registry.execute(
            "create_color_palette",
            theme="ocean",
            num_colors=5,
        )

        assert "colors" in result
        assert len(result["colors"]) == 5
        assert result["theme"] == "ocean"

    def test_execute_create_ui_mockup(self):
        """Test executing the create_ui_mockup tool."""
        self.manager.register_plugin_class("design", DesignPlugin)
        self.manager.load_plugin("design")

        result = self.tool_registry.execute(
            "create_ui_mockup",
            page_type="landing",
            components=["hero", "features", "cta"],
            style="modern",
        )

        assert "mockup_url" in result
        assert result["page_type"] == "landing"
        assert "hero" in result["components_used"]

    def test_plugin_with_config(self):
        """Test loading plugin with configuration."""
        config = {
            "api_key": "test-key-123",
            "default_style": "modern",
            "max_image_size": 2048,
        }

        self.manager.register_plugin_class("design", DesignPlugin)
        self.manager.load_plugin("design", config=config)

        plugin = self.manager.get_plugin("design")
        assert plugin.config == config

    def test_plugin_health_check(self):
        """Test plugin health check."""
        config = {"api_key": "test-key"}

        self.manager.register_plugin_class("design", DesignPlugin)
        self.manager.load_plugin("design", config=config)

        health = self.manager.health_check("design")

        assert health["plugin_id"] == "design"
        assert health["api_configured"] is True
        assert health["status"] == "healthy"

    def test_plugin_health_check_no_api_key(self):
        """Test health check with missing API key."""
        self.manager.register_plugin_class("design", DesignPlugin)
        self.manager.load_plugin("design")

        health = self.manager.health_check("design")

        assert health["api_configured"] is False
        assert health["status"] == "degraded"

    def test_unload_plugin_removes_tools(self):
        """Test unloading plugin removes its tools."""
        self.manager.register_plugin_class("design", DesignPlugin)
        self.manager.load_plugin("design")

        # Verify tools exist
        assert self.tool_registry.has("generate_image")

        # Unload plugin
        self.manager.unload_plugin("design")

        # Verify tools removed
        assert not self.tool_registry.has("generate_image")
        assert not self.tool_registry.has("create_color_palette")

    def test_unload_plugin_removes_competencies(self):
        """Test unloading plugin removes its competencies."""
        self.manager.register_plugin_class("design", DesignPlugin)
        self.manager.load_plugin("design")

        # Verify competencies exist
        assert self.competency_registry.has("color_theory")

        # Unload plugin
        self.manager.unload_plugin("design")

        # Verify competencies removed
        assert not self.competency_registry.has("color_theory")
        assert not self.competency_registry.has("ui_design")

    def test_list_tools_by_plugin(self):
        """Test listing tools from the plugin."""
        self.manager.register_plugin_class("design", DesignPlugin)
        self.manager.load_plugin("design")

        design_tools = self.tool_registry.list_by_plugin("design")

        assert len(design_tools) == 3
        tool_names = {t.name for t in design_tools}
        assert tool_names == {"generate_image", "create_color_palette", "create_ui_mockup"}

    def test_list_competencies_by_plugin(self):
        """Test listing competencies from the plugin."""
        self.manager.register_plugin_class("design", DesignPlugin)
        self.manager.load_plugin("design")

        design_comps = self.competency_registry.list_by_plugin("design")

        assert len(design_comps) == 4
        comp_ids = {c.id for c in design_comps}
        assert comp_ids == {"color_theory", "ui_design", "wireframing", "ai_image_generation"}
