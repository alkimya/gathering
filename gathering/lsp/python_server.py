"""
Python Language Server implementation using Jedi.

Provides autocomplete, diagnostics, hover, and go-to-definition for Python code.
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict
import ast
import re

logger = logging.getLogger(__name__)


class PythonLSPServer:
    """
    Python Language Server using Jedi for static analysis.

    Provides IDE features without requiring heavy dependencies.
    Falls back to AST-based analysis if Jedi is not available.
    """

    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        self.initialized = False
        self.use_jedi = False

        # Try to import Jedi
        try:
            import jedi
            self.jedi = jedi
            self.use_jedi = True
            logger.info("Using Jedi for Python LSP")
        except ImportError:
            logger.warning("Jedi not available, using fallback AST analysis")
            self.jedi = None

    async def initialize(self, workspace_path: str) -> dict:
        """Initialize the Python LSP server."""
        self.workspace_path = Path(workspace_path)
        self.initialized = True

        return {
            "capabilities": {
                "completionProvider": {
                    "resolveProvider": False,
                    "triggerCharacters": [".", "(", "["]
                },
                "hoverProvider": True,
                "definitionProvider": True,
                "diagnosticProvider": True
            }
        }

    async def shutdown(self):
        """Shutdown the server."""
        self.initialized = False

    async def get_completions(
        self,
        file_path: str,
        line: int,
        character: int,
        content: Optional[str] = None
    ) -> List[Dict]:
        """
        Get autocomplete suggestions.

        Args:
            file_path: Path to the Python file
            line: Line number (1-indexed)
            character: Character position (0-indexed)
            content: Optional file content (if not provided, reads from disk)

        Returns:
            List of completion items
        """
        if not self.initialized:
            await self.initialize(str(self.workspace_path))

        # Get file content
        if content is None:
            full_path = self.workspace_path / file_path
            if full_path.exists():
                content = full_path.read_text()
            else:
                return []

        if self.use_jedi:
            return await self._get_jedi_completions(content, line, character)
        else:
            return await self._get_fallback_completions(content, line, character)

    async def _get_jedi_completions(
        self,
        content: str,
        line: int,
        character: int
    ) -> List[Dict]:
        """Get completions using Jedi."""
        try:
            script = self.jedi.Script(content, path=str(self.workspace_path))
            completions = script.complete(line, character)

            items = []
            for completion in completions[:50]:  # Limit to 50 results
                item = {
                    "label": completion.name,
                    "kind": self._get_completion_kind(completion.type),
                    "detail": completion.type,
                    "insertText": completion.name,
                }

                # Add documentation if available
                if completion.docstring():
                    item["documentation"] = completion.docstring()[:500]

                items.append(item)

            return items

        except Exception as e:
            logger.error(f"Jedi completion error: {e}")
            return []

    async def _get_fallback_completions(
        self,
        content: str,
        line: int,
        character: int
    ) -> List[Dict]:
        """Fallback completion using simple parsing."""
        # Extract current line
        lines = content.split('\n')
        if line <= 0 or line > len(lines):
            return []

        current_line = lines[line - 1][:character]

        # Check if we're after a dot (member access)
        if '.' in current_line:
            # Simple completion for common imports
            return self._get_common_completions(current_line)

        # Keyword completions
        python_keywords = [
            "def", "class", "import", "from", "if", "else", "elif",
            "for", "while", "try", "except", "finally", "with", "as",
            "return", "yield", "pass", "break", "continue", "raise",
            "async", "await", "lambda", "True", "False", "None"
        ]

        # Extract partial word being typed
        match = re.search(r'(\w+)$', current_line)
        if match:
            partial = match.group(1).lower()
            keywords = [
                {
                    "label": kw,
                    "kind": 14,  # Keyword
                    "insertText": kw,
                    "detail": "keyword"
                }
                for kw in python_keywords
                if kw.startswith(partial)
            ]
            return keywords

        return []

    def _get_common_completions(self, line: str) -> List[Dict]:
        """Get completions for common Python modules."""
        common_completions = {
            "np.": ["array", "zeros", "ones", "arange", "linspace", "mean", "std", "sum"],
            "pd.": ["DataFrame", "Series", "read_csv", "read_json", "concat", "merge"],
            "os.": ["path", "getcwd", "listdir", "mkdir", "remove", "environ"],
            "sys.": ["argv", "exit", "path", "platform", "version"],
            "json.": ["loads", "dumps", "load", "dump"],
            "re.": ["search", "match", "findall", "sub", "compile"],
        }

        for prefix, methods in common_completions.items():
            if line.endswith(prefix):
                return [
                    {
                        "label": method,
                        "kind": 2,  # Method
                        "insertText": method,
                        "detail": f"{prefix}{method}"
                    }
                    for method in methods
                ]

        return []

    async def get_diagnostics(
        self,
        file_path: str,
        content: Optional[str] = None
    ) -> List[Dict]:
        """
        Get diagnostics (syntax errors, type issues) for a file.

        Returns:
            List of diagnostic items
        """
        if content is None:
            full_path = self.workspace_path / file_path
            if full_path.exists():
                content = full_path.read_text()
            else:
                return []

        diagnostics = []

        # Basic syntax checking with AST
        try:
            ast.parse(content)
        except SyntaxError as e:
            diagnostics.append({
                "range": {
                    "start": {"line": (e.lineno or 1) - 1, "character": (e.offset or 0) - 1},
                    "end": {"line": (e.lineno or 1) - 1, "character": (e.offset or 0) + 10}
                },
                "severity": 1,  # Error
                "message": str(e.msg),
                "source": "python"
            })

        # Check for common issues
        diagnostics.extend(self._check_common_issues(content))

        return diagnostics

    def _check_common_issues(self, content: str) -> List[Dict]:
        """Check for common Python issues."""
        issues = []
        lines = content.split('\n')

        for i, line in enumerate(lines):
            # Check for unused imports (simple heuristic)
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                # Extract imported name
                match = re.search(r'import\s+(\w+)', line)
                if match:
                    imported_name = match.group(1)
                    # Check if it's used anywhere else
                    if content.count(imported_name) == 1:
                        issues.append({
                            "range": {
                                "start": {"line": i, "character": 0},
                                "end": {"line": i, "character": len(line)}
                            },
                            "severity": 2,  # Warning
                            "message": f"'{imported_name}' imported but unused",
                            "source": "python-linter"
                        })

        return issues

    async def get_hover(
        self,
        file_path: str,
        line: int,
        character: int,
        content: Optional[str] = None
    ) -> Optional[Dict]:
        """Get hover information (documentation) at a position."""
        if not self.use_jedi:
            return None

        if content is None:
            full_path = self.workspace_path / file_path
            if full_path.exists():
                content = full_path.read_text()
            else:
                return None

        try:
            script = self.jedi.Script(content, path=str(self.workspace_path))
            names = script.help(line, character)

            if names:
                name = names[0]
                return {
                    "contents": {
                        "kind": "markdown",
                        "value": f"```python\n{name.full_name}\n```\n\n{name.docstring()}"
                    }
                }
        except Exception as e:
            logger.error(f"Hover error: {e}")

        return None

    async def get_definition(
        self,
        file_path: str,
        line: int,
        character: int,
        content: Optional[str] = None
    ) -> Optional[Dict]:
        """Get definition location for a symbol."""
        if not self.use_jedi:
            return None

        if content is None:
            full_path = self.workspace_path / file_path
            if full_path.exists():
                content = full_path.read_text()
            else:
                return None

        try:
            script = self.jedi.Script(content, path=str(self.workspace_path))
            definitions = script.goto(line, character)

            if definitions:
                definition = definitions[0]
                return {
                    "uri": f"file://{definition.module_path}",
                    "range": {
                        "start": {
                            "line": definition.line - 1 if definition.line else 0,
                            "character": definition.column if definition.column else 0
                        },
                        "end": {
                            "line": definition.line - 1 if definition.line else 0,
                            "character": definition.column + len(definition.name) if definition.column else 0
                        }
                    }
                }
        except Exception as e:
            logger.error(f"Go to definition error: {e}")

        return None

    def _get_completion_kind(self, jedi_type: str) -> int:
        """Convert Jedi type to LSP completion kind."""
        type_map = {
            "module": 9,
            "class": 7,
            "function": 3,
            "param": 6,
            "path": 17,
            "keyword": 14,
            "property": 10,
            "statement": 6,
        }
        return type_map.get(jedi_type, 1)  # Default to Text
