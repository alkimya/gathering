"""
Language Server Protocol Integration.

Provides LSP capabilities for various programming languages
to enable IDE features like autocomplete, diagnostics, etc.
"""

from gathering.lsp.manager import LSPManager
from gathering.lsp.python_server import PythonLSPServer

__all__ = ["LSPManager", "PythonLSPServer"]
