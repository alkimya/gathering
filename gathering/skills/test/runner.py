"""
Test Skill for GatheRing.
Provides test execution and coverage tools for agents.
"""

import subprocess
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from gathering.skills.base import BaseSkill, SkillResponse, SkillPermission


class TestSkill(BaseSkill):
    """
    Test execution and coverage skill.

    Provides tools for:
    - Running pytest tests (single, multiple, or all)
    - Generating and parsing coverage reports
    - Test discovery
    - Watch mode for TDD
    - Failure analysis and suggestions
    """

    name = "test"
    description = "Test execution and coverage analysis"
    version = "1.0.0"
    required_permissions = [SkillPermission.READ, SkillPermission.EXECUTE]

    # Safety limits
    MAX_OUTPUT_SIZE = 50_000  # Max chars for test output
    DEFAULT_TIMEOUT = 300  # 5 minutes default timeout
    MAX_TIMEOUT = 1800  # 30 minutes max

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.working_dir = config.get("working_dir") if config else None
        self.python_path = config.get("python_path", "python3") if config else "python3"
        self.pytest_args = config.get("pytest_args", []) if config else []
        self.coverage_threshold = config.get("coverage_threshold", 80) if config else 80

    def get_tools_definition(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "test_run",
                "description": "Run pytest tests. Can run all tests, specific files, or specific test functions.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Project path (optional, uses working_dir if not specified)"
                        },
                        "tests": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific test files or test::function patterns to run"
                        },
                        "markers": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Pytest markers to filter (e.g., ['slow', 'integration'])"
                        },
                        "keywords": {
                            "type": "string",
                            "description": "Keyword expression to filter tests (-k)"
                        },
                        "verbose": {
                            "type": "boolean",
                            "description": "Verbose output (-v)",
                            "default": True
                        },
                        "fail_fast": {
                            "type": "boolean",
                            "description": "Stop on first failure (-x)",
                            "default": False
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds",
                            "default": 300
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "test_coverage",
                "description": "Run tests with coverage analysis and generate a report.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Project path"
                        },
                        "source": {
                            "type": "string",
                            "description": "Source directory to measure coverage for"
                        },
                        "tests": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific test files or patterns to run"
                        },
                        "report_type": {
                            "type": "string",
                            "enum": ["term", "html", "xml", "json"],
                            "description": "Coverage report format",
                            "default": "term"
                        },
                        "fail_under": {
                            "type": "integer",
                            "description": "Minimum coverage percentage required",
                            "default": 80
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "test_discover",
                "description": "Discover available tests in the project without running them.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Project path"
                        },
                        "pattern": {
                            "type": "string",
                            "description": "Test file pattern",
                            "default": "test_*.py"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "test_last_failed",
                "description": "Re-run only the tests that failed in the last run.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Project path"
                        },
                        "verbose": {
                            "type": "boolean",
                            "description": "Verbose output",
                            "default": True
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "test_watch",
                "description": "Start pytest in watch mode (requires pytest-watch). Runs tests on file changes.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Project path"
                        },
                        "tests": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific tests to watch"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "test_analyze_failures",
                "description": "Analyze test failures and provide suggestions for fixes.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Project path"
                        },
                        "test_output": {
                            "type": "string",
                            "description": "Raw test output to analyze (optional, will run tests if not provided)"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "test_create",
                "description": "Generate a test file skeleton for a given module.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Project path"
                        },
                        "module": {
                            "type": "string",
                            "description": "Module path to generate tests for (e.g., 'gathering.skills.base')"
                        },
                        "output_dir": {
                            "type": "string",
                            "description": "Output directory for test file",
                            "default": "tests"
                        },
                        "style": {
                            "type": "string",
                            "enum": ["class", "function"],
                            "description": "Test style (class-based or function-based)",
                            "default": "class"
                        }
                    },
                    "required": ["module"]
                }
            },
        ]

    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> SkillResponse:
        """Execute a test tool."""
        self.ensure_initialized()

        start_time = datetime.utcnow()

        try:
            handlers = {
                "test_run": self._test_run,
                "test_coverage": self._test_coverage,
                "test_discover": self._test_discover,
                "test_last_failed": self._test_last_failed,
                "test_watch": self._test_watch,
                "test_analyze_failures": self._test_analyze_failures,
                "test_create": self._test_create,
            }

            if tool_name not in handlers:
                return SkillResponse(
                    success=False,
                    message=f"Unknown tool: {tool_name}",
                    error="unknown_tool",
                    skill_name=self.name,
                    tool_name=tool_name,
                )

            result = handlers[tool_name](tool_input)
            result.skill_name = self.name
            result.tool_name = tool_name
            result.duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            return result

        except Exception as e:
            return SkillResponse(
                success=False,
                message=f"Error executing {tool_name}: {str(e)}",
                error=str(e),
                skill_name=self.name,
                tool_name=tool_name,
            )

    def _get_project_path(self, tool_input: Dict[str, Any]) -> Path:
        """Get project path from input or config."""
        path = tool_input.get("path") or self.working_dir
        if not path:
            raise ValueError("No project path specified")
        return Path(path).resolve()

    def _run_pytest(
        self,
        args: List[str],
        cwd: Optional[Path] = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> subprocess.CompletedProcess:
        """Run pytest with given arguments."""
        timeout = min(timeout, self.MAX_TIMEOUT)
        cmd = [self.python_path, "-m", "pytest"] + self.pytest_args + args

        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        return result

    def _truncate_output(self, output: str) -> tuple[str, bool]:
        """Truncate output if too large."""
        if len(output) > self.MAX_OUTPUT_SIZE:
            return output[:self.MAX_OUTPUT_SIZE] + "\n... (truncated)", True
        return output, False

    def _parse_pytest_output(self, output: str) -> Dict[str, Any]:
        """Parse pytest output for summary information."""
        result = {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
            "warnings": 0,
            "duration": None,
            "failures": [],
        }

        # Parse summary line: "===== X passed, Y failed, Z skipped in N.NNs ====="
        summary_match = re.search(
            r"=+ ([\d\w\s,]+) in ([\d.]+)s =+",
            output
        )
        if summary_match:
            summary = summary_match.group(1)
            result["duration"] = float(summary_match.group(2))

            for part in summary.split(","):
                part = part.strip()
                if "passed" in part:
                    result["passed"] = int(re.search(r"(\d+)", part).group(1))
                elif "failed" in part:
                    result["failed"] = int(re.search(r"(\d+)", part).group(1))
                elif "skipped" in part:
                    result["skipped"] = int(re.search(r"(\d+)", part).group(1))
                elif "error" in part:
                    result["errors"] = int(re.search(r"(\d+)", part).group(1))
                elif "warning" in part:
                    result["warnings"] = int(re.search(r"(\d+)", part).group(1))

        # Parse failure details
        failure_pattern = re.compile(
            r"FAILED ([\w/._:]+) - (.+?)(?=\n(?:FAILED|=|$))",
            re.MULTILINE
        )
        for match in failure_pattern.finditer(output):
            result["failures"].append({
                "test": match.group(1),
                "reason": match.group(2).strip()
            })

        return result

    def _test_run(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Run pytest tests."""
        project_path = self._get_project_path(tool_input)

        args = []

        # Add specific tests or default to tests/
        tests = tool_input.get("tests", [])
        if tests:
            args.extend(tests)
        else:
            # Default to tests/ directory if it exists
            tests_dir = project_path / "tests"
            if tests_dir.exists():
                args.append("tests/")

        # Add markers
        markers = tool_input.get("markers", [])
        for marker in markers:
            args.extend(["-m", marker])

        # Add keyword filter
        if tool_input.get("keywords"):
            args.extend(["-k", tool_input["keywords"]])

        # Verbosity
        if tool_input.get("verbose", True):
            args.append("-v")

        # Fail fast
        if tool_input.get("fail_fast"):
            args.append("-x")

        # Add short traceback for readability
        args.append("--tb=short")

        timeout = tool_input.get("timeout", self.DEFAULT_TIMEOUT)
        result = self._run_pytest(args, cwd=project_path, timeout=timeout)

        output, truncated = self._truncate_output(result.stdout + result.stderr)
        parsed = self._parse_pytest_output(result.stdout + result.stderr)

        # Determine overall success
        all_passed = result.returncode == 0
        total_tests = parsed["passed"] + parsed["failed"] + parsed["skipped"] + parsed["errors"]

        return SkillResponse(
            success=all_passed,
            message=f"Tests {'passed' if all_passed else 'failed'}: {parsed['passed']} passed, {parsed['failed']} failed, {parsed['skipped']} skipped",
            data={
                "summary": parsed,
                "output": output,
                "truncated": truncated,
                "return_code": result.returncode,
                "total_tests": total_tests,
            }
        )

    def _test_coverage(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Run tests with coverage."""
        project_path = self._get_project_path(tool_input)

        args = ["--cov"]

        # Source to cover
        source = tool_input.get("source")
        if source:
            args.append(f"--cov={source}")

        # Specific tests
        tests = tool_input.get("tests", [])
        if tests:
            args.extend(tests)
        else:
            tests_dir = project_path / "tests"
            if tests_dir.exists():
                args.append("tests/")

        # Report type
        report_type = tool_input.get("report_type", "term")
        if report_type == "term":
            args.append("--cov-report=term-missing")
        elif report_type == "html":
            args.extend(["--cov-report=html", "--cov-report=term"])
        elif report_type == "xml":
            args.extend(["--cov-report=xml", "--cov-report=term"])
        elif report_type == "json":
            args.extend(["--cov-report=json", "--cov-report=term"])

        # Fail under threshold
        fail_under = tool_input.get("fail_under", self.coverage_threshold)
        args.append(f"--cov-fail-under={fail_under}")

        result = self._run_pytest(args, cwd=project_path)

        output, truncated = self._truncate_output(result.stdout + result.stderr)

        # Parse coverage percentage
        coverage_match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", output)
        coverage_pct = int(coverage_match.group(1)) if coverage_match else None

        # Parse file-level coverage
        file_coverage = []
        file_pattern = re.compile(
            r"^([\w/._]+\.py)\s+(\d+)\s+(\d+)\s+(\d+)%\s*([\d,\-\s]*)?$",
            re.MULTILINE
        )
        for match in file_pattern.finditer(output):
            file_coverage.append({
                "file": match.group(1),
                "statements": int(match.group(2)),
                "missing": int(match.group(3)),
                "coverage": int(match.group(4)),
                "missing_lines": match.group(5).strip() if match.group(5) else "",
            })

        passed_threshold = coverage_pct is not None and coverage_pct >= fail_under

        return SkillResponse(
            success=result.returncode == 0 and passed_threshold,
            message=f"Coverage: {coverage_pct}% (threshold: {fail_under}%)",
            data={
                "total_coverage": coverage_pct,
                "threshold": fail_under,
                "passed_threshold": passed_threshold,
                "file_coverage": file_coverage,
                "report_type": report_type,
                "output": output,
                "truncated": truncated,
            }
        )

    def _test_discover(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Discover tests without running them."""
        project_path = self._get_project_path(tool_input)

        args = ["--collect-only", "-q"]

        result = self._run_pytest(args, cwd=project_path)

        # Parse discovered tests
        tests = []
        for line in result.stdout.split("\n"):
            line = line.strip()
            if line and "::" in line and not line.startswith("="):
                tests.append(line)

        # Group by file
        tests_by_file: Dict[str, List[str]] = {}
        for test in tests:
            parts = test.split("::")
            file_path = parts[0]
            test_name = "::".join(parts[1:]) if len(parts) > 1 else test

            if file_path not in tests_by_file:
                tests_by_file[file_path] = []
            tests_by_file[file_path].append(test_name)

        return SkillResponse(
            success=True,
            message=f"Discovered {len(tests)} tests in {len(tests_by_file)} files",
            data={
                "total_tests": len(tests),
                "total_files": len(tests_by_file),
                "tests_by_file": tests_by_file,
                "all_tests": tests,
            }
        )

    def _test_last_failed(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Re-run last failed tests."""
        project_path = self._get_project_path(tool_input)

        args = ["--lf"]  # --last-failed

        if tool_input.get("verbose", True):
            args.append("-v")

        args.append("--tb=short")

        result = self._run_pytest(args, cwd=project_path)

        output, truncated = self._truncate_output(result.stdout + result.stderr)
        parsed = self._parse_pytest_output(result.stdout + result.stderr)

        # Check if there were no previously failed tests
        no_failed = "no previously failed tests" in output.lower()

        if no_failed:
            return SkillResponse(
                success=True,
                message="No previously failed tests to run",
                data={"no_failed_tests": True}
            )

        return SkillResponse(
            success=result.returncode == 0,
            message=f"Re-ran failed tests: {parsed['passed']} passed, {parsed['failed']} still failing",
            data={
                "summary": parsed,
                "output": output,
                "truncated": truncated,
            }
        )

    def _test_watch(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Start test watch mode (informational - actual watch runs in background)."""
        project_path = self._get_project_path(tool_input)

        # Check if pytest-watch is available
        check_result = subprocess.run(
            [self.python_path, "-c", "import pytest_watch"],
            capture_output=True,
            text=True,
        )

        if check_result.returncode != 0:
            return SkillResponse(
                success=False,
                message="pytest-watch not installed. Install with: pip install pytest-watch",
                error="pytest_watch_not_installed",
                data={
                    "install_command": "pip install pytest-watch"
                }
            )

        # Build watch command
        cmd = [self.python_path, "-m", "pytest_watch"]

        tests = tool_input.get("tests", [])
        if tests:
            cmd.extend(["--"] + tests)

        return SkillResponse(
            success=True,
            message="Watch mode command ready",
            needs_confirmation=True,
            confirmation_type="long_running",
            confirmation_message="Start pytest-watch? This will run continuously until stopped.",
            data={
                "command": " ".join(cmd),
                "working_dir": str(project_path),
                "note": "Watch mode requires a dedicated terminal/process"
            }
        )

    def _test_analyze_failures(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Analyze test failures and suggest fixes."""
        project_path = self._get_project_path(tool_input)

        test_output = tool_input.get("test_output")

        # Run tests if no output provided
        if not test_output:
            result = self._run_pytest(["-v", "--tb=long", "tests/"], cwd=project_path)
            test_output = result.stdout + result.stderr

        # Parse failures
        failures = []

        # Pattern for detailed failure info
        failure_blocks = re.split(r"_{10,}\s*\n", test_output)

        for block in failure_blocks:
            if "FAILED" not in block and "ERROR" not in block:
                continue

            failure = {
                "test_name": None,
                "error_type": None,
                "error_message": None,
                "file_path": None,
                "line_number": None,
                "code_snippet": None,
                "suggestions": [],
            }

            # Extract test name
            test_match = re.search(r"(test_\w+)", block)
            if test_match:
                failure["test_name"] = test_match.group(1)

            # Extract file and line
            file_line_match = re.search(r"([\w/._]+\.py):(\d+)", block)
            if file_line_match:
                failure["file_path"] = file_line_match.group(1)
                failure["line_number"] = int(file_line_match.group(2))

            # Extract error type and message
            error_match = re.search(r"([\w]+Error|[\w]+Exception):\s*(.+?)(?:\n|$)", block)
            if error_match:
                failure["error_type"] = error_match.group(1)
                failure["error_message"] = error_match.group(2).strip()

            # Generate suggestions based on error type
            if failure["error_type"]:
                suggestions = self._get_fix_suggestions(
                    failure["error_type"],
                    failure["error_message"] or "",
                    block
                )
                failure["suggestions"] = suggestions

            if failure["test_name"]:
                failures.append(failure)

        # Summary statistics
        error_types = {}
        for f in failures:
            err_type = f["error_type"] or "Unknown"
            error_types[err_type] = error_types.get(err_type, 0) + 1

        return SkillResponse(
            success=True,
            message=f"Analyzed {len(failures)} failures",
            data={
                "total_failures": len(failures),
                "failures": failures,
                "error_type_summary": error_types,
                "has_suggestions": any(f["suggestions"] for f in failures),
            }
        )

    def _get_fix_suggestions(
        self,
        error_type: str,
        error_message: str,
        context: str
    ) -> List[str]:
        """Generate fix suggestions based on error type."""
        suggestions = []

        if error_type == "AssertionError":
            if "==" in context:
                suggestions.append("Check that expected and actual values match")
            if "True" in error_message or "False" in error_message:
                suggestions.append("Verify the condition being asserted")
            suggestions.append("Review test expectations - they may need updating if requirements changed")

        elif error_type == "AttributeError":
            suggestions.append("Check that the object has the expected attribute")
            suggestions.append("Verify imports are correct")
            suggestions.append("Ensure the object is properly initialized")

        elif error_type == "TypeError":
            if "argument" in error_message:
                suggestions.append("Check function signature - wrong number or type of arguments")
            if "NoneType" in error_message:
                suggestions.append("A function returned None unexpectedly - add null checks")
            suggestions.append("Verify data types match expected values")

        elif error_type == "KeyError":
            suggestions.append("Check that the key exists in the dictionary")
            suggestions.append("Use .get() with a default value for optional keys")

        elif error_type == "ImportError" or error_type == "ModuleNotFoundError":
            suggestions.append("Install missing dependency")
            suggestions.append("Check import path is correct")
            suggestions.append("Verify module is in PYTHONPATH")

        elif error_type == "ValueError":
            suggestions.append("Check input values are within expected range")
            suggestions.append("Validate input data before processing")

        elif error_type == "FileNotFoundError":
            suggestions.append("Check file path is correct")
            suggestions.append("Ensure test fixtures are properly set up")
            suggestions.append("Use pytest tmp_path fixture for temporary files")

        elif error_type == "TimeoutError":
            suggestions.append("Increase test timeout if operation is legitimately slow")
            suggestions.append("Check for infinite loops or deadlocks")
            suggestions.append("Mock slow external dependencies")

        # Generic suggestions
        if not suggestions:
            suggestions.append(f"Review the {error_type} documentation")
            suggestions.append("Check recent code changes that might have caused this")

        return suggestions

    def _test_create(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Generate a test file skeleton."""
        project_path = self._get_project_path(tool_input)
        module_path = tool_input.get("module")

        if not module_path:
            return SkillResponse(
                success=False,
                message="Module path is required",
                error="missing_module"
            )

        output_dir = tool_input.get("output_dir", "tests")
        style = tool_input.get("style", "class")

        # Convert module path to file path
        module_parts = module_path.split(".")
        module_name = module_parts[-1]
        test_filename = f"test_{module_name}.py"
        test_path = project_path / output_dir / test_filename

        # Try to import and inspect the module
        module_functions = []
        module_classes = []

        try:
            import importlib
            import inspect

            mod = importlib.import_module(module_path)

            for name, obj in inspect.getmembers(mod):
                if name.startswith("_"):
                    continue
                if inspect.isfunction(obj) and obj.__module__ == module_path:
                    module_functions.append(name)
                elif inspect.isclass(obj) and obj.__module__ == module_path:
                    module_classes.append(name)

        except ImportError:
            # Module not importable, generate basic skeleton
            pass

        # Generate test content
        if style == "class":
            content = self._generate_class_style_tests(
                module_path, module_name, module_functions, module_classes
            )
        else:
            content = self._generate_function_style_tests(
                module_path, module_name, module_functions, module_classes
            )

        return SkillResponse(
            success=True,
            message=f"Test skeleton generated for {module_path}",
            needs_confirmation=True,
            confirmation_type="write_file",
            confirmation_message=f"Create test file at {test_path}?",
            data={
                "test_path": str(test_path),
                "content": content,
                "module": module_path,
                "discovered_functions": module_functions,
                "discovered_classes": module_classes,
            }
        )

    def _generate_class_style_tests(
        self,
        module_path: str,
        module_name: str,
        functions: List[str],
        classes: List[str]
    ) -> str:
        """Generate class-based test file content."""
        lines = [
            '"""',
            f'Tests for {module_path}',
            '"""',
            '',
            'import pytest',
            f'from {module_path} import *',
            '',
            '',
        ]

        # Generate test class for module functions
        if functions:
            lines.append(f'class Test{module_name.title().replace("_", "")}:')
            lines.append(f'    """Tests for {module_name} module functions."""')
            lines.append('')

            for func in functions:
                lines.append(f'    def test_{func}(self):')
                lines.append(f'        """Test {func} function."""')
                lines.append('        # TODO: Implement test')
                lines.append(f'        # result = {func}(...)')
                lines.append('        # assert result == expected')
                lines.append('        pytest.skip("Not implemented")')
                lines.append('')

        # Generate test classes for each discovered class
        for cls in classes:
            lines.append(f'class Test{cls}:')
            lines.append(f'    """Tests for {cls} class."""')
            lines.append('')
            lines.append('    @pytest.fixture')
            lines.append('    def instance(self):')
            lines.append(f'        """Create a {cls} instance for testing."""')
            lines.append(f'        # return {cls}(...)')
            lines.append('        pytest.skip("Fixture not implemented")')
            lines.append('')
            lines.append('    def test_creation(self, instance):')
            lines.append(f'        """Test {cls} can be created."""')
            lines.append('        assert instance is not None')
            lines.append('')

        return '\n'.join(lines)

    def _generate_function_style_tests(
        self,
        module_path: str,
        module_name: str,
        functions: List[str],
        classes: List[str]
    ) -> str:
        """Generate function-based test file content."""
        lines = [
            '"""',
            f'Tests for {module_path}',
            '"""',
            '',
            'import pytest',
            f'from {module_path} import *',
            '',
            '',
        ]

        # Generate test functions for module functions
        for func in functions:
            lines.append(f'def test_{func}():')
            lines.append(f'    """Test {func} function."""')
            lines.append('    # TODO: Implement test')
            lines.append(f'    # result = {func}(...)')
            lines.append('    # assert result == expected')
            lines.append('    pytest.skip("Not implemented")')
            lines.append('')

        # Generate test functions for classes
        for cls in classes:
            lines.append('@pytest.fixture')
            lines.append(f'def {cls.lower()}_instance():')
            lines.append(f'    """Create a {cls} instance for testing."""')
            lines.append(f'    # return {cls}(...)')
            lines.append('    pytest.skip("Fixture not implemented")')
            lines.append('')
            lines.append(f'def test_{cls.lower()}_creation({cls.lower()}_instance):')
            lines.append(f'    """Test {cls} can be created."""')
            lines.append(f'    assert {cls.lower()}_instance is not None')
            lines.append('')

        return '\n'.join(lines)
