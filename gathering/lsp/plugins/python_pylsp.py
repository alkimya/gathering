"""
Professional Python LSP Plugin using python-lsp-server.

Uses pylsp with extensions:
- pylsp-mypy: Type checking with mypy
- python-lsp-ruff: Fast linting with ruff
- pylsp-rope: Advanced refactoring
- Jedi: Intelligent autocomplete

This provides VS Code-level Python support.
"""

from typing import Optional, List, Dict
import logging
from pathlib import Path

from gathering.lsp.plugin_system import lsp_plugin
from gathering.lsp.manager import BaseLSPServer

try:
    from gathering.lsp.pylsp_wrapper import PylspWrapper, PYLSP_AVAILABLE
except ImportError:
    PYLSP_AVAILABLE = False

logger = logging.getLogger(__name__)


@lsp_plugin(
    language="python",
    name="Python LSP (pylsp)",
    version="2.0.0",
    author="Gathering Team",
    description="Professional Python language server using pylsp with mypy, ruff, and rope",
    dependencies=["python-lsp-server[all]", "pylsp-mypy", "python-lsp-ruff", "pylsp-rope"]
)
class PythonPylspServer(BaseLSPServer):
    """
    Professional Python Language Server using pylsp.

    Features:
    - Jedi-powered autocomplete with type inference
    - Mypy type checking (real-time)
    - Ruff linting (extremely fast)
    - Rope refactoring and auto-imports
    - Go-to-definition
    - Hover documentation
    - Signature help
    """

    def __init__(self, workspace_path: str):
        super().__init__(workspace_path)
        self.wrapper: Optional[PylspWrapper] = None

    async def initialize(self, workspace_path: str) -> dict:
        """Initialize pylsp server."""
        self.workspace_path = Path(workspace_path)

        if not PYLSP_AVAILABLE:
            logger.warning("python-lsp-server not available, install with: pip install 'python-lsp-server[all]'")
            return {
                "capabilities": {
                    "completionProvider": {"triggerCharacters": ["."]},
                    "diagnosticProvider": False
                }
            }

        try:
            # Create pylsp wrapper
            self.wrapper = PylspWrapper(str(self.workspace_path))
            self.initialized = True

            logger.info(f"✓ Initialized pylsp wrapper for {workspace_path}")

            return {
                "capabilities": {
                    "completionProvider": {
                        "resolveProvider": True,
                        "triggerCharacters": [".", "(", "[", ",", " "]
                    },
                    "hoverProvider": True,
                    "definitionProvider": True,
                    "referencesProvider": True,
                    "documentSymbolProvider": True,
                    "workspaceSymbolProvider": True,
                    "codeActionProvider": True,
                    "documentFormattingProvider": True,
                    "diagnosticProvider": True,
                    "renameProvider": True,
                    "signatureHelpProvider": {
                        "triggerCharacters": ["(", ","]
                    }
                }
            }

        except Exception as e:
            logger.error(f"Failed to initialize pylsp: {e}")
            return {
                "capabilities": {
                    "completionProvider": {"triggerCharacters": ["."]},
                    "diagnosticProvider": False
                }
            }

    async def get_completions(
        self,
        file_path: str,
        line: int,
        character: int,
        content: Optional[str] = None
    ) -> List[Dict]:
        """Get intelligent completions from pylsp."""
        if not self.wrapper or not content:
            return []

        try:
            completions = self.wrapper.get_completions(
                file_path,
                line,
                character,
                content
            )

            logger.debug(f"Got {len(completions)} completions from pylsp")
            return completions

        except Exception as e:
            logger.error(f"Completion error: {e}")
            return []

    async def get_diagnostics(
        self,
        file_path: str,
        content: Optional[str] = None
    ) -> List[Dict]:
        """Get diagnostics from pylsp (mypy + ruff)."""
        if not self.wrapper or not content:
            return []

        try:
            diagnostics = self.wrapper.get_diagnostics(file_path, content)
            return diagnostics

        except Exception as e:
            logger.error(f"Diagnostics error: {e}")
            return []

    async def get_hover(
        self,
        file_path: str,
        line: int,
        character: int,
        content: Optional[str] = None
    ) -> Optional[Dict]:
        """Get hover information (docstrings, type hints)."""
        if not self.wrapper or not content:
            return None

        try:
            hover = self.wrapper.get_hover(
                file_path,
                line,
                character,
                content
            )

            return hover

        except Exception as e:
            logger.error(f"Hover error: {e}")
            return None

    async def get_definition(
        self,
        file_path: str,
        line: int,
        character: int,
        content: Optional[str] = None
    ) -> Optional[Dict]:
        """Get definition location."""
        if not self.wrapper or not content:
            return None

        try:
            definition = self.wrapper.get_definition(
                file_path,
                line,
                character,
                content
            )

            return definition

        except Exception as e:
            logger.error(f"Definition error: {e}")
            return None

    async def shutdown(self):
        """Shutdown pylsp server."""
        self.wrapper = None
        self.initialized = False
        logger.info("Python pylsp server shut down")
