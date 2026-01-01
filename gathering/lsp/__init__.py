"""
Language Server Protocol Integration.

Provides LSP capabilities for various programming languages
to enable IDE features like autocomplete, diagnostics, etc.
"""

from gathering.lsp.manager import LSPManager
from gathering.lsp.python_server import PythonLSPServer
from gathering.lsp.plugin_system import LSPPluginRegistry

# Auto-import plugins to trigger registration
# This ensures plugins are available when the module is loaded
import gathering.lsp.plugins.python_pylsp  # noqa: F401
import gathering.lsp.plugins.javascript_lsp  # noqa: F401
import gathering.lsp.plugins.rust_lsp  # noqa: F401

__all__ = ["LSPManager", "PythonLSPServer", "LSPPluginRegistry"]
