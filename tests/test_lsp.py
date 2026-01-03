"""
Tests for LSP (Language Server Protocol) system.

Covers:
- LSPManager server management
- LSPPluginRegistry plugin system
- BaseLSPServer interface
- Plugin discovery
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path


class TestBaseLSPServer:
    """Test BaseLSPServer base class."""

    def test_init(self):
        """Test server initialization."""
        from gathering.lsp.manager import BaseLSPServer

        server = BaseLSPServer("/path/to/workspace")

        assert server.workspace_path == Path("/path/to/workspace")
        assert server.initialized is False

    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test server shutdown."""
        from gathering.lsp.manager import BaseLSPServer

        server = BaseLSPServer("/path/to/workspace")
        server.initialized = True

        await server.shutdown()

        assert server.initialized is False

    @pytest.mark.asyncio
    async def test_abstract_methods_raise(self):
        """Test that abstract methods raise NotImplementedError."""
        from gathering.lsp.manager import BaseLSPServer

        server = BaseLSPServer("/path/to/workspace")

        with pytest.raises(NotImplementedError):
            await server.initialize("/path")

        with pytest.raises(NotImplementedError):
            await server.get_completions("file.py", 1, 0)

        with pytest.raises(NotImplementedError):
            await server.get_diagnostics("file.py")

        with pytest.raises(NotImplementedError):
            await server.get_hover("file.py", 1, 0)

        with pytest.raises(NotImplementedError):
            await server.get_definition("file.py", 1, 0)


class TestLSPPluginRegistry:
    """Test LSPPluginRegistry."""

    def setup_method(self):
        """Clear registry before each test."""
        from gathering.lsp.plugin_system import LSPPluginRegistry
        LSPPluginRegistry._plugins.clear()

    def test_register_plugin(self):
        """Test registering a plugin."""
        from gathering.lsp.plugin_system import LSPPluginRegistry
        from gathering.lsp.manager import BaseLSPServer

        @LSPPluginRegistry.register("testlang")
        class TestLangServer(BaseLSPServer):
            pass

        assert "testlang" in LSPPluginRegistry.list_plugins()
        assert LSPPluginRegistry.get_plugin("testlang") == TestLangServer

    def test_register_non_subclass_raises(self):
        """Test that registering a non-BaseLSPServer class raises."""
        from gathering.lsp.plugin_system import LSPPluginRegistry

        with pytest.raises(TypeError, match="must inherit from BaseLSPServer"):
            @LSPPluginRegistry.register("badlang")
            class NotAServer:
                pass

    def test_get_nonexistent_plugin(self):
        """Test getting a nonexistent plugin returns None."""
        from gathering.lsp.plugin_system import LSPPluginRegistry

        assert LSPPluginRegistry.get_plugin("nonexistent") is None

    def test_list_plugins_empty(self):
        """Test listing plugins when none registered."""
        from gathering.lsp.plugin_system import LSPPluginRegistry

        assert LSPPluginRegistry.list_plugins() == []

    def test_list_plugins_with_registered(self):
        """Test listing registered plugins."""
        from gathering.lsp.plugin_system import LSPPluginRegistry
        from gathering.lsp.manager import BaseLSPServer

        @LSPPluginRegistry.register("lang1")
        class Lang1Server(BaseLSPServer):
            pass

        @LSPPluginRegistry.register("lang2")
        class Lang2Server(BaseLSPServer):
            pass

        plugins = LSPPluginRegistry.list_plugins()
        assert "lang1" in plugins
        assert "lang2" in plugins


class TestPluginMetadata:
    """Test PluginMetadata class."""

    def test_create_metadata(self):
        """Test creating plugin metadata."""
        from gathering.lsp.plugin_system import PluginMetadata

        metadata = PluginMetadata(
            name="Test LSP",
            version="1.0.0",
            author="Test Author",
            description="Test description",
            language="testlang",
            dependencies=["dep1", "dep2"]
        )

        assert metadata.name == "Test LSP"
        assert metadata.version == "1.0.0"
        assert metadata.author == "Test Author"
        assert metadata.language == "testlang"
        assert metadata.dependencies == ["dep1", "dep2"]

    def test_metadata_to_dict(self):
        """Test converting metadata to dictionary."""
        from gathering.lsp.plugin_system import PluginMetadata

        metadata = PluginMetadata(
            name="Test",
            version="1.0.0",
            author="Author",
            description="Desc",
            language="lang"
        )

        data = metadata.to_dict()

        assert data["name"] == "Test"
        assert data["version"] == "1.0.0"
        assert data["language"] == "lang"
        assert data["dependencies"] == []

    def test_metadata_defaults(self):
        """Test metadata default values."""
        from gathering.lsp.plugin_system import PluginMetadata

        metadata = PluginMetadata(
            name="Test",
            version="1.0.0",
            author="Author",
            description="Desc",
            language="lang"
        )

        assert metadata.dependencies == []
        assert metadata.config_schema == {}


