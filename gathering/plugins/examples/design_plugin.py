"""
Design Plugin for GatheRing.

Provides AI-powered design and image generation tools.

Features:
- Image generation (AI-based)
- Image editing and manipulation
- Color palette generation
- UI mockup creation

This is an example plugin that demonstrates:
- How to create tools with complex parameters
- How to define competencies with prerequisites
- How to handle optional dependencies
- How to add configuration
- How to implement health checks

Usage:
    from gathering.plugins.examples import DesignPlugin
    from gathering.plugins import plugin_manager

    # Register plugin class
    plugin_manager.register_plugin_class("design", DesignPlugin)

    # Load with configuration
    plugin_manager.load_plugin("design", config={
        "api_key": "your-api-key",  # For AI image generation
        "default_style": "modern",
        "max_image_size": 2048,
    })

    # Enable plugin
    plugin_manager.enable_plugin("design")

    # Use tools
    from gathering.core.tool_registry import tool_registry
    result = tool_registry.execute(
        "generate_image",
        prompt="A futuristic cityscape at sunset",
        style="modern",
        dimensions="1024x1024"
    )
"""

from typing import List, Dict, Any
import logging

from gathering.plugins.base import Plugin, PluginMetadata
from gathering.core.tool_registry import ToolDefinition, ToolCategory
from gathering.core.competency_registry import (
    CompetencyDefinition,
    CompetencyCategory,
    CompetencyLevel,
)


logger = logging.getLogger(__name__)


