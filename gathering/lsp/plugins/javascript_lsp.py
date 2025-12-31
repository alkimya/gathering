"""
JavaScript/TypeScript LSP Plugin Example.

Demonstrates how to create a custom LSP server plugin.
"""

from typing import Optional, List, Dict
import re
from pathlib import Path

from gathering.lsp.plugin_system import lsp_plugin
from gathering.lsp.manager import BaseLSPServer


@lsp_plugin(
    language="javascript",
    name="JavaScript LSP",
    version="1.0.0",
    author="Gathering Team",
    description="Basic JavaScript language server with autocomplete",
    dependencies=[]
)
class JavaScriptLSPServer(BaseLSPServer):
    """
    Simple JavaScript LSP server.

    Provides basic autocomplete for:
    - JavaScript keywords
    - Common DOM APIs
    - Node.js APIs
    """

    def __init__(self, workspace_path: str):
        super().__init__(workspace_path)
        self.js_keywords = [
            "function", "const", "let", "var", "if", "else", "for", "while",
            "return", "class", "extends", "constructor", "async", "await",
            "import", "export", "default", "from", "try", "catch", "finally",
            "throw", "new", "this", "super", "static", "get", "set"
        ]

        self.dom_apis = {
            "document.": [
                "getElementById", "querySelector", "querySelectorAll",
                "createElement", "createTextNode", "addEventListener",
                "body", "head", "title", "cookie"
            ],
            "console.": [
                "log", "error", "warn", "info", "debug", "table", "time", "timeEnd"
            ],
            "window.": [
                "setTimeout", "setInterval", "clearTimeout", "clearInterval",
                "fetch", "alert", "confirm", "prompt", "localStorage", "sessionStorage"
            ],
            "Array.": [
                "from", "isArray", "of"
            ],
            "Object.": [
                "keys", "values", "entries", "assign", "freeze", "seal"
            ],
            "Math.": [
                "random", "floor", "ceil", "round", "abs", "max", "min", "sqrt", "pow"
            ]
        }

    async def initialize(self, workspace_path: str) -> dict:
        """Initialize JavaScript LSP server."""
        self.workspace_path = Path(workspace_path)
        self.initialized = True

        return {
            "capabilities": {
                "completionProvider": {
                    "resolveProvider": False,
                    "triggerCharacters": [".", "("]
                },
                "hoverProvider": False,
                "definitionProvider": False,
                "diagnosticProvider": True
            }
        }

    async def get_completions(
        self,
        file_path: str,
        line: int,
        character: int,
        content: Optional[str] = None
    ) -> List[Dict]:
        """Get JavaScript completions."""
        if content is None:
            full_path = self.workspace_path / file_path
            if full_path.exists():
                content = full_path.read_text()
            else:
                return []

        lines = content.split('\n')
        if line <= 0 or line > len(lines):
            return []

        current_line = lines[line - 1][:character]

        # Check for API completions (document., console., etc.)
        for prefix, methods in self.dom_apis.items():
            if current_line.endswith(prefix):
                return [
                    {
                        "label": method,
                        "kind": 2,  # Method
                        "insertText": method,
                        "detail": f"{prefix}{method}",
                        "documentation": f"JavaScript {prefix}{method}"
                    }
                    for method in methods
                ]

        # Check for keyword completions
        match = re.search(r'(\w+)$', current_line)
        if match:
            partial = match.group(1)
            return [
                {
                    "label": kw,
                    "kind": 14,  # Keyword
                    "insertText": kw,
                    "detail": "keyword"
                }
                for kw in self.js_keywords
                if kw.startswith(partial)
            ]

        return []

    async def get_diagnostics(
        self,
        file_path: str,
        content: Optional[str] = None
    ) -> List[Dict]:
        """Get JavaScript diagnostics."""
        if content is None:
            full_path = self.workspace_path / file_path
            if full_path.exists():
                content = full_path.read_text()
            else:
                return []

        diagnostics = []
        lines = content.split('\n')

        # Simple lint checks
        for i, line in enumerate(lines):
            # Check for console.log (warn about leaving it in production)
            if 'console.log' in line and not line.strip().startswith('//'):
                diagnostics.append({
                    "range": {
                        "start": {"line": i, "character": 0},
                        "end": {"line": i, "character": len(line)}
                    },
                    "severity": 2,  # Warning
                    "message": "console.log() call should be removed before production",
                    "source": "javascript-linter"
                })

            # Check for var usage (suggest const/let)
            if re.search(r'\bvar\s+\w+', line):
                diagnostics.append({
                    "range": {
                        "start": {"line": i, "character": line.find('var')},
                        "end": {"line": i, "character": line.find('var') + 3}
                    },
                    "severity": 3,  # Information
                    "message": "Consider using 'const' or 'let' instead of 'var'",
                    "source": "javascript-linter"
                })

        return diagnostics

    async def get_hover(
        self,
        file_path: str,
        line: int,
        character: int,
        content: Optional[str] = None
    ) -> Optional[Dict]:
        """JavaScript hover not implemented."""
        return None

    async def get_definition(
        self,
        file_path: str,
        line: int,
        character: int,
        content: Optional[str] = None
    ) -> Optional[Dict]:
        """JavaScript go-to-definition not implemented."""
        return None


# Also register TypeScript with the same server for now
@lsp_plugin(
    language="typescript",
    name="TypeScript LSP",
    version="1.0.0",
    author="Gathering Team",
    description="Basic TypeScript language server (shares JavaScript implementation)",
    dependencies=[]
)
class TypeScriptLSPServer(JavaScriptLSPServer):
    """TypeScript LSP - extends JavaScript LSP."""

    def __init__(self, workspace_path: str):
        super().__init__(workspace_path)

        # Add TypeScript-specific keywords
        self.js_keywords.extend([
            "interface", "type", "enum", "namespace", "declare",
            "public", "private", "protected", "readonly", "abstract"
        ])
