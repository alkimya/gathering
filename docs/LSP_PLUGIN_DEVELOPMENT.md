## 🔌 LSP Plugin Development Guide

**Audience**: Developers who want to add custom language support
**Version**: 1.0.0
**Date**: 2025-12-30

---

## 🎯 Overview

The Gathering LSP system is **fully extensible**. You can add support for any programming language by creating a simple plugin.

### Architecture Benefits

✅ **Modular**: Plugins are self-contained
✅ **Auto-discovered**: Drop in `plugins/` directory and restart
✅ **Type-safe**: Strong interfaces with BaseLSPServer
✅ **No core modification**: Add features without touching main codebase

---

## 📁 Plugin Structure

```
gathering/lsp/plugins/
├── __init__.py
├── javascript_lsp.py      # Example: JavaScript/TypeScript
├── rust_lsp.py             # Your custom plugin
└── my_custom_lang.py       # Another custom plugin
```

---

## 🚀 Quick Start - Create a Plugin

### Step 1: Create Plugin File

Create `gathering/lsp/plugins/rust_lsp.py`:

```python
from gathering.lsp.plugin_system import lsp_plugin
from gathering.lsp.manager import BaseLSPServer
from typing import Optional, List, Dict

@lsp_plugin(
    language="rust",
    name="Rust LSP",
    version="1.0.0",
    author="Your Name",
    description="Rust language server integration",
    dependencies=["rust-analyzer"]  # Optional external tools
)
class RustLSPServer(BaseLSPServer):
    """Rust language server implementation."""

    async def initialize(self, workspace_path: str) -> dict:
        """
        Initialize the LSP server.

        Returns server capabilities.
        """
        self.workspace_path = workspace_path
        self.initialized = True

        return {
            "capabilities": {
                "completionProvider": {
                    "triggerCharacters": [".", ":"]
                },
                "hoverProvider": True,
                "definitionProvider": True,
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
        """
        Get autocomplete suggestions.

        Args:
            file_path: Path to file being edited
            line: Line number (1-indexed)
            character: Character position (0-indexed)
            content: File content (or None to read from disk)

        Returns:
            List of completion items
        """
        # Your completion logic here
        return [
            {
                "label": "println!",
                "kind": 3,  # Function/Macro
                "detail": "Rust macro",
                "insertText": "println!(\"{}\")",
                "documentation": "Prints to stdout with newline"
            }
        ]

    async def get_diagnostics(
        self,
        file_path: str,
        content: Optional[str] = None
    ) -> List[Dict]:
        """
        Get diagnostics (errors, warnings).

        Returns:
            List of diagnostic items
        """
        # Your linting logic here
        return []

    async def get_hover(
        self,
        file_path: str,
        line: int,
        character: int,
        content: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Get hover documentation.

        Returns:
            Hover info or None
        """
        return {
            "contents": {
                "kind": "markdown",
                "value": "# Documentation\\n\\nHover text here"
            }
        }

    async def get_definition(
        self,
        file_path: str,
        line: int,
        character: int,
        content: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Get symbol definition location.

        Returns:
            Definition location or None
        """
        return {
            "uri": f"file://{file_path}",
            "range": {
                "start": {"line": 10, "character": 0},
                "end": {"line": 10, "character": 10}
            }
        }
```

### Step 2: Test Your Plugin

```bash
# Start the API server
python -m gathering.api

# Test initialization
curl -X POST http://localhost:8000/api/lsp/1/initialize \
  -H "Content-Type: application/json" \
  -d '{
    "language": "rust",
    "workspace_path": "/path/to/workspace"
  }'

# Test completions
curl -X POST http://localhost:8000/api/lsp/1/completions?language=rust \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "main.rs",
    "line": 5,
    "character": 10
  }'
```

### Step 3: Deploy

That's it! Your plugin is automatically discovered and available.

---

## 🔧 Advanced Features

### 1. External LSP Server Integration

Wrap an external LSP server (like `rust-analyzer`):