class DesignPlugin(Plugin):
    """
    Plugin providing AI-powered design and image tools.

    This plugin demonstrates how to create a domain-specific plugin
    with tools, competencies, and configuration.
    """

    @property
    def metadata(self) -> PluginMetadata:
        """Plugin metadata."""
        return PluginMetadata(
            id="design",
            name="Design & Image Tools",
            version="1.0.0",
            description="AI-powered design tools for image generation, editing, and creative work",
            author="GatheRing Team",
            author_email="loc.cosnier@pm.me",
            license="MIT",
            homepage="https://github.com/alkimya/gathering",
            tags=["design", "image", "ai", "creative"],
            python_dependencies=[
                # Optional dependencies for full functionality
                # "pillow>=9.0.0",  # Image manipulation
                # "requests>=2.28.0",  # API calls
            ],
            min_gathering_version="0.1.0",
            config_schema={
                "type": "object",
                "properties": {
                    "api_key": {
                        "type": "string",
                        "description": "API key for AI image generation service",
                    },
                    "default_style": {
                        "type": "string",
                        "enum": ["modern", "classic", "abstract", "realistic"],
                        "default": "modern",
                    },
                    "max_image_size": {
                        "type": "integer",
                        "default": 2048,
                        "description": "Maximum image dimension in pixels",
                    },
                },
            },
        )

    def register_tools(self) -> List[ToolDefinition]:
        """Register design tools."""
        return [
            ToolDefinition(
                name="generate_image",
                description="Generate an image using AI based on a text prompt",
                category=ToolCategory.IMAGE,
                function=self.generate_image,
                required_competencies=["ai_image_generation"],
                parameters={
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "Text description of the image to generate",
                        },
                        "style": {
                            "type": "string",
                            "enum": ["modern", "classic", "abstract", "realistic"],
                            "description": "Visual style for the image",
                        },
                        "dimensions": {
                            "type": "string",
                            "enum": ["512x512", "1024x1024", "2048x2048"],
                            "description": "Image dimensions",
                        },
                    },
                    "required": ["prompt"],
                },
                returns={
                    "type": "object",
                    "properties": {
                        "image_url": {"type": "string"},
                        "dimensions": {"type": "string"},
                        "style": {"type": "string"},
                    },
                },
                examples=[
                    'generate_image(prompt="A sunset over mountains", style="realistic")',
                    'generate_image(prompt="Abstract geometric patterns", style="abstract", dimensions="2048x2048")',
                ],
                plugin_id=self.metadata.id,
            ),
            ToolDefinition(
                name="create_color_palette",
                description="Generate a color palette based on a theme or image",
                category=ToolCategory.IMAGE,
                function=self.create_color_palette,
                required_competencies=["color_theory"],
                parameters={
                    "type": "object",
                    "properties": {
                        "theme": {
                            "type": "string",
                            "description": "Theme for the color palette (e.g., 'ocean', 'sunset', 'forest')",
                        },
                        "num_colors": {
                            "type": "integer",
                            "minimum": 3,
                            "maximum": 10,
                            "default": 5,
                            "description": "Number of colors in the palette",
                        },
                    },
                    "required": ["theme"],
                },
                returns={
                    "type": "object",
                    "properties": {
                        "colors": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "theme": {"type": "string"},
                    },
                },
                examples=[
                    'create_color_palette(theme="ocean", num_colors=5)',
                    'create_color_palette(theme="sunset")',
                ],
                plugin_id=self.metadata.id,
            ),
            ToolDefinition(
                name="create_ui_mockup",
                description="Create a UI mockup based on specifications",
                category=ToolCategory.IMAGE,
                function=self.create_ui_mockup,
                required_competencies=["ui_design", "wireframing"],
                parameters={
                    "type": "object",
                    "properties": {
                        "page_type": {
                            "type": "string",
                            "enum": ["landing", "dashboard", "form", "profile"],
                            "description": "Type of UI page",
                        },
                        "components": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of UI components to include",
                        },
                        "style": {
                            "type": "string",
                            "enum": ["modern", "classic", "minimal"],
                            "default": "modern",
                        },
                    },
                    "required": ["page_type", "components"],
                },
                returns={
                    "type": "object",
                    "properties": {
                        "mockup_url": {"type": "string"},
                        "components_used": {"type": "array"},
                    },
                },
                examples=[
                    'create_ui_mockup(page_type="landing", components=["hero", "features", "cta"])',
                ],
                plugin_id=self.metadata.id,
            ),
        ]

    def register_competencies(self) -> List[CompetencyDefinition]:
        """Register design competencies."""
        return [
            CompetencyDefinition(
                id="color_theory",
                name="Color Theory",
                description="Understanding of color theory, palettes, and harmony",
                category=CompetencyCategory.GRAPHIC_DESIGN,
                level=CompetencyLevel.INTERMEDIATE,
                capabilities=["palette_generation", "color_matching"],
                tools_enabled=["create_color_palette"],
                plugin_id=self.metadata.id,
            ),
            CompetencyDefinition(
                id="ui_design",
                name="UI Design",
                description="User interface design skills",
                category=CompetencyCategory.UI_UX_DESIGN,
                level=CompetencyLevel.ADVANCED,
                prerequisites=["color_theory"],
                capabilities=["layout_design", "component_design"],
                tools_enabled=["create_ui_mockup"],
                plugin_id=self.metadata.id,
            ),
            CompetencyDefinition(
                id="wireframing",
                name="Wireframing",
                description="Creating wireframes and mockups",
                category=CompetencyCategory.UI_UX_DESIGN,
                level=CompetencyLevel.INTERMEDIATE,
                prerequisites=["ui_design"],
                capabilities=["mockup_creation", "prototyping"],
                tools_enabled=["create_ui_mockup"],
                plugin_id=self.metadata.id,
            ),
            CompetencyDefinition(
                id="ai_image_generation",
                name="AI Image Generation",
                description="Using AI to generate images from text prompts",
                category=CompetencyCategory.GRAPHIC_DESIGN,
                level=CompetencyLevel.EXPERT,
                prerequisites=["color_theory"],
                capabilities=["text_to_image", "prompt_engineering"],
                tools_enabled=["generate_image"],
                plugin_id=self.metadata.id,
                metadata={
                    "learning_resources": [
                        "https://docs.gathering.ai/design/image-generation",
                    ],
                },
            ),
        ]

    # ========================================================================
    # Tool Implementations
    # ========================================================================

    def generate_image(
        self,
        prompt: str,
        style: str = "modern",
        dimensions: str = "1024x1024",
    ) -> Dict[str, Any]:
        """
        Generate an image using AI.

        In a real implementation, this would call an AI image generation API
        like DALL-E, Midjourney, or Stable Diffusion.

        Args:
            prompt: Text description of the image.
            style: Visual style.
            dimensions: Image dimensions.

        Returns:
            Dictionary with image URL and metadata.
        """
        logger.info(f"Generating image: {prompt} (style={style}, dimensions={dimensions})")

        # In a real implementation, you would:
        # 1. Validate API key from config
        # 2. Call the AI image generation API
        # 3. Handle errors and retries
        # 4. Return the actual image URL

        # Simulated response
        return {
            "image_url": f"https://api.example.com/images/generated-{hash(prompt)}.png",
            "dimensions": dimensions,
            "style": style,
            "prompt": prompt,
            "status": "generated",
        }

    def create_color_palette(
        self,
        theme: str,
        num_colors: int = 5,
    ) -> Dict[str, Any]:
        """
        Create a color palette based on a theme.

        Args:
            theme: Theme for the palette.
            num_colors: Number of colors.

        Returns:
            Dictionary with color palette.
        """
        logger.info(f"Creating color palette: {theme} ({num_colors} colors)")

        # Simple theme-based palettes
        # In a real implementation, you might use color theory algorithms
        # or ML models to generate harmonious palettes
        theme_palettes = {
            "ocean": ["#006BA6", "#0496FF", "#FFBC42", "#D81159", "#8F2D56"],
            "sunset": ["#FF6B35", "#F7931E", "#FBB03B", "#DA627D", "#A53860"],
            "forest": ["#2D6A4F", "#40916C", "#52B788", "#74C69D", "#95D5B2"],
            "modern": ["#264653", "#2A9D8F", "#E9C46A", "#F4A261", "#E76F51"],
        }

        colors = theme_palettes.get(
            theme.lower(),
            ["#000000", "#333333", "#666666", "#999999", "#CCCCCC"],
        )

        return {
            "colors": colors[:num_colors],
            "theme": theme,
            "num_colors": len(colors[:num_colors]),
        }

    def create_ui_mockup(
        self,
        page_type: str,
        components: List[str],
        style: str = "modern",
    ) -> Dict[str, Any]:
        """
        Create a UI mockup.

        Args:
            page_type: Type of page.
            components: List of components.
            style: Visual style.

        Returns:
            Dictionary with mockup information.
        """
        logger.info(
            f"Creating UI mockup: {page_type} "
            f"(components={components}, style={style})"
        )

        # In a real implementation, you would:
        # 1. Generate actual mockup using design tools
        # 2. Or call a mockup generation API
        # 3. Return the mockup URL

        return {
            "mockup_url": f"https://api.example.com/mockups/{page_type}-{hash(str(components))}.png",
            "page_type": page_type,
            "components_used": components,
            "style": style,
            "status": "created",
        }

    # ========================================================================
    # Plugin Lifecycle
    # ========================================================================

    def on_enable(self) -> None:
        """Called when plugin is enabled."""
        super().on_enable()
        logger.info("Design plugin enabled - AI image generation tools ready")

        # You could add initialization here:
        # - Connect to external APIs
        # - Load ML models
        # - Start background services

    def on_disable(self) -> None:
        """Called when plugin is disabled."""
        super().on_disable()
        logger.info("Design plugin disabled")

        # Clean up resources:
        # - Disconnect from APIs
        # - Unload models
        # - Stop background services

    def health_check(self) -> Dict[str, Any]:
        """Check plugin health."""
        health = super().health_check()

        # Add custom health checks
        api_key = self.config.get("api_key")
        health["api_configured"] = bool(api_key)

        # In a real implementation, you might:
        # - Test API connectivity
        # - Check resource availability
        # - Verify model loading

        if api_key:
            health["status"] = "healthy"
            health["message"] = "Design tools ready"
        else:
            health["status"] = "degraded"
            health["message"] = "API key not configured"

        return health
