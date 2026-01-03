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
    def _validate_file_path(cls, project_path: str, file_path: str) -> bool:
        """
        Validate that a file path is within the project directory.

        Prevents path traversal attacks via git operations.

        Args:
            project_path: The project root path.
            file_path: The file path to validate.

        Returns:
            True if path is safe, False otherwise.
        """
        if not file_path:
            return True  # No path is safe

        try:
            project = Path(project_path).resolve()
            target = (project / file_path).resolve()
            # Check that target is within project
            target.relative_to(project)
            return True
        except ValueError:
            logger.warning(f"Path traversal attempt blocked: {file_path}")
            return False

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

        # Validate file_path to prevent path traversal
        if file_path and not cls._validate_file_path(project_path, file_path):
            return {"error": "Invalid file path"}

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

        # Validate file_path to prevent path traversal
        if not cls._validate_file_path(project_path, file_path):
            logger.warning(f"Path traversal blocked in get_file_history: {file_path}")
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
            # Porcelain format: XY filename
            # X = status in index (staged)
            # Y = status in working tree (unstaged)
            modified = []
            added = []
            deleted = []
            untracked = []

            staged_modified = []
            staged_added = []
            staged_deleted = []

            for line in lines[1:]:
                if not line.strip():
                    continue

                index_status = line[0]  # First character: staged
                worktree_status = line[1]  # Second character: unstaged
                filepath = line[3:].strip()

                # Untracked files
                if index_status == "?" and worktree_status == "?":
                    untracked.append(filepath)
                    continue

                # Staged changes (index status)
                if index_status == "M":
                    staged_modified.append(filepath)
                elif index_status == "A":
                    staged_added.append(filepath)
                elif index_status == "D":
                    staged_deleted.append(filepath)

                # Unstaged changes (worktree status)
                if worktree_status == "M":
                    modified.append(filepath)
                elif worktree_status == "A":
                    added.append(filepath)
                elif worktree_status == "D":
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
                "staged": {
                    "modified": staged_modified,
                    "added": staged_added,
                    "deleted": staged_deleted,
                },
                "clean": len(modified) + len(added) + len(deleted) + len(untracked) == 0,
            }

        except Exception as e:
            logger.error(f"Error getting git status: {e}")
            return {"error": str(e)}

    @classmethod
    def get_graph(
        cls,
        project_path: str,
        limit: int = 50,
        all_branches: bool = True,
    ) -> Dict[str, Any]:
        """
        Get git graph data for visualization (like git log --graph).

        Args:
            project_path: Path to project.
            limit: Maximum number of commits.
            all_branches: Include all branches (default True).

        Returns:
            Dict with commits and branch/merge information for graph rendering.

        Example:
            >>> graph = GitManager.get_graph("/my/project")
            >>> print(graph["commits"][0])
        """
        if not cls.is_git_repo(project_path):
            return {"error": "Not a git repository"}

        try:
            # Get commits with parent information for graph
            cmd = [
                "git",
                "log",
                f"-n{limit}",
                "--pretty=format:%H|%P|%an|%ae|%at|%s|%D",
                "--date-order",
            ]

            if all_branches:
                cmd.append("--all")

            result = subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
                check=True,
            )

            commits = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split("|")
                if len(parts) < 6:
                    continue

                commit_hash = parts[0]
                parents = parts[1].split() if parts[1] else []
                author_name = parts[2]
                author_email = parts[3]
                timestamp = int(parts[4])
                message = parts[5]
                refs = parts[6] if len(parts) > 6 else ""

                # Parse refs (branches, tags)
                branches = []
                tags = []
                if refs:
                    for ref in refs.split(", "):
                        if ref.startswith("tag: "):
                            tags.append(ref[5:])
                        elif ref.startswith("HEAD -> "):
                            branches.append(ref[8:])
                        elif ref != "HEAD":
                            branches.append(ref)

                commits.append({
                    "hash": commit_hash,
                    "short_hash": commit_hash[:7],
                    "parents": parents,
                    "parent_count": len(parents),
                    "author_name": author_name,
                    "author_email": author_email,
                    "timestamp": timestamp,
                    "date": datetime.fromtimestamp(timestamp).isoformat(),
                    "message": message,
                    "branches": branches,
                    "tags": tags,
                    "is_merge": len(parents) > 1,
                })

            return {
                "commits": commits,
                "total": len(commits),
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Git graph command failed: {e.stderr}")
            return {"error": str(e.stderr)}
        except Exception as e:
            logger.error(f"Error getting git graph: {e}")
            return {"error": str(e)}

    @classmethod
    def stage_files(cls, project_path: str, files: List[str]) -> Dict[str, Any]:
        """
        Stage files for commit.

        Args:
            project_path: Path to project.
            files: List of file paths to stage.

        Returns:
            Status information or error.
        """
        if not cls.is_git_repo(project_path):
            return {"error": "Not a git repository"}

        # Validate all file paths to prevent path traversal
        for file_path in files:
            if not cls._validate_file_path(project_path, file_path):
                return {"error": f"Invalid file path: {file_path}"}

        try:
            # Stage each file
            for file_path in files:
                result = subprocess.run(
                    ["git", "add", file_path],
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode != 0:
                    logger.error(f"Failed to stage {file_path}: {result.stderr}")
                    return {"error": f"Failed to stage {file_path}: {result.stderr}"}

            return {"success": True, "files": files}

        except Exception as e:
            logger.error(f"Error staging files: {e}")
            return {"error": str(e)}

    @classmethod
    def unstage_files(cls, project_path: str, files: List[str]) -> Dict[str, Any]:
        """
        Unstage files.

        Args:
            project_path: Path to project.
            files: List of file paths to unstage.

        Returns:
            Status information or error.
        """
        if not cls.is_git_repo(project_path):
            return {"error": "Not a git repository"}

        # Validate all file paths to prevent path traversal
        for file_path in files:
            if not cls._validate_file_path(project_path, file_path):
                return {"error": f"Invalid file path: {file_path}"}

        try:
            # Unstage each file
            for file_path in files:
                result = subprocess.run(
                    ["git", "restore", "--staged", file_path],
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode != 0:
                    logger.error(f"Failed to unstage {file_path}: {result.stderr}")
                    return {"error": f"Failed to unstage {file_path}: {result.stderr}"}

            return {"success": True, "files": files}

        except Exception as e:
            logger.error(f"Error unstaging files: {e}")
            return {"error": str(e)}

    @classmethod
    def commit(
        cls,
        project_path: str,
        message: str,
        author_name: Optional[str] = None,
        author_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a commit.

        Args:
            project_path: Path to project.
            message: Commit message.
            author_name: Optional author name.
            author_email: Optional author email.

        Returns:
            Commit information or error.
        """
        if not cls.is_git_repo(project_path):
            return {"error": "Not a git repository"}

        if not message or not message.strip():
            return {"error": "Commit message is required"}

        try:
            cmd = ["git", "commit", "-m", message]

            # Add author if provided
            if author_name and author_email:
                cmd.extend(["--author", f"{author_name} <{author_email}>"])

            result = subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                logger.error(f"Commit failed: {result.stderr}")
                return {"error": result.stderr}

            # Extract commit hash from output
            output = result.stdout
            commit_hash = None
            if output:
                # Parse output like "[branch abc1234] message"
                parts = output.split()
                if len(parts) >= 2:
                    commit_hash = parts[1].strip("[]")

            return {
                "success": True,
                "message": message,
                "hash": commit_hash,
                "output": output,
            }

        except Exception as e:
            logger.error(f"Error creating commit: {e}")
            return {"error": str(e)}

    @classmethod
    def push(
        cls,
        project_path: str,
        remote: str = "origin",
        branch: Optional[str] = None,
        set_upstream: bool = False,
    ) -> Dict[str, Any]:
        """
        Push to remote repository.

        Args:
            project_path: Path to project.
            remote: Remote name (default: origin).
            branch: Branch name (None = current branch).
            set_upstream: Set upstream tracking.

        Returns:
            Status information or error.
        """
        if not cls.is_git_repo(project_path):
            return {"error": "Not a git repository"}

        try:
            cmd = ["git", "push"]

            if set_upstream:
                cmd.append("-u")

            cmd.append(remote)

            if branch:
                cmd.append(branch)

            result = subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                logger.error(f"Push failed: {result.stderr}")
                return {"error": result.stderr}

            return {
                "success": True,
                "remote": remote,
                "branch": branch,
                "output": result.stdout + result.stderr,
            }

        except subprocess.TimeoutExpired:
            logger.error("Push timed out")
            return {"error": "Push operation timed out"}
        except Exception as e:
            logger.error(f"Error pushing: {e}")
            return {"error": str(e)}

    @classmethod
    def pull(
        cls,
        project_path: str,
        remote: str = "origin",
        branch: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Pull from remote repository.

        Args:
            project_path: Path to project.
            remote: Remote name (default: origin).
            branch: Branch name (None = current branch).

        Returns:
            Status information or error.
        """
        if not cls.is_git_repo(project_path):
            return {"error": "Not a git repository"}

        try:
            cmd = ["git", "pull", remote]

            if branch:
                cmd.append(branch)

            result = subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                logger.error(f"Pull failed: {result.stderr}")
                return {"error": result.stderr}

            return {
                "success": True,
                "remote": remote,
                "branch": branch,
                "output": result.stdout + result.stderr,
            }

        except subprocess.TimeoutExpired:
            logger.error("Pull timed out")
            return {"error": "Pull operation timed out"}
        except Exception as e:
            logger.error(f"Error pulling: {e}")
            return {"error": str(e)}
