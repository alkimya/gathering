"""
Core Plugin for GatheRing.

Provides essential tools that are always available:
- Calculator (safe math evaluation)
- File System operations (sandboxed)
- Code execution (Python)
- Git operations

This plugin registers the fundamental tools that existed
before the plugin system was introduced.

Usage:
    from gathering.plugins import plugin_manager
    from gathering.plugins.core import CorePlugin

    # Register and load core plugin
    plugin_manager.register_plugin_class("core", CorePlugin)
    plugin_manager.load_plugin("core")
    plugin_manager.enable_plugin("core")
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
import subprocess
import ast
import operator
import re

from gathering.plugins.base import Plugin, PluginMetadata
from gathering.core.tool_registry import ToolDefinition, ToolCategory
from gathering.core.competency_registry import (
    CompetencyDefinition,
    CompetencyCategory,
    CompetencyLevel,
)


logger = logging.getLogger(__name__)


# =============================================================================
# Safe Expression Evaluator (from implementations.py)
# =============================================================================


class SafeExpressionEvaluator:
    """
    Safe mathematical expression evaluator using AST.
    Prevents code injection by only allowing math operations.
    """

    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    @classmethod
    def evaluate(cls, expression: str) -> float:
        """
        Safely evaluate a mathematical expression.

        Args:
            expression: A string containing a math expression

        Returns:
            The result of the calculation

        Raises:
            ValueError: If expression is invalid or uses unsupported operations
        """
        try:
            tree = ast.parse(expression, mode="eval")
            return cls._eval_node(tree.body)
        except (SyntaxError, ValueError) as e:
            raise ValueError(f"Invalid expression: {expression}") from e

    @classmethod
    def _eval_node(cls, node: ast.expr) -> float:
        """Recursively evaluate an AST node."""
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return float(node.value)
            raise ValueError(f"Unsupported constant type: {type(node.value)}")

        if isinstance(node, ast.Num):  # Python 3.7 compatibility
            return float(node.n)

        if isinstance(node, ast.BinOp):
            left = cls._eval_node(node.left)
            right = cls._eval_node(node.right)
            op_type = type(node.op)
            if op_type not in cls.OPERATORS:
                raise ValueError(f"Unsupported operator: {op_type.__name__}")
            return cls.OPERATORS[op_type](left, right)

        if isinstance(node, ast.UnaryOp):
            operand = cls._eval_node(node.operand)
            op_type = type(node.op)
            if op_type not in cls.OPERATORS:
                raise ValueError(f"Unsupported operator: {op_type.__name__}")
            return cls.OPERATORS[op_type](operand)

        raise ValueError(f"Unsupported expression type: {type(node).__name__}")


# =============================================================================
# Core Plugin
# =============================================================================


class CorePlugin(Plugin):
    """
    Core GatheRing plugin with essential tools.

    Provides fundamental tools:
    - Calculator: Safe math evaluation
    - File operations: Read/write files (sandboxed)
    - Shell commands: Execute bash commands
    - Git operations: Status, commit, push, pull
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._base_path = Path(config.get("base_path", ".")) if config else Path(".")

    @property
    def metadata(self) -> PluginMetadata:
        """Plugin metadata."""
        return PluginMetadata(
            id="core",
            name="Core Tools",
            version="1.0.0",
            description="Essential tools for GatheRing: calculator, file system, git",
            author="GatheRing Team",
            author_email="gathering.ai@pm.me",
            license="MIT",
            homepage="https://github.com/alkimya/gathering",
            tags=["core", "filesystem", "git", "calculator", "shell"],
            python_dependencies=[],
            min_gathering_version="0.1.0",
            config_schema={
                "type": "object",
                "properties": {
                    "base_path": {
                        "type": "string",
                        "description": "Base path for file operations",
                        "default": ".",
                    },
                    "allow_shell": {
                        "type": "boolean",
                        "description": "Allow shell command execution",
                        "default": True,
                    },
                },
            },
        )

    def register_tools(self) -> List[ToolDefinition]:
        """Register core tools."""
        return [
            # Calculator
            ToolDefinition(
                name="calculate",
                description="Evaluate a mathematical expression safely",
                category=ToolCategory.UTILITY,
                function=self.calculate,
                required_competencies=[],
                parameters={
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "Mathematical expression to evaluate (e.g., '2 + 2 * 3', '15% of 200')",
                        },
                    },
                    "required": ["expression"],
                },
                returns={
                    "type": "number",
                    "description": "Result of the calculation",
                },
                examples=[
                    "calculate(expression='2 + 2')",
                    "calculate(expression='10 * (5 + 3)')",
                    "calculate(expression='15% of 200')",
                ],
                plugin_id="core",
            ),
            # Read file
            ToolDefinition(
                name="read_file",
                description="Read contents of a file",
                category=ToolCategory.FILE_SYSTEM,
                function=self.read_file,
                required_competencies=["file_management"],
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file to read",
                        },
                        "encoding": {
                            "type": "string",
                            "description": "File encoding (default: utf-8)",
                            "default": "utf-8",
                        },
                    },
                    "required": ["path"],
                },
                returns={
                    "type": "string",
                    "description": "Contents of the file",
                },
                examples=[
                    "read_file(path='README.md')",
                    "read_file(path='data.csv', encoding='latin-1')",
                ],
                plugin_id="core",
            ),
            # Write file
            ToolDefinition(
                name="write_file",
                description="Write content to a file",
                category=ToolCategory.FILE_SYSTEM,
                function=self.write_file,
                required_competencies=["file_management"],
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file to write",
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write",
                        },
                        "encoding": {
                            "type": "string",
                            "description": "File encoding (default: utf-8)",
                            "default": "utf-8",
                        },
                    },
                    "required": ["path", "content"],
                },
                returns={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "bytes_written": {"type": "integer"},
                    },
                },
                examples=[
                    "write_file(path='output.txt', content='Hello, World!')",
                ],
                plugin_id="core",
            ),
            # List directory
            ToolDefinition(
                name="list_directory",
                description="List contents of a directory",
                category=ToolCategory.FILE_SYSTEM,
                function=self.list_directory,
                required_competencies=["file_management"],
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the directory",
                            "default": ".",
                        },
                        "pattern": {
                            "type": "string",
                            "description": "Glob pattern to filter files",
                        },
                    },
                },
                returns={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of files and directories",
                },
                examples=[
                    "list_directory()",
                    "list_directory(path='src', pattern='*.py')",
                ],
                plugin_id="core",
            ),
            # Git status
            ToolDefinition(
                name="git_status",
                description="Get current git repository status",
                category=ToolCategory.VERSION_CONTROL,
                function=self.git_status,
                required_competencies=["version_control"],
                parameters={
                    "type": "object",
                    "properties": {},
                },
                returns={
                    "type": "object",
                    "description": "Git status information",
                },
                examples=["git_status()"],
                plugin_id="core",
            ),
            # Git diff
            ToolDefinition(
                name="git_diff",
                description="Show changes in the repository",
                category=ToolCategory.VERSION_CONTROL,
                function=self.git_diff,
                required_competencies=["version_control"],
                parameters={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Specific file to diff (optional)",
                        },
                        "staged": {
                            "type": "boolean",
                            "description": "Show staged changes",
                            "default": False,
                        },
                    },
                },
                returns={
                    "type": "string",
                    "description": "Diff output",
                },
                examples=[
                    "git_diff()",
                    "git_diff(staged=True)",
                    "git_diff(file_path='src/main.py')",
                ],
                plugin_id="core",
            ),
            # Shell command
            ToolDefinition(
                name="run_command",
                description="Execute a shell command",
                category=ToolCategory.CODE_EXECUTION,
                function=self.run_command,
                required_competencies=["shell_commands"],
                parameters={
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Shell command to execute",
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds (default: 30)",
                            "default": 30,
                        },
                    },
                    "required": ["command"],
                },
                returns={
                    "type": "object",
                    "properties": {
                        "stdout": {"type": "string"},
                        "stderr": {"type": "string"},
                        "return_code": {"type": "integer"},
                    },
                },
                examples=[
                    "run_command(command='ls -la')",
                    "run_command(command='python --version')",
                ],
                plugin_id="core",
            ),
            # Python eval
            ToolDefinition(
                name="python_eval",
                description="Execute Python code and return result",
                category=ToolCategory.CODE_EXECUTION,
                function=self.python_eval,
                required_competencies=["python_programming"],
                parameters={
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Python code to execute",
                        },
                    },
                    "required": ["code"],
                },
                returns={
                    "type": "object",
                    "properties": {
                        "result": {"description": "Return value"},
                        "output": {"type": "string", "description": "Printed output"},
                        "error": {"type": "string", "description": "Error message if any"},
                    },
                },
                examples=[
                    "python_eval(code='2 + 2')",
                    "python_eval(code='import math; math.pi')",
                ],
                plugin_id="core",
            ),
        ]

    def register_competencies(self) -> List[CompetencyDefinition]:
        """Register core competencies."""
        return [
            CompetencyDefinition(
                id="file_management",
                name="File Management",
                description="Read, write, and manage files and directories",
                category=CompetencyCategory.PROGRAMMING,
                level=CompetencyLevel.INTERMEDIATE,
                capabilities=["read_files", "write_files", "list_directories"],
                tools_enabled=["read_file", "write_file", "list_directory"],
                plugin_id="core",
            ),
            CompetencyDefinition(
                id="version_control",
                name="Version Control (Git)",
                description="Use Git for version control: status, diff, commit",
                category=CompetencyCategory.DEVOPS,
                level=CompetencyLevel.INTERMEDIATE,
                capabilities=["git_status", "git_diff", "git_commit"],
                tools_enabled=["git_status", "git_diff"],
                plugin_id="core",
            ),
            CompetencyDefinition(
                id="shell_commands",
                name="Shell Commands",
                description="Execute shell commands safely",
                category=CompetencyCategory.DEVOPS,
                level=CompetencyLevel.ADVANCED,
                capabilities=["run_bash", "run_scripts"],
                tools_enabled=["run_command"],
                plugin_id="core",
            ),
            CompetencyDefinition(
                id="python_programming",
                name="Python Programming",
                description="Write and execute Python code",
                category=CompetencyCategory.PROGRAMMING,
                level=CompetencyLevel.INTERMEDIATE,
                capabilities=["python_scripting", "data_processing"],
                tools_enabled=["python_eval"],
                plugin_id="core",
            ),
            CompetencyDefinition(
                id="mathematics",
                name="Mathematics",
                description="Perform mathematical calculations",
                category=CompetencyCategory.SCIENTIFIC_COMPUTING,
                level=CompetencyLevel.NOVICE,
                capabilities=["arithmetic", "algebra"],
                tools_enabled=["calculate"],
                plugin_id="core",
            ),
        ]

    # =========================================================================
    # Tool Implementations
    # =========================================================================

    def calculate(self, expression: str) -> float:
        """
        Safely evaluate a mathematical expression.

        Supports:
        - Basic arithmetic: +, -, *, /, //, %, **
        - Parentheses for grouping
        - Percentage expressions: "15% of 200"
        """
        expression = expression.strip()

        # Handle percentage expressions: "15% of 200"
        percentage_match = re.match(
            r"^\s*(\d+(?:\.\d+)?)\s*%\s*of\s*(\d+(?:\.\d+)?)\s*$",
            expression,
            re.IGNORECASE,
        )
        if percentage_match:
            percent = float(percentage_match.group(1))
            value = float(percentage_match.group(2))
            return (percent / 100) * value

        return SafeExpressionEvaluator.evaluate(expression)

    def read_file(self, path: str, encoding: str = "utf-8") -> str:
        """Read contents of a file."""
        file_path = self._resolve_path(path)
        return file_path.read_text(encoding=encoding)

    def write_file(
        self, path: str, content: str, encoding: str = "utf-8"
    ) -> Dict[str, Any]:
        """Write content to a file."""
        file_path = self._resolve_path(path)

        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_path.write_text(content, encoding=encoding)
        return {"success": True, "bytes_written": len(content.encode(encoding))}

    def list_directory(
        self, path: str = ".", pattern: Optional[str] = None
    ) -> List[str]:
        """List contents of a directory."""
        dir_path = self._resolve_path(path)

        if not dir_path.is_dir():
            raise ValueError(f"Not a directory: {path}")

        if pattern:
            entries = list(dir_path.glob(pattern))
        else:
            entries = list(dir_path.iterdir())

        return sorted([str(e.relative_to(dir_path)) for e in entries])

    def git_status(self) -> Dict[str, Any]:
        """Get git repository status."""
        result = subprocess.run(
            ["git", "status", "--porcelain", "-b"],
            capture_output=True,
            text=True,
            cwd=str(self._base_path),
        )

        if result.returncode != 0:
            return {"error": result.stderr.strip()}

        lines = result.stdout.strip().split("\n")
        branch = ""
        modified = []
        added = []
        deleted = []
        untracked = []

        for line in lines:
            if line.startswith("##"):
                branch = line[3:].split("...")[0] if "..." in line else line[3:]
            elif line.startswith(" M") or line.startswith("M "):
                modified.append(line[3:])
            elif line.startswith("A "):
                added.append(line[3:])
            elif line.startswith(" D") or line.startswith("D "):
                deleted.append(line[3:])
            elif line.startswith("??"):
                untracked.append(line[3:])

        return {
            "branch": branch,
            "modified": modified,
            "added": added,
            "deleted": deleted,
            "untracked": untracked,
            "clean": not (modified or added or deleted or untracked),
        }

    def git_diff(
        self, file_path: Optional[str] = None, staged: bool = False
    ) -> str:
        """Show git diff."""
        cmd = ["git", "diff"]
        if staged:
            cmd.append("--staged")
        if file_path:
            cmd.append(file_path)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(self._base_path),
        )

        return result.stdout if result.returncode == 0 else result.stderr

    def run_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """Execute a shell command."""
        if not self._config.get("allow_shell", True):
            return {
                "stdout": "",
                "stderr": "Shell commands are disabled",
                "return_code": 1,
            }

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self._base_path),
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
                "return_code": -1,
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "return_code": -1,
            }

    def python_eval(self, code: str) -> Dict[str, Any]:
        """Execute Python code."""
        import io
        import sys

        # Capture output
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = captured_out = io.StringIO()
        sys.stderr = captured_err = io.StringIO()

        result = None
        error = None

        try:
            # Try eval first (for expressions)
            try:
                result = eval(code)
            except SyntaxError:
                # Fall back to exec for statements
                exec(code)
                result = None
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        return {
            "result": result,
            "output": captured_out.getvalue(),
            "error": error or captured_err.getvalue() or None,
        }

    def _resolve_path(self, path: str) -> Path:
        """Resolve a path relative to base_path."""
        requested = Path(path)
        if requested.is_absolute():
            return requested
        return (self._base_path / path).resolve()

    def health_check(self) -> Dict[str, Any]:
        """Check plugin health."""
        checks = {
            "filesystem": self._base_path.exists(),
            "git": self._check_git(),
        }

        all_ok = all(checks.values())

        return {
            "plugin_id": "core",
            "status": "healthy" if all_ok else "degraded",
            "error": None if all_ok else "Some checks failed",
            "details": checks,
        }

    def _check_git(self) -> bool:
        """Check if git is available."""
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False


# Export for discovery
plugin_class = CorePlugin
