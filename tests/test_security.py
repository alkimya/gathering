"""
Security tests for GatheRing framework.
These tests verify that security measures are properly implemented.
"""

import pytest
import tempfile
from pathlib import Path

from gathering.core.implementations import (
    CalculatorTool,
    FileSystemTool,
    SafeExpressionEvaluator,
    PathTraversalError,
)
from gathering.core.exceptions import ToolExecutionError


class TestCalculatorSecurity:
    """Security tests for the CalculatorTool."""

    @pytest.fixture
    def calculator(self):
        """Create a calculator tool instance."""
        return CalculatorTool.from_config({"name": "calculator"})

    # =========================================================================
    # Safe Expression Evaluator Tests
    # =========================================================================

    def test_basic_arithmetic(self, calculator):
        """Test basic arithmetic operations work correctly."""
        test_cases = [
            ("2 + 2", 4.0),
            ("10 - 3", 7.0),
            ("4 * 5", 20.0),
            ("20 / 4", 5.0),
            ("10 // 3", 3.0),
            ("10 % 3", 1.0),
            ("2 ** 10", 1024.0),
            ("-5", -5.0),
            ("+5", 5.0),
            ("(2 + 3) * 4", 20.0),
        ]
        for expression, expected in test_cases:
            result = calculator.execute(expression)
            assert result.success, f"Failed for: {expression}"
            assert result.output == expected, f"Wrong result for: {expression}"

    def test_percentage_calculation(self, calculator):
        """Test percentage expressions."""
        result = calculator.execute("15% of 2500")
        assert result.success
        assert result.output == 375.0

        result = calculator.execute("50% of 100")
        assert result.success
        assert result.output == 50.0

    def test_code_injection_blocked(self, calculator):
        """Test that code injection attempts are blocked."""
        malicious_expressions = [
            # Attempt to access classes
            "().__class__.__bases__[0].__subclasses__()",
            "''.__class__.__mro__[2].__subclasses__()",
            # Import attempts
            "__import__('os').system('ls')",
            "import os",
            # Built-in function calls
            "open('/etc/passwd').read()",
            "eval('1+1')",
            "exec('print(1)')",
            "compile('1+1', '', 'eval')",
            # Attribute access
            "getattr(__builtins__, 'open')",
            # Lambda and comprehensions
            "[x for x in range(10)]",
            "lambda: 1",
            # String operations that could lead to injection
            "'test'.join(['a', 'b'])",
        ]

        for expr in malicious_expressions:
            result = calculator.execute(expr)
            assert not result.success, f"Should have blocked: {expr}"
            assert result.error is not None

    def test_resource_exhaustion_blocked(self, calculator):
        """Test that resource exhaustion attacks are blocked."""
        # Very large numbers
        result = calculator.execute("10 ** 1000000")
        assert not result.success
        assert "too large" in result.error.lower()

        # Very long expression
        long_expr = "1 + " * 500 + "1"
        result = calculator.execute(long_expr)
        assert not result.success

    def test_division_by_zero(self, calculator):
        """Test that division by zero is handled."""
        result = calculator.execute("1 / 0")
        assert not result.success
        assert "division by zero" in result.error.lower()

    def test_invalid_expressions(self, calculator):
        """Test that invalid expressions are rejected."""
        invalid_expressions = [
            "",  # Empty
            "   ",  # Whitespace only
            "abc",  # Non-numeric
            "1 +",  # Incomplete
            "+ 1 +",  # Invalid syntax
        ]

        for expr in invalid_expressions:
            result = calculator.execute(expr)
            assert not result.success, f"Should have rejected: {expr!r}"

    def test_safe_evaluator_directly(self):
        """Test the SafeExpressionEvaluator class directly."""
        # Valid expressions
        assert SafeExpressionEvaluator.evaluate("2 + 2") == 4.0
        assert SafeExpressionEvaluator.evaluate("-5") == -5.0
        assert SafeExpressionEvaluator.evaluate("(1 + 2) * 3") == 9.0

        # Invalid expressions should raise ValueError
        with pytest.raises(ValueError):
            SafeExpressionEvaluator.evaluate("__import__('os')")

        with pytest.raises(ValueError):
            SafeExpressionEvaluator.evaluate("open('file')")


