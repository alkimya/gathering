"""
LSP Manager - Manages language server instances.
"""

from typing import Dict, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class LSPManager:
    """
    Manages Language Server Protocol servers for different languages.

    Maintains a pool of LSP server instances per project and language.
    """

    _servers: Dict[str, Dict[str, 'BaseLSPServer']] = {}

    @classmethod
    def get_server(
        cls,
        project_id: int,
        language: str,
        workspace_path: Optional[str] = None
    ) -> 'BaseLSPServer':
        """
        Get or create an LSP server for a project and language.

        Args:
            project_id: Project identifier
            language: Programming language (python, javascript, etc.)
            workspace_path: Path to workspace root

        Returns:
            LSP server instance
        """
        key = f"{project_id}:{language}"

        if key not in cls._servers:
            logger.info(f"Creating new LSP server for {key}")

            # Try to get plugin first
            from gathering.lsp.plugin_system import LSPPluginRegistry

            plugin_class = LSPPluginRegistry.get_plugin(language)

            if plugin_class:
                server = plugin_class(workspace_path or ".")
                logger.info(f"Using plugin for {language}: {plugin_class.__name__}")
            else:
                # Fallback to built-in servers
                if language == "python":
                    from gathering.lsp.python_server import PythonLSPServer
                    server = PythonLSPServer(workspace_path or ".")
                else:
                    raise ValueError(
                        f"Unsupported language: {language}. "
                        f"Available plugins: {LSPPluginRegistry.list_plugins()}"
                    )

            cls._servers[key] = server

        return cls._servers[key]

    @classmethod
    async def initialize_server(
        cls,
        project_id: int,
        language: str,
        workspace_path: str
    ) -> dict:
        """
        Initialize an LSP server.

        Args:
            project_id: Project identifier
            language: Programming language
            workspace_path: Path to workspace root

        Returns:
            Server capabilities
        """
        server = cls.get_server(project_id, language, workspace_path)
        capabilities = await server.initialize(workspace_path)

        logger.info(f"Initialized LSP server for {language} in project {project_id}")
        return capabilities

    @classmethod
    async def shutdown_server(cls, project_id: int, language: str):
        """Shutdown an LSP server."""
        key = f"{project_id}:{language}"

        if key in cls._servers:
            server = cls._servers[key]
            await server.shutdown()
            del cls._servers[key]
            logger.info(f"Shutdown LSP server for {key}")

    @classmethod
    def shutdown_all(cls):
        """Shutdown all LSP servers."""
        for key in list(cls._servers.keys()):
            project_id, language = key.split(":")
            cls.shutdown_server(int(project_id), language)


class BaseLSPServer:
    """Base class for LSP server implementations."""

    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        self.initialized = False

    async def initialize(self, workspace_path: str) -> dict:
        """Initialize the LSP server."""
        raise NotImplementedError

    async def shutdown(self):
        """Shutdown the LSP server."""
        self.initialized = False

    async def get_completions(
        self,
        file_path: str,
        line: int,
        character: int,
        content: Optional[str] = None
    ) -> list:
        """Get autocomplete suggestions."""
        raise NotImplementedError

    async def get_diagnostics(
        self,
        file_path: str,
        content: Optional[str] = None
    ) -> list:
        """Get diagnostics (errors, warnings) for a file."""
        raise NotImplementedError

    async def get_hover(
        self,
        file_path: str,
        line: int,
        character: int
    ) -> Optional[dict]:
        """Get hover information (documentation)."""
        raise NotImplementedError

    async def get_definition(
        self,
        file_path: str,
        line: int,
        character: int
    ) -> Optional[dict]:
        """Get definition location."""
        raise NotImplementedError
