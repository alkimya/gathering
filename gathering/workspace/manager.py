"""
Workspace Manager for project workspaces.

Handles workspace type detection and provides unified interface
for different workspace types.
"""

import os
from pathlib import Path
from enum import Enum
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class WorkspaceType(str, Enum):
    """Types of workspaces."""

    DEVELOPMENT = "development"
    DESIGN_3D = "design_3d"
    VIDEO = "video"
    FINANCE = "finance"
    DATA_SCIENCE = "data_science"
    CUSTOM = "custom"


class WorkspaceManager:
    """
    Manages project workspaces.

    Detects workspace type and provides appropriate tools
    for each type of project.
    """

    # Patterns for workspace type detection
    DETECTION_PATTERNS = {
        WorkspaceType.DEVELOPMENT: {
            "files": [
                "package.json",
                "requirements.txt",
                "Cargo.toml",
                "pom.xml",
                "build.gradle",
                "go.mod",
                "Gemfile",
                "composer.json",
            ],
            "folders": [".git", "src", "tests", "test", "node_modules"],
            "extensions": [".py", ".js", ".ts", ".java", ".go", ".rs"],
        },
        WorkspaceType.DESIGN_3D: {
            "files": [],
            "folders": ["models", "textures", "renders", "scenes"],
            "extensions": [".blend", ".obj", ".fbx", ".max", ".ma", ".mb", ".c4d"],
        },
        WorkspaceType.VIDEO: {
            "files": [],
            "folders": ["footage", "renders", "audio", "exports"],
            "extensions": [".mp4", ".mov", ".avi", ".mkv", ".prproj", ".aep"],
        },
        WorkspaceType.FINANCE: {
            "files": ["strategy.py", "backtest.py", "config.yaml"],
            "folders": ["data", "strategies", "indicators", "backtests"],
            "extensions": [".py"],
        },
        WorkspaceType.DATA_SCIENCE: {
            "files": ["requirements.txt", "environment.yml"],
            "folders": ["data", "notebooks", "models", "datasets"],
            "extensions": [".ipynb", ".py", ".R"],
        },
    }

    @classmethod
    def detect_type(cls, project_path: str) -> WorkspaceType:
        """
        Detect workspace type from project structure.

        Args:
            project_path: Path to project directory.

        Returns:
            Detected workspace type.

        Example:
            >>> workspace_type = WorkspaceManager.detect_type("/my/project")
            >>> print(workspace_type)
            WorkspaceType.DEVELOPMENT
        """
        path = Path(project_path)
        if not path.exists():
            logger.warning(f"Project path does not exist: {project_path}")
            return WorkspaceType.CUSTOM

        # Score each workspace type
        scores: Dict[WorkspaceType, int] = {wt: 0 for wt in WorkspaceType}

        # Check files
        for workspace_type, patterns in cls.DETECTION_PATTERNS.items():
            # Check for specific files
            for file in patterns["files"]:
                if (path / file).exists():
                    scores[workspace_type] += 10

            # Check for folders
            for folder in patterns["folders"]:
                if (path / folder).exists():
                    scores[workspace_type] += 5

            # Check for file extensions (sample first 100 files)
            ext_count = 0
            for ext in patterns["extensions"]:
                for _ in path.rglob(f"*{ext}"):
                    ext_count += 1
                    if ext_count >= 10:
                        break
                if ext_count >= 10:
                    break

            scores[workspace_type] += min(ext_count, 10)

        # Return type with highest score
        max_score = max(scores.values())
        if max_score == 0:
            return WorkspaceType.CUSTOM

        for workspace_type, score in scores.items():
            if score == max_score:
                logger.info(
                    f"Detected workspace type: {workspace_type} (score: {score})"
                )
                return workspace_type

        return WorkspaceType.CUSTOM

    @classmethod
    def get_workspace_info(cls, project_path: str) -> Dict[str, Any]:
        """
        Get workspace information.

        Args:
            project_path: Path to project.

        Returns:
            Dictionary with workspace info.

        Example:
            >>> info = WorkspaceManager.get_workspace_info("/my/project")
            >>> print(info["type"])
            'development'
        """
        workspace_type = cls.detect_type(project_path)
        path = Path(project_path)

        # Count files
        file_count = sum(1 for _ in path.rglob("*") if _.is_file())

        # Get size
        total_size = sum(
            f.stat().st_size for f in path.rglob("*") if f.is_file()
        )

        # Check if git repo
        is_git = (path / ".git").exists()

        return {
            "type": workspace_type.value,
            "path": str(path.absolute()),
            "name": path.name,
            "file_count": file_count,
            "size_bytes": total_size,
            "size_mb": round(total_size / (1024 * 1024), 2),
            "is_git_repo": is_git,
        }

    @classmethod
    def get_capabilities(cls, workspace_type: WorkspaceType) -> List[str]:
        """
        Get capabilities available for a workspace type.

        Args:
            workspace_type: Type of workspace.

        Returns:
            List of capability names.

        Example:
            >>> caps = WorkspaceManager.get_capabilities(WorkspaceType.DEVELOPMENT)
            >>> print(caps)
            ['file_explorer', 'editor', 'git', 'terminal', 'tests']
        """
        capabilities_map = {
            WorkspaceType.DEVELOPMENT: [
                "file_explorer",
                "editor",
                "git",
                "terminal",
                "tests",
                "debugger",
                "diff_viewer",
            ],
            WorkspaceType.DESIGN_3D: [
                "file_explorer",
                "3d_viewer",
                "timeline",
                "render_queue",
                "asset_library",
            ],
            WorkspaceType.VIDEO: [
                "file_explorer",
                "video_player",
                "timeline",
                "effects",
                "export_queue",
            ],
            WorkspaceType.FINANCE: [
                "file_explorer",
                "editor",
                "charts",
                "backtester",
                "portfolio",
                "terminal",
            ],
            WorkspaceType.DATA_SCIENCE: [
                "file_explorer",
                "notebook",
                "editor",
                "visualizations",
                "datasets",
                "terminal",
            ],
            WorkspaceType.CUSTOM: ["file_explorer", "editor"],
        }

        return capabilities_map.get(workspace_type, ["file_explorer"])
