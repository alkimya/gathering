"""
Security tests for Phase 1: Auth + Security Foundation.
Tests SQL injection prevention, path traversal defense, and safe_update_builder.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from gathering.utils.sql import safe_update_builder


class TestSafeUpdateBuilder:
    """Tests for SQL safe_update_builder utility."""

    def test_valid_columns_accepted(self):
        """Allowed columns produce valid SET clause."""
        clause, params = safe_update_builder(
            {"name", "description", "status"},
            {"name": "Test", "status": "active"},
        )
        assert "name = %(name)s" in clause
        assert "status = %(status)s" in clause
        assert params == {"name": "Test", "status": "active"}

    def test_invalid_column_rejected(self):
        """Columns not in allowlist raise ValueError."""
        with pytest.raises(ValueError, match="not in allowed columns"):
            safe_update_builder(
                {"name", "description"},
                {"name": "Test", "evil_injection": "DROP TABLE"},
            )

    def test_always_set_appended(self):
        """always_set expressions are included in clause."""
        clause, params = safe_update_builder(
            {"name"},
            {"name": "Test"},
            always_set={"updated_at": "CURRENT_TIMESTAMP"},
        )
        assert "updated_at = CURRENT_TIMESTAMP" in clause
        assert "name = %(name)s" in clause
        assert "updated_at" not in params  # Not parameterized

    def test_empty_updates_produces_empty_clause(self):
        """Empty updates dict produces empty clause."""
        clause, params = safe_update_builder({"name"}, {})
        assert clause == ""
        assert params == {}

    def test_sql_injection_via_column_name_blocked(self):
        """SQL injection attempt via column name is rejected."""
        with pytest.raises(ValueError):
            safe_update_builder(
                {"name"},
                {"name; DROP TABLE users--": "value"},
            )

    def test_special_characters_in_values_safe(self):
        """Special characters in values are safely parameterized."""
        clause, params = safe_update_builder(
            {"name"},
            {"name": "'; DROP TABLE users;--"},
        )
        assert params["name"] == "'; DROP TABLE users;--"
        assert "%(name)s" in clause  # Parameterized, not inlined

    def test_multiple_columns_all_validated(self):
        """All columns in a multi-column update are validated."""
        clause, params = safe_update_builder(
            {"name", "status", "description"},
            {"name": "x", "status": "active", "description": "test"},
        )
        assert len(params) == 3
        assert "name = %(name)s" in clause
        assert "status = %(status)s" in clause
        assert "description = %(description)s" in clause

    def test_always_set_only(self):
        """always_set works even with empty updates dict."""
        clause, params = safe_update_builder(
            {"name"},
            {},
            always_set={"updated_at": "CURRENT_TIMESTAMP"},
        )
        assert "updated_at = CURRENT_TIMESTAMP" in clause
        assert params == {}

    def test_partial_invalid_columns_rejected(self):
        """Even one invalid column in a batch causes rejection."""
        with pytest.raises(ValueError, match="bad_col"):
            safe_update_builder(
                {"name", "status"},
                {"name": "ok", "bad_col": "nope"},
            )

    def test_column_with_spaces_rejected(self):
        """Column names with spaces are rejected (not in allowlist)."""
        with pytest.raises(ValueError):
            safe_update_builder(
                {"name"},
                {"name with spaces": "value"},
            )


class TestPathTraversalPrevention:
    """Tests for workspace path traversal defense."""

    def setup_method(self):
        """Set up test fixtures."""
        from gathering.api.routers.workspace import validate_file_path
        self.validate = validate_file_path
        self.project_root = os.getcwd()

    def test_normal_path_accepted(self):
        """Normal relative paths within project are accepted."""
        result = self.validate(self.project_root, "pyproject.toml")
        assert result.exists()

    def test_dot_dot_slash_rejected(self):
        """Basic ../ traversal is rejected with 403."""
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            self.validate(self.project_root, "../../../etc/passwd")
        assert exc_info.value.status_code == 403

    def test_encoded_dot_dot_rejected(self):
        """URL-encoded %2e%2e/ traversal is rejected with 403."""
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            self.validate(self.project_root, "%2e%2e/%2e%2e/etc/passwd")
        assert exc_info.value.status_code == 403

    def test_double_encoded_dot_dot_rejected(self):
        """Double URL-encoded (%252e%252e/) traversal is rejected with 403."""
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            self.validate(self.project_root, "%252e%252e/%252e%252e/etc/passwd")
        assert exc_info.value.status_code == 403

    def test_mixed_encoding_rejected(self):
        """Mixed encoding (..%2f) traversal is rejected with 403."""
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            self.validate(self.project_root, "..%2f..%2fetc/passwd")
        assert exc_info.value.status_code == 403

    def test_backslash_traversal_rejected(self):
        """Backslash-based traversal is rejected."""
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            self.validate(self.project_root, "..\\..\\etc\\passwd")
        assert exc_info.value.status_code == 403

    def test_null_byte_in_path_rejected(self):
        """Null byte in path is rejected (ValueError from Path)."""
        from fastapi import HTTPException
        # Null bytes in paths cause ValueError on Linux
        with pytest.raises((HTTPException, ValueError)):
            self.validate(self.project_root, "file\x00.txt/../../../etc/passwd")

    def test_deeply_nested_valid_path(self):
        """Deeply nested but valid path within project is accepted."""
        # This path doesn't exist but should not be rejected as traversal
        result = self.validate(self.project_root, "gathering/api/routers/workspace.py")
        assert result.is_absolute()

    def test_dot_dot_after_valid_prefix(self):
        """Path with .. after a valid prefix is rejected."""
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            self.validate(self.project_root, "gathering/../../../etc/passwd")
        assert exc_info.value.status_code == 403