class TestLspPluginDecorator:
    """Test lsp_plugin decorator."""

    def setup_method(self):
        """Clear registry before each test."""
        from gathering.lsp.plugin_system import LSPPluginRegistry
        LSPPluginRegistry._plugins.clear()

    def test_lsp_plugin_decorator(self):
        """Test the lsp_plugin decorator."""
        from gathering.lsp.plugin_system import lsp_plugin, LSPPluginRegistry
        from gathering.lsp.manager import BaseLSPServer

        @lsp_plugin(
            language="decorated",
            name="Decorated LSP",
            version="2.0.0",
            author="Test",
            description="Test plugin"
        )
        class DecoratedServer(BaseLSPServer):
            pass

        # Should be registered
        assert "decorated" in LSPPluginRegistry.list_plugins()

        # Should have metadata
        assert hasattr(DecoratedServer, "__lsp_language__")
        assert DecoratedServer.__lsp_language__ == "decorated"
        assert hasattr(DecoratedServer, "__lsp_metadata__")
        assert DecoratedServer.__lsp_metadata__.name == "Decorated LSP"


class TestLSPManager:
    """Test LSPManager server management."""

    def setup_method(self):
        """Clear servers before each test."""
        from gathering.lsp.manager import LSPManager
        from gathering.lsp.plugin_system import LSPPluginRegistry
        LSPManager._servers.clear()
        LSPPluginRegistry._plugins.clear()

    def test_get_server_creates_new(self):
        """Test that get_server creates a new server instance."""
        from gathering.lsp.manager import LSPManager, BaseLSPServer
        from gathering.lsp.plugin_system import LSPPluginRegistry

        # Register a test plugin
        @LSPPluginRegistry.register("testlang")
        class TestServer(BaseLSPServer):
            async def initialize(self, workspace_path):
                return {"capabilities": {}}

        server = LSPManager.get_server(1, "testlang", "/workspace")

        assert isinstance(server, TestServer)
        assert server.workspace_path == Path("/workspace")

    def test_get_server_returns_existing(self):
        """Test that get_server returns existing server."""
        from gathering.lsp.manager import LSPManager, BaseLSPServer
        from gathering.lsp.plugin_system import LSPPluginRegistry

        @LSPPluginRegistry.register("testlang2")
        class TestServer2(BaseLSPServer):
            pass

        server1 = LSPManager.get_server(1, "testlang2", "/workspace")
        server2 = LSPManager.get_server(1, "testlang2", "/workspace")

        assert server1 is server2

    def test_get_server_unsupported_language(self):
        """Test getting server for unsupported language raises."""
        from gathering.lsp.manager import LSPManager

        with pytest.raises(ValueError, match="Unsupported language"):
            LSPManager.get_server(1, "unsupported_language_xyz", "/workspace")

    @pytest.mark.asyncio
    async def test_initialize_server(self):
        """Test initializing a server."""
        from gathering.lsp.manager import LSPManager, BaseLSPServer
        from gathering.lsp.plugin_system import LSPPluginRegistry

        @LSPPluginRegistry.register("initlang")
        class InitServer(BaseLSPServer):
            async def initialize(self, workspace_path):
                self.initialized = True
                return {"capabilities": {"completionProvider": True}}

        caps = await LSPManager.initialize_server(1, "initlang", "/workspace")

        assert caps["capabilities"]["completionProvider"] is True

    @pytest.mark.asyncio
    async def test_shutdown_server(self):
        """Test shutting down a server."""
        from gathering.lsp.manager import LSPManager, BaseLSPServer
        from gathering.lsp.plugin_system import LSPPluginRegistry

        @LSPPluginRegistry.register("shutdownlang")
        class ShutdownServer(BaseLSPServer):
            async def initialize(self, workspace_path):
                return {}

        # Create server
        LSPManager.get_server(1, "shutdownlang", "/workspace")
        assert "1:shutdownlang" in LSPManager._servers

        # Shutdown
        await LSPManager.shutdown_server(1, "shutdownlang")
        assert "1:shutdownlang" not in LSPManager._servers


