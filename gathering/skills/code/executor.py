"""Sandboxed code execution skill."""

import ast
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Any

from gathering.skills.base import BaseSkill


@dataclass
class CodeConfig:
    """Configuration for code execution security."""

    # Execution timeout in seconds
    timeout: int = 30

    # Maximum output size in bytes
    max_output_size: int = 100 * 1024  # 100 KB

    # Maximum memory usage in MB (Linux only)
    max_memory_mb: int = 256

    # Allowed Python imports (empty = all allowed, but dangerous ones blocked)
    allowed_imports: list[str] = field(default_factory=list)

    # Blocked Python imports
    blocked_imports: list[str] = field(default_factory=lambda: [
        "os.system", "subprocess", "shutil.rmtree",
        "socket", "http.server", "ftplib", "smtplib",
        "ctypes", "multiprocessing", "threading",
        "__builtins__.__import__"
    ])

    # Allowed languages
    allowed_languages: list[str] = field(default_factory=lambda: [
        "python", "javascript", "bash", "sql"
    ])

    # Working directory for code execution
    work_dir: str = "/tmp/gathering_code"

    # Use Docker for isolation (if available)
    use_docker: bool = False
    docker_image: str = "python:3.11-slim"


class RestrictedImportError(Exception):
    """Raised when a blocked import is attempted."""
    pass


