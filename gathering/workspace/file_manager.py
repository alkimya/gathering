"""
File Manager for workspace file operations.

Handles file tree generation, reading, writing with git status integration.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import mimetypes
import logging
import subprocess

logger = logging.getLogger(__name__)


class FileManager:
    """
    Manages file operations in a workspace.

    Provides file tree, reading, writing with git status integration.
    """

    # File types to exclude from tree
    EXCLUDED_PATTERNS = [
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        ".git",
        ".idea",
        ".vscode",
        "*.pyc",
        "*.egg-info",
        "dist",
        "build",
        ".DS_Store",
    ]

    @classmethod
    def list_files(
        cls,
        project_path: str,
        include_git_status: bool = True,
        max_depth: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        List files in project with git status.

        Args:
            project_path: Path to project.
            include_git_status: Include git status for files.
            max_depth: Maximum depth to traverse (None = unlimited).

        Returns:
            File tree structure with git status.

        Example:
            >>> tree = FileManager.list_files("/my/project")
            >>> print(tree["children"][0]["name"])
            'src'
        """
        path = Path(project_path)
        if not path.exists():
            raise ValueError(f"Project path does not exist: {project_path}")

        # Get git status if requested
        git_status = {}
        if include_git_status:
            git_status = cls._get_git_status(project_path)

        # Build tree
        tree = cls._build_tree(path, path, git_status, max_depth, 0)
        return tree

    @classmethod
    def _build_tree(
        cls,
        root_path: Path,
        current_path: Path,
        git_status: Dict[str, str],
        max_depth: Optional[int],
        current_depth: int,
    ) -> Dict[str, Any]:
        """Build file tree recursively."""
        # Check depth limit
        if max_depth is not None and current_depth >= max_depth:
            return None

        relative_path = current_path.relative_to(root_path)
        rel_str = str(relative_path)

        # Check if should exclude
        if cls._should_exclude(current_path):
            return None

        node: Dict[str, Any] = {
            "name": current_path.name,
            "path": rel_str if rel_str != "." else "",
            "type": "directory" if current_path.is_dir() else "file",
        }

        # Add git status
        if rel_str in git_status:
            node["git_status"] = git_status[rel_str]

        # If directory, recurse
        if current_path.is_dir():
            children = []
            try:
                for child in sorted(current_path.iterdir()):
                    child_node = cls._build_tree(
                        root_path,
                        child,
                        git_status,
                        max_depth,
                        current_depth + 1,
                    )
                    if child_node:
                        children.append(child_node)

                node["children"] = children
            except PermissionError:
                logger.warning(f"Permission denied: {current_path}")
                node["children"] = []
        else:
            # Add file metadata
            try:
                stat = current_path.stat()
                node["size"] = stat.st_size
                node["modified"] = stat.st_mtime

                # Detect file type
                mime_type, _ = mimetypes.guess_type(str(current_path))
                node["mime_type"] = mime_type or "application/octet-stream"

            except Exception as e:
                logger.warning(f"Error getting file stats: {e}")

        return node

    @classmethod
    def _should_exclude(cls, path: Path) -> bool:
        """Check if path should be excluded."""
        name = path.name

        # Check excluded patterns
        for pattern in cls.EXCLUDED_PATTERNS:
            if pattern.startswith("*"):
                # Extension match
                if name.endswith(pattern[1:]):
                    return True
            else:
                # Exact match
                if name == pattern:
                    return True

        return False

    @classmethod
    def _get_git_status(cls, project_path: str) -> Dict[str, str]:
        """
        Get git status for all files.

        Returns:
            Dict mapping file path to status (M, A, D, ??, etc.)
        """
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                return {}

            status_map = {}
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                # Parse git status format: "XY filename"
                status = line[:2]
                filepath = line[3:].strip()

                # Clean status
                clean_status = status.strip()
                if not clean_status:
                    continue

                status_map[filepath] = clean_status

            return status_map

        except Exception as e:
            logger.warning(f"Error getting git status: {e}")
            return {}

    @classmethod
    def read_file(cls, project_path: str, file_path: str) -> Dict[str, Any]:
        """
        Read file contents.

        Args:
            project_path: Path to project.
            file_path: Relative path to file within project.

        Returns:
            Dictionary with file content and metadata.

        Example:
            >>> content = FileManager.read_file("/my/project", "src/main.py")
            >>> print(content["content"][:50])
            'import sys\n\ndef main():\n    print("Hello")\n'
        """
        full_path = Path(project_path) / file_path

        # Security check - ensure file is within project
        try:
            full_path.resolve().relative_to(Path(project_path).resolve())
        except ValueError:
            raise ValueError(f"File path outside project: {file_path}")

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not full_path.is_file():
            raise ValueError(f"Not a file: {file_path}")

        # Read file
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            # Binary file
            with open(full_path, "rb") as f:
                binary_content = f.read()
            return {
                "path": file_path,
                "type": "binary",
                "size": len(binary_content),
                "error": "Binary file - cannot display content",
            }

        # Get metadata
        stat = full_path.stat()
        mime_type, encoding = mimetypes.guess_type(str(full_path))

        return {
            "path": file_path,
            "content": content,
            "type": "text",
            "mime_type": mime_type or "text/plain",
            "encoding": encoding or "utf-8",
            "size": stat.st_size,
            "lines": len(content.split("\n")),
            "modified": stat.st_mtime,
        }

    @classmethod
    def write_file(
        cls,
        project_path: str,
        file_path: str,
        content: str,
        create_backup: bool = True,
    ) -> Dict[str, Any]:
        """
        Write file contents.

        Args:
            project_path: Path to project.
            file_path: Relative path to file.
            content: New content.
            create_backup: Create backup of original file.

        Returns:
            Dictionary with operation result.

        Example:
            >>> result = FileManager.write_file(
            ...     "/my/project",
            ...     "src/main.py",
            ...     "def main():\\n    pass\\n"
            ... )
            >>> print(result["success"])
            True
        """
        full_path = Path(project_path) / file_path

        # Security check
        try:
            full_path.resolve().relative_to(Path(project_path).resolve())
        except ValueError:
            raise ValueError(f"File path outside project: {file_path}")

        # Create backup if file exists
        backup_path = None
        if create_backup and full_path.exists():
            import shutil
            import time

            timestamp = int(time.time())
            backup_path = full_path.with_suffix(f".{timestamp}.bak")
            shutil.copy2(full_path, backup_path)

        # Ensure parent directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

            return {
                "success": True,
                "path": file_path,
                "backup": str(backup_path) if backup_path else None,
                "size": len(content),
                "lines": len(content.split("\n")),
            }

        except Exception as e:
            # Restore backup if write failed
            if backup_path and backup_path.exists():
                import shutil

                shutil.copy2(backup_path, full_path)
                backup_path.unlink()

            raise Exception(f"Failed to write file: {e}") from e

    @classmethod
    def delete_file(cls, project_path: str, file_path: str) -> Dict[str, Any]:
        """
        Delete a file.

        Args:
            project_path: Path to project.
            file_path: Relative path to file.

        Returns:
            Dictionary with operation result.
        """
        full_path = Path(project_path) / file_path

        # Security check
        try:
            full_path.resolve().relative_to(Path(project_path).resolve())
        except ValueError:
            raise ValueError(f"File path outside project: {file_path}")

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Delete
        full_path.unlink()

        return {
            "success": True,
            "path": file_path,
            "deleted": True,
        }

    @classmethod
    def get_file_language(cls, file_path: str) -> str:
        """
        Detect programming language from file extension.

        Args:
            file_path: Path to file.

        Returns:
            Language identifier for syntax highlighting.
        """
        extension_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "cpp",
            ".hpp": "cpp",
            ".cs": "csharp",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala",
            ".html": "html",
            ".css": "css",
            ".scss": "scss",
            ".sass": "sass",
            ".json": "json",
            ".xml": "xml",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".md": "markdown",
            ".sql": "sql",
            ".sh": "shell",
            ".bash": "shell",
            ".zsh": "shell",
        }

        ext = Path(file_path).suffix.lower()
        return extension_map.get(ext, "plaintext")
