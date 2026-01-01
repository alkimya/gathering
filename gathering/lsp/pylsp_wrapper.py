"""
Simplified pylsp wrapper that works synchronously.

Since asyncio subprocess communication with LSP is complex,
this uses a simpler approach: directly import and use pylsp's components.
"""

import logging
from typing import Optional, List, Dict
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import pylsp components
try:
    from pylsp import uris
    from pylsp.workspace import Workspace, Document
    from pylsp.config.config import Config
    from pylsp_mypy import plugin as mypy_plugin
    from pylsp import hookimpl

    PYLSP_AVAILABLE = True
except ImportError:
    PYLSP_AVAILABLE = False
    logger.warning("python-lsp-server not available")


class PylspWrapper:
    """
    Wrapper around pylsp that can be used directly without subprocess communication.

    This approach directly uses pylsp's internal APIs instead of JSON-RPC.
    """

    def __init__(self, workspace_path: str):
        if not PYLSP_AVAILABLE:
            raise ImportError("python-lsp-server not installed")

        self.workspace_path = Path(workspace_path)
        self.workspace_uri = uris.from_fs_path(str(self.workspace_path))

        # Create workspace
        self.workspace = Workspace(self.workspace_uri, None)

        # Create config with plugins enabled
        self.config = Config(
            self.workspace_uri,
            {},
            0,
            {
                "pylsp": {
                    "plugins": {
                        "jedi_completion": {"enabled": True, "include_params": True},
                        "jedi_hover": {"enabled": True},
                        "jedi_references": {"enabled": True},
                        "jedi_signature_help": {"enabled": True},
                        "jedi_symbols": {"enabled": True},
                        "rope_completion": {"enabled": True},
                        "rope_autoimport": {"enabled": True},
                        "pylsp_mypy": {"enabled": True, "live_mode": False},
                        "ruff": {"enabled": True},
                        "pycodestyle": {"enabled": False},
                        "pyflakes": {"enabled": False},
                        "pylint": {"enabled": False},
                        "yapf": {"enabled": True},
                    }
                }
            }
        )

    def get_completions(
        self,
        file_path: str,
        line: int,
        character: int,
        content: str
    ) -> List[Dict]:
        """Get completions from pylsp."""
        try:
            from pylsp.plugins.jedi_completion import pylsp_completions as jedi_completions

            # Create document URI
            full_path = self.workspace_path / file_path
            doc_uri = uris.from_fs_path(str(full_path))

            # Create or update document
            doc = self.workspace.get_maybe_document(doc_uri)
            if not doc:
                doc = Document(doc_uri, self.workspace, content)
                self.workspace._docs[doc_uri] = doc
            else:
                # Update content
                doc._source = content

            # LSP uses 0-based line numbers
            position = {"line": line - 1, "character": character}

            completions = []

            # Get Jedi completions (config, doc, position)
            try:
                completions = jedi_completions(
                    self.config,
                    doc,
                    position
                ) or []
            except Exception as e:
                logger.error(f"Jedi completion error: {e}", exc_info=True)
                completions = []

            # Convert to our format
            result = []
            for item in completions:
                result.append({
                    "label": item.get("label", ""),
                    "kind": item.get("kind", 1),
                    "insertText": item.get("insertText", item.get("label", "")),
                    "detail": item.get("detail", ""),
                    "documentation": self._extract_doc(item.get("documentation")) or ""
                })

            logger.info(f"✓ pylsp returned {len(result)} completions")
            return result

        except Exception as e:
            logger.error(f"Completion error: {e}", exc_info=True)
            return []

    def get_hover(
        self,
        file_path: str,
        line: int,
        character: int,
        content: str
    ) -> Optional[Dict]:
        """Get hover information."""
        try:
            from pylsp.plugins.hover import pylsp_hover as jedi_hover

            full_path = self.workspace_path / file_path
            doc_uri = uris.from_fs_path(str(full_path))

            doc = self.workspace.get_maybe_document(doc_uri)
            if not doc:
                doc = Document(doc_uri, self.workspace, content)
                self.workspace._docs[doc_uri] = doc
            else:
                doc._source = content

            position = {"line": line - 1, "character": character}

            hover_result = jedi_hover(
                self.config,
                doc,
                position
            )

            if not hover_result:
                return None

            contents = hover_result.get("contents")
            if isinstance(contents, dict):
                value = contents.get("value", "")
            elif isinstance(contents, str):
                value = contents
            else:
                value = str(contents)

            return {"contents": {"value": value}}

        except Exception as e:
            logger.error(f"Hover error: {e}")
            return None

    def get_definition(
        self,
        file_path: str,
        line: int,
        character: int,
        content: str
    ) -> Optional[Dict]:
        """Get definition location."""
        try:
            from pylsp.plugins.definition import pylsp_definitions as jedi_definitions

            full_path = self.workspace_path / file_path
            doc_uri = uris.from_fs_path(str(full_path))

            doc = self.workspace.get_maybe_document(doc_uri)
            if not doc:
                doc = Document(doc_uri, self.workspace, content)
                self.workspace._docs[doc_uri] = doc
            else:
                doc._source = content

            position = {"line": line - 1, "character": character}

            definitions = jedi_definitions(
                self.config,
                doc,
                position
            )

            if not definitions:
                return None

            # Return first definition
            defn = definitions[0]
            return {
                "uri": defn.get("uri", ""),
                "range": defn.get("range", {})
            }

        except Exception as e:
            logger.error(f"Definition error: {e}")
            return None

    def get_diagnostics(
        self,
        file_path: str,
        content: str
    ) -> List[Dict]:
        """Get diagnostics (errors/warnings)."""
        try:
            from pylsp.plugins import pycodestyle_lint, pyflakes_lint

            # Try ruff
            try:
                from pylsp_ruff import plugin as ruff_plugin
                use_ruff = True
            except ImportError:
                use_ruff = False

            full_path = self.workspace_path / file_path
            doc_uri = uris.from_fs_path(str(full_path))

            doc = self.workspace.get_maybe_document(doc_uri)
            if not doc:
                doc = Document(doc_uri, self.workspace, content)
                self.workspace._docs[doc_uri] = doc
            else:
                doc._source = content

            diagnostics = []

            # Use ruff if available (faster and better)
            if use_ruff:
                try:
                    # pylsp_ruff uses (workspace, document) signature
                    ruff_diags = ruff_plugin.pylsp_lint(self.workspace, doc)
                    if ruff_diags:
                        diagnostics.extend(ruff_diags)
                        logger.debug(f"Ruff returned {len(ruff_diags)} diagnostics")
                except Exception as e:
                    logger.debug(f"Ruff diagnostics error: {e}")

            # Fallback to pyflakes
            if not diagnostics:
                try:
                    # pyflakes_lint uses (workspace, document) signature
                    pyflakes_diags = pyflakes_lint.pylsp_lint(self.workspace, doc)
                    if pyflakes_diags:
                        diagnostics.extend(pyflakes_diags)
                        logger.debug(f"Pyflakes returned {len(pyflakes_diags)} diagnostics")
                except Exception as e:
                    logger.debug(f"Pyflakes diagnostics error: {e}")

            return diagnostics

        except Exception as e:
            logger.error(f"Diagnostics error: {e}")
            return []

    def _extract_doc(self, doc: any) -> Optional[str]:
        """Extract documentation string."""
        if not doc:
            return None
        if isinstance(doc, str):
            return doc
        if isinstance(doc, dict):
            return doc.get("value")
        return None
