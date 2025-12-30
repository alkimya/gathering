"""
Workspace management for GatheRing projects.

Provides IDE-like functionality for monitoring and interacting with
agent projects in real-time.

Features:
- File explorer with git status
- File reading/editing with history
- Git integration (commits, diffs, branches)
- Terminal execution
- Test runner integration
- Agent activity tracking

Usage:
    from gathering.workspace import WorkspaceManager, WorkspaceType

    # Detect workspace type
    workspace_type = WorkspaceManager.detect_type("/path/to/project")

    # Get file tree
    files = WorkspaceManager.list_files("/path/to/project")

    # Read file
    content = WorkspaceManager.read_file("/path/to/project/src/main.py")

    # Get git history
    commits = WorkspaceManager.get_git_commits("/path/to/project")
"""

from gathering.workspace.manager import WorkspaceManager, WorkspaceType
from gathering.workspace.file_manager import FileManager
from gathering.workspace.git_manager import GitManager
from gathering.workspace.activity_tracker import ActivityTracker

__all__ = [
    "WorkspaceManager",
    "WorkspaceType",
    "FileManager",
    "GitManager",
    "ActivityTracker",
]