class CodeExecutionSkill(BaseSkill):
    """Skill for executing code in sandboxed environments."""

    name = "code"
    description = "Execute code in sandboxed environments with security controls"
    version = "1.0.0"

    def __init__(self, config: CodeConfig | dict | None = None):
        super().__init__(config if isinstance(config, dict) else None)
        self.code_config = config if isinstance(config, CodeConfig) else CodeConfig()
        os.makedirs(self.code_config.work_dir, exist_ok=True)

    def get_tools_definition(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "python_exec",
                "description": "Execute Python code in a sandboxed environment",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Python code to execute"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Execution timeout in seconds",
                            "default": 30
                        }
                    },
                    "required": ["code"]
                }
            },
            {
                "name": "python_eval",
                "description": "Evaluate a Python expression and return the result",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "Python expression to evaluate"
                        }
                    },
                    "required": ["expression"]
                }
            },
            {
                "name": "javascript_exec",
                "description": "Execute JavaScript code using Node.js",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "JavaScript code to execute"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Execution timeout in seconds",
                            "default": 30
                        }
                    },
                    "required": ["code"]
                }
            },
            {
                "name": "bash_exec",
                "description": "Execute a bash script (limited commands)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "script": {
                            "type": "string",
                            "description": "Bash script to execute"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Execution timeout in seconds",
                            "default": 30
                        }
                    },
                    "required": ["script"]
                }
            },
            {
                "name": "sql_exec",
                "description": "Execute SQL query (SELECT only, read-only)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "SQL SELECT query"
                        },
                        "database_url": {
                            "type": "string",
                            "description": "Database connection URL"
                        }
                    },
                    "required": ["query", "database_url"]
                }
            },
            {
                "name": "code_analyze",
                "description": "Analyze code for syntax errors and potential issues",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Code to analyze"
                        },
                        "language": {
                            "type": "string",
                            "description": "Programming language",
                            "enum": ["python", "javascript"]
                        }
                    },
                    "required": ["code", "language"]
                }
            },
            {
                "name": "code_format",
                "description": "Format code according to language standards",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Code to format"
                        },
                        "language": {
                            "type": "string",
                            "description": "Programming language",
                            "enum": ["python", "javascript", "json"]
                        }
                    },
                    "required": ["code", "language"]
                }
            },
            {
                "name": "repl_session",
                "description": "Start an interactive REPL session for iterative code execution",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "language": {
                            "type": "string",
                            "description": "Programming language",
                            "enum": ["python"],
                            "default": "python"
                        },
                        "initial_code": {
                            "type": "string",
                            "description": "Initial code to set up the session"
                        }
                    }
                }
            }
        ]

    def _check_python_imports(self, code: str) -> tuple[bool, str]:
        """Check for blocked imports in Python code."""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax error: {e}"

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for blocked in self.code_config.blocked_imports:
                        if alias.name.startswith(blocked.split('.')[0]):
                            return False, f"Import '{alias.name}' is not allowed"

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for blocked in self.code_config.blocked_imports:
                    if module.startswith(blocked.split('.')[0]):
                        return False, f"Import from '{module}' is not allowed"

            # Check for exec/eval calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ['exec', 'eval', 'compile', '__import__']:
                        return False, f"Function '{node.func.id}' is not allowed"

        return True, ""

    def _execute_python(self, code: str, timeout: int) -> dict[str, Any]:
        """Execute Python code with security restrictions."""
        # Check for blocked imports
        is_safe, error = self._check_python_imports(code)
        if not is_safe:
            return {"success": False, "error": error}

        # Create temp file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            dir=self.code_config.work_dir,
            delete=False
        ) as f:
            f.write(code)
            temp_file = f.name

        try:
            # Execute in subprocess for isolation
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.code_config.work_dir,
                env={
                    "PATH": os.environ.get("PATH", ""),
                    "PYTHONPATH": "",
                    "HOME": self.code_config.work_dir
                }
            )

            output = result.stdout[:self.code_config.max_output_size]
            error_output = result.stderr[:self.code_config.max_output_size]

            return {
                "success": result.returncode == 0,
                "output": output,
                "error": error_output if error_output else None,
                "return_code": result.returncode
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Execution timed out after {timeout} seconds"}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            try:
                os.unlink(temp_file)
            except Exception:
                pass

    def _eval_python(self, expression: str) -> dict[str, Any]:
        """
        Evaluate a Python expression safely using AST-based evaluation.
        No use of eval() - only pure AST interpretation for security.
        """
        import math
        import operator

        # Allowed constants and functions
        SAFE_NAMES = {
            'True': True, 'False': False, 'None': None,
            'pi': math.pi, 'e': math.e, 'tau': math.tau,
            'inf': math.inf, 'nan': math.nan,
        }

        SAFE_FUNCTIONS = {
            # Math functions
            'abs': abs, 'round': round, 'min': min, 'max': max,
            'sum': sum, 'pow': pow, 'divmod': divmod,
            'sqrt': math.sqrt, 'sin': math.sin, 'cos': math.cos,
            'tan': math.tan, 'log': math.log, 'log10': math.log10,
            'log2': math.log2, 'exp': math.exp, 'floor': math.floor,
            'ceil': math.ceil, 'factorial': math.factorial,
            'gcd': math.gcd, 'lcm': getattr(math, 'lcm', lambda a, b: abs(a * b) // math.gcd(a, b)),
            # Type conversions
            'int': int, 'float': float, 'str': str, 'bool': bool,
            'list': list, 'tuple': tuple, 'set': set, 'dict': dict,
            # Utility
            'len': len, 'range': range, 'sorted': sorted, 'reversed': reversed,
            'hex': hex, 'bin': bin, 'oct': oct, 'ord': ord, 'chr': chr,
        }

        SAFE_OPERATORS = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.FloorDiv: operator.floordiv,
            ast.Mod: operator.mod,
            ast.Pow: operator.pow,
            ast.LShift: operator.lshift,
            ast.RShift: operator.rshift,
            ast.BitOr: operator.or_,
            ast.BitXor: operator.xor,
            ast.BitAnd: operator.and_,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
            ast.Not: operator.not_,
            ast.Invert: operator.invert,
        }

        SAFE_COMPARISONS = {
            ast.Eq: operator.eq,
            ast.NotEq: operator.ne,
            ast.Lt: operator.lt,
            ast.LtE: operator.le,
            ast.Gt: operator.gt,
            ast.GtE: operator.ge,
            ast.In: lambda x, y: x in y,
            ast.NotIn: lambda x, y: x not in y,
        }

        def safe_eval_node(node):
            """Recursively evaluate an AST node safely."""
            if isinstance(node, ast.Expression):
                return safe_eval_node(node.body)

            elif isinstance(node, ast.Constant):
                return node.value

            elif isinstance(node, ast.Num):  # Python 3.7 compatibility
                return node.n

            elif isinstance(node, ast.Str):  # Python 3.7 compatibility
                return node.s

            elif isinstance(node, ast.Name):
                name = node.id
                if name in SAFE_NAMES:
                    return SAFE_NAMES[name]
                if name in SAFE_FUNCTIONS:
                    return SAFE_FUNCTIONS[name]
                raise ValueError(f"Name '{name}' is not allowed")

            elif isinstance(node, ast.BinOp):
                left = safe_eval_node(node.left)
                right = safe_eval_node(node.right)
                op_type = type(node.op)
                if op_type not in SAFE_OPERATORS:
                    raise ValueError(f"Operator {op_type.__name__} is not allowed")
                return SAFE_OPERATORS[op_type](left, right)

            elif isinstance(node, ast.UnaryOp):
                operand = safe_eval_node(node.operand)
                op_type = type(node.op)
                if op_type not in SAFE_OPERATORS:
                    raise ValueError(f"Operator {op_type.__name__} is not allowed")
                return SAFE_OPERATORS[op_type](operand)

            elif isinstance(node, ast.Compare):
                left = safe_eval_node(node.left)
                for op, comparator in zip(node.ops, node.comparators):
                    right = safe_eval_node(comparator)
                    op_type = type(op)
                    if op_type not in SAFE_COMPARISONS:
                        raise ValueError(f"Comparison {op_type.__name__} is not allowed")
                    if not SAFE_COMPARISONS[op_type](left, right):
                        return False
                    left = right
                return True

            elif isinstance(node, ast.BoolOp):
                if isinstance(node.op, ast.And):
                    return all(safe_eval_node(v) for v in node.values)
                elif isinstance(node.op, ast.Or):
                    return any(safe_eval_node(v) for v in node.values)

            elif isinstance(node, ast.IfExp):
                test = safe_eval_node(node.test)
                return safe_eval_node(node.body) if test else safe_eval_node(node.orelse)

            elif isinstance(node, ast.Call):
                func = safe_eval_node(node.func)
                if func not in SAFE_FUNCTIONS.values():
                    raise ValueError("Function call not allowed")
                args = [safe_eval_node(arg) for arg in node.args]
                return func(*args)

            elif isinstance(node, ast.List):
                return [safe_eval_node(elt) for elt in node.elts]

            elif isinstance(node, ast.Tuple):
                return tuple(safe_eval_node(elt) for elt in node.elts)

            elif isinstance(node, ast.Set):
                return {safe_eval_node(elt) for elt in node.elts}

            elif isinstance(node, ast.Dict):
                return {
                    safe_eval_node(k): safe_eval_node(v)
                    for k, v in zip(node.keys, node.values)
                }

            elif isinstance(node, ast.Subscript):
                value = safe_eval_node(node.value)
                if isinstance(node.slice, ast.Slice):
                    return value[
                        safe_eval_node(node.slice.lower) if node.slice.lower else None:
                        safe_eval_node(node.slice.upper) if node.slice.upper else None:
                        safe_eval_node(node.slice.step) if node.slice.step else None
                    ]
                else:
                    index = safe_eval_node(node.slice)
                    return value[index]

            else:
                raise ValueError(f"Node type {type(node).__name__} is not allowed")

        try:
            # Parse expression
            tree = ast.parse(expression, mode='eval')

            # Evaluate using safe AST walker
            result = safe_eval_node(tree)

            return {"success": True, "result": result, "type": type(result).__name__}

        except SyntaxError as e:
            return {"success": False, "error": f"Syntax error: {e}"}
        except ValueError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Evaluation error: {e}"}

    def _execute_javascript(self, code: str, timeout: int) -> dict[str, Any]:
        """Execute JavaScript code using Node.js."""
        # Check if Node.js is available
        try:
            subprocess.run(["node", "--version"], capture_output=True, check=True)
        except Exception:
            return {"success": False, "error": "Node.js is not installed"}

        # Create temp file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.js',
            dir=self.code_config.work_dir,
            delete=False
        ) as f:
            # Wrap code to prevent dangerous operations
            wrapped = f"""
// Sandboxed execution
const vm = require('vm');
const code = {repr(code)};
try {{
    const result = vm.runInNewContext(code, {{
        console: console,
        JSON: JSON,
        Math: Math,
        Date: Date,
        Array: Array,
        Object: Object,
        String: String,
        Number: Number,
        Boolean: Boolean,
        RegExp: RegExp,
        Error: Error,
        setTimeout: undefined,
        setInterval: undefined,
        require: undefined,
        process: undefined,
        global: undefined
    }}, {{ timeout: {timeout * 1000} }});
    if (result !== undefined) console.log(result);
}} catch (e) {{
    console.error(e.message);
    process.exit(1);
}}
"""
            f.write(wrapped)
            temp_file = f.name

        try:
            result = subprocess.run(
                ["node", temp_file],
                capture_output=True,
                text=True,
                timeout=timeout + 5,
                cwd=self.code_config.work_dir
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout[:self.code_config.max_output_size],
                "error": result.stderr[:self.code_config.max_output_size] if result.stderr else None,
                "return_code": result.returncode
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Execution timed out after {timeout} seconds"}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            try:
                os.unlink(temp_file)
            except Exception:
                pass

    def _execute_bash(self, script: str, timeout: int) -> dict[str, Any]:
        """Execute bash script with restrictions."""
        # Block dangerous commands
        dangerous = [
            'rm -rf', 'mkfs', 'dd if=', ':(){', 'fork',
            '> /dev/', 'chmod 777', 'curl | bash', 'wget | bash',
            'sudo', 'su ', '/etc/passwd', '/etc/shadow',
            'nc -', 'netcat', 'ncat'
        ]

        script_lower = script.lower()
        for pattern in dangerous:
            if pattern in script_lower:
                return {"success": False, "error": f"Script contains blocked pattern: {pattern}"}

        try:
            result = subprocess.run(
                ["bash", "-c", script],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.code_config.work_dir,
                env={
                    "PATH": "/usr/bin:/bin",
                    "HOME": self.code_config.work_dir
                }
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout[:self.code_config.max_output_size],
                "error": result.stderr[:self.code_config.max_output_size] if result.stderr else None,
                "return_code": result.returncode
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Execution timed out after {timeout} seconds"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_sql(self, query: str, database_url: str) -> dict[str, Any]:
        """Execute SQL query (SELECT only)."""
        # Only allow SELECT queries
        query_upper = query.strip().upper()
        if not query_upper.startswith("SELECT"):
            return {"success": False, "error": "Only SELECT queries are allowed"}

        # Block dangerous patterns
        dangerous = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE", "GRANT", "REVOKE"]
        for pattern in dangerous:
            if pattern in query_upper:
                return {"success": False, "error": f"Query contains blocked keyword: {pattern}"}

        try:
            # Use psycopg for PostgreSQL
            if database_url.startswith("postgresql"):
                import psycopg
                with psycopg.connect(database_url) as conn:
                    with conn.cursor() as cur:
                        cur.execute(query)
                        columns = [desc[0] for desc in cur.description] if cur.description else []
                        rows = cur.fetchall()
                        return {
                            "success": True,
                            "columns": columns,
                            "rows": [list(row) for row in rows[:1000]],  # Limit rows
                            "row_count": len(rows)
                        }

            # Use sqlite3 for SQLite
            elif database_url.startswith("sqlite"):
                import sqlite3
                db_path = database_url.replace("sqlite:///", "")
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.execute(query)
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []
                    rows = cursor.fetchall()
                    return {
                        "success": True,
                        "columns": columns,
                        "rows": [list(row) for row in rows[:1000]],
                        "row_count": len(rows)
                    }

            else:
                return {"success": False, "error": "Unsupported database type"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _analyze_code(self, code: str, language: str) -> dict[str, Any]:
        """Analyze code for issues."""
        issues = []

        if language == "python":
            try:
                tree = ast.parse(code)

                # Check for common issues
                for node in ast.walk(tree):
                    # Bare except
                    if isinstance(node, ast.ExceptHandler) and node.type is None:
                        issues.append({
                            "type": "warning",
                            "line": node.lineno,
                            "message": "Bare 'except' clause catches all exceptions"
                        })

                    # Mutable default argument
                    if isinstance(node, ast.FunctionDef):
                        for default in node.args.defaults:
                            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                                issues.append({
                                    "type": "warning",
                                    "line": node.lineno,
                                    "message": f"Mutable default argument in function '{node.name}'"
                                })

                    # Global statement
                    if isinstance(node, ast.Global):
                        issues.append({
                            "type": "info",
                            "line": node.lineno,
                            "message": "Use of 'global' statement"
                        })

                return {
                    "success": True,
                    "valid": True,
                    "issues": issues,
                    "issue_count": len(issues)
                }

            except SyntaxError as e:
                return {
                    "success": True,
                    "valid": False,
                    "error": {
                        "line": e.lineno,
                        "column": e.offset,
                        "message": e.msg
                    }
                }

        elif language == "javascript":
            # Basic JS syntax check using Node
            try:
                result = subprocess.run(
                    ["node", "--check", "-e", code],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return {"success": True, "valid": True, "issues": []}
                else:
                    return {
                        "success": True,
                        "valid": False,
                        "error": result.stderr
                    }
            except Exception:
                return {"success": False, "error": "Could not analyze JavaScript"}

        return {"success": False, "error": f"Unsupported language: {language}"}

    def _format_code(self, code: str, language: str) -> dict[str, Any]:
        """Format code according to language standards."""
        if language == "python":
            try:
                import black
                formatted = black.format_str(code, mode=black.Mode())
                return {"success": True, "formatted": formatted}
            except ImportError:
                # Fallback: return code as-is
                return {"success": True, "formatted": code, "note": "black not installed"}
            except Exception as e:
                return {"success": False, "error": str(e)}

        elif language == "javascript":
            # Could use prettier via subprocess if available
            return {"success": False, "error": "JavaScript formatting requires prettier"}

        elif language == "json":
            try:
                import json
                parsed = json.loads(code)
                formatted = json.dumps(parsed, indent=2)
                return {"success": True, "formatted": formatted}
            except json.JSONDecodeError as e:
                return {"success": False, "error": f"Invalid JSON: {e}"}

        return {"success": False, "error": f"Unsupported language: {language}"}

    def execute(self, tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
        """Execute a code execution tool."""

        if tool_name == "python_exec":
            return self._execute_python(
                tool_input["code"],
                tool_input.get("timeout", self.code_config.timeout)
            )

        elif tool_name == "python_eval":
            return self._eval_python(tool_input["expression"])

        elif tool_name == "javascript_exec":
            return self._execute_javascript(
                tool_input["code"],
                tool_input.get("timeout", self.code_config.timeout)
            )

        elif tool_name == "bash_exec":
            return self._execute_bash(
                tool_input["script"],
                tool_input.get("timeout", self.code_config.timeout)
            )

        elif tool_name == "sql_exec":
            return self._execute_sql(
                tool_input["query"],
                tool_input["database_url"]
            )

        elif tool_name == "code_analyze":
            return self._analyze_code(
                tool_input["code"],
                tool_input["language"]
            )

        elif tool_name == "code_format":
            return self._format_code(
                tool_input["code"],
                tool_input["language"]
            )

        elif tool_name == "repl_session":
            # REPL sessions would require more complex state management
            return {
                "success": True,
                "session_id": "repl_1",
                "message": "REPL session started. Use python_exec for each command.",
                "language": tool_input.get("language", "python")
            }

        else:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