class TestFileSystemSecurity:
    """Security tests for the FileSystemTool."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def filesystem(self, temp_dir):
        """Create a filesystem tool with temp directory as base."""
        return FileSystemTool.from_config({
            "name": "filesystem",
            "base_path": str(temp_dir),
            "permissions": ["read", "write", "delete"],
        })

    # =========================================================================
    # Path Traversal Tests
    # =========================================================================

    def test_path_traversal_blocked(self, filesystem):
        """Test that path traversal attacks are blocked."""
        traversal_attempts = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "foo/../../bar",
            "~/../../etc/passwd",
        ]

        for path in traversal_attempts:
            with pytest.raises(ToolExecutionError) as exc_info:
                filesystem.execute({"action": "read", "path": path})
            assert "traversal" in str(exc_info.value).lower() or "pattern" in str(exc_info.value).lower()

    def test_absolute_path_traversal_blocked(self, filesystem):
        """Test that absolute paths outside sandbox are blocked via exception or result."""
        # /etc/passwd is blocked by the 'passwd' pattern, returning an error result
        result = filesystem.execute({"action": "read", "path": "/etc/passwd"})
        assert not result.success
        assert "not permitted" in result.error.lower()

    def test_dangerous_patterns_blocked(self, filesystem):
        """Test that dangerous patterns in paths are blocked."""
        dangerous_paths = [
            "${HOME}/.ssh/id_rsa",
            "$(whoami)",
            "`id`",
            "test/../../../etc/passwd",
        ]

        for path in dangerous_paths:
            with pytest.raises(ToolExecutionError):
                filesystem.execute({"action": "read", "path": path})

    def test_blocked_file_patterns(self, filesystem):
        """Test that sensitive file patterns are blocked."""
        blocked_patterns = [
            ".env",
            ".git/config",
            "id_rsa",
            "credentials.json",
            ".ssh/config",
        ]

        for path in blocked_patterns:
            result = filesystem.execute({"action": "read", "path": path})
            assert not result.success
            assert "not permitted" in result.error.lower()

    def test_safe_file_operations(self, filesystem, temp_dir):
        """Test that safe file operations work correctly."""
        # Write a file
        result = filesystem.execute({
            "action": "write",
            "path": "test.txt",
            "content": "Hello, World!",
        })
        assert result.success

        # Read the file
        result = filesystem.execute({
            "action": "read",
            "path": "test.txt",
        })
        assert result.success
        assert result.output == "Hello, World!"

        # List directory
        result = filesystem.execute({
            "action": "list",
            "path": ".",
        })
        assert result.success
        assert any(entry["name"] == "test.txt" for entry in result.output)

        # Delete the file
        result = filesystem.execute({
            "action": "delete",
            "path": "test.txt",
        })
        assert result.success

    def test_permission_checks(self, temp_dir):
        """Test that permission checks work."""
        # Tool with only read permission
        read_only = FileSystemTool.from_config({
            "name": "readonly",
            "base_path": str(temp_dir),
            "permissions": ["read"],
        })

        # Should fail to write
        with pytest.raises(ToolExecutionError) as exc_info:
            read_only.execute({
                "action": "write",
                "path": "test.txt",
                "content": "test",
            })
        assert "permission" in str(exc_info.value).lower()

        # Should fail to delete
        with pytest.raises(ToolExecutionError):
            read_only.execute({
                "action": "delete",
                "path": "test.txt",
            })

    def test_file_size_limits(self, filesystem):
        """Test that file size limits are enforced."""
        # Try to write a very large file
        large_content = "x" * (11 * 1024 * 1024)  # 11 MB
        result = filesystem.execute({
            "action": "write",
            "path": "large.txt",
            "content": large_content,
        })
        assert not result.success
        assert "too large" in result.error.lower()

    def test_absolute_path_within_sandbox(self, filesystem, temp_dir):
        """Test that absolute paths within sandbox are allowed."""
        # Create a file first
        filesystem.execute({
            "action": "write",
            "path": "test.txt",
            "content": "test",
        })

        # Try to read with absolute path within sandbox
        absolute_path = str(temp_dir / "test.txt")
        result = filesystem.execute({
            "action": "read",
            "path": absolute_path,
        })
        assert result.success

    def test_absolute_path_outside_sandbox_blocked(self, filesystem):
        """Test that absolute paths outside sandbox are blocked."""
        # Paths outside sandbox that don't match blocked patterns should raise exception
        with pytest.raises(ToolExecutionError):
            filesystem.execute({
                "action": "read",
                "path": "/tmp/other_directory/file.txt",
            })


class TestExceptionSecurity:
    """Test that exceptions don't leak sensitive information."""

    def test_exception_truncates_input(self):
        """Test that large inputs are truncated in exceptions."""
        from gathering.core.exceptions import ToolExecutionError

        large_input = "x" * 1000
        exc = ToolExecutionError("Test error", input_data=large_input)

        # Check that input is truncated in details
        assert len(exc.details.get("input_data", "")) <= 210  # 200 + "..."

    def test_exception_to_dict(self):
        """Test exception serialization."""
        from gathering.core.exceptions import GatheringError

        exc = GatheringError("Test error", {"key": "value"})
        data = exc.to_dict()

        assert data["error_type"] == "GatheringError"
        assert data["message"] == "Test error"
        assert "timestamp" in data


class TestConfigSecurity:
    """Test configuration security."""

    def test_secret_key_not_exposed(self):
        """Test that secret keys are not exposed in string representations."""
        from gathering.core.config import Settings
        from pydantic import SecretStr

        # Create settings with a secret
        settings = Settings(
            openai_api_key=SecretStr("sk-secret-key-12345"),
        )

        # Secret should not appear in string representation
        settings_str = str(settings)
        assert "sk-secret-key-12345" not in settings_str

        # But we can still access it explicitly
        assert settings.openai_api_key.get_secret_value() == "sk-secret-key-12345"
