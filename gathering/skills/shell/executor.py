"""
Shell Skill - Safe command execution with security controls.
"""

import os
import re
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

from gathering.skills.base import BaseSkill, SkillResponse, SkillPermission


@dataclass
class ShellConfig:
    """Shell execution configuration."""
    # Allowed base commands (checked before execution)
    allowed_commands: Set[str] = field(default_factory=lambda: {
        # File operations (read-only by default)
        "ls", "cat", "head", "tail", "less", "file", "stat", "wc",
        "find", "locate", "which", "whereis", "type",
        # Text processing
        "grep", "awk", "sed", "cut", "sort", "uniq", "tr", "diff",
        "jq", "yq", "xq",
        # Archive/compression
        "tar", "gzip", "gunzip", "zip", "unzip", "zcat",
        # Network (read-only)
        "curl", "wget", "ping", "dig", "nslookup", "host",
        # System info
        "date", "cal", "uptime", "free", "df", "du", "env", "printenv",
        "uname", "hostname", "id", "whoami", "groups",
        "ps", "top", "htop", "pgrep",
        # Development tools
        "git", "npm", "npx", "yarn", "pip", "python", "python3",
        "node", "deno", "bun", "cargo", "go", "make", "cmake",
        "docker", "docker-compose", "kubectl",
        # Editors/viewers
        "tree", "bat", "exa", "fd", "rg", "ag", "fzf",
        # Other utilities
        "echo", "printf", "basename", "dirname", "realpath",
        "md5sum", "sha256sum", "base64", "xxd",
    })

    # Commands that require WRITE permission
    write_commands: Set[str] = field(default_factory=lambda: {
        "cp", "mv", "rm", "mkdir", "rmdir", "touch", "chmod", "chown",
        "ln", "install",
    })

    # Patterns that are ALWAYS blocked
    blocked_patterns: List[str] = field(default_factory=lambda: [
        r"rm\s+(-[rf]+\s+)*(/|~|\$HOME)",  # rm -rf / or ~
        r">\s*/dev/",                        # Write to devices
        r"mkfs",                             # Format filesystems
        r"dd\s+if=",                         # Raw disk operations
        r"chmod\s+(777|a\+rwx)",             # Dangerous permissions
        r":\(\)\s*\{",                       # Fork bomb
        r"\|\s*sh\s*$",                      # Pipe to shell
        r"\|\s*bash\s*$",                    # Pipe to bash
        r"curl.*\|\s*(sh|bash)",             # Curl pipe to shell
        r"wget.*\|\s*(sh|bash)",             # Wget pipe to shell
        r"eval\s*\(",                        # Eval
        r"`.*`",                             # Command substitution (backticks)
        r"\$\(.*\)",                         # Command substitution
        r"sudo",                             # Sudo
        r"su\s+",                            # Su
        r"/etc/passwd",                      # Password file
        r"/etc/shadow",                      # Shadow file
        r"\.ssh/",                           # SSH keys
    ])

    # Max execution time
    timeout: int = 60

    # Max output size
    max_output_size: int = 100000

    # Working directory restrictions
    allowed_paths: List[str] = field(default_factory=list)

    # Enable write operations
    allow_write: bool = False


