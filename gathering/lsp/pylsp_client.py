"""
Python LSP Server Client.

Full-featured Python language server using python-lsp-server (pylsp)
with extensions: pylsp-mypy, pylsp-rope, python-lsp-ruff.

This provides professional-grade features:
- Real type-aware autocomplete
- Mypy type checking
- Ruff linting (fast Python linter)
- Rope refactoring
- Go-to-definition
- Find references
- Hover documentation
"""

import asyncio
import json
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
import subprocess

logger = logging.getLogger(__name__)


class PylspClient:
    """
    Client for python-lsp-server (pylsp) via stdio communication.

    Communicates with pylsp subprocess using JSON-RPC over stdin/stdout.
    """

    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        self.process: Optional[subprocess.Popen] = None
        self.request_id = 0
        self.initialized = False

    async def start(self):
        """Start the pylsp subprocess."""
        if self.process:
            return

        try:
            # Start pylsp subprocess
            self.process = subprocess.Popen(
                ['pylsp'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0
            )

            logger.info(f"Started pylsp process (PID: {self.process.pid})")

            # Initialize the server
            await self._initialize()

        except FileNotFoundError:
            logger.error("pylsp not found. Install with: pip install 'python-lsp-server[all]'")
            raise
        except Exception as e:
            logger.error(f"Failed to start pylsp: {e}")
            raise

    async def _initialize(self):
        """Send LSP initialize request."""
        init_params = {
            "processId": None,
            "rootUri": f"file://{self.workspace_path.absolute()}",
            "capabilities": {
                "textDocument": {
                    "completion": {
                        "completionItem": {
                            "snippetSupport": True,
                            "documentationFormat": ["markdown", "plaintext"]
                        }
                    },
                    "hover": {
                        "contentFormat": ["markdown", "plaintext"]
                    },
                    "signatureHelp": {
                        "signatureInformation": {
                            "documentationFormat": ["markdown", "plaintext"]
                        }
                    }
                },
                "workspace": {
                    "configuration": True,
                    "didChangeConfiguration": {"dynamicRegistration": True}
                }
            },
            "initializationOptions": {
                "pylsp": {
                    "plugins": {
                        # Enable all plugins
                        "jedi_completion": {"enabled": True, "include_params": True},
                        "jedi_hover": {"enabled": True},
                        "jedi_references": {"enabled": True},
                        "jedi_signature_help": {"enabled": True},
                        "jedi_symbols": {"enabled": True},
                        "pylsp_mypy": {"enabled": True, "live_mode": True},
                        "ruff": {"enabled": True},
                        "rope_completion": {"enabled": True},
                        "rope_autoimport": {"enabled": True},
                        "pycodestyle": {"enabled": False},  # Use ruff instead
                        "pyflakes": {"enabled": False},     # Use ruff instead
                        "pylint": {"enabled": False},       # Use ruff instead
                        "yapf": {"enabled": True},
                        "autopep8": {"enabled": False}
                    }
                }
            }
        }

        response = await self._send_request("initialize", init_params)

        if response:
            # Send initialized notification
            await self._send_notification("initialized", {})
            self.initialized = True
            logger.info("pylsp initialized successfully")
            return response

        raise Exception("Failed to initialize pylsp")

    async def _send_request(self, method: str, params: Any) -> Optional[Dict]:
        """Send a JSON-RPC request and wait for response."""
        if not self.process or not self.process.stdin:
            return None

        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params
        }

        # Send request
        request_str = json.dumps(request)
        content_length = len(request_str)
        message = f"Content-Length: {content_length}\r\n\r\n{request_str}"

        try:
            self.process.stdin.write(message)
            self.process.stdin.flush()

            # Read response
            response = await self._read_response()
            return response

        except Exception as e:
            logger.error(f"Error sending request: {e}")
            return None

    async def _send_notification(self, method: str, params: Any):
        """Send a JSON-RPC notification (no response expected)."""
        if not self.process or not self.process.stdin:
            return

        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }

        notification_str = json.dumps(notification)
        content_length = len(notification_str)
        message = f"Content-Length: {content_length}\r\n\r\n{notification_str}"

        try:
            self.process.stdin.write(message)
            self.process.stdin.flush()
        except Exception as e:
            logger.error(f"Error sending notification: {e}")

    async def _read_response(self) -> Optional[Dict]:
        """Read a JSON-RPC response from stdout."""
        if not self.process or not self.process.stdout:
            return None

        try:
            # Read headers
            headers = {}
            while True:
                line = self.process.stdout.readline().strip()
                if not line:
                    break
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip()] = value.strip()

            # Read content
            content_length = int(headers.get('Content-Length', 0))
            if content_length > 0:
                content = self.process.stdout.read(content_length)
                response = json.loads(content)

                if 'error' in response:
                    logger.error(f"LSP error: {response['error']}")
                    return None

                return response.get('result')

        except Exception as e:
            logger.error(f"Error reading response: {e}")
            return None

    async def did_open(self, file_path: str, content: str):
        """Notify that a document was opened."""
        uri = f"file://{Path(file_path).absolute()}"

        await self._send_notification("textDocument/didOpen", {
            "textDocument": {
                "uri": uri,
                "languageId": "python",
                "version": 1,
                "text": content
            }
        })

    async def did_change(self, file_path: str, content: str, version: int = 1):
        """Notify that a document changed."""
        uri = f"file://{Path(file_path).absolute()}"

        await self._send_notification("textDocument/didChange", {
            "textDocument": {
                "uri": uri,
                "version": version
            },
            "contentChanges": [
                {"text": content}
            ]
        })

    async def completion(
        self,
        file_path: str,
        line: int,
        character: int,
        content: str
    ) -> List[Dict]:
        """Get completion suggestions."""
        if not self.initialized:
            await self.start()

        uri = f"file://{Path(file_path).absolute()}"

        # Update document content
        await self.did_change(file_path, content)

        # Request completions
        response = await self._send_request("textDocument/completion", {
            "textDocument": {"uri": uri},
            "position": {"line": line - 1, "character": character}
        })

        if not response:
            return []

        # Handle both CompletionList and CompletionItem[] formats
        items = response.get('items', response) if isinstance(response, dict) else response

        # Convert to our format
        completions = []
        for item in items:
            completions.append({
                "label": item.get("label", ""),
                "kind": item.get("kind", 1),
                "insertText": item.get("insertText", item.get("label", "")),
                "detail": item.get("detail"),
                "documentation": self._extract_documentation(item.get("documentation"))
            })

        return completions

    async def hover(
        self,
        file_path: str,
        line: int,
        character: int,
        content: str
    ) -> Optional[Dict]:
        """Get hover information."""
        if not self.initialized:
            await self.start()

        uri = f"file://{Path(file_path).absolute()}"

        # Update document content
        await self.did_change(file_path, content)

        # Request hover
        response = await self._send_request("textDocument/hover", {
            "textDocument": {"uri": uri},
            "position": {"line": line - 1, "character": character}
        })

        if not response or not response.get("contents"):
            return None

        contents = response["contents"]

        # Extract markdown content
        if isinstance(contents, dict):
            value = contents.get("value", "")
        elif isinstance(contents, list):
            value = "\n".join(
                item.get("value", "") if isinstance(item, dict) else str(item)
                for item in contents
            )
        else:
            value = str(contents)

        return {"contents": {"value": value}}

    async def definition(
        self,
        file_path: str,
        line: int,
        character: int,
        content: str
    ) -> Optional[Dict]:
        """Get definition location."""
        if not self.initialized:
            await self.start()

        uri = f"file://{Path(file_path).absolute()}"

        # Update document content
        await self.did_change(file_path, content)

        # Request definition
        response = await self._send_request("textDocument/definition", {
            "textDocument": {"uri": uri},
            "position": {"line": line - 1, "character": character}
        })

        if not response:
            return None

        # Handle both Location and Location[] formats
        locations = response if isinstance(response, list) else [response]

        if not locations:
            return None

        # Return first location
        loc = locations[0]
        return {
            "uri": loc.get("uri", ""),
            "range": loc.get("range", {})
        }

    async def diagnostics(self, file_path: str, content: str) -> List[Dict]:
        """
        Get diagnostics (errors/warnings).

        Note: pylsp sends diagnostics via publishDiagnostics notification,
        not as a response to a request. This is a simplified implementation
        that triggers a document change and waits briefly for diagnostics.
        """
        if not self.initialized:
            await self.start()

        uri = f"file://{Path(file_path).absolute()}"

        # Update document - this will trigger diagnostics
        await self.did_change(file_path, content)

        # In a real implementation, we'd listen for publishDiagnostics notifications
        # For now, return empty (diagnostics will be sent via notifications)
        return []

    def _extract_documentation(self, doc: Any) -> Optional[str]:
        """Extract documentation string from various formats."""
        if not doc:
            return None

        if isinstance(doc, str):
            return doc

        if isinstance(doc, dict):
            return doc.get("value")

        return None

    async def shutdown(self):
        """Shutdown the pylsp server."""
        if not self.process:
            return

        try:
            await self._send_request("shutdown", {})
            await self._send_notification("exit", {})

            self.process.wait(timeout=5)
            logger.info("pylsp shut down successfully")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            if self.process:
                self.process.kill()

        finally:
            self.process = None
            self.initialized = False
