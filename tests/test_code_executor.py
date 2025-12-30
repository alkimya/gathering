"""
Tests for Code Executor skill.
Tests the sandboxed code execution with security controls.
"""

import pytest
from gathering.skills.code.executor import CodeExecutionSkill, CodeConfig


class TestCodeExecutorSafety:
    """Tests for code execution safety features."""

    @pytest.fixture
    def executor(self):
        """Create a code executor instance."""
        return CodeExecutionSkill()

    def test_eval_simple_math(self, executor):
        """Test evaluating simple math expressions."""
        result = executor._eval_python("2 + 3 * 4")
        assert result["success"] is True
        assert result["result"] == 14

    def test_eval_math_functions(self, executor):
        """Test evaluating math functions."""
        result = executor._eval_python("sqrt(16) + abs(-5)")
        assert result["success"] is True
        assert result["result"] == 9.0

    def test_eval_comparison(self, executor):
        """Test evaluating comparisons."""
        result = executor._eval_python("5 > 3")
        assert result["success"] is True
        assert result["result"] is True

    def test_eval_list(self, executor):
        """Test evaluating list expressions."""
        result = executor._eval_python("[1, 2, 3, 4]")
        assert result["success"] is True
        assert result["result"] == [1, 2, 3, 4]

    def test_eval_dict(self, executor):
        """Test evaluating dict expressions."""
        result = executor._eval_python("{'a': 1, 'b': 2}")
        assert result["success"] is True
        assert result["result"] == {'a': 1, 'b': 2}

    def test_eval_conditional(self, executor):
        """Test evaluating conditional expressions."""
        result = executor._eval_python("'yes' if 5 > 3 else 'no'")
        assert result["success"] is True
        assert result["result"] == "yes"

    def test_eval_function_calls(self, executor):
        """Test evaluating allowed function calls."""
        result = executor._eval_python("len([1, 2, 3])")
        assert result["success"] is True
        assert result["result"] == 3

    def test_eval_nested_expression(self, executor):
        """Test evaluating nested expressions."""
        result = executor._eval_python("sum([1, 2, 3]) * max(2, 5)")
        assert result["success"] is True
        assert result["result"] == 30

    def test_eval_blocks_import(self, executor):
        """Test that import statements are blocked."""
        result = executor._eval_python("__import__('os')")
        assert result["success"] is False
        assert "not allowed" in result["error"].lower()

    def test_eval_blocks_exec(self, executor):
        """Test that exec is blocked."""
        result = executor._eval_python("exec('print(1)')")
        assert result["success"] is False

    def test_eval_blocks_eval(self, executor):
        """Test that eval is blocked."""
        result = executor._eval_python("eval('1+1')")
        assert result["success"] is False

    def test_eval_blocks_open(self, executor):
        """Test that file operations are blocked."""
        result = executor._eval_python("open('/etc/passwd')")
        assert result["success"] is False

    def test_eval_blocks_dunder(self, executor):
        """Test that dunder methods are blocked."""
        result = executor._eval_python("().__class__.__bases__[0]")
        assert result["success"] is False

    def test_eval_blocks_arbitrary_names(self, executor):
        """Test that arbitrary variable names are blocked."""
        result = executor._eval_python("os.system('ls')")
        assert result["success"] is False
        assert "not allowed" in result["error"].lower()

    def test_eval_syntax_error(self, executor):
        """Test handling of syntax errors."""
        result = executor._eval_python("2 + * 3")  # Invalid syntax
        assert result["success"] is False
        assert "syntax" in result["error"].lower()

    def test_eval_pi_constant(self, executor):
        """Test accessing pi constant."""
        result = executor._eval_python("pi")
        assert result["success"] is True
        assert abs(result["result"] - 3.14159) < 0.001

    def test_eval_boolean_logic(self, executor):
        """Test boolean logic operations."""
        result = executor._eval_python("True and not False")
        assert result["success"] is True
        assert result["result"] is True

    def test_eval_subscript(self, executor):
        """Test subscript operations."""
        result = executor._eval_python("[1, 2, 3, 4][1]")
        assert result["success"] is True
        assert result["result"] == 2

    def test_eval_slice(self, executor):
        """Test slice operations."""
        result = executor._eval_python("[1, 2, 3, 4][1:3]")
        assert result["success"] is True
        assert result["result"] == [2, 3]


