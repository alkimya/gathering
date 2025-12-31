"""
Rust Language Server Plugin.

Provides LSP capabilities for Rust using keyword-based autocomplete
and basic syntax checking.
"""

from typing import Optional, List, Dict
import re
from pathlib import Path

from gathering.lsp.plugin_system import lsp_plugin
from gathering.lsp.manager import BaseLSPServer


@lsp_plugin(
    language="rust",
    name="Rust LSP",
    version="1.0.0",
    author="Gathering Team",
    description="Rust language server with autocomplete and diagnostics",
    dependencies=[]  # Can be upgraded to use rust-analyzer later
)
class RustLSPServer(BaseLSPServer):
    """
    Rust Language Server.

    Provides:
    - Keyword autocomplete
    - Standard library completion
    - Basic syntax checking
    - Common patterns
    """

    def __init__(self, workspace_path: str):
        super().__init__(workspace_path)

        # Rust keywords
        self.rust_keywords = [
            "fn", "let", "mut", "const", "static", "if", "else", "match",
            "loop", "while", "for", "in", "break", "continue", "return",
            "struct", "enum", "impl", "trait", "type", "mod", "use", "pub",
            "crate", "super", "self", "Self", "async", "await", "move",
            "ref", "where", "unsafe", "extern", "as", "dyn"
        ]

        # Common types
        self.rust_types = [
            "i8", "i16", "i32", "i64", "i128", "isize",
            "u8", "u16", "u32", "u64", "u128", "usize",
            "f32", "f64", "bool", "char", "str",
            "String", "Vec", "Option", "Result", "Box", "Rc", "Arc"
        ]

        # Standard library common items
        self.std_items = {
            "std::": [
                "collections", "io", "fs", "env", "path", "process",
                "thread", "sync", "time", "net"
            ],
            "std::collections::": [
                "HashMap", "HashSet", "BTreeMap", "BTreeSet", "LinkedList", "VecDeque"
            ],
            "std::io::": [
                "Read", "Write", "BufRead", "BufReader", "BufWriter", "stdin", "stdout", "stderr"
            ],
            "std::fs::": [
                "File", "read", "write", "read_to_string", "OpenOptions"
            ],
            "Vec<": ["new", "push", "pop", "len", "is_empty", "clear", "append"],
            "String::": ["new", "from", "push", "push_str", "len", "is_empty", "chars"],
            "Option<": ["Some", "None", "unwrap", "expect", "map", "and_then"],
            "Result<": ["Ok", "Err", "unwrap", "expect", "map", "and_then"],
        }

        # Macros
        self.rust_macros = [
            "println!", "print!", "eprintln!", "eprint!",
            "format!", "panic!", "assert!", "assert_eq!",
            "vec!", "dbg!", "todo!", "unimplemented!"
        ]

    async def initialize(self, workspace_path: str) -> dict:
        """Initialize Rust LSP server."""
        self.workspace_path = Path(workspace_path)
        self.initialized = True

        return {
            "capabilities": {
                "completionProvider": {
                    "resolveProvider": False,
                    "triggerCharacters": [":", ".", "<"]
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
        """Get Rust completions."""
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

        # Check for std library completions
        for prefix, items in self.std_items.items():
            if current_line.endswith(prefix):
                return [
                    {
                        "label": item,
                        "kind": 9 if prefix.endswith("::") else 2,  # Module or Method
                        "insertText": item,
                        "detail": f"{prefix}{item}",
                        "documentation": f"Rust std library: {prefix}{item}"
                    }
                    for item in items
                ]

        # Check for macros
        if current_line.endswith("!"):
            partial = current_line.split()[-1][:-1] if current_line.split() else ""
            return [
                {
                    "label": macro,
                    "kind": 3,  # Function (macro)
                    "insertText": macro,
                    "detail": "macro",
                    "documentation": f"Rust macro: {macro}"
                }
                for macro in self.rust_macros
                if macro.startswith(partial)
            ]

        # Check for keyword or type completions
        match = re.search(r'(\w+)$', current_line)
        if match:
            partial = match.group(1)

            # Combine keywords, types, and macros
            all_completions = []

            # Keywords
            all_completions.extend([
                {
                    "label": kw,
                    "kind": 14,  # Keyword
                    "insertText": kw,
                    "detail": "keyword"
                }
                for kw in self.rust_keywords
                if kw.startswith(partial)
            ])

            # Types
            all_completions.extend([
                {
                    "label": typ,
                    "kind": 7,  # Class (type)
                    "insertText": typ,
                    "detail": "type"
                }
                for typ in self.rust_types
                if typ.startswith(partial)
            ])

            # Macros (without the !)
            all_completions.extend([
                {
                    "label": macro,
                    "kind": 3,  # Function
                    "insertText": macro,
                    "detail": "macro"
                }
                for macro in self.rust_macros
                if macro[:-1].startswith(partial)  # Remove ! for comparison
            ])

            return all_completions

        return []

    async def get_diagnostics(
        self,
        file_path: str,
        content: Optional[str] = None
    ) -> List[Dict]:
        """Get Rust diagnostics."""
        if content is None:
            full_path = self.workspace_path / file_path
            if full_path.exists():
                content = full_path.read_text()
            else:
                return []

        diagnostics = []
        lines = content.split('\n')

        for i, line in enumerate(lines):
            # Check for missing semicolons (basic heuristic)
            stripped = line.strip()
            if stripped and not stripped.endswith((';', '{', '}', ',')):
                # Check if it's a statement that should end with semicolon
                if any(stripped.startswith(kw) for kw in ['let', 'return', 'use']):
                    if not stripped.endswith('!'):  # Macros don't need semicolons
                        diagnostics.append({
                            "range": {
                                "start": {"line": i, "character": 0},
                                "end": {"line": i, "character": len(line)}
                            },
                            "severity": 3,  # Information
                            "message": "Consider adding a semicolon ';'",
                            "source": "rust-linter"
                        })

            # Check for unwrap() usage (warning)
            if '.unwrap()' in line:
                col = line.find('.unwrap()')
                diagnostics.append({
                    "range": {
                        "start": {"line": i, "character": col},
                        "end": {"line": i, "character": col + 9}
                    },
                    "severity": 2,  # Warning
                    "message": "Using unwrap() can cause panics. Consider using expect() or match instead",
                    "source": "rust-linter"
                })

            # Check for println! in release code
            if 'println!' in line and not line.strip().startswith('//'):
                diagnostics.append({
                    "range": {
                        "start": {"line": i, "character": line.find('println!')},
                        "end": {"line": i, "character": line.find('println!') + 8}
                    },
                    "severity": 3,  # Information
                    "message": "Consider using proper logging instead of println! in production",
                    "source": "rust-linter"
                })

        return diagnostics

    async def get_hover(
        self,
        file_path: str,
        line: int,
        character: int,
        content: Optional[str] = None
    ) -> Optional[Dict]:
        """Rust hover not implemented (would need rust-analyzer)."""
        return None

    async def get_definition(
        self,
        file_path: str,
        line: int,
        character: int,
        content: Optional[str] = None
    ) -> Optional[Dict]:
        """Rust go-to-definition not implemented (would need rust-analyzer)."""
        return None