```python
import subprocess
import json

@lsp_plugin(
    language="rust",
    name="Rust Analyzer",
    version="1.0.0",
    dependencies=["rust-analyzer"]
)
class RustAnalyzerLSP(BaseLSPServer):
    def __init__(self, workspace_path: str):
        super().__init__(workspace_path)
        self.process = None

    async def initialize(self, workspace_path: str) -> dict:
        # Start rust-analyzer process
        self.process = subprocess.Popen(
            ["rust-analyzer"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Send LSP initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "rootUri": f"file://{workspace_path}",
                "capabilities": {}
            }
        }

        self._send_lsp_message(init_request)
        response = self._receive_lsp_message()

        self.initialized = True
        return response.get("result", {})

    def _send_lsp_message(self, message: dict):
        """Send JSON-RPC message to LSP server."""
        content = json.dumps(message)
        header = f"Content-Length: {len(content)}\\r\\n\\r\\n"
        self.process.stdin.write((header + content).encode())
        self.process.stdin.flush()

    def _receive_lsp_message(self) -> dict:
        """Receive JSON-RPC message from LSP server."""
        # Read Content-Length header
        header = self.process.stdout.readline().decode()
        length = int(header.split(":")[1].strip())

        # Skip empty line
        self.process.stdout.readline()

        # Read content
        content = self.process.stdout.read(length).decode()
        return json.loads(content)

    async def shutdown(self):
        """Shutdown the external LSP server."""
        if self.process:
            self.process.terminate()
            self.process.wait()
        self.initialized = False
```

### 2. Configuration Support

```python
@lsp_plugin(
    language="mylang",
    name="MyLang LSP",
    config_schema={
        "linter_rules": {
            "type": "object",
            "description": "Linting rules configuration"
        },
        "format_on_save": {
            "type": "boolean",
            "default": True
        }
    }
)
class MyLangLSP(BaseLSPServer):
    def __init__(self, workspace_path: str, config: dict = None):
        super().__init__(workspace_path)
        self.config = config or {}
        self.format_on_save = self.config.get("format_on_save", True)
```

### 3. Custom Capabilities

```python
class CustomLSPServer(BaseLSPServer):
    async def initialize(self, workspace_path: str) -> dict:
        return {
            "capabilities": {
                "completionProvider": True,
                "hoverProvider": True,
                "definitionProvider": True,
                "diagnosticProvider": True,

                # Custom capabilities
                "executeCommandProvider": {
                    "commands": ["mylang.formatCode", "mylang.runTests"]
                },
                "codeActionProvider": True,
                "referencesProvider": True,
                "renameProvider": True
            }
        }

    async def execute_command(self, command: str, arguments: list):
        """Execute custom commands."""
        if command == "mylang.formatCode":
            # Format code
            return {"formatted": True}

        elif command == "mylang.runTests":
            # Run tests
            return {"tests_passed": 42, "tests_failed": 0}
```

---

## 📚 API Reference

### BaseLSPServer Methods

All plugins must inherit from `BaseLSPServer` and implement these methods:

#### `async initialize(workspace_path: str) -> dict`

Initialize the LSP server. Returns server capabilities.

**Returns**:
```python
{
    "capabilities": {
        "completionProvider": bool | dict,
        "hoverProvider": bool,
        "definitionProvider": bool,
        "diagnosticProvider": bool
    }
}
```

#### `async get_completions(file_path, line, character, content=None) -> list`

Get autocomplete suggestions.

**Returns**: List of completion items:
```python
[{
    "label": str,           # Display text
    "kind": int,            # Completion kind (see LSP spec)
    "detail": str,          # Additional info
    "insertText": str,      # Text to insert
    "documentation": str    # Documentation (optional)
}]
```

**Completion Kinds**:
- `1` - Text
- `2` - Method
- `3` - Function
- `6` - Variable
- `7` - Class
- `9` - Module
- `14` - Keyword

#### `async get_diagnostics(file_path, content=None) -> list`

Get diagnostics (errors, warnings).

**Returns**: List of diagnostic items:
```python
[{
    "range": {
        "start": {"line": int, "character": int},
        "end": {"line": int, "character": int}
    },
    "severity": int,  # 1=Error, 2=Warning, 3=Info, 4=Hint
    "message": str,
    "source": str     # e.g., "mylang-linter"
}]
```

#### `async get_hover(file_path, line, character, content=None) -> dict | None`

Get hover documentation.

**Returns**:
```python
{
    "contents": {
        "kind": "markdown" | "plaintext",
        "value": str  # Documentation text
    }
}
```

