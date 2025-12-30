"""
Example plugins for GatheRing.

Demonstrates how to create plugins that extend GatheRing with
domain-specific tools and competencies.

Included examples:
- DesignPlugin: AI-powered image generation and design tools
- FinancePlugin: Financial analysis and trading tools
- DataSciencePlugin: Data analysis and visualization tools

To use an example plugin:
    from gathering.plugins.examples import DesignPlugin
    from gathering.plugins import plugin_manager

    # Register and load
    plugin_manager.register_plugin_class("design", DesignPlugin)
    plugin_manager.load_plugin("design", config={
        "api_key": "your-api-key",
    })
    plugin_manager.enable_plugin("design")

    # Now agents can use the tools
    from gathering.core.tool_registry import tool_registry
    result = tool_registry.execute("generate_image", prompt="A sunset over mountains")
"""

from gathering.plugins.examples.design_plugin import DesignPlugin

__all__ = [
    "DesignPlugin",
]