class ShellSkill(BaseSkill):
    """
    Shell command execution with comprehensive security controls.

    Tools:
    - shell_exec: Execute a shell command
    - file_read: Read file contents
    - file_write: Write to a file (requires permission)
    - file_list: List directory contents
    - file_info: Get file/directory information
    - find_files: Search for files
    - process_list: List running processes
    """

    name = "shell"
    description = "Shell command execution with security controls"
    version = "1.0.0"
    required_permissions = [SkillPermission.EXECUTE]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.shell_config = ShellConfig()
        if config:
            if "allowed_commands" in config:
                self.shell_config.allowed_commands = set(config["allowed_commands"])
            if "blocked_patterns" in config:
                self.shell_config.blocked_patterns = config["blocked_patterns"]
            if "timeout" in config:
                self.shell_config.timeout = config["timeout"]
            if "allow_write" in config:
                self.shell_config.allow_write = config["allow_write"]
            if "allowed_paths" in config:
                self.shell_config.allowed_paths = config["allowed_paths"]

    def get_tools_definition(self) -> List[Dict[str, Any]]:
        """Return tool definitions."""
        tools = [
            {
                "name": "shell_exec",
                "description": "Execute a shell command. Commands are validated against a security whitelist.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Shell command to execute"
                        },
                        "cwd": {
                            "type": "string",
                            "description": "Working directory (optional)"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds (default: 60)",
                            "default": 60,
                            "maximum": 300
                        },
                        "env": {
                            "type": "object",
                            "description": "Additional environment variables"
                        }
                    },
                    "required": ["command"]
                }
            },
            {
                "name": "file_read",
                "description": "Read the contents of a file",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path to read"
                        },
                        "encoding": {
                            "type": "string",
                            "description": "File encoding",
                            "default": "utf-8"
                        },
                        "max_lines": {
                            "type": "integer",
                            "description": "Maximum lines to read",
                            "default": 1000
                        },
                        "start_line": {
                            "type": "integer",
                            "description": "Start from line number",
                            "default": 1
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "file_list",
                "description": "List files and directories",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Directory path",
                            "default": "."
                        },
                        "pattern": {
                            "type": "string",
                            "description": "Glob pattern to filter"
                        },
                        "recursive": {
                            "type": "boolean",
                            "description": "Recurse into subdirectories",
                            "default": False
                        },
                        "include_hidden": {
                            "type": "boolean",
                            "description": "Include hidden files",
                            "default": False
                        }
                    }
                }
            },
            {
                "name": "file_info",
                "description": "Get detailed file or directory information",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to file or directory"
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "find_files",
                "description": "Search for files by name pattern",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Directory to search in",
                            "default": "."
                        },
                        "pattern": {
                            "type": "string",
                            "description": "Filename pattern (glob or regex)"
                        },
                        "type": {
                            "type": "string",
                            "enum": ["file", "directory", "any"],
                            "default": "any"
                        },
                        "max_depth": {
                            "type": "integer",
                            "description": "Maximum directory depth"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum results",
                            "default": 100
                        }
                    },
                    "required": ["pattern"]
                }
            },
            {
                "name": "grep_search",
                "description": "Search for text patterns in files",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Search pattern (regex)"
                        },
                        "path": {
                            "type": "string",
                            "description": "File or directory to search",
                            "default": "."
                        },
                        "recursive": {
                            "type": "boolean",
                            "description": "Search recursively",
                            "default": True
                        },
                        "ignore_case": {
                            "type": "boolean",
                            "description": "Case insensitive",
                            "default": False
                        },
                        "file_pattern": {
                            "type": "string",
                            "description": "File glob pattern (e.g., '*.py')"
                        },
                        "context_lines": {
                            "type": "integer",
                            "description": "Lines of context",
                            "default": 0
                        }
                    },
                    "required": ["pattern"]
                }
            },
        ]

        # Add write tools if allowed
        if self.shell_config.allow_write:
            tools.append({
                "name": "file_write",
                "description": "Write content to a file",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path to write"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write"
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["write", "append"],
                            "default": "write"
                        },
                        "create_dirs": {
                            "type": "boolean",
                            "description": "Create parent directories",
                            "default": False
                        }
                    },
                    "required": ["path", "content"]
                }
            })

        return tools

    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> SkillResponse:
        """Execute a shell tool."""
        start_time = datetime.utcnow()
        self.ensure_initialized()

        try:
            if tool_name == "shell_exec":
                result = self._shell_exec(
                    command=tool_input["command"],
                    cwd=tool_input.get("cwd"),
                    timeout=tool_input.get("timeout", self.shell_config.timeout),
                    env=tool_input.get("env"),
                )
            elif tool_name == "file_read":
                result = self._file_read(
                    path=tool_input["path"],
                    encoding=tool_input.get("encoding", "utf-8"),
                    max_lines=tool_input.get("max_lines", 1000),
                    start_line=tool_input.get("start_line", 1),
                )
            elif tool_name == "file_write":
                if not self.shell_config.allow_write:
                    return SkillResponse(
                        success=False,
                        message="Write operations are not enabled",
                        skill_name=self.name,
                        tool_name=tool_name,
                    )
                result = self._file_write(
                    path=tool_input["path"],
                    content=tool_input["content"],
                    mode=tool_input.get("mode", "write"),
                    create_dirs=tool_input.get("create_dirs", False),
                )
            elif tool_name == "file_list":
                result = self._file_list(
                    path=tool_input.get("path", "."),
                    pattern=tool_input.get("pattern"),
                    recursive=tool_input.get("recursive", False),
                    include_hidden=tool_input.get("include_hidden", False),
                )
            elif tool_name == "file_info":
                result = self._file_info(path=tool_input["path"])
            elif tool_name == "find_files":
                result = self._find_files(
                    pattern=tool_input["pattern"],
                    path=tool_input.get("path", "."),
                    file_type=tool_input.get("type", "any"),
                    max_depth=tool_input.get("max_depth"),
                    max_results=tool_input.get("max_results", 100),
                )
            elif tool_name == "grep_search":
                result = self._grep_search(
                    pattern=tool_input["pattern"],
                    path=tool_input.get("path", "."),
                    recursive=tool_input.get("recursive", True),
                    ignore_case=tool_input.get("ignore_case", False),
                    file_pattern=tool_input.get("file_pattern"),
                    context_lines=tool_input.get("context_lines", 0),
                )
            else:
                return SkillResponse(
                    success=False,
                    message=f"Unknown tool: {tool_name}",
                    skill_name=self.name,
                    tool_name=tool_name,
                )

            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            return SkillResponse(
                success=result.get("success", True),
                message=result.get("message", f"Executed {tool_name}"),
                data=result,
                skill_name=self.name,
                tool_name=tool_name,
                duration_ms=duration,
            )

        except Exception as e:
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            return SkillResponse(
                success=False,
                message=f"Error: {str(e)}",
                error=str(e),
                skill_name=self.name,
                tool_name=tool_name,
                duration_ms=duration,
            )

    def _validate_command(self, command: str) -> tuple[bool, str]:
        """
        Validate a command against security rules.
        Returns (is_valid, error_message).
        """
        # Check blocked patterns
        for pattern in self.shell_config.blocked_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Command matches blocked pattern: {pattern}"

        # Extract base command
        try:
            parts = shlex.split(command)
            if not parts:
                return False, "Empty command"
            base_cmd = parts[0]
        except ValueError as e:
            return False, f"Invalid command syntax: {e}"

        # Handle path-based commands
        if "/" in base_cmd:
            base_cmd = os.path.basename(base_cmd)

        # Check if command is allowed
        all_allowed = self.shell_config.allowed_commands.copy()
        if self.shell_config.allow_write:
            all_allowed.update(self.shell_config.write_commands)

        if base_cmd not in all_allowed:
            return False, f"Command '{base_cmd}' is not in the allowed list"

        return True, ""

    def _shell_exec(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: int = 60,
        env: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Execute a shell command."""
        # Validate command
        is_valid, error = self._validate_command(command)
        if not is_valid:
            return {
                "success": False,
                "message": f"Command blocked: {error}",
                "command": command,
            }

        # Validate working directory
        if cwd:
            cwd = os.path.abspath(cwd)
            if not os.path.isdir(cwd):
                return {
                    "success": False,
                    "message": f"Working directory does not exist: {cwd}",
                }
            if self.shell_config.allowed_paths:
                allowed = any(cwd.startswith(p) for p in self.shell_config.allowed_paths)
                if not allowed:
                    return {
                        "success": False,
                        "message": f"Working directory not in allowed paths",
                    }

        # Build environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)

        # Parse command into arguments (shell=False for security)
        try:
            cmd_args = shlex.split(command)
        except ValueError as e:
            return {
                "success": False,
                "message": f"Invalid command syntax: {e}",
                "command": command,
            }

        # Execute command with shell=False (secure)
        try:
            result = subprocess.run(
                cmd_args,
                shell=False,
                cwd=cwd,
                env=process_env,
                capture_output=True,
                text=True,
                timeout=min(timeout, self.shell_config.timeout),
            )

            stdout = result.stdout[:self.shell_config.max_output_size]
            stderr = result.stderr[:self.shell_config.max_output_size]

            return {
                "success": result.returncode == 0,
                "command": command,
                "return_code": result.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "truncated": len(result.stdout) > self.shell_config.max_output_size,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "message": f"Command timed out after {timeout}s",
                "command": command,
            }
        except FileNotFoundError:
            return {
                "success": False,
                "message": f"Command not found: {cmd_args[0]}",
                "command": command,
            }

    def _file_read(
        self,
        path: str,
        encoding: str = "utf-8",
        max_lines: int = 1000,
        start_line: int = 1,
    ) -> Dict[str, Any]:
        """Read file contents."""
        path = os.path.abspath(path)

        if not os.path.exists(path):
            return {"success": False, "message": f"File not found: {path}"}

        if not os.path.isfile(path):
            return {"success": False, "message": f"Not a file: {path}"}

        try:
            with open(path, "r", encoding=encoding) as f:
                lines = f.readlines()

            total_lines = len(lines)
            start_idx = max(0, start_line - 1)
            end_idx = min(start_idx + max_lines, total_lines)
            selected_lines = lines[start_idx:end_idx]

            return {
                "success": True,
                "path": path,
                "content": "".join(selected_lines),
                "total_lines": total_lines,
                "start_line": start_idx + 1,
                "end_line": end_idx,
                "truncated": end_idx < total_lines,
            }

        except UnicodeDecodeError:
            return {
                "success": False,
                "message": f"Cannot decode file with encoding {encoding}",
            }

    def _file_write(
        self,
        path: str,
        content: str,
        mode: str = "write",
        create_dirs: bool = False,
    ) -> Dict[str, Any]:
        """Write to a file."""
        path = os.path.abspath(path)

        # Check allowed paths
        if self.shell_config.allowed_paths:
            allowed = any(path.startswith(p) for p in self.shell_config.allowed_paths)
            if not allowed:
                return {"success": False, "message": "Path not in allowed list"}

        # Create directories if needed
        if create_dirs:
            os.makedirs(os.path.dirname(path), exist_ok=True)

        write_mode = "a" if mode == "append" else "w"
        with open(path, write_mode) as f:
            f.write(content)

        return {
            "success": True,
            "path": path,
            "bytes_written": len(content.encode("utf-8")),
            "mode": mode,
        }

    def _file_list(
        self,
        path: str = ".",
        pattern: Optional[str] = None,
        recursive: bool = False,
        include_hidden: bool = False,
    ) -> Dict[str, Any]:
        """List directory contents."""
        path = os.path.abspath(path)

        if not os.path.exists(path):
            return {"success": False, "message": f"Path not found: {path}"}

        if not os.path.isdir(path):
            return {"success": False, "message": f"Not a directory: {path}"}

        entries = []
        if recursive:
            for root, dirs, files in os.walk(path):
                if not include_hidden:
                    dirs[:] = [d for d in dirs if not d.startswith(".")]
                    files = [f for f in files if not f.startswith(".")]

                for name in dirs + files:
                    full_path = os.path.join(root, name)
                    rel_path = os.path.relpath(full_path, path)
                    if pattern and not re.search(pattern, name):
                        continue
                    entries.append(self._get_entry_info(full_path, rel_path))
        else:
            for name in os.listdir(path):
                if not include_hidden and name.startswith("."):
                    continue
                if pattern and not re.search(pattern, name):
                    continue
                full_path = os.path.join(path, name)
                entries.append(self._get_entry_info(full_path, name))

        return {
            "success": True,
            "path": path,
            "count": len(entries),
            "entries": sorted(entries, key=lambda x: (not x["is_dir"], x["name"])),
        }

    def _get_entry_info(self, full_path: str, name: str) -> Dict[str, Any]:
        """Get basic info about a directory entry."""
        stat = os.stat(full_path)
        return {
            "name": name,
            "is_dir": os.path.isdir(full_path),
            "size": stat.st_size if not os.path.isdir(full_path) else 0,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }

    def _file_info(self, path: str) -> Dict[str, Any]:
        """Get detailed file information."""
        path = os.path.abspath(path)

        if not os.path.exists(path):
            return {"success": False, "message": f"Path not found: {path}"}

        stat = os.stat(path)
        is_dir = os.path.isdir(path)

        info = {
            "success": True,
            "path": path,
            "name": os.path.basename(path),
            "is_file": os.path.isfile(path),
            "is_dir": is_dir,
            "is_symlink": os.path.islink(path),
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
            "mode": oct(stat.st_mode)[-3:],
        }

        if is_dir:
            try:
                info["item_count"] = len(os.listdir(path))
            except PermissionError:
                info["item_count"] = -1

        return info

    def _find_files(
        self,
        pattern: str,
        path: str = ".",
        file_type: str = "any",
        max_depth: Optional[int] = None,
        max_results: int = 100,
    ) -> Dict[str, Any]:
        """Find files matching a pattern."""
        path = os.path.abspath(path)
        results = []

        for root, dirs, files in os.walk(path):
            # Check depth
            if max_depth is not None:
                depth = root[len(path):].count(os.sep)
                if depth >= max_depth:
                    dirs[:] = []
                    continue

            items = []
            if file_type in ("file", "any"):
                items.extend([(f, False) for f in files])
            if file_type in ("directory", "any"):
                items.extend([(d, True) for d in dirs])

            for name, is_dir in items:
                if re.search(pattern, name):
                    full_path = os.path.join(root, name)
                    results.append({
                        "path": full_path,
                        "name": name,
                        "is_dir": is_dir,
                    })
                    if len(results) >= max_results:
                        return {
                            "success": True,
                            "pattern": pattern,
                            "count": len(results),
                            "truncated": True,
                            "results": results,
                        }

        return {
            "success": True,
            "pattern": pattern,
            "count": len(results),
            "truncated": False,
            "results": results,
        }

    def _grep_search(
        self,
        pattern: str,
        path: str = ".",
        recursive: bool = True,
        ignore_case: bool = False,
        file_pattern: Optional[str] = None,
        context_lines: int = 0,
    ) -> Dict[str, Any]:
        """Search for text patterns in files."""
        path = os.path.abspath(path)
        flags = re.IGNORECASE if ignore_case else 0
        regex = re.compile(pattern, flags)

        matches = []
        files_searched = 0

        def search_file(file_path: str):
            nonlocal files_searched
            files_searched += 1

            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()

                for i, line in enumerate(lines, 1):
                    if regex.search(line):
                        match = {
                            "file": file_path,
                            "line_number": i,
                            "line": line.rstrip(),
                        }
                        if context_lines > 0:
                            start = max(0, i - 1 - context_lines)
                            end = min(len(lines), i + context_lines)
                            match["context_before"] = [l.rstrip() for l in lines[start:i-1]]
                            match["context_after"] = [l.rstrip() for l in lines[i:end]]
                        matches.append(match)

            except (IOError, PermissionError):
                pass

        if os.path.isfile(path):
            search_file(path)
        else:
            for root, dirs, files in os.walk(path):
                if not recursive:
                    dirs[:] = []

                for name in files:
                    if file_pattern and not re.search(file_pattern, name):
                        continue
                    search_file(os.path.join(root, name))

        return {
            "success": True,
            "pattern": pattern,
            "files_searched": files_searched,
            "match_count": len(matches),
            "matches": matches[:100],  # Limit results
            "truncated": len(matches) > 100,
        }
