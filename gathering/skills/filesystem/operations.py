"""
Filesystem Skill for GatheRing.
Provides secure file system operations for agents.
"""

import shutil
import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from gathering.skills.base import BaseSkill, SkillResponse, SkillPermission


class FileSystemSkill(BaseSkill):
    """
    Secure file system operations skill.

    Provides tools for:
    - Reading and writing files
    - Directory operations
    - File search and listing
    - File metadata and checksums
    - Safe file manipulation with sandboxing
    """

    name = "filesystem"
    description = "Secure file system operations"
    version = "1.0.0"
    required_permissions = [SkillPermission.READ, SkillPermission.WRITE]

    # Safety limits
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    MAX_READ_SIZE = 1 * 1024 * 1024   # 1 MB for reading
    MAX_LIST_ENTRIES = 1000

    # Forbidden paths (security)
    FORBIDDEN_PATHS = [
        "/etc/passwd", "/etc/shadow", "/etc/sudoers",
        "/proc", "/sys", "/dev", "/boot",
        "~/.ssh", "~/.gnupg", "~/.aws",
    ]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.working_dir = config.get("working_dir") if config else None
        self.allowed_paths = config.get("allowed_paths", []) if config else []
        self.sandbox_mode = config.get("sandbox_mode", True) if config else True

    def get_tools_definition(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "fs_read",
                "description": "Read contents of a file",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the file to read"},
                        "encoding": {"type": "string", "description": "File encoding", "default": "utf-8"},
                        "lines": {"type": "integer", "description": "Max lines to read (0 = all)"},
                        "offset": {"type": "integer", "description": "Line offset to start from"}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "fs_write",
                "description": "Write content to a file",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the file to write"},
                        "content": {"type": "string", "description": "Content to write"},
                        "mode": {
                            "type": "string",
                            "enum": ["write", "append"],
                            "description": "Write mode",
                            "default": "write"
                        },
                        "create_dirs": {"type": "boolean", "description": "Create parent directories", "default": True}
                    },
                    "required": ["path", "content"]
                }
            },
            {
                "name": "fs_list",
                "description": "List directory contents",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Directory path to list"},
                        "pattern": {"type": "string", "description": "Glob pattern to filter"},
                        "recursive": {"type": "boolean", "description": "List recursively", "default": False},
                        "include_hidden": {"type": "boolean", "description": "Include hidden files", "default": False}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "fs_info",
                "description": "Get file or directory information",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to get info for"},
                        "checksum": {"type": "boolean", "description": "Calculate file checksum", "default": False}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "fs_mkdir",
                "description": "Create a directory",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Directory path to create"},
                        "parents": {"type": "boolean", "description": "Create parent directories", "default": True}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "fs_delete",
                "description": "Delete a file or directory",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to delete"},
                        "recursive": {"type": "boolean", "description": "Delete recursively (for directories)", "default": False}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "fs_copy",
                "description": "Copy a file or directory",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string", "description": "Source path"},
                        "destination": {"type": "string", "description": "Destination path"},
                        "overwrite": {"type": "boolean", "description": "Overwrite if exists", "default": False}
                    },
                    "required": ["source", "destination"]
                }
            },
            {
                "name": "fs_move",
                "description": "Move or rename a file or directory",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string", "description": "Source path"},
                        "destination": {"type": "string", "description": "Destination path"},
                        "overwrite": {"type": "boolean", "description": "Overwrite if exists", "default": False}
                    },
                    "required": ["source", "destination"]
                }
            },
            {
                "name": "fs_search",
                "description": "Search for files by name or content",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Directory to search in"},
                        "pattern": {"type": "string", "description": "Filename pattern (glob)"},
                        "content": {"type": "string", "description": "Content to search for"},
                        "max_results": {"type": "integer", "description": "Maximum results", "default": 100}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "fs_tree",
                "description": "Get directory tree structure",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Root directory"},
                        "max_depth": {"type": "integer", "description": "Maximum depth", "default": 3},
                        "include_files": {"type": "boolean", "description": "Include files (not just dirs)", "default": True}
                    },
                    "required": ["path"]
                }
            },
        ]

    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> SkillResponse:
        """Execute a filesystem tool."""
        self.ensure_initialized()

        start_time = datetime.utcnow()

        try:
            handlers = {
                "fs_read": self._fs_read,
                "fs_write": self._fs_write,
                "fs_list": self._fs_list,
                "fs_info": self._fs_info,
                "fs_mkdir": self._fs_mkdir,
                "fs_delete": self._fs_delete,
                "fs_copy": self._fs_copy,
                "fs_move": self._fs_move,
                "fs_search": self._fs_search,
                "fs_tree": self._fs_tree,
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

    def _resolve_path(self, path: str) -> Path:
        """Resolve and validate a path."""
        resolved = Path(path).expanduser().resolve()

        # Security check
        if self.sandbox_mode:
            str_path = str(resolved)
            for forbidden in self.FORBIDDEN_PATHS:
                forbidden_resolved = str(Path(forbidden).expanduser().resolve())
                if str_path.startswith(forbidden_resolved):
                    raise PermissionError(f"Access denied: {path}")

            # Check allowed paths if configured
            if self.allowed_paths:
                allowed = any(
                    str_path.startswith(str(Path(ap).expanduser().resolve()))
                    for ap in self.allowed_paths
                )
                if not allowed:
                    raise PermissionError(f"Path not in allowed list: {path}")

        return resolved

    def _fs_read(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Read file contents."""
        path = self._resolve_path(tool_input["path"])
        encoding = tool_input.get("encoding", "utf-8")
        max_lines = tool_input.get("lines", 0)
        offset = tool_input.get("offset", 0)

        if not path.exists():
            return SkillResponse(success=False, message=f"File not found: {path}", error="not_found")

        if not path.is_file():
            return SkillResponse(success=False, message=f"Not a file: {path}", error="not_file")

        # Check file size
        size = path.stat().st_size
        if size > self.MAX_READ_SIZE:
            return SkillResponse(
                success=False,
                message=f"File too large: {size} bytes (max {self.MAX_READ_SIZE})",
                error="file_too_large"
            )

        try:
            with open(path, "r", encoding=encoding) as f:
                if max_lines > 0 or offset > 0:
                    lines = f.readlines()
                    if offset > 0:
                        lines = lines[offset:]
                    if max_lines > 0:
                        lines = lines[:max_lines]
                    content = "".join(lines)
                    total_lines = len(lines)
                else:
                    content = f.read()
                    total_lines = content.count("\n") + 1

            return SkillResponse(
                success=True,
                message=f"Read {len(content)} chars from {path.name}",
                data={
                    "content": content,
                    "path": str(path),
                    "size": size,
                    "lines": total_lines,
                }
            )
        except UnicodeDecodeError:
            return SkillResponse(
                success=False,
                message=f"Cannot decode file with {encoding}",
                error="decode_error"
            )

    def _fs_write(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Write content to file."""
        path = self._resolve_path(tool_input["path"])
        content = tool_input["content"]
        mode = tool_input.get("mode", "write")
        create_dirs = tool_input.get("create_dirs", True)

        if len(content) > self.MAX_FILE_SIZE:
            return SkillResponse(
                success=False,
                message=f"Content too large: {len(content)} bytes",
                error="content_too_large"
            )

        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)

        file_mode = "a" if mode == "append" else "w"
        existed = path.exists()

        with open(path, file_mode, encoding="utf-8") as f:
            f.write(content)

        return SkillResponse(
            success=True,
            message=f"{'Appended to' if mode == 'append' else 'Wrote'} {path.name}",
            data={
                "path": str(path),
                "bytes_written": len(content),
                "created": not existed,
            }
        )

    def _fs_list(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """List directory contents."""
        path = self._resolve_path(tool_input["path"])
        pattern = tool_input.get("pattern", "*")
        recursive = tool_input.get("recursive", False)
        include_hidden = tool_input.get("include_hidden", False)

        if not path.exists():
            return SkillResponse(success=False, message=f"Path not found: {path}", error="not_found")

        if not path.is_dir():
            return SkillResponse(success=False, message=f"Not a directory: {path}", error="not_directory")

        entries = []
        glob_method = path.rglob if recursive else path.glob

        for entry in glob_method(pattern):
            if not include_hidden and entry.name.startswith("."):
                continue

            if len(entries) >= self.MAX_LIST_ENTRIES:
                break

            try:
                stat = entry.stat()
                entries.append({
                    "name": entry.name,
                    "path": str(entry),
                    "type": "directory" if entry.is_dir() else "file",
                    "size": stat.st_size if entry.is_file() else None,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
            except (PermissionError, OSError):
                continue

        return SkillResponse(
            success=True,
            message=f"Found {len(entries)} entries",
            data={
                "entries": entries,
                "path": str(path),
                "truncated": len(entries) >= self.MAX_LIST_ENTRIES,
            }
        )

    def _fs_info(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Get file/directory information."""
        path = self._resolve_path(tool_input["path"])
        calc_checksum = tool_input.get("checksum", False)

        if not path.exists():
            return SkillResponse(success=False, message=f"Path not found: {path}", error="not_found")

        stat = path.stat()
        is_file = path.is_file()

        info = {
            "path": str(path),
            "name": path.name,
            "type": "file" if is_file else "directory",
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
            "permissions": oct(stat.st_mode)[-3:],
        }

        if is_file:
            info["mime_type"] = mimetypes.guess_type(path)[0]

            if calc_checksum and stat.st_size <= self.MAX_READ_SIZE:
                with open(path, "rb") as f:
                    info["checksum_md5"] = hashlib.md5(f.read()).hexdigest()

        return SkillResponse(
            success=True,
            message=f"Info for {path.name}",
            data=info
        )

    def _fs_mkdir(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Create directory."""
        path = self._resolve_path(tool_input["path"])
        parents = tool_input.get("parents", True)

        if path.exists():
            return SkillResponse(
                success=True,
                message=f"Directory already exists: {path}",
                data={"path": str(path), "created": False}
            )

        path.mkdir(parents=parents, exist_ok=True)

        return SkillResponse(
            success=True,
            message=f"Created directory: {path}",
            data={"path": str(path), "created": True}
        )

    def _fs_delete(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Delete file or directory."""
        path = self._resolve_path(tool_input["path"])
        recursive = tool_input.get("recursive", False)

        if not path.exists():
            return SkillResponse(success=False, message=f"Path not found: {path}", error="not_found")

        # Require confirmation for deletion
        if path.is_dir():
            if recursive:
                return SkillResponse(
                    success=True,
                    message=f"Ready to delete directory: {path}",
                    needs_confirmation=True,
                    confirmation_type="destructive",
                    confirmation_message=f"Delete directory '{path}' and all contents? This cannot be undone.",
                    data={"path": str(path), "type": "directory", "recursive": True}
                )
            else:
                try:
                    path.rmdir()
                    return SkillResponse(
                        success=True,
                        message=f"Deleted empty directory: {path}",
                        data={"path": str(path), "type": "directory"}
                    )
                except OSError:
                    return SkillResponse(
                        success=False,
                        message="Directory not empty. Use recursive=True to delete.",
                        error="directory_not_empty"
                    )
        else:
            return SkillResponse(
                success=True,
                message=f"Ready to delete file: {path}",
                needs_confirmation=True,
                confirmation_type="destructive",
                confirmation_message=f"Delete file '{path}'? This cannot be undone.",
                data={"path": str(path), "type": "file"}
            )

    def _fs_copy(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Copy file or directory."""
        source = self._resolve_path(tool_input["source"])
        destination = self._resolve_path(tool_input["destination"])
        overwrite = tool_input.get("overwrite", False)

        if not source.exists():
            return SkillResponse(success=False, message=f"Source not found: {source}", error="not_found")

        if destination.exists() and not overwrite:
            return SkillResponse(
                success=False,
                message=f"Destination exists: {destination}",
                error="destination_exists"
            )

        if source.is_file():
            shutil.copy2(source, destination)
        else:
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(source, destination)

        return SkillResponse(
            success=True,
            message=f"Copied {source.name} to {destination}",
            data={
                "source": str(source),
                "destination": str(destination),
            }
        )

    def _fs_move(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Move or rename file/directory."""
        source = self._resolve_path(tool_input["source"])
        destination = self._resolve_path(tool_input["destination"])
        overwrite = tool_input.get("overwrite", False)

        if not source.exists():
            return SkillResponse(success=False, message=f"Source not found: {source}", error="not_found")

        if destination.exists() and not overwrite:
            return SkillResponse(
                success=False,
                message=f"Destination exists: {destination}",
                error="destination_exists"
            )

        shutil.move(str(source), str(destination))

        return SkillResponse(
            success=True,
            message=f"Moved {source.name} to {destination}",
            data={
                "source": str(source),
                "destination": str(destination),
            }
        )

    def _fs_search(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Search for files."""
        path = self._resolve_path(tool_input["path"])
        pattern = tool_input.get("pattern", "*")
        content_search = tool_input.get("content")
        max_results = tool_input.get("max_results", 100)

        if not path.exists():
            return SkillResponse(success=False, message=f"Path not found: {path}", error="not_found")

        results = []
        for entry in path.rglob(pattern):
            if len(results) >= max_results:
                break

            if not entry.is_file():
                continue

            match_info = {
                "path": str(entry),
                "name": entry.name,
                "size": entry.stat().st_size,
            }

            # Content search
            if content_search:
                try:
                    with open(entry, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        if content_search in content:
                            # Find line numbers
                            lines = content.split("\n")
                            matching_lines = [
                                i + 1 for i, line in enumerate(lines)
                                if content_search in line
                            ]
                            match_info["matching_lines"] = matching_lines[:10]
                            results.append(match_info)
                except (PermissionError, OSError):
                    continue
            else:
                results.append(match_info)

        return SkillResponse(
            success=True,
            message=f"Found {len(results)} matches",
            data={
                "results": results,
                "truncated": len(results) >= max_results,
            }
        )

    def _fs_tree(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Get directory tree structure."""
        path = self._resolve_path(tool_input["path"])
        max_depth = tool_input.get("max_depth", 3)
        include_files = tool_input.get("include_files", True)

        if not path.exists():
            return SkillResponse(success=False, message=f"Path not found: {path}", error="not_found")

        def build_tree(current: Path, depth: int) -> Dict[str, Any]:
            if depth > max_depth:
                return {"name": current.name, "type": "directory", "truncated": True}

            node = {
                "name": current.name,
                "type": "directory" if current.is_dir() else "file",
            }

            if current.is_dir():
                children = []
                try:
                    for child in sorted(current.iterdir()):
                        if child.name.startswith("."):
                            continue
                        if child.is_dir():
                            children.append(build_tree(child, depth + 1))
                        elif include_files:
                            children.append({
                                "name": child.name,
                                "type": "file",
                                "size": child.stat().st_size,
                            })
                except PermissionError:
                    node["error"] = "permission_denied"

                node["children"] = children

            return node

        tree = build_tree(path, 0)

        return SkillResponse(
            success=True,
            message=f"Tree for {path}",
            data={"tree": tree}
        )
