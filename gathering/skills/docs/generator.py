"""
Documentation Skill for GatheRing.
Provides documentation generation and management for agents.
"""

import ast
import subprocess
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from gathering.skills.base import BaseSkill, SkillResponse, SkillPermission


class DocsSkill(BaseSkill):
    """
    Documentation generation and management skill.

    Provides tools for:
    - Generating docstrings for functions/classes
    - Creating README files
    - API documentation generation
    - Markdown file management
    - Code documentation analysis
    """

    name = "docs"
    description = "Documentation generation and management"
    version = "1.0.0"
    required_permissions = [SkillPermission.READ, SkillPermission.WRITE]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.working_dir = config.get("working_dir") if config else None
        self.doc_style = config.get("doc_style", "google") if config else "google"

    def get_tools_definition(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "docs_analyze",
                "description": "Analyze documentation coverage in a codebase",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to analyze"},
                        "file_pattern": {"type": "string", "description": "File pattern", "default": "*.py"}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "docs_generate_docstring",
                "description": "Generate docstring for a function or class",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Function or class code"},
                        "style": {
                            "type": "string",
                            "enum": ["google", "numpy", "sphinx"],
                            "description": "Docstring style",
                            "default": "google"
                        }
                    },
                    "required": ["code"]
                }
            },
            {
                "name": "docs_generate_readme",
                "description": "Generate a README.md template for a project",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Project path"},
                        "project_name": {"type": "string", "description": "Project name"},
                        "description": {"type": "string", "description": "Project description"},
                        "sections": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Sections to include",
                            "default": ["installation", "usage", "api", "contributing", "license"]
                        }
                    },
                    "required": ["path", "project_name"]
                }
            },
            {
                "name": "docs_extract",
                "description": "Extract documentation from source files",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File or directory path"},
                        "output_format": {
                            "type": "string",
                            "enum": ["markdown", "json", "html"],
                            "description": "Output format",
                            "default": "markdown"
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "docs_generate_api",
                "description": "Generate API documentation for a module",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Module path"},
                        "output_dir": {"type": "string", "description": "Output directory"},
                        "include_private": {"type": "boolean", "description": "Include private members", "default": False}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "docs_lint",
                "description": "Check documentation for issues",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to check"},
                        "check_spelling": {"type": "boolean", "description": "Check spelling", "default": False},
                        "check_links": {"type": "boolean", "description": "Check broken links", "default": True}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "docs_changelog",
                "description": "Generate or update a CHANGELOG entry",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Project path"},
                        "version": {"type": "string", "description": "Version number"},
                        "changes": {
                            "type": "object",
                            "properties": {
                                "added": {"type": "array", "items": {"type": "string"}},
                                "changed": {"type": "array", "items": {"type": "string"}},
                                "fixed": {"type": "array", "items": {"type": "string"}},
                                "removed": {"type": "array", "items": {"type": "string"}}
                            },
                            "description": "Changes by category"
                        }
                    },
                    "required": ["path", "version", "changes"]
                }
            },
        ]

    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> SkillResponse:
        """Execute a documentation tool."""
        self.ensure_initialized()

        start_time = datetime.utcnow()

        try:
            handlers = {
                "docs_analyze": self._docs_analyze,
                "docs_generate_docstring": self._docs_generate_docstring,
                "docs_generate_readme": self._docs_generate_readme,
                "docs_extract": self._docs_extract,
                "docs_generate_api": self._docs_generate_api,
                "docs_lint": self._docs_lint,
                "docs_changelog": self._docs_changelog,
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

    def _docs_analyze(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Analyze documentation coverage."""
        path = self._get_path(tool_input)
        file_pattern = tool_input.get("file_pattern", "*.py")

        if not path.exists():
            return SkillResponse(success=False, message=f"Path not found: {path}", error="not_found")

        stats = {
            "total_files": 0,
            "documented_files": 0,
            "total_functions": 0,
            "documented_functions": 0,
            "total_classes": 0,
            "documented_classes": 0,
            "undocumented": [],
        }

        files = list(path.rglob(file_pattern)) if path.is_dir() else [path]

        for file_path in files:
            if not file_path.is_file():
                continue

            stats["total_files"] += 1

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    source = f.read()

                tree = ast.parse(source)

                # Check module docstring
                if ast.get_docstring(tree):
                    stats["documented_files"] += 1

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        stats["total_functions"] += 1
                        if ast.get_docstring(node):
                            stats["documented_functions"] += 1
                        else:
                            stats["undocumented"].append({
                                "type": "function",
                                "name": node.name,
                                "file": str(file_path),
                                "line": node.lineno,
                            })

                    elif isinstance(node, ast.ClassDef):
                        stats["total_classes"] += 1
                        if ast.get_docstring(node):
                            stats["documented_classes"] += 1
                        else:
                            stats["undocumented"].append({
                                "type": "class",
                                "name": node.name,
                                "file": str(file_path),
                                "line": node.lineno,
                            })

            except (SyntaxError, UnicodeDecodeError):
                continue

        # Calculate coverage percentages
        total = stats["total_functions"] + stats["total_classes"]
        documented = stats["documented_functions"] + stats["documented_classes"]
        coverage = (documented / total * 100) if total > 0 else 100

        stats["coverage_percent"] = round(coverage, 1)

        return SkillResponse(
            success=True,
            message=f"Documentation coverage: {stats['coverage_percent']}%",
            data=stats
        )

    def _docs_generate_docstring(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Generate docstring for code."""
        code = tool_input["code"]
        style = tool_input.get("style", self.doc_style)

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return SkillResponse(success=False, message=f"Invalid Python code: {e}", error="syntax_error")

        # Find the main node (function or class)
        main_node = None
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                main_node = node
                break

        if not main_node:
            return SkillResponse(
                success=False,
                message="No function or class found in code",
                error="no_definition_found"
            )

        # Generate docstring based on style
        if isinstance(main_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            docstring = self._generate_function_docstring(main_node, style)
        else:
            docstring = self._generate_class_docstring(main_node, style)

        return SkillResponse(
            success=True,
            message=f"Generated {style} docstring for {main_node.name}",
            data={
                "docstring": docstring,
                "style": style,
                "name": main_node.name,
                "type": "function" if isinstance(main_node, (ast.FunctionDef, ast.AsyncFunctionDef)) else "class",
            }
        )

    def _generate_function_docstring(self, node: ast.FunctionDef, style: str) -> str:
        """Generate docstring for a function."""
        args = []
        for arg in node.args.args:
            if arg.arg != "self":
                annotation = ""
                if arg.annotation:
                    annotation = ast.unparse(arg.annotation)
                args.append((arg.arg, annotation))

        # Get return annotation
        returns = ""
        if node.returns:
            returns = ast.unparse(node.returns)

        if style == "google":
            lines = ['"""Brief description.', ""]
            if args:
                lines.append("Args:")
                for name, ann in args:
                    type_hint = f" ({ann})" if ann else ""
                    lines.append(f"    {name}{type_hint}: Description.")
                lines.append("")
            if returns:
                lines.append("Returns:")
                lines.append(f"    {returns}: Description.")
                lines.append("")
            lines.append('"""')

        elif style == "numpy":
            lines = ['"""Brief description.', "", "Parameters", "----------"]
            for name, ann in args:
                type_hint = f" : {ann}" if ann else ""
                lines.append(f"{name}{type_hint}")
                lines.append("    Description.")
            if returns:
                lines.extend(["", "Returns", "-------", f"{returns}", "    Description."])
            lines.append('"""')

        else:  # sphinx
            lines = ['"""Brief description.', ""]
            for name, ann in args:
                type_hint = f" {ann}" if ann else ""
                lines.append(f":param {name}: Description.")
                if ann:
                    lines.append(f":type {name}:{type_hint}")
            if returns:
                lines.append(f":returns: Description.")
                lines.append(f":rtype: {returns}")
            lines.append('"""')

        return "\n".join(lines)

    def _generate_class_docstring(self, node: ast.ClassDef, style: str) -> str:
        """Generate docstring for a class."""
        # Find __init__ method for attributes
        init_args = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                for arg in item.args.args:
                    if arg.arg != "self":
                        annotation = ""
                        if arg.annotation:
                            annotation = ast.unparse(arg.annotation)
                        init_args.append((arg.arg, annotation))
                break

        if style == "google":
            lines = ['"""Brief description.', ""]
            if init_args:
                lines.append("Attributes:")
                for name, ann in init_args:
                    type_hint = f" ({ann})" if ann else ""
                    lines.append(f"    {name}{type_hint}: Description.")
                lines.append("")
            lines.append('"""')

        elif style == "numpy":
            lines = ['"""Brief description.', ""]
            if init_args:
                lines.extend(["Attributes", "----------"])
                for name, ann in init_args:
                    type_hint = f" : {ann}" if ann else ""
                    lines.append(f"{name}{type_hint}")
                    lines.append("    Description.")
            lines.append('"""')

        else:  # sphinx
            lines = ['"""Brief description.', ""]
            for name, ann in init_args:
                lines.append(f":ivar {name}: Description.")
                if ann:
                    lines.append(f":vartype {name}: {ann}")
            lines.append('"""')

        return "\n".join(lines)

    def _docs_generate_readme(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Generate README template."""
        path = self._get_path(tool_input)
        project_name = tool_input["project_name"]
        description = tool_input.get("description", "")
        sections = tool_input.get("sections", ["installation", "usage", "api", "contributing", "license"])

        readme_parts = [f"# {project_name}", ""]

        if description:
            readme_parts.extend([description, ""])

        section_templates = {
            "installation": """## Installation

```bash
pip install {project_name}
```
""",
            "usage": """## Usage

```python
import {module_name}

# Example usage
```
""",
            "api": """## API Reference

### Main Functions

- `function_name()`: Description
""",
            "contributing": """## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
""",
            "license": """## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
""",
            "features": """## Features

- Feature 1
- Feature 2
- Feature 3
""",
            "requirements": """## Requirements

- Python 3.8+
- Dependencies listed in `requirements.txt`
""",
        }

        module_name = project_name.lower().replace("-", "_").replace(" ", "_")

        for section in sections:
            if section in section_templates:
                content = section_templates[section].format(
                    project_name=project_name,
                    module_name=module_name,
                )
                readme_parts.append(content)

        readme_content = "\n".join(readme_parts)

        return SkillResponse(
            success=True,
            message=f"Generated README for {project_name}",
            needs_confirmation=True,
            confirmation_type="write_file",
            confirmation_message=f"Create README.md at {path}?",
            data={
                "content": readme_content,
                "path": str(path / "README.md"),
                "sections": sections,
            }
        )

    def _docs_extract(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Extract documentation from source."""
        path = self._get_path(tool_input)
        output_format = tool_input.get("output_format", "markdown")

        if not path.exists():
            return SkillResponse(success=False, message=f"Path not found: {path}", error="not_found")

        docs = []

        files = list(path.rglob("*.py")) if path.is_dir() else [path]

        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    source = f.read()

                tree = ast.parse(source)
                module_doc = ast.get_docstring(tree)

                file_docs = {
                    "file": str(file_path),
                    "module_docstring": module_doc,
                    "classes": [],
                    "functions": [],
                }

                for node in ast.iter_child_nodes(tree):
                    if isinstance(node, ast.ClassDef):
                        class_doc = {
                            "name": node.name,
                            "docstring": ast.get_docstring(node),
                            "methods": [],
                        }
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef):
                                class_doc["methods"].append({
                                    "name": item.name,
                                    "docstring": ast.get_docstring(item),
                                })
                        file_docs["classes"].append(class_doc)

                    elif isinstance(node, ast.FunctionDef):
                        file_docs["functions"].append({
                            "name": node.name,
                            "docstring": ast.get_docstring(node),
                        })

                docs.append(file_docs)

            except (SyntaxError, UnicodeDecodeError):
                continue

        # Format output
        if output_format == "markdown":
            output = self._format_docs_markdown(docs)
        elif output_format == "html":
            output = self._format_docs_html(docs)
        else:
            output = docs

        return SkillResponse(
            success=True,
            message=f"Extracted documentation from {len(docs)} files",
            data={
                "documentation": output,
                "format": output_format,
                "files_processed": len(docs),
            }
        )

    def _format_docs_markdown(self, docs: List[Dict]) -> str:
        """Format docs as markdown."""
        lines = []

        for file_doc in docs:
            lines.append(f"# {Path(file_doc['file']).name}")
            lines.append("")

            if file_doc["module_docstring"]:
                lines.append(file_doc["module_docstring"])
                lines.append("")

            for cls in file_doc["classes"]:
                lines.append(f"## Class: {cls['name']}")
                lines.append("")
                if cls["docstring"]:
                    lines.append(cls["docstring"])
                    lines.append("")

                for method in cls["methods"]:
                    lines.append(f"### {method['name']}")
                    if method["docstring"]:
                        lines.append(method["docstring"])
                    lines.append("")

            for func in file_doc["functions"]:
                lines.append(f"## Function: {func['name']}")
                if func["docstring"]:
                    lines.append(func["docstring"])
                lines.append("")

        return "\n".join(lines)

    def _format_docs_html(self, docs: List[Dict]) -> str:
        """Format docs as HTML."""
        html_parts = ["<html><body>"]

        for file_doc in docs:
            html_parts.append(f"<h1>{Path(file_doc['file']).name}</h1>")

            if file_doc["module_docstring"]:
                html_parts.append(f"<p>{file_doc['module_docstring']}</p>")

            for cls in file_doc["classes"]:
                html_parts.append(f"<h2>Class: {cls['name']}</h2>")
                if cls["docstring"]:
                    html_parts.append(f"<p>{cls['docstring']}</p>")

                for method in cls["methods"]:
                    html_parts.append(f"<h3>{method['name']}</h3>")
                    if method["docstring"]:
                        html_parts.append(f"<p>{method['docstring']}</p>")

            for func in file_doc["functions"]:
                html_parts.append(f"<h2>Function: {func['name']}</h2>")
                if func["docstring"]:
                    html_parts.append(f"<p>{func['docstring']}</p>")

        html_parts.append("</body></html>")
        return "\n".join(html_parts)

    def _docs_generate_api(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Generate API documentation."""
        path = self._get_path(tool_input)
        output_dir = tool_input.get("output_dir", "docs/api")
        include_private = tool_input.get("include_private", False)

        if not path.exists():
            return SkillResponse(success=False, message=f"Path not found: {path}", error="not_found")

        # Check if pdoc or sphinx is available
        try:
            subprocess.run(["pdoc", "--version"], capture_output=True, check=True)
            has_pdoc = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            has_pdoc = False

        if has_pdoc:
            cmd = ["pdoc", "--output-dir", output_dir, str(path)]
            if not include_private:
                cmd.append("--skip-errors")

            return SkillResponse(
                success=True,
                message="Ready to generate API docs with pdoc",
                needs_confirmation=True,
                confirmation_type="execute",
                confirmation_message=f"Generate API documentation to {output_dir}?",
                data={
                    "command": " ".join(cmd),
                    "output_dir": output_dir,
                    "tool": "pdoc",
                }
            )
        else:
            return SkillResponse(
                success=False,
                message="pdoc not installed. Install with: pip install pdoc",
                error="pdoc_not_installed",
                data={"install_command": "pip install pdoc"}
            )

    def _docs_lint(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Check documentation for issues."""
        path = self._get_path(tool_input)
        check_links = tool_input.get("check_links", True)

        if not path.exists():
            return SkillResponse(success=False, message=f"Path not found: {path}", error="not_found")

        issues = []

        # Check markdown files
        md_files = list(path.rglob("*.md")) if path.is_dir() else [path]

        for md_file in md_files:
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    lines = content.split("\n")

                # Check for broken internal links
                if check_links:
                    link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
                    for i, line in enumerate(lines):
                        for match in link_pattern.finditer(line):
                            link_target = match.group(2)
                            if not link_target.startswith(("http://", "https://", "#")):
                                # Relative link
                                target_path = md_file.parent / link_target
                                if not target_path.exists():
                                    issues.append({
                                        "file": str(md_file),
                                        "line": i + 1,
                                        "type": "broken_link",
                                        "message": f"Broken link: {link_target}",
                                    })

                # Check for empty headings
                for i, line in enumerate(lines):
                    if re.match(r'^#+\s*$', line):
                        issues.append({
                            "file": str(md_file),
                            "line": i + 1,
                            "type": "empty_heading",
                            "message": "Empty heading",
                        })

                # Check for trailing whitespace
                for i, line in enumerate(lines):
                    if line.rstrip() != line and line.strip():
                        issues.append({
                            "file": str(md_file),
                            "line": i + 1,
                            "type": "trailing_whitespace",
                            "message": "Trailing whitespace",
                        })

            except UnicodeDecodeError:
                issues.append({
                    "file": str(md_file),
                    "type": "encoding_error",
                    "message": "Unable to read file (encoding issue)",
                })

        return SkillResponse(
            success=len(issues) == 0,
            message=f"Found {len(issues)} documentation issues",
            data={
                "issues": issues,
                "files_checked": len(md_files),
            }
        )

    def _docs_changelog(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Generate or update changelog."""
        path = self._get_path(tool_input)
        version = tool_input["version"]
        changes = tool_input["changes"]

        changelog_path = path / "CHANGELOG.md"
        today = datetime.now().strftime("%Y-%m-%d")

        # Build new entry
        entry_lines = [f"## [{version}] - {today}", ""]

        if changes.get("added"):
            entry_lines.append("### Added")
            for item in changes["added"]:
                entry_lines.append(f"- {item}")
            entry_lines.append("")

        if changes.get("changed"):
            entry_lines.append("### Changed")
            for item in changes["changed"]:
                entry_lines.append(f"- {item}")
            entry_lines.append("")

        if changes.get("fixed"):
            entry_lines.append("### Fixed")
            for item in changes["fixed"]:
                entry_lines.append(f"- {item}")
            entry_lines.append("")

        if changes.get("removed"):
            entry_lines.append("### Removed")
            for item in changes["removed"]:
                entry_lines.append(f"- {item}")
            entry_lines.append("")

        new_entry = "\n".join(entry_lines)

        # Check if changelog exists
        if changelog_path.exists():
            with open(changelog_path, "r", encoding="utf-8") as f:
                existing = f.read()

            # Insert after header
            if "# Changelog" in existing:
                parts = existing.split("\n", 2)
                if len(parts) >= 2:
                    updated = parts[0] + "\n\n" + new_entry + "\n" + parts[2] if len(parts) > 2 else parts[0] + "\n\n" + new_entry
                else:
                    updated = existing + "\n\n" + new_entry
            else:
                updated = "# Changelog\n\n" + new_entry + "\n\n" + existing
        else:
            updated = "# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n" + new_entry

        return SkillResponse(
            success=True,
            message=f"Generated changelog entry for v{version}",
            needs_confirmation=True,
            confirmation_type="write_file",
            confirmation_message=f"Update CHANGELOG.md with v{version} entry?",
            data={
                "path": str(changelog_path),
                "content": updated,
                "entry": new_entry,
                "version": version,
            }
        )
