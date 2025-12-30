"""
Git Manager for workspace git operations.

Handles git commits, diffs, branches, and history.
"""

import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class GitManager:
    """
    Manages git operations in a workspace.

    Provides git commits, diffs, branches, and history.
    """

    @classmethod
    def is_git_repo(cls, project_path: str) -> bool:
        """
        Check if project is a git repository.

        Args:
            project_path: Path to project.

        Returns:
            True if git repository.
        """
        git_dir = Path(project_path) / ".git"
        return git_dir.exists()

    @classmethod
    def get_commits(
        cls,
        project_path: str,
        limit: int = 50,
        branch: Optional[str] = None,
        author: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get git commit history.

        Args:
            project_path: Path to project.
            limit: Maximum number of commits.
            branch: Branch name (None = current branch).
            author: Filter by author.

        Returns:
            List of commits with metadata.

        Example:
            >>> commits = GitManager.get_commits("/my/project", limit=10)
            >>> print(commits[0]["message"])
            'feat: add new feature'
        """
        if not cls.is_git_repo(project_path):
            return []

        # Build git log command
        cmd = [
            "git",
            "log",
            f"-n{limit}",
            "--pretty=format:%H%n%an%n%ae%n%at%n%s%n%b%n---END---",
        ]

        if branch:
            cmd.append(branch)

        if author:
            cmd.extend(["--author", author])

        try:
            result = subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                logger.error(f"Git log failed: {result.stderr}")
                return []

            # Parse output
            commits = []
            commit_texts = result.stdout.split("---END---\n")

            for commit_text in commit_texts:
                if not commit_text.strip():
                    continue

                lines = commit_text.strip().split("\n")
                if len(lines) < 5:
                    continue

                commit = {
                    "hash": lines[0],
                    "author_name": lines[1],
                    "author_email": lines[2],
                    "timestamp": int(lines[3]),
                    "date": datetime.fromtimestamp(int(lines[3])).isoformat(),
                    "message": lines[4],
                    "body": "\n".join(lines[5:]) if len(lines) > 5 else "",
                }

                # Get files changed in this commit
                commit["files"] = cls._get_commit_files(project_path, commit["hash"])

                # Get stats
                commit["stats"] = cls._get_commit_stats(project_path, commit["hash"])

                commits.append(commit)

            return commits

        except subprocess.TimeoutExpired:
            logger.error("Git log timed out")
            return []
        except Exception as e:
            logger.error(f"Error getting commits: {e}")
            return []

    @classmethod
    def _get_commit_files(cls, project_path: str, commit_hash: str) -> List[str]:
        """Get files changed in a commit."""
        try:
            result = subprocess.run(
                ["git", "show", "--name-only", "--pretty=format:", commit_hash],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
                return files

        except Exception as e:
            logger.warning(f"Error getting commit files: {e}")

        return []

    @classmethod
    def _get_commit_stats(cls, project_path: str, commit_hash: str) -> Dict[str, int]:
        """Get commit statistics (additions, deletions)."""
        try:
            result = subprocess.run(
                ["git", "show", "--stat", "--pretty=format:", commit_hash],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                # Parse stats from last line
                lines = result.stdout.strip().split("\n")
                if lines:
                    last_line = lines[-1]
                    # Format: "X files changed, Y insertions(+), Z deletions(-)"
                    parts = last_line.split(",")

                    files_changed = 0
                    insertions = 0
                    deletions = 0

                    for part in parts:
                        part = part.strip()
                        if "file" in part:
                            files_changed = int(part.split()[0])
                        elif "insertion" in part:
                            insertions = int(part.split()[0])
                        elif "deletion" in part:
                            deletions = int(part.split()[0])

                    return {
                        "files_changed": files_changed,
                        "insertions": insertions,
                        "deletions": deletions,
                    }

        except Exception as e:
            logger.warning(f"Error getting commit stats: {e}")

        return {"files_changed": 0, "insertions": 0, "deletions": 0}

    @classmethod
    def get_diff(
        cls,
        project_path: str,
        commit_hash: Optional[str] = None,
        file_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get git diff.

        Args:
            project_path: Path to project.
            commit_hash: Commit to diff (None = working directory).
            file_path: Specific file to diff (None = all files).

        Returns:
            Diff content and metadata.

        Example:
            >>> diff = GitManager.get_diff("/my/project", commit_hash="abc123")
            >>> print(diff["diff"][:100])
            'diff --git a/src/main.py b/src/main.py...'
        """
        if not cls.is_git_repo(project_path):
            return {"error": "Not a git repository"}

        cmd = ["git", "diff"]

        if commit_hash:
            cmd.extend([f"{commit_hash}^", commit_hash])

        if file_path:
            cmd.append("--")
            cmd.append(file_path)

        try:
            result = subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return {"error": result.stderr}

            return {
                "diff": result.stdout,
                "commit": commit_hash,
                "file": file_path,
            }

        except Exception as e:
            logger.error(f"Error getting diff: {e}")
            return {"error": str(e)}

    @classmethod
    def get_branches(cls, project_path: str) -> Dict[str, Any]:
        """
        Get git branches.

        Args:
            project_path: Path to project.

        Returns:
            Dictionary with branch information.
        """
        if not cls.is_git_repo(project_path):
            return {"current": None, "branches": []}

        try:
            # Get current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=5,
            )

            current_branch = result.stdout.strip() if result.returncode == 0 else None

            # Get all branches
            result = subprocess.run(
                ["git", "branch", "-a"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=5,
            )

            branches = []
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    line = line.strip()
                    if not line:
                        continue

                    is_current = line.startswith("*")
                    branch_name = line.lstrip("* ").strip()

                    # Skip HEAD reference
                    if "HEAD" in branch_name:
                        continue

                    # Clean remote branch names
                    if branch_name.startswith("remotes/"):
                        branch_type = "remote"
                        branch_name = branch_name[8:]  # Remove "remotes/"
                    else:
                        branch_type = "local"

                    branches.append({
                        "name": branch_name,
                        "type": branch_type,
                        "current": is_current,
                    })

            return {
                "current": current_branch,
                "branches": branches,
            }

        except Exception as e:
            logger.error(f"Error getting branches: {e}")
            return {"current": None, "branches": [], "error": str(e)}

    @classmethod
    def get_file_history(
        cls,
        project_path: str,
        file_path: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Get git history for a specific file.

        Args:
            project_path: Path to project.
            file_path: Relative path to file.
            limit: Maximum number of commits.

        Returns:
            List of commits that modified the file.
        """
        if not cls.is_git_repo(project_path):
            return []

        cmd = [
            "git",
            "log",
            f"-n{limit}",
            "--pretty=format:%H%n%an%n%at%n%s%n---END---",
            "--",
            file_path,
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return []

            commits = []
            commit_texts = result.stdout.split("---END---\n")

            for commit_text in commit_texts:
                if not commit_text.strip():
                    continue

                lines = commit_text.strip().split("\n")
                if len(lines) < 4:
                    continue

                commits.append({
                    "hash": lines[0],
                    "author": lines[1],
                    "timestamp": int(lines[2]),
                    "date": datetime.fromtimestamp(int(lines[2])).isoformat(),
                    "message": lines[3],
                    "file": file_path,
                })

            return commits

        except Exception as e:
            logger.error(f"Error getting file history: {e}")
            return []

    @classmethod
    def get_status(cls, project_path: str) -> Dict[str, Any]:
        """
        Get git status.

        Args:
            project_path: Path to project.

        Returns:
            Git status information.
        """
        if not cls.is_git_repo(project_path):
            return {"is_git_repo": False}

        try:
            # Get status
            result = subprocess.run(
                ["git", "status", "--porcelain", "-b"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                return {"error": result.stderr}

            lines = result.stdout.split("\n")

            # Parse branch info
            branch_line = lines[0] if lines else ""
            branch = None
            ahead = 0
            behind = 0

            if branch_line.startswith("##"):
                parts = branch_line[3:].split("...")
                if parts:
                    branch = parts[0].strip()

                # Check ahead/behind
                if "[" in branch_line:
                    tracking_info = branch_line.split("[")[1].split("]")[0]
                    if "ahead" in tracking_info:
                        ahead = int(tracking_info.split("ahead ")[1].split("]")[0].split(",")[0])
                    if "behind" in tracking_info:
                        behind = int(tracking_info.split("behind ")[1].split("]")[0])

            # Parse file statuses
            modified = []
            added = []
            deleted = []
            untracked = []

            for line in lines[1:]:
                if not line.strip():
                    continue

                status = line[:2]
                filepath = line[3:].strip()

                if status == "??":
                    untracked.append(filepath)
                elif "M" in status:
                    modified.append(filepath)
                elif "A" in status:
                    added.append(filepath)
                elif "D" in status:
                    deleted.append(filepath)

            return {
                "is_git_repo": True,
                "branch": branch,
                "ahead": ahead,
                "behind": behind,
                "modified": modified,
                "added": added,
                "deleted": deleted,
                "untracked": untracked,
                "clean": len(modified) + len(added) + len(deleted) + len(untracked) == 0,
            }

        except Exception as e:
            logger.error(f"Error getting git status: {e}")
            return {"error": str(e)}