class TestCodeExecutorPythonExecution:
    """Tests for Python code execution."""

    @pytest.fixture
    def executor(self):
        """Create a code executor instance."""
        config = CodeConfig(timeout=5)
        return CodeExecutionSkill(config)

    def test_check_imports_allows_safe(self, executor):
        """Test that safe imports are allowed."""
        code = "import math\nprint(math.pi)"
        is_safe, error = executor._check_python_imports(code)
        assert is_safe is True

    def test_check_imports_blocks_subprocess(self, executor):
        """Test that subprocess import is blocked."""
        code = "import subprocess\nsubprocess.run(['ls'])"
        is_safe, error = executor._check_python_imports(code)
        assert is_safe is False
        assert "subprocess" in error

    def test_check_imports_blocks_os_system(self, executor):
        """Test that os.system is detected as dangerous."""
        code = "import os\nos.system('ls')"
        is_safe, error = executor._check_python_imports(code)
        # os is blocked at module level
        assert is_safe is False

    def test_check_imports_blocks_socket(self, executor):
        """Test that socket import is blocked."""
        code = "import socket"
        is_safe, error = executor._check_python_imports(code)
        assert is_safe is False

    def test_check_imports_blocks_exec_call(self, executor):
        """Test that exec() calls are blocked."""
        code = "exec('print(1)')"
        is_safe, error = executor._check_python_imports(code)
        assert is_safe is False
        assert "exec" in error

    def test_check_imports_blocks_eval_call(self, executor):
        """Test that eval() calls are blocked."""
        code = "result = eval('1+1')"
        is_safe, error = executor._check_python_imports(code)
        assert is_safe is False
        assert "eval" in error

    def test_check_imports_syntax_error(self, executor):
        """Test handling of syntax errors in import check."""
        code = "def broken("
        is_safe, error = executor._check_python_imports(code)
        assert is_safe is False
        assert "syntax" in error.lower()


class TestCodeExecutorToolDefinitions:
    """Tests for tool definitions."""

    @pytest.fixture
    def executor(self):
        """Create a code executor instance."""
        return CodeExecutionSkill()

    def test_tools_defined(self, executor):
        """Test that tools are defined."""
        tools = executor.get_tools_definition()
        assert len(tools) > 0

    def test_python_exec_tool_exists(self, executor):
        """Test that python_exec tool exists."""
        tools = executor.get_tools_definition()
        tool_names = [t["name"] for t in tools]
        assert "python_exec" in tool_names

    def test_python_eval_tool_exists(self, executor):
        """Test that python_eval tool exists."""
        tools = executor.get_tools_definition()
        tool_names = [t["name"] for t in tools]
        assert "python_eval" in tool_names

    def test_code_analyze_tool_exists(self, executor):
        """Test that code_analyze tool exists."""
        tools = executor.get_tools_definition()
        tool_names = [t["name"] for t in tools]
        assert "code_analyze" in tool_names

    def test_tool_has_required_fields(self, executor):
        """Test that tools have required fields."""
        tools = executor.get_tools_definition()
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool


class TestCodeConfig:
    """Tests for CodeConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CodeConfig()
        assert config.timeout == 30
        assert config.max_output_size == 100 * 1024
        assert config.max_memory_mb == 256
        assert "python" in config.allowed_languages
        assert "subprocess" in config.blocked_imports

    def test_custom_config(self):
        """Test custom configuration."""
        config = CodeConfig(timeout=10, max_memory_mb=128)
        assert config.timeout == 10
        assert config.max_memory_mb == 128

    def test_blocked_imports_default(self):
        """Test default blocked imports list."""
        config = CodeConfig()
        dangerous = ["subprocess", "socket", "ctypes"]
        for module in dangerous:
            assert any(module in blocked for blocked in config.blocked_imports)
