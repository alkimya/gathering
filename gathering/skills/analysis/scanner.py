"""
Code Analysis Skill for GatheRing.
Provides code analysis, linting, and security scanning for agents.
"""

import ast
import re
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from gathering.skills.base import BaseSkill, SkillResponse, SkillPermission


class CodeAnalysisSkill(BaseSkill):
    """
    Code analysis and security scanning skill.

    Provides tools for:
    - Static code analysis (AST-based)
    - Linting with popular tools (ruff, flake8, pylint)
    - Security vulnerability scanning
    - Code complexity metrics
    - Dependency analysis
    - Type checking
    """

    name = "analysis"
    description = "Code analysis, linting, and security scanning"
    version = "1.0.0"
    required_permissions = [SkillPermission.READ, SkillPermission.EXECUTE]

    # Known security patterns
    SECURITY_PATTERNS = {
        "hardcoded_secret": [
            r"(?i)(password|secret|api_key|token|auth)\s*=\s*['\"][^'\"]{8,}['\"]",
            r"(?i)(AWS|AZURE|GCP)_[A-Z_]*KEY\s*=\s*['\"][^'\"]+['\"]",
        ],
        "sql_injection": [
            r"execute\s*\(\s*['\"].*%s.*['\"]",
            r"f['\"].*SELECT.*\{.*\}.*['\"]",
        ],
        "command_injection": [
            r"os\.system\s*\(",
            r"subprocess\.(call|run|Popen)\s*\([^)]*shell\s*=\s*True",
            r"eval\s*\(",
            r"exec\s*\(",
        ],
        "path_traversal": [
            r"open\s*\([^)]*\+[^)]*\)",
            r"Path\s*\([^)]*\+[^)]*\)",
        ],
        "insecure_deserialization": [
            r"pickle\.loads?\s*\(",
            r"yaml\.load\s*\([^)]*Loader\s*=\s*None",
            r"yaml\.unsafe_load\s*\(",
        ],
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.working_dir = config.get("working_dir") if config else None
        self.exclude_patterns = config.get("exclude_patterns", ["venv", "node_modules", "__pycache__", ".git"]) if config else []

    def get_tools_definition(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "analysis_lint",
                "description": "Run linting on Python code",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File or directory to lint"},
                        "tool": {
                            "type": "string",
                            "enum": ["ruff", "flake8", "pylint", "auto"],
                            "description": "Linting tool to use",
                            "default": "auto"
                        },
                        "fix": {"type": "boolean", "description": "Auto-fix issues (ruff only)", "default": False}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "analysis_security",
                "description": "Scan code for security vulnerabilities",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File or directory to scan"},
                        "severity": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "critical"],
                            "description": "Minimum severity to report",
                            "default": "low"
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "analysis_complexity",
                "description": "Analyze code complexity metrics",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File or directory to analyze"},
                        "threshold": {"type": "integer", "description": "Complexity threshold", "default": 10}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "analysis_dependencies",
                "description": "Analyze project dependencies",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Project path"},
                        "check_vulnerabilities": {"type": "boolean", "description": "Check for known vulnerabilities", "default": True},
                        "check_outdated": {"type": "boolean", "description": "Check for outdated packages", "default": True}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "analysis_type_check",
                "description": "Run type checking with mypy",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File or directory to check"},
                        "strict": {"type": "boolean", "description": "Use strict mode", "default": False}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "analysis_dead_code",
                "description": "Find unused code (imports, variables, functions)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File or directory to analyze"}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "analysis_duplicates",
                "description": "Find duplicate code blocks",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Directory to analyze"},
                        "min_lines": {"type": "integer", "description": "Minimum lines to consider duplicate", "default": 5}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "analysis_metrics",
                "description": "Get overall code metrics and statistics",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Directory to analyze"}
                    },
                    "required": ["path"]
                }
            },
        ]

    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> SkillResponse:
        """Execute a code analysis tool."""
        self.ensure_initialized()

        start_time = datetime.utcnow()

        try:
            handlers = {
                "analysis_lint": self._analysis_lint,
                "analysis_security": self._analysis_security,
                "analysis_complexity": self._analysis_complexity,
                "analysis_dependencies": self._analysis_dependencies,
                "analysis_type_check": self._analysis_type_check,
                "analysis_dead_code": self._analysis_dead_code,
                "analysis_duplicates": self._analysis_duplicates,
                "analysis_metrics": self._analysis_metrics,
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

    def _get_path(self, tool_input: Dict[str, Any]) -> Path:
        """Get resolved path."""
        path = tool_input.get("path") or self.working_dir
        if not path:
            raise ValueError("No path specified")
        return Path(path).resolve()

    def _should_exclude(self, path: Path) -> bool:
        """Check if path should be excluded."""
        return any(excl in str(path) for excl in self.exclude_patterns)

    def _analysis_lint(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Run linting."""
        path = self._get_path(tool_input)
        tool = tool_input.get("tool", "auto")
        fix = tool_input.get("fix", False)

        if not path.exists():
            return SkillResponse(success=False, message=f"Path not found: {path}", error="not_found")

        # Auto-detect available linter
        if tool == "auto":
            for linter in ["ruff", "flake8", "pylint"]:
                try:
                    subprocess.run([linter, "--version"], capture_output=True, check=True)
                    tool = linter
                    break
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue
            else:
                return SkillResponse(
                    success=False,
                    message="No linter found. Install ruff, flake8, or pylint.",
                    error="no_linter",
                    data={"install_command": "pip install ruff"}
                )

        # Build command
        if tool == "ruff":
            cmd = ["ruff", "check", str(path)]
            if fix:
                cmd.append("--fix")
            cmd.extend(["--output-format", "json"])
        elif tool == "flake8":
            cmd = ["flake8", str(path), "--format=json"]
        else:  # pylint
            cmd = ["pylint", str(path), "--output-format=json"]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            output = result.stdout or result.stderr

            # Parse output
            issues = []
            try:
                if tool == "ruff":
                    issues = json.loads(output) if output.strip() else []
                elif output.strip():
                    issues = json.loads(output)
            except json.JSONDecodeError:
                # Fall back to line parsing
                for line in output.split("\n"):
                    if line.strip():
                        issues.append({"raw": line})

            return SkillResponse(
                success=result.returncode == 0,
                message=f"Found {len(issues)} issues" if issues else "No issues found",
                data={
                    "tool": tool,
                    "issues": issues[:100],  # Limit output
                    "total_issues": len(issues),
                    "fixed": fix and tool == "ruff",
                    "path": str(path),
                }
            )

        except subprocess.TimeoutExpired:
            return SkillResponse(success=False, message="Linting timed out", error="timeout")
        except FileNotFoundError:
            return SkillResponse(
                success=False,
                message=f"{tool} not installed",
                error="tool_not_found",
                data={"install_command": f"pip install {tool}"}
            )

    def _analysis_security(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Scan for security vulnerabilities."""
        path = self._get_path(tool_input)
        min_severity = tool_input.get("severity", "low")

        if not path.exists():
            return SkillResponse(success=False, message=f"Path not found: {path}", error="not_found")

        severity_levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        min_level = severity_levels.get(min_severity, 1)

        findings = []
        files = list(path.rglob("*.py")) if path.is_dir() else [path]

        for file_path in files:
            if self._should_exclude(file_path):
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    lines = content.split("\n")

                for category, patterns in self.SECURITY_PATTERNS.items():
                    for pattern in patterns:
                        for i, line in enumerate(lines):
                            if re.search(pattern, line):
                                # Determine severity
                                if category in ("hardcoded_secret", "command_injection"):
                                    severity = "critical"
                                elif category in ("sql_injection", "insecure_deserialization"):
                                    severity = "high"
                                elif category == "path_traversal":
                                    severity = "medium"
                                else:
                                    severity = "low"

                                if severity_levels[severity] >= min_level:
                                    findings.append({
                                        "file": str(file_path),
                                        "line": i + 1,
                                        "category": category,
                                        "severity": severity,
                                        "code": line.strip()[:100],
                                        "pattern": pattern,
                                    })

            except (UnicodeDecodeError, PermissionError):
                continue

        # Try bandit if available
        bandit_findings = []
        try:
            result = subprocess.run(
                ["bandit", "-r", str(path), "-f", "json", "-q"],
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.stdout:
                bandit_output = json.loads(result.stdout)
                bandit_findings = bandit_output.get("results", [])
        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
            pass

        # Merge findings
        all_findings = findings + [
            {
                "file": f["filename"],
                "line": f["line_number"],
                "category": f["test_id"],
                "severity": f["issue_severity"].lower(),
                "code": f["code"],
                "message": f["issue_text"],
                "source": "bandit",
            }
            for f in bandit_findings
            if severity_levels.get(f["issue_severity"].lower(), 0) >= min_level
        ]

        # Sort by severity
        all_findings.sort(key=lambda x: -severity_levels.get(x["severity"], 0))

        return SkillResponse(
            success=len(all_findings) == 0,
            message=f"Found {len(all_findings)} security issues",
            data={
                "findings": all_findings[:50],
                "total_findings": len(all_findings),
                "by_severity": {
                    sev: len([f for f in all_findings if f["severity"] == sev])
                    for sev in severity_levels.keys()
                },
                "files_scanned": len(files),
            }
        )

    def _analysis_complexity(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Analyze code complexity."""
        path = self._get_path(tool_input)
        threshold = tool_input.get("threshold", 10)

        if not path.exists():
            return SkillResponse(success=False, message=f"Path not found: {path}", error="not_found")

        results = []
        files = list(path.rglob("*.py")) if path.is_dir() else [path]

        for file_path in files:
            if self._should_exclude(file_path):
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    source = f.read()

                tree = ast.parse(source)

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        complexity = self._calculate_complexity(node)

                        if complexity >= threshold:
                            results.append({
                                "file": str(file_path),
                                "function": node.name,
                                "line": node.lineno,
                                "complexity": complexity,
                                "over_threshold": complexity >= threshold,
                            })

            except (SyntaxError, UnicodeDecodeError):
                continue

        # Sort by complexity
        results.sort(key=lambda x: -x["complexity"])

        avg_complexity = sum(r["complexity"] for r in results) / len(results) if results else 0

        return SkillResponse(
            success=True,
            message=f"Analyzed {len(files)} files",
            data={
                "complex_functions": results[:20],
                "total_functions": len(results),
                "over_threshold": len([r for r in results if r["over_threshold"]]),
                "average_complexity": round(avg_complexity, 2),
                "threshold": threshold,
            }
        )

    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                complexity += 1
            elif isinstance(child, ast.IfExp):
                complexity += 1

        return complexity

    def _analysis_dependencies(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Analyze project dependencies."""
        path = self._get_path(tool_input)
        check_vulnerabilities = tool_input.get("check_vulnerabilities", True)
        check_outdated = tool_input.get("check_outdated", True)

        if not path.exists():
            return SkillResponse(success=False, message=f"Path not found: {path}", error="not_found")

        # Find requirements files
        req_files = []
        for pattern in ["requirements*.txt", "pyproject.toml", "setup.py", "Pipfile"]:
            req_files.extend(path.glob(pattern))
            if path.is_dir():
                req_files.extend(path.rglob(pattern))

        dependencies = []

        # Parse requirements.txt
        for req_file in req_files:
            if req_file.suffix == ".txt":
                try:
                    with open(req_file, "r") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#"):
                                # Parse package==version or package>=version
                                match = re.match(r"([a-zA-Z0-9_-]+)([<>=!]+)?(.+)?", line)
                                if match:
                                    dependencies.append({
                                        "name": match.group(1),
                                        "version_spec": match.group(2) or "",
                                        "version": match.group(3) or "",
                                        "source": str(req_file),
                                    })
                except (UnicodeDecodeError, PermissionError):
                    continue

        # Check for vulnerabilities using pip-audit if available
        vulnerabilities = []
        if check_vulnerabilities:
            try:
                result = subprocess.run(
                    ["pip-audit", "--format", "json"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=str(path)
                )
                if result.stdout:
                    audit_output = json.loads(result.stdout)
                    vulnerabilities = audit_output.get("dependencies", [])
            except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
                pass

        # Check for outdated packages
        outdated = []
        if check_outdated:
            try:
                result = subprocess.run(
                    ["pip", "list", "--outdated", "--format", "json"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.stdout:
                    outdated = json.loads(result.stdout)
            except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
                pass

        return SkillResponse(
            success=True,
            message=f"Found {len(dependencies)} dependencies",
            data={
                "dependencies": dependencies,
                "vulnerabilities": vulnerabilities,
                "outdated": outdated,
                "requirement_files": [str(f) for f in req_files],
            }
        )

    def _analysis_type_check(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Run type checking with mypy."""
        path = self._get_path(tool_input)
        strict = tool_input.get("strict", False)

        if not path.exists():
            return SkillResponse(success=False, message=f"Path not found: {path}", error="not_found")

        cmd = ["mypy", str(path), "--show-error-codes"]
        if strict:
            cmd.append("--strict")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            output = result.stdout + result.stderr

            # Parse mypy output
            errors = []
            for line in output.split("\n"):
                match = re.match(r"(.+):(\d+): (\w+): (.+)", line)
                if match:
                    errors.append({
                        "file": match.group(1),
                        "line": int(match.group(2)),
                        "level": match.group(3),
                        "message": match.group(4),
                    })

            return SkillResponse(
                success=result.returncode == 0,
                message=f"Found {len(errors)} type errors" if errors else "No type errors",
                data={
                    "errors": errors[:50],
                    "total_errors": len(errors),
                    "strict_mode": strict,
                }
            )

        except FileNotFoundError:
            return SkillResponse(
                success=False,
                message="mypy not installed",
                error="mypy_not_found",
                data={"install_command": "pip install mypy"}
            )

    def _analysis_dead_code(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Find unused code."""
        path = self._get_path(tool_input)

        if not path.exists():
            return SkillResponse(success=False, message=f"Path not found: {path}", error="not_found")

        # Try vulture if available
        try:
            result = subprocess.run(
                ["vulture", str(path), "--min-confidence", "80"],
                capture_output=True,
                text=True,
                timeout=120
            )

            dead_code = []
            for line in result.stdout.split("\n"):
                match = re.match(r"(.+):(\d+): (.+)", line)
                if match:
                    dead_code.append({
                        "file": match.group(1),
                        "line": int(match.group(2)),
                        "message": match.group(3),
                    })

            return SkillResponse(
                success=True,
                message=f"Found {len(dead_code)} unused code items",
                data={
                    "dead_code": dead_code[:50],
                    "total": len(dead_code),
                    "tool": "vulture",
                }
            )

        except FileNotFoundError:
            # Fallback: basic unused import detection
            unused_imports = []
            files = list(path.rglob("*.py")) if path.is_dir() else [path]

            for file_path in files:
                if self._should_exclude(file_path):
                    continue

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        source = f.read()

                    tree = ast.parse(source)

                    # Get all imported names
                    imports = set()
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                imports.add(alias.asname or alias.name.split(".")[0])
                        elif isinstance(node, ast.ImportFrom):
                            for alias in node.names:
                                imports.add(alias.asname or alias.name)

                    # Check if used
                    names_used = set()
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Name):
                            names_used.add(node.id)

                    unused = imports - names_used - {"*"}
                    for name in unused:
                        unused_imports.append({
                            "file": str(file_path),
                            "import": name,
                        })

                except (SyntaxError, UnicodeDecodeError):
                    continue

            return SkillResponse(
                success=True,
                message=f"Found {len(unused_imports)} potentially unused imports",
                data={
                    "unused_imports": unused_imports[:50],
                    "total": len(unused_imports),
                    "tool": "ast",
                    "note": "Install vulture for more comprehensive analysis",
                }
            )

    def _analysis_duplicates(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Find duplicate code."""
        path = self._get_path(tool_input)
        min_lines = tool_input.get("min_lines", 5)

        if not path.exists():
            return SkillResponse(success=False, message=f"Path not found: {path}", error="not_found")

        # Simple hash-based duplicate detection
        code_blocks = {}
        duplicates = []

        files = list(path.rglob("*.py")) if path.is_dir() else [path]

        for file_path in files:
            if self._should_exclude(file_path):
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                # Sliding window for code blocks
                for i in range(len(lines) - min_lines + 1):
                    block = "".join(lines[i:i + min_lines])
                    # Skip mostly whitespace/comments
                    cleaned = re.sub(r"^\s*#.*$", "", block, flags=re.MULTILINE).strip()
                    if len(cleaned) < min_lines * 10:
                        continue

                    block_hash = hash(cleaned)

                    if block_hash in code_blocks:
                        duplicates.append({
                            "original": code_blocks[block_hash],
                            "duplicate": {
                                "file": str(file_path),
                                "start_line": i + 1,
                                "end_line": i + min_lines,
                            },
                            "lines": min_lines,
                        })
                    else:
                        code_blocks[block_hash] = {
                            "file": str(file_path),
                            "start_line": i + 1,
                            "end_line": i + min_lines,
                        }

            except (UnicodeDecodeError, PermissionError):
                continue

        return SkillResponse(
            success=True,
            message=f"Found {len(duplicates)} duplicate blocks",
            data={
                "duplicates": duplicates[:20],
                "total": len(duplicates),
                "min_lines": min_lines,
                "files_scanned": len(files),
            }
        )

    def _analysis_metrics(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Get overall code metrics."""
        path = self._get_path(tool_input)

        if not path.exists():
            return SkillResponse(success=False, message=f"Path not found: {path}", error="not_found")

        metrics = {
            "total_files": 0,
            "total_lines": 0,
            "code_lines": 0,
            "comment_lines": 0,
            "blank_lines": 0,
            "total_functions": 0,
            "total_classes": 0,
            "avg_function_length": 0,
            "by_extension": {},
        }

        function_lengths = []
        files = list(path.rglob("*")) if path.is_dir() else [path]

        for file_path in files:
            if not file_path.is_file() or self._should_exclude(file_path):
                continue

            ext = file_path.suffix.lower()

            # Count by extension
            if ext not in metrics["by_extension"]:
                metrics["by_extension"][ext] = {"files": 0, "lines": 0}
            metrics["by_extension"][ext]["files"] += 1

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                metrics["total_files"] += 1
                metrics["total_lines"] += len(lines)
                metrics["by_extension"][ext]["lines"] += len(lines)

                for line in lines:
                    stripped = line.strip()
                    if not stripped:
                        metrics["blank_lines"] += 1
                    elif stripped.startswith("#") or stripped.startswith("//"):
                        metrics["comment_lines"] += 1
                    else:
                        metrics["code_lines"] += 1

                # Parse Python files for more metrics
                if ext == ".py":
                    try:
                        tree = ast.parse("".join(lines))
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ClassDef):
                                metrics["total_classes"] += 1
                            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                metrics["total_functions"] += 1
                                func_lines = node.end_lineno - node.lineno + 1 if hasattr(node, "end_lineno") else 10
                                function_lengths.append(func_lines)
                    except SyntaxError:
                        pass

            except (UnicodeDecodeError, PermissionError):
                continue

        if function_lengths:
            metrics["avg_function_length"] = round(sum(function_lengths) / len(function_lengths), 1)

        return SkillResponse(
            success=True,
            message=f"Analyzed {metrics['total_files']} files",
            data=metrics
        )
