"""
Tool validation, async execution, and workspace path tests.

Covers: JSON Schema validation in ToolRegistry and SkillRegistry,
async/sync tool execution paths, concurrent async parallelism,
and workspace path resolution with DB/env/fallback.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from gathering.core.tool_registry import ToolCategory, ToolDefinition, ToolRegistry
from gathering.skills.base import BaseSkill, SkillResponse
from gathering.skills.registry import SkillRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SIMPLE_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "count": {"type": "integer"},
    },
    "required": ["name"],
}


def make_tool_def(**overrides) -> ToolDefinition:
    """Factory returning a ToolDefinition with sensible defaults."""
    defaults = dict(
        name="test_tool",
        description="Test tool",
        category=ToolCategory.UTILITY,
        function=lambda **kw: kw,
        required_competencies=[],
        parameters=SIMPLE_SCHEMA,
        returns={},
    )
    defaults.update(overrides)
    return ToolDefinition(**defaults)


class MockSkill(BaseSkill):
    """A minimal concrete skill for testing."""

    name = "mock_skill"
    description = "Mock skill for tests"
    version = "1.0.0"

    def __init__(self, config=None, tools_def=None, execute_fn=None):
        super().__init__(config)
        self._tools_def = tools_def or []
        self._execute_fn = execute_fn
        self._initialized = True  # Skip lazy init

    def get_tools_definition(self) -> List[Dict[str, Any]]:
        return self._tools_def

    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> SkillResponse:
        if self._execute_fn:
            return self._execute_fn(tool_name, tool_input)
        return SkillResponse(success=True, message="ok", data=tool_input)


# ---------------------------------------------------------------------------
# ToolRegistry validation tests (FEAT-07)
# ---------------------------------------------------------------------------


class TestToolRegistryValidation:
    """JSON Schema validation on ToolRegistry.execute()."""

    def setup_method(self):
        self.registry = ToolRegistry()

    def test_execute_valid_params_succeeds(self):
        """Valid parameters pass validation and return result."""
        tool = make_tool_def()
        self.registry.register(tool)

        result = self.registry.execute("test_tool", name="hello", count=5)
        assert result == {"name": "hello", "count": 5}

    def test_execute_invalid_type_raises(self):
        """Invalid type for parameter raises ValueError."""
        tool = make_tool_def()
        self.registry.register(tool)

        with pytest.raises(ValueError, match="name"):
            self.registry.execute("test_tool", name=123)

    def test_execute_missing_required_raises(self):
        """Missing required parameter raises ValueError."""
        tool = make_tool_def()
        self.registry.register(tool)

        with pytest.raises(ValueError, match="name"):
            self.registry.execute("test_tool", count=5)

    def test_execute_extra_params_with_no_additional_properties(self):
        """Extra params rejected when additionalProperties is false."""
        strict_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name"],
            "additionalProperties": False,
        }
        tool = make_tool_def(name="strict_tool", parameters=strict_schema)
        self.registry.register(tool)

        with pytest.raises(ValueError):
            self.registry.execute("strict_tool", name="ok", extra="nope")

    def test_execute_no_schema_skips_validation(self):
        """Empty parameters dict skips validation entirely."""
        tool = make_tool_def(name="no_schema_tool", parameters={})
        self.registry.register(tool)

        # Should not raise even with arbitrary params
        result = self.registry.execute("no_schema_tool", anything="goes", num=42)
        assert result == {"anything": "goes", "num": 42}

    def test_validation_error_includes_path(self):
        """Validation error for nested schema includes field path."""
        nested_schema = {
            "type": "object",
            "properties": {
                "config": {
                    "type": "object",
                    "properties": {
                        "level": {"type": "integer"},
                    },
                    "required": ["level"],
                },
            },
            "required": ["config"],
        }
        tool = make_tool_def(name="nested_tool", parameters=nested_schema)
        self.registry.register(tool)

        with pytest.raises(ValueError, match="level"):
            self.registry.execute("nested_tool", config={"level": "not_an_int"})


# ---------------------------------------------------------------------------
# ToolRegistry async tests (FEAT-08)
# ---------------------------------------------------------------------------


class TestToolRegistryAsync:
    """Async execution paths in ToolRegistry."""

    def setup_method(self):
        self.registry = ToolRegistry()

    @pytest.mark.asyncio
    async def test_execute_async_awaits_async_function(self):
        """Async tool function is properly awaited."""
        async def async_fn(**kwargs):
            return {"result": "async", **kwargs}

        tool = make_tool_def(
            name="async_tool",
            function=async_fn,
            async_function=True,
            parameters={},
        )
        self.registry.register(tool)

        result = await self.registry.execute_async("async_tool", x=1)
        assert result == {"result": "async", "x": 1}

    @pytest.mark.asyncio
    async def test_execute_async_wraps_sync_in_executor(self):
        """Sync tool runs in executor when called via execute_async."""
        def sync_fn(**kwargs):
            return {"result": "sync", **kwargs}

        tool = make_tool_def(
            name="sync_tool",
            function=sync_fn,
            async_function=False,
            parameters={},
        )
        self.registry.register(tool)

        result = await self.registry.execute_async("sync_tool", y=2)
        assert result == {"result": "sync", "y": 2}

    def test_execute_sync_rejects_async_tool(self):
        """Sync execute() raises RuntimeError for async tools."""
        async def async_fn(**kwargs):
            return kwargs

        tool = make_tool_def(
            name="async_only",
            function=async_fn,
            async_function=True,
            parameters={},
        )
        self.registry.register(tool)

        with pytest.raises(RuntimeError, match="execute_async"):
            self.registry.execute("async_only")

    @pytest.mark.asyncio
    async def test_concurrent_async_tools_run_parallel(self):
        """Two async tools run concurrently, not sequentially."""
        async def slow_fn(**kwargs):
            await asyncio.sleep(0.1)
            return {"done": True}

        tool_a = make_tool_def(
            name="slow_a",
            function=slow_fn,
            async_function=True,
            parameters={},
        )
        tool_b = make_tool_def(
            name="slow_b",
            function=slow_fn,
            async_function=True,
            parameters={},
        )
        self.registry.register(tool_a)
        self.registry.register(tool_b)

        start = time.monotonic()
        results = await asyncio.gather(
            self.registry.execute_async("slow_a"),
            self.registry.execute_async("slow_b"),
        )
        elapsed = time.monotonic() - start

        assert all(r["done"] for r in results)
        # If run in parallel, total time should be ~0.1s, not ~0.2s
        assert elapsed < 0.18, f"Expected parallel execution but took {elapsed:.3f}s"


# ---------------------------------------------------------------------------
# SkillRegistry validation tests (FEAT-07)
# ---------------------------------------------------------------------------


class TestSkillRegistryValidation:
    """JSON Schema validation on SkillRegistry.execute_tool()."""

    def setup_method(self):
        # Reset the registry class-level state between tests
        SkillRegistry.reset()

    def teardown_method(self):
        SkillRegistry.reset()

    def test_skill_registry_validates_input_schema(self):
        """Invalid tool input returns SkillResponse with validation error."""
        tools_def = [
            {
                "name": "validate_me",
                "description": "A validating tool",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer"},
                    },
                    "required": ["count"],
                },
            }
        ]
        skill = MockSkill(tools_def=tools_def)
        SkillRegistry.register("test_skill", type(skill), replace=True)

        # Patch get() to return our mock skill instance directly
        with patch.object(SkillRegistry, "get", return_value=skill):
            result = SkillRegistry.execute_tool(
                "validate_me",
                {"count": "not_an_int"},
                skill_name="test_skill",
            )

        assert result.success is False
        assert "validation_error" in (result.error or "")

    def test_skill_registry_passes_valid_input(self):
        """Valid tool input passes validation and executes skill."""
        tools_def = [
            {
                "name": "valid_tool",
                "description": "A tool with schema",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer"},
                    },
                    "required": ["count"],
                },
            }
        ]
        skill = MockSkill(tools_def=tools_def)
        SkillRegistry.register("test_skill2", type(skill), replace=True)

        with patch.object(SkillRegistry, "get", return_value=skill):
            result = SkillRegistry.execute_tool(
                "valid_tool",
                {"count": 42},
                skill_name="test_skill2",
            )

        assert result.success is True


# ---------------------------------------------------------------------------
# Workspace path tests (RLBL-04)
# ---------------------------------------------------------------------------


class TestWorkspacePath:
    """Workspace path resolution from DB, env, and cwd fallback."""

    def setup_method(self):
        """Clear the workspace path cache before each test."""
        from gathering.api.routers.workspace import _project_path_cache
        _project_path_cache.clear()

    def test_workspace_root_env_var(self, monkeypatch, tmp_path):
        """WORKSPACE_ROOT env var takes precedence when DB returns nothing."""
        workspace_dir = str(tmp_path)
        monkeypatch.setenv("WORKSPACE_ROOT", workspace_dir)

        # Patch DB at source module (lazy import inside _resolve_project_path)
        mock_db = MagicMock()
        mock_db.execute_one = MagicMock(return_value=None)

        with patch(
            "gathering.api.dependencies.get_database_service",
            return_value=mock_db,
        ):
            from gathering.api.routers.workspace import get_project_path, _project_path_cache
            _project_path_cache.clear()
            result = get_project_path(999)

        assert result == workspace_dir

    def test_workspace_fallback_to_cwd_with_warning(self, monkeypatch):
        """Without WORKSPACE_ROOT or DB, falls back to cwd with warning."""
        monkeypatch.delenv("WORKSPACE_ROOT", raising=False)

        mock_db = MagicMock()
        mock_db.execute_one = MagicMock(return_value=None)

        import os

        with (
            patch(
                "gathering.api.dependencies.get_database_service",
                return_value=mock_db,
            ),
            patch("gathering.api.routers.workspace.logger") as mock_logger,
        ):
            from gathering.api.routers.workspace import get_project_path, _project_path_cache
            _project_path_cache.clear()
            result = get_project_path(999)

        assert result == os.getcwd()
        # Verify a warning was logged about falling back to cwd
        mock_logger.warning.assert_called()
        warning_msg = str(mock_logger.warning.call_args)
        assert "cwd" in warning_msg.lower() or "WORKSPACE_ROOT" in warning_msg

    def test_workspace_db_lookup(self, monkeypatch, tmp_path):
        """DB repository_path is used when available and valid."""
        db_path = str(tmp_path)
        monkeypatch.delenv("WORKSPACE_ROOT", raising=False)

        mock_db = MagicMock()
        mock_db.execute_one = MagicMock(return_value={"repository_path": db_path})

        with patch(
            "gathering.api.dependencies.get_database_service",
            return_value=mock_db,
        ):
            from gathering.api.routers.workspace import get_project_path, _project_path_cache
            _project_path_cache.clear()
            result = get_project_path(1)

        assert result == db_path
