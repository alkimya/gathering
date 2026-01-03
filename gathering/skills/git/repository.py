"""
Git Skill for GatheRing.
Provides Git operations for agents.
"""

import subprocess
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from gathering.skills.base import BaseSkill, SkillResponse, SkillPermission


class GitSkill(BaseSkill):
    """
    Git operations skill.

    Provides tools for:
    - Repository management (clone, init)
    - Staging and commits
    - Branch operations
    - Push/pull operations
    - Pull request creation (via gh CLI)
    """

    name = "git"
    description = "Git version control operations"
    version = "1.0.0"
    required_permissions = [SkillPermission.GIT, SkillPermission.READ, SkillPermission.WRITE]

    # Safety limits
    MAX_DIFF_SIZE = 100_000  # Max chars for diff output
    MAX_LOG_ENTRIES = 100

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.working_dir = config.get("working_dir") if config else None
        self.allowed_remotes = config.get("allowed_remotes", []) if config else []

    def get_tools_definition(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "git_status",
                "description": "Get the current status of the git repository (staged, unstaged, untracked files)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the repository (optional, uses working_dir if not specified)"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "git_diff",
                "description": "Show changes between commits, commit and working tree, etc.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Repository path"},
                        "staged": {"type": "boolean", "description": "Show staged changes only", "default": False},
                        "file": {"type": "string", "description": "Specific file to diff"}
                    },
                    "required": []
                }
            },
            {
                "name": "git_log",
                "description": "Show commit history",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Repository path"},
                        "limit": {"type": "integer", "description": "Number of commits to show", "default": 10},
                        "oneline": {"type": "boolean", "description": "One line per commit", "default": True},
                        "branch": {"type": "string", "description": "Branch to show logs for"}
                    },
                    "required": []
                }
            },
            {
                "name": "git_add",
                "description": "Stage files for commit",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Repository path"},
                        "files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Files to stage (use '.' for all)"
                        }
                    },
                    "required": ["files"]
                }
            },
            {
                "name": "git_commit",
                "description": "Create a commit with staged changes",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Repository path"},
                        "message": {"type": "string", "description": "Commit message"},
                        "author": {"type": "string", "description": "Author in 'Name <email>' format"}
                    },
                    "required": ["message"]
                }
            },
            {
                "name": "git_push",
                "description": "Push commits to remote repository",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Repository path"},
                        "remote": {"type": "string", "description": "Remote name", "default": "origin"},
                        "branch": {"type": "string", "description": "Branch to push"},
                        "set_upstream": {"type": "boolean", "description": "Set upstream tracking", "default": False}
                    },
                    "required": []
                }
            },
            {
                "name": "git_pull",
                "description": "Pull changes from remote repository",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Repository path"},
                        "remote": {"type": "string", "description": "Remote name", "default": "origin"},
                        "branch": {"type": "string", "description": "Branch to pull"},
                        "rebase": {"type": "boolean", "description": "Rebase instead of merge", "default": False}
                    },
                    "required": []
                }
            },
            {
                "name": "git_branch",
                "description": "List, create, or switch branches",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Repository path"},
                        "action": {
                            "type": "string",
                            "enum": ["list", "create", "switch", "delete"],
                            "description": "Branch action"
                        },
                        "name": {"type": "string", "description": "Branch name (for create/switch/delete)"}
                    },
                    "required": ["action"]
                }
            },
            {
                "name": "git_clone",
                "description": "Clone a repository",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Repository URL"},
                        "destination": {"type": "string", "description": "Destination path"},
                        "branch": {"type": "string", "description": "Branch to clone"},
                        "depth": {"type": "integer", "description": "Shallow clone depth"}
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "git_create_pr",
                "description": "Create a pull request using GitHub CLI (gh)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Repository path"},
                        "title": {"type": "string", "description": "PR title"},
                        "body": {"type": "string", "description": "PR description"},
                        "base": {"type": "string", "description": "Base branch", "default": "main"},
                        "draft": {"type": "boolean", "description": "Create as draft", "default": False}
                    },
                    "required": ["title", "body"]
                }
            },
            {
                "name": "git_rebase",
                "description": "Rebase current branch onto another branch or commit",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Repository path"},
                        "onto": {"type": "string", "description": "Branch or commit to rebase onto"},
                        "upstream": {"type": "string", "description": "Upstream branch for --onto (optional)"},
                        "branch": {"type": "string", "description": "Branch to rebase (default: current)"},
                        "abort": {"type": "boolean", "description": "Abort ongoing rebase", "default": False},
                        "continue_rebase": {"type": "boolean", "description": "Continue after resolving conflicts", "default": False},
                        "skip": {"type": "boolean", "description": "Skip current commit during rebase", "default": False}
                    },
                    "required": []
                }
            },
            {
                "name": "git_stash",
                "description": "Stash or restore uncommitted changes",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Repository path"},
                        "action": {
                            "type": "string",
                            "enum": ["push", "pop", "list", "apply", "drop", "clear"],
                            "description": "Stash action",
                            "default": "push"
                        },
                        "message": {"type": "string", "description": "Stash message (for push)"},
                        "index": {"type": "integer", "description": "Stash index (for pop/apply/drop)", "default": 0},
                        "include_untracked": {"type": "boolean", "description": "Include untracked files", "default": False}
                    },
                    "required": []
                }
            },
            {
                "name": "git_cherry_pick",
                "description": "Apply specific commits to current branch",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Repository path"},
                        "commits": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Commit hashes to cherry-pick"
                        },
                        "no_commit": {"type": "boolean", "description": "Apply changes without committing", "default": False},
                        "abort": {"type": "boolean", "description": "Abort ongoing cherry-pick", "default": False},
                        "continue_pick": {"type": "boolean", "description": "Continue after resolving conflicts", "default": False}
                    },
                    "required": []
                }
            },
        ]

    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> SkillResponse:
        """Execute a git tool."""
        self.ensure_initialized()

        start_time = datetime.utcnow()

        try:
            # Route to appropriate handler
            handlers = {
                "git_status": self._git_status,
                "git_diff": self._git_diff,
                "git_log": self._git_log,
                "git_add": self._git_add,
                "git_commit": self._git_commit,
                "git_push": self._git_push,
                "git_pull": self._git_pull,
                "git_branch": self._git_branch,
                "git_clone": self._git_clone,
                "git_create_pr": self._git_create_pr,
                "git_rebase": self._git_rebase,
                "git_stash": self._git_stash,
                "git_cherry_pick": self._git_cherry_pick,
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

    def _get_repo_path(self, tool_input: Dict[str, Any]) -> Path:
        """Get repository path from input or config."""
        path = tool_input.get("path") or self.working_dir
        if not path:
            raise ValueError("No repository path specified")
        return Path(path).resolve()

    def _run_git(
        self,
        args: List[str],
        cwd: Optional[Path] = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        """Run a git command safely."""
        cmd = ["git"] + args

        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if check and result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, cmd, result.stdout, result.stderr
            )

        return result

    def _git_status(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Get repository status."""
        repo_path = self._get_repo_path(tool_input)

        # Get status in porcelain format for parsing
        result = self._run_git(["status", "--porcelain", "-b"], cwd=repo_path)

        lines = result.stdout.strip().split("\n")
        branch_info = lines[0] if lines else ""
        file_lines = lines[1:] if len(lines) > 1 else []

        # Parse branch info
        branch_match = re.match(r"## (.+?)(?:\.\.\.(.+))?$", branch_info)
        current_branch = branch_match.group(1) if branch_match else "unknown"
        tracking = branch_match.group(2) if branch_match else None

        # Parse file status
        staged = []
        unstaged = []
        untracked = []

        for line in file_lines:
            if not line:
                continue
            status = line[:2]
            filename = line[3:]

            if status[0] in "MADRC":
                staged.append({"status": status[0], "file": filename})
            if status[1] in "MD":
                unstaged.append({"status": status[1], "file": filename})
            if status == "??":
                untracked.append(filename)

        return SkillResponse(
            success=True,
            message=f"Repository status for {repo_path}",
            data={
                "branch": current_branch,
                "tracking": tracking,
                "staged": staged,
                "unstaged": unstaged,
                "untracked": untracked,
                "clean": len(staged) == 0 and len(unstaged) == 0 and len(untracked) == 0,
            }
        )

    def _git_diff(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Show diff."""
        repo_path = self._get_repo_path(tool_input)

        args = ["diff"]
        if tool_input.get("staged"):
            args.append("--cached")
        if tool_input.get("file"):
            args.append("--")
            args.append(tool_input["file"])

        result = self._run_git(args, cwd=repo_path)
        diff_output = result.stdout

        # Truncate if too large
        if len(diff_output) > self.MAX_DIFF_SIZE:
            diff_output = diff_output[:self.MAX_DIFF_SIZE] + "\n... (truncated)"

        return SkillResponse(
            success=True,
            message="Diff retrieved",
            data={"diff": diff_output, "truncated": len(result.stdout) > self.MAX_DIFF_SIZE}
        )

    def _git_log(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Show commit log."""
        repo_path = self._get_repo_path(tool_input)

        limit = min(tool_input.get("limit", 10), self.MAX_LOG_ENTRIES)
        args = ["log", f"-{limit}"]

        if tool_input.get("oneline", True):
            args.append("--oneline")
        else:
            args.extend(["--format=%H|%an|%ae|%ad|%s", "--date=iso"])

        if tool_input.get("branch"):
            args.append(tool_input["branch"])

        result = self._run_git(args, cwd=repo_path)

        if tool_input.get("oneline", True):
            commits = [
                {"hash": line.split()[0], "message": " ".join(line.split()[1:])}
                for line in result.stdout.strip().split("\n") if line
            ]
        else:
            commits = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split("|")
                    commits.append({
                        "hash": parts[0],
                        "author": parts[1],
                        "email": parts[2],
                        "date": parts[3],
                        "message": parts[4] if len(parts) > 4 else "",
                    })

        return SkillResponse(
            success=True,
            message=f"Found {len(commits)} commits",
            data={"commits": commits}
        )

    def _git_add(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Stage files."""
        repo_path = self._get_repo_path(tool_input)
        files = tool_input.get("files", [])

        if not files:
            return SkillResponse(
                success=False,
                message="No files specified to add",
                error="no_files"
            )

        args = ["add"] + files
        self._run_git(args, cwd=repo_path)

        return SkillResponse(
            success=True,
            message=f"Staged {len(files)} file(s)",
            data={"files": files}
        )

    def _git_commit(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Create a commit with agent trailers for traceability."""
        repo_path = self._get_repo_path(tool_input)
        message = tool_input.get("message")

        if not message:
            return SkillResponse(
                success=False,
                message="Commit message is required",
                error="no_message"
            )

        # Add agent trailers if context is available
        agent_name = None
        agent_id = None
        if hasattr(self, "context") and self.context:
            agent_name = self.context.get("agent_name")
            agent_id = self.context.get("agent_id")

        # Build commit message with trailers
        if agent_name:
            full_message = f"{message}\n\nAgent: {agent_name}"
            if agent_id:
                full_message += f"\nAgent-ID: {agent_id}"
        else:
            full_message = message

        args = ["commit", "-m", full_message]

        if tool_input.get("author"):
            args.extend(["--author", tool_input["author"]])

        result = self._run_git(args, cwd=repo_path)

        # Parse commit hash from output
        commit_match = re.search(r"\[[\w-]+ ([a-f0-9]+)\]", result.stdout)
        commit_hash = commit_match.group(1) if commit_match else None

        return SkillResponse(
            success=True,
            message="Commit created successfully",
            data={
                "hash": commit_hash,
                "message": message,
                "agent": agent_name,
                "agent_id": agent_id,
            }
        )

    def _git_push(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Push to remote."""
        repo_path = self._get_repo_path(tool_input)
        remote = tool_input.get("remote", "origin")
        branch = tool_input.get("branch")

        # Confirmation for push
        return SkillResponse(
            success=True,
            message=f"Ready to push to {remote}",
            needs_confirmation=True,
            confirmation_type="user",
            confirmation_message=f"Push to {remote}/{branch or 'current branch'}?",
            data={
                "action": "push",
                "remote": remote,
                "branch": branch,
                "path": str(repo_path),
            }
        )

    def _git_pull(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Pull from remote."""
        repo_path = self._get_repo_path(tool_input)
        remote = tool_input.get("remote", "origin")
        branch = tool_input.get("branch")

        args = ["pull", remote]
        if branch:
            args.append(branch)
        if tool_input.get("rebase"):
            args.append("--rebase")

        result = self._run_git(args, cwd=repo_path)

        return SkillResponse(
            success=True,
            message="Pull completed successfully",
            data={"output": result.stdout}
        )

    def _git_branch(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Branch operations."""
        repo_path = self._get_repo_path(tool_input)
        action = tool_input.get("action", "list")
        branch_name = tool_input.get("name")

        if action == "list":
            result = self._run_git(["branch", "-a"], cwd=repo_path)
            branches = [b.strip().lstrip("* ") for b in result.stdout.split("\n") if b.strip()]
            current = next((b.strip()[2:] for b in result.stdout.split("\n") if b.startswith("*")), None)
            return SkillResponse(
                success=True,
                message=f"Found {len(branches)} branches",
                data={"branches": branches, "current": current}
            )

        elif action == "create":
            if not branch_name:
                return SkillResponse(success=False, message="Branch name required", error="no_name")
            self._run_git(["branch", branch_name], cwd=repo_path)
            return SkillResponse(
                success=True,
                message=f"Created branch '{branch_name}'",
                data={"branch": branch_name}
            )

        elif action == "switch":
            if not branch_name:
                return SkillResponse(success=False, message="Branch name required", error="no_name")
            self._run_git(["checkout", branch_name], cwd=repo_path)
            return SkillResponse(
                success=True,
                message=f"Switched to branch '{branch_name}'",
                data={"branch": branch_name}
            )

        elif action == "delete":
            if not branch_name:
                return SkillResponse(success=False, message="Branch name required", error="no_name")
            return SkillResponse(
                success=True,
                message=f"Ready to delete branch '{branch_name}'",
                needs_confirmation=True,
                confirmation_type="destructive",
                confirmation_message=f"Delete branch '{branch_name}'? This cannot be undone.",
                data={"action": "delete_branch", "branch": branch_name}
            )

        return SkillResponse(success=False, message=f"Unknown action: {action}", error="unknown_action")

    def _git_clone(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Clone a repository."""
        url = tool_input.get("url")
        if not url:
            return SkillResponse(success=False, message="Repository URL required", error="no_url")

        # Validate URL if restrictions configured
        if self.allowed_remotes:
            allowed = any(url.startswith(remote) for remote in self.allowed_remotes)
            if not allowed:
                return SkillResponse(
                    success=False,
                    message="Remote not in allowed list",
                    error="remote_not_allowed"
                )

        args = ["clone", url]

        if tool_input.get("destination"):
            args.append(tool_input["destination"])
        if tool_input.get("branch"):
            args.extend(["-b", tool_input["branch"]])
        if tool_input.get("depth"):
            args.extend(["--depth", str(tool_input["depth"])])

        self._run_git(args)

        return SkillResponse(
            success=True,
            message=f"Cloned repository from {url}",
            data={"url": url, "destination": tool_input.get("destination")}
        )

    def _git_create_pr(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Create a pull request using GitHub CLI."""
        repo_path = self._get_repo_path(tool_input)

        # Check if gh is available
        try:
            subprocess.run(["gh", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return SkillResponse(
                success=False,
                message="GitHub CLI (gh) not installed or not authenticated",
                error="gh_not_available"
            )

        title = tool_input.get("title")
        body = tool_input.get("body")
        base = tool_input.get("base", "main")

        if not title or not body:
            return SkillResponse(
                success=False,
                message="Title and body are required for PR",
                error="missing_fields"
            )

        args = ["gh", "pr", "create", "--title", title, "--body", body, "--base", base]

        if tool_input.get("draft"):
            args.append("--draft")

        result = subprocess.run(
            args,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return SkillResponse(
                success=False,
                message=f"Failed to create PR: {result.stderr}",
                error=result.stderr
            )

        # Extract PR URL from output
        pr_url = result.stdout.strip()

        return SkillResponse(
            success=True,
            message=f"Pull request created: {pr_url}",
            data={"url": pr_url, "title": title}
        )

    def _git_rebase(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Rebase current branch onto another."""
        repo_path = self._get_repo_path(tool_input)

        # Handle abort/continue/skip first
        if tool_input.get("abort"):
            self._run_git(["rebase", "--abort"], cwd=repo_path)
            return SkillResponse(
                success=True,
                message="Rebase aborted",
                data={"action": "abort"}
            )

        if tool_input.get("continue_rebase"):
            result = self._run_git(["rebase", "--continue"], cwd=repo_path, check=False)
            if result.returncode != 0:
                return SkillResponse(
                    success=False,
                    message="Cannot continue rebase - conflicts may remain",
                    error=result.stderr,
                    data={"action": "continue", "conflicts": True}
                )
            return SkillResponse(
                success=True,
                message="Rebase continued successfully",
                data={"action": "continue"}
            )

        if tool_input.get("skip"):
            self._run_git(["rebase", "--skip"], cwd=repo_path)
            return SkillResponse(
                success=True,
                message="Skipped current commit",
                data={"action": "skip"}
            )

        # Normal rebase
        onto = tool_input.get("onto")
        if not onto:
            return SkillResponse(
                success=False,
                message="Target branch/commit required for rebase",
                error="missing_onto"
            )

        args = ["rebase"]

        # --onto syntax: git rebase --onto <newbase> <upstream> [<branch>]
        upstream = tool_input.get("upstream")
        if upstream:
            args.extend(["--onto", onto, upstream])
        else:
            args.append(onto)

        branch = tool_input.get("branch")
        if branch:
            args.append(branch)

        # Rebase is a potentially destructive operation - require confirmation
        return SkillResponse(
            success=True,
            message=f"Ready to rebase onto {onto}",
            needs_confirmation=True,
            confirmation_type="destructive",
            confirmation_message=f"Rebase {'branch ' + branch if branch else 'current branch'} onto {onto}? This will rewrite commit history.",
            data={
                "action": "rebase",
                "onto": onto,
                "upstream": upstream,
                "branch": branch,
                "command": " ".join(["git"] + args),
                "path": str(repo_path),
            }
        )

    def _git_stash(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Stash operations."""
        repo_path = self._get_repo_path(tool_input)
        action = tool_input.get("action", "push")

        if action == "list":
            result = self._run_git(["stash", "list"], cwd=repo_path)
            stashes = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    # Format: stash@{0}: WIP on branch: message
                    match = re.match(r"(stash@\{(\d+)\}): (.+)", line)
                    if match:
                        stashes.append({
                            "ref": match.group(1),
                            "index": int(match.group(2)),
                            "description": match.group(3)
                        })
            return SkillResponse(
                success=True,
                message=f"Found {len(stashes)} stash(es)",
                data={"stashes": stashes}
            )

        elif action == "push":
            args = ["stash", "push"]
            if tool_input.get("message"):
                args.extend(["-m", tool_input["message"]])
            if tool_input.get("include_untracked"):
                args.append("-u")

            result = self._run_git(args, cwd=repo_path, check=False)
            if "No local changes" in result.stdout:
                return SkillResponse(
                    success=True,
                    message="No changes to stash",
                    data={"stashed": False}
                )
            return SkillResponse(
                success=True,
                message="Changes stashed",
                data={"stashed": True, "output": result.stdout.strip()}
            )

        elif action == "pop":
            index = tool_input.get("index", 0)
            result = self._run_git(["stash", "pop", f"stash@{{{index}}}"], cwd=repo_path, check=False)
            if result.returncode != 0:
                return SkillResponse(
                    success=False,
                    message=f"Failed to pop stash: {result.stderr}",
                    error=result.stderr
                )
            return SkillResponse(
                success=True,
                message=f"Popped stash@{{{index}}}",
                data={"index": index}
            )

        elif action == "apply":
            index = tool_input.get("index", 0)
            result = self._run_git(["stash", "apply", f"stash@{{{index}}}"], cwd=repo_path, check=False)
            if result.returncode != 0:
                return SkillResponse(
                    success=False,
                    message=f"Failed to apply stash: {result.stderr}",
                    error=result.stderr
                )
            return SkillResponse(
                success=True,
                message=f"Applied stash@{{{index}}} (stash kept)",
                data={"index": index}
            )

        elif action == "drop":
            index = tool_input.get("index", 0)
            return SkillResponse(
                success=True,
                message=f"Ready to drop stash@{{{index}}}",
                needs_confirmation=True,
                confirmation_type="destructive",
                confirmation_message=f"Drop stash@{{{index}}}? This cannot be undone.",
                data={"action": "drop", "index": index}
            )

        elif action == "clear":
            return SkillResponse(
                success=True,
                message="Ready to clear all stashes",
                needs_confirmation=True,
                confirmation_type="destructive",
                confirmation_message="Clear ALL stashes? This cannot be undone.",
                data={"action": "clear"}
            )

        return SkillResponse(
            success=False,
            message=f"Unknown stash action: {action}",
            error="unknown_action"
        )

    def _git_cherry_pick(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Cherry-pick commits."""
        repo_path = self._get_repo_path(tool_input)

        # Handle abort/continue
        if tool_input.get("abort"):
            self._run_git(["cherry-pick", "--abort"], cwd=repo_path)
            return SkillResponse(
                success=True,
                message="Cherry-pick aborted",
                data={"action": "abort"}
            )

        if tool_input.get("continue_pick"):
            result = self._run_git(["cherry-pick", "--continue"], cwd=repo_path, check=False)
            if result.returncode != 0:
                return SkillResponse(
                    success=False,
                    message="Cannot continue cherry-pick - conflicts may remain",
                    error=result.stderr
                )
            return SkillResponse(
                success=True,
                message="Cherry-pick continued",
                data={"action": "continue"}
            )

        commits = tool_input.get("commits", [])
        if not commits:
            return SkillResponse(
                success=False,
                message="At least one commit hash required",
                error="missing_commits"
            )

        args = ["cherry-pick"]
        if tool_input.get("no_commit"):
            args.append("-n")
        args.extend(commits)

        result = self._run_git(args, cwd=repo_path, check=False)

        if result.returncode != 0:
            # Check if it's a conflict
            if "CONFLICT" in result.stdout or "conflict" in result.stderr:
                return SkillResponse(
                    success=False,
                    message="Cherry-pick has conflicts that need resolution",
                    error="conflicts",
                    data={
                        "commits": commits,
                        "conflicts": True,
                        "output": result.stdout,
                        "hint": "Resolve conflicts, then use continue_pick=True or abort=True"
                    }
                )
            return SkillResponse(
                success=False,
                message=f"Cherry-pick failed: {result.stderr}",
                error=result.stderr
            )

        return SkillResponse(
            success=True,
            message=f"Cherry-picked {len(commits)} commit(s)",
            data={"commits": commits, "no_commit": tool_input.get("no_commit", False)}
        )
