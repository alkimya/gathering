"""
LSP Plugin System - Extensible architecture for custom LSP servers.

Allows users to add their own language servers without modifying core code.
"""

from typing import Dict, Type, Optional, List
from pathlib import Path
import logging
import importlib
import inspect

from gathering.lsp.manager import BaseLSPServer

logger = logging.getLogger(__name__)


class LSPPluginRegistry:
    """
    Registry for LSP plugins.

    Allows registration of custom LSP servers for any language.

    Example:
        # Register a custom TypeScript LSP server
        @LSPPluginRegistry.register("typescript")
        class TypeScriptLSPServer(BaseLSPServer):
            async def get_completions(self, ...):
                # Custom implementation
                pass
    """

    _plugins: Dict[str, Type[BaseLSPServer]] = {}

    @classmethod
    def register(cls, language: str):
        """
        Decorator to register an LSP server plugin.

        Usage:
            @LSPPluginRegistry.register("typescript")
            class TypeScriptServer(BaseLSPServer):
                ...
        """
        def decorator(server_class: Type[BaseLSPServer]):
            if not issubclass(server_class, BaseLSPServer):
                raise TypeError(
                    f"{server_class.__name__} must inherit from BaseLSPServer"
                )

            cls._plugins[language] = server_class
            logger.info(f"Registered LSP plugin for {language}: {server_class.__name__}")
            return server_class

        return decorator

    @classmethod
    def get_plugin(cls, language: str) -> Optional[Type[BaseLSPServer]]:
        """Get the plugin class for a language."""
        return cls._plugins.get(language)

    @classmethod
    def list_plugins(cls) -> List[str]:
        """List all registered language plugins."""
        return list(cls._plugins.keys())

    @classmethod
    def discover_plugins(cls, plugin_dir: Optional[str] = None):
        """
        Auto-discover plugins from a directory.

        Looks for Python files in the plugins directory and loads classes
        that inherit from BaseLSPServer.

        Args:
            plugin_dir: Directory to search for plugins
                       (default: gathering/lsp/plugins/)
        """
        if plugin_dir is None:
            plugin_dir = Path(__file__).parent / "plugins"
        else:
            plugin_dir = Path(plugin_dir)

        if not plugin_dir.exists():
            logger.warning(f"Plugin directory not found: {plugin_dir}")
            return

        logger.info(f"Discovering LSP plugins in {plugin_dir}")

        # Scan for Python files
        for plugin_file in plugin_dir.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue  # Skip private files

            try:
                # Import the module
                module_name = f"gathering.lsp.plugins.{plugin_file.stem}"
                module = importlib.import_module(module_name)

                # Find BaseLSPServer subclasses
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (
                        issubclass(obj, BaseLSPServer) and
                        obj is not BaseLSPServer and
                        hasattr(obj, '__lsp_language__')
                    ):
                        language = obj.__lsp_language__
                        cls._plugins[language] = obj
                        logger.info(f"Auto-discovered plugin: {name} for {language}")

            except Exception as e:
                logger.error(f"Failed to load plugin from {plugin_file}: {e}")


class PluginMetadata:
    """
    Metadata for LSP plugins.

    Provides information about plugin capabilities and requirements.
    """

    def __init__(
        self,
        name: str,
        version: str,
        author: str,
        description: str,
        language: str,
        dependencies: Optional[List[str]] = None,
        config_schema: Optional[Dict] = None
    ):
        self.name = name
        self.version = version
        self.author = author
        self.description = description
        self.language = language
        self.dependencies = dependencies or []
        self.config_schema = config_schema or {}

    def to_dict(self) -> Dict:
        """Convert metadata to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "language": self.language,
            "dependencies": self.dependencies,
            "config_schema": self.config_schema
        }


def lsp_plugin(
    language: str,
    name: str,
    version: str = "1.0.0",
    author: str = "Unknown",
    description: str = "",
    dependencies: Optional[List[str]] = None
):
    """
    Decorator to create an LSP plugin with metadata.

    Usage:
        @lsp_plugin(
            language="rust",
            name="Rust LSP",
            version="1.0.0",
            author="Your Name",
            description="Rust language server integration",
            dependencies=["rust-analyzer"]
        )
        class RustLSPServer(BaseLSPServer):
            async def get_completions(self, ...):
                ...
    """
    def decorator(server_class: Type[BaseLSPServer]):
        # Attach metadata
        server_class.__lsp_language__ = language
        server_class.__lsp_metadata__ = PluginMetadata(
            name=name,
            version=version,
            author=author,
            description=description,
            language=language,
            dependencies=dependencies
        )

        # Auto-register
        LSPPluginRegistry.register(language)(server_class)

        return server_class

    return decorator


# ============================================================================
# Example Plugin Template
# ============================================================================

"""
To create a custom LSP plugin, save this template to:
gathering/lsp/plugins/your_language.py

```python
from gathering.lsp.plugin_system import lsp_plugin
from gathering.lsp.manager import BaseLSPServer

@lsp_plugin(
    language="mylang",
    name="MyLang LSP",
    version="1.0.0",
    author="Your Name",
    description="Custom language server",
    dependencies=["mylang-lsp"]
)
class MyLangLSPServer(BaseLSPServer):
    async def initialize(self, workspace_path: str) -> dict:
        # Initialize your LSP server
        self.initialized = True
        return {
            "capabilities": {
                "completionProvider": True,
                "hoverProvider": True
            }
        }

    async def get_completions(self, file_path, line, character, content=None):
        # Return completion items
        return [
            {
                "label": "my_function",
                "kind": 3,  # Function
                "detail": "Custom function",
                "insertText": "my_function()"
            }
        ]

    async def get_diagnostics(self, file_path, content=None):
        # Return diagnostics
        return []

    async def get_hover(self, file_path, line, character, content=None):
        # Return hover info
        return {
            "contents": {
                "kind": "markdown",
                "value": "# Documentation\\n\\nHover text here"
            }
        }

    async def get_definition(self, file_path, line, character, content=None):
        # Return definition location
        return None
```

The plugin will be auto-discovered on startup!
"""