class TestPluginDiscovery:
    """Test plugin auto-discovery."""

    def setup_method(self):
        """Clear registry before each test."""
        from gathering.lsp.plugin_system import LSPPluginRegistry
        LSPPluginRegistry._plugins.clear()

    def test_discover_plugins_nonexistent_dir(self):
        """Test discovering plugins from nonexistent directory."""
        from gathering.lsp.plugin_system import LSPPluginRegistry

        # Should not raise, just log warning
        LSPPluginRegistry.discover_plugins("/nonexistent/path")

        # No plugins should be registered
        assert len(LSPPluginRegistry.list_plugins()) == 0

    @patch("gathering.lsp.plugin_system.importlib.import_module")
    def test_discover_plugins_import_error(self, mock_import):
        """Test discovering plugins with import error."""
        from gathering.lsp.plugin_system import LSPPluginRegistry
        import tempfile
        import os

        # Create a temp directory with a plugin file
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_file = os.path.join(tmpdir, "test_plugin.py")
            with open(plugin_file, "w") as f:
                f.write("# Empty plugin")

            mock_import.side_effect = ImportError("Module not found")

            # Should not raise, just log error
            LSPPluginRegistry.discover_plugins(tmpdir)


class TestLSPRouterIntegration:
    """Test LSP API router."""

    def setup_method(self):
        """Clear LSP state before each test."""
        from gathering.lsp.manager import LSPManager
        from gathering.lsp.plugin_system import LSPPluginRegistry
        LSPManager._servers.clear()
        LSPPluginRegistry._plugins.clear()

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from gathering.api.routers.lsp import router

        app = FastAPI()
        app.include_router(router)

        return TestClient(app)

    def test_get_status_endpoint(self, client):
        """Test GET /lsp/{project_id}/status endpoint."""
        response = client.get("/lsp/1/status")

        assert response.status_code == 200
        data = response.json()
        # Response includes: active, project_id, language
        assert "active" in data
        assert data["project_id"] == 1

    def test_initialize_endpoint_unsupported_language(self, client):
        """Test POST /lsp/{project_id}/initialize with unsupported language."""
        response = client.post(
            "/lsp/1/initialize",
            json={"language": "unsupported_xyz", "workspace_path": "/tmp"}
        )

        # Should return 400 for unsupported language
        assert response.status_code == 400
        assert "Unsupported language" in response.json()["detail"]


class TestMockLSPServer:
    """Test with a fully mocked LSP server."""

    @pytest.mark.asyncio
    async def test_full_lsp_workflow(self):
        """Test a complete LSP workflow."""
        from gathering.lsp.manager import BaseLSPServer
        from gathering.lsp.plugin_system import LSPPluginRegistry, lsp_plugin

        # Clear registry
        LSPPluginRegistry._plugins.clear()

        @lsp_plugin(
            language="mock",
            name="Mock LSP",
            version="1.0.0",
            author="Test",
            description="Mock server for testing"
        )
        class MockLSPServer(BaseLSPServer):
            async def initialize(self, workspace_path):
                self.initialized = True
                return {
                    "capabilities": {
                        "completionProvider": True,
                        "hoverProvider": True,
                        "definitionProvider": True
                    }
                }

            async def get_completions(self, file_path, line, character, content=None):
                return [
                    {"label": "test_func", "kind": 3, "detail": "Test function"}
                ]

            async def get_diagnostics(self, file_path, content=None):
                return [
                    {
                        "range": {"start": {"line": 0, "character": 0}},
                        "message": "Test warning",
                        "severity": 2
                    }
                ]

            async def get_hover(self, file_path, line, character):
                return {
                    "contents": {"kind": "markdown", "value": "# Test\n\nHover text"}
                }

            async def get_definition(self, file_path, line, character):
                return {
                    "uri": f"file://{file_path}",
                    "range": {"start": {"line": 10, "character": 0}}
                }

        # Create and initialize server
        server = MockLSPServer("/workspace")
        caps = await server.initialize("/workspace")

        assert caps["capabilities"]["completionProvider"] is True
        assert server.initialized is True

        # Test completions
        completions = await server.get_completions("test.py", 1, 0)
        assert len(completions) == 1
        assert completions[0]["label"] == "test_func"

        # Test diagnostics
        diagnostics = await server.get_diagnostics("test.py")
        assert len(diagnostics) == 1
        assert diagnostics[0]["message"] == "Test warning"

        # Test hover
        hover = await server.get_hover("test.py", 1, 0)
        assert "contents" in hover

        # Test definition
        definition = await server.get_definition("test.py", 1, 0)
        assert "uri" in definition

        # Shutdown
        await server.shutdown()
        assert server.initialized is False