#### `async get_definition(file_path, line, character, content=None) -> dict | None`

Get symbol definition location.

**Returns**:
```python
{
    "uri": str,  # File URI (file:///path/to/file)
    "range": {
        "start": {"line": int, "character": int},
        "end": {"line": int, "character": int}
    }
}
```

---

## 🧪 Testing Your Plugin

### Unit Tests

```python
# tests/test_mylang_lsp.py
import pytest
from gathering.lsp.plugins.mylang_lsp import MyLangLSPServer

@pytest.mark.asyncio
async def test_completions():
    server = MyLangLSPServer("/tmp/workspace")
    await server.initialize("/tmp/workspace")

    completions = await server.get_completions(
        file_path="test.mylang",
        line=1,
        character=5,
        content="my_fu"
    )

    assert len(completions) > 0
    assert completions[0]["label"] == "my_function"

@pytest.mark.asyncio
async def test_diagnostics():
    server = MyLangLSPServer("/tmp/workspace")
    await server.initialize("/tmp/workspace")

    diagnostics = await server.get_diagnostics(
        file_path="test.mylang",
        content="invalid syntax here"
    )

    assert len(diagnostics) > 0
    assert diagnostics[0]["severity"] == 1  # Error
```

---

## 🌟 Example Plugins

### 1. Simple Keyword Autocomplete

```python
@lsp_plugin(language="sql", name="SQL LSP", version="1.0.0")
class SQLLSPServer(BaseLSPServer):
    SQL_KEYWORDS = ["SELECT", "FROM", "WHERE", "JOIN", "GROUP BY"]

    async def get_completions(self, file_path, line, character, content=None):
        # Get current word being typed
        if content:
            lines = content.split('\\n')
            current_line = lines[line-1][:character]
            word_match = re.search(r'(\\w+)$', current_line)

            if word_match:
                partial = word_match.group(1).upper()
                return [
                    {"label": kw, "kind": 14, "insertText": kw}
                    for kw in self.SQL_KEYWORDS
                    if kw.startswith(partial)
                ]

        return []
```

### 2. Regex-based Linter

```python
@lsp_plugin(language="python", name="Python Style Checker", version="1.0.0")
class PythonStyleLSP(BaseLSPServer):
    async def get_diagnostics(self, file_path, content=None):
        diagnostics = []
        lines = content.split('\\n')

        for i, line in enumerate(lines):
            # Check line length > 80
            if len(line) > 80:
                diagnostics.append({
                    "range": {
                        "start": {"line": i, "character": 80},
                        "end": {"line": i, "character": len(line)}
                    },
                    "severity": 2,  # Warning
                    "message": "Line exceeds 80 characters"
                })

        return diagnostics
```

---

## 🚀 Deployment

### Option 1: Built-in Plugin

Place your plugin in `gathering/lsp/plugins/your_plugin.py`. It will be auto-discovered on startup.

### Option 2: External Plugin

```python
# In your application code
from gathering.lsp.plugin_system import LSPPluginRegistry
from your_package import YourLSPServer

LSPPluginRegistry.register("yourlang")(YourLSPServer)
```

### Option 3: Dynamic Discovery

```python
# Discover from custom directory
from gathering.lsp.plugin_system import LSPPluginRegistry

LSPPluginRegistry.discover_plugins("/path/to/custom/plugins")
```

---

## 📊 Best Practices

### Performance

✅ **Cache results** when possible
✅ **Limit completion items** to ~50 results
✅ **Use async/await** for I/O operations
✅ **Lazy load** external tools

### Error Handling

✅ **Catch exceptions** and log errors
✅ **Return empty lists** on error (don't crash)
✅ **Provide helpful error messages**

### Code Quality

✅ **Type hints** for all methods
✅ **Docstrings** for public APIs
✅ **Unit tests** for core functionality
✅ **Follow PEP 8** style guide

---

## 📞 Support

- **Documentation**: [PHASE8_ADVANCED_IDE.md](PHASE8_ADVANCED_IDE.md)
- **Examples**: `gathering/lsp/plugins/`
- **Issues**: GitHub Issues

---

**Happy Plugin Development! 🎉**

Your plugins make Gathering IDE better for everyone!
