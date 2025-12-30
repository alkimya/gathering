"""
Tests for Workspace System.

Tests workspace management, file operations, git integration,
and activity tracking.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import subprocess
import time

from gathering.workspace import (
    WorkspaceManager,
    WorkspaceType,
    FileManager,
    GitManager,
    ActivityTracker,
)
from gathering.workspace.activity_tracker import ActivityType


class TestWorkspaceManager:
    """Test WorkspaceManager class."""

    def setup_method(self):
        """Setup test workspace."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = Path(self.temp_dir) / "test_project"
        self.project_path.mkdir()

    def teardown_method(self):
        """Cleanup test workspace."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_detect_development_workspace(self):
        """Test detecting development workspace."""
        # Create development project structure
        (self.project_path / "package.json").write_text('{"name": "test"}')
        (self.project_path / "src").mkdir()
        (self.project_path / "tests").mkdir()

        workspace_type = WorkspaceManager.detect_type(str(self.project_path))
        assert workspace_type == WorkspaceType.DEVELOPMENT

    def test_detect_python_project(self):
        """Test detecting Python project."""
        (self.project_path / "requirements.txt").write_text("pytest\n")
        (self.project_path / "src").mkdir()
        (self.project_path / "src" / "main.py").write_text("print('hello')")

        workspace_type = WorkspaceManager.detect_type(str(self.project_path))
        assert workspace_type == WorkspaceType.DEVELOPMENT

    def test_detect_custom_workspace(self):
        """Test detecting custom workspace (no patterns match)."""
        # Empty directory
        workspace_type = WorkspaceManager.detect_type(str(self.project_path))
        assert workspace_type == WorkspaceType.CUSTOM

    def test_get_workspace_info(self):
        """Test getting workspace information."""
        (self.project_path / "requirements.txt").write_text("pytest\n")
        (self.project_path / "src").mkdir()

        info = WorkspaceManager.get_workspace_info(str(self.project_path))

        assert info["type"] == WorkspaceType.DEVELOPMENT.value
        assert info["name"] == "test_project"
        assert info["file_count"] >= 1
        assert info["size_bytes"] > 0
        assert info["is_git_repo"] is False

    def test_get_capabilities(self):
        """Test getting workspace capabilities."""
        caps = WorkspaceManager.get_capabilities(WorkspaceType.DEVELOPMENT)

        assert "file_explorer" in caps
        assert "editor" in caps
        assert "git" in caps
        assert "terminal" in caps
        assert "tests" in caps

    def test_get_capabilities_3d(self):
        """Test getting 3D workspace capabilities."""
        caps = WorkspaceManager.get_capabilities(WorkspaceType.DESIGN_3D)

        assert "file_explorer" in caps
        assert "3d_viewer" in caps
        assert "timeline" in caps


class TestFileManager:
    """Test FileManager class."""

    def setup_method(self):
        """Setup test files."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = Path(self.temp_dir) / "test_project"
        self.project_path.mkdir()

        # Create test file structure
        (self.project_path / "src").mkdir()
        (self.project_path / "src" / "main.py").write_text("def main():\n    pass\n")
        (self.project_path / "tests").mkdir()
        (self.project_path / "tests" / "test_main.py").write_text("def test_main():\n    pass\n")
        (self.project_path / "README.md").write_text("# Test Project\n")

    def teardown_method(self):
        """Cleanup test files."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_list_files(self):
        """Test listing files."""
        tree = FileManager.list_files(
            str(self.project_path),
            include_git_status=False,
        )

        assert tree["name"] == "test_project"
        assert tree["type"] == "directory"
        assert len(tree["children"]) == 3  # src, tests, README.md

    def test_list_files_excludes_patterns(self):
        """Test that excluded patterns are not in tree."""
        # Create excluded directories
        (self.project_path / "__pycache__").mkdir()
        (self.project_path / "node_modules").mkdir()

        tree = FileManager.list_files(str(self.project_path), include_git_status=False)

        # Check excluded folders are not present
        child_names = [c["name"] for c in tree["children"]]
        assert "__pycache__" not in child_names
        assert "node_modules" not in child_names

    def test_read_file(self):
        """Test reading file."""
        result = FileManager.read_file(str(self.project_path), "src/main.py")

        assert result["path"] == "src/main.py"
        assert result["type"] == "text"
        assert "def main():" in result["content"]
        assert result["lines"] == 3  # Split counts empty line at end
        assert result["mime_type"] == "text/x-python"

    def test_read_nonexistent_file(self):
        """Test reading nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            FileManager.read_file(str(self.project_path), "nonexistent.py")

    def test_read_file_outside_project(self):
        """Test reading file outside project raises error."""
        with pytest.raises(ValueError, match="outside project"):
            FileManager.read_file(str(self.project_path), "../outside.py")

    def test_write_file(self):
        """Test writing file."""
        content = "def new_function():\n    return 42\n"
        result = FileManager.write_file(
            str(self.project_path),
            "src/new_file.py",
            content,
        )

        assert result["success"] is True
        assert result["path"] == "src/new_file.py"
        assert result["size"] == len(content)

        # Verify file was written
        written_content = (self.project_path / "src" / "new_file.py").read_text()
        assert written_content == content

    def test_write_file_creates_backup(self):
        """Test writing existing file creates backup."""
        original = "original content"
        (self.project_path / "test.txt").write_text(original)

        new_content = "new content"
        result = FileManager.write_file(
            str(self.project_path),
            "test.txt",
            new_content,
            create_backup=True,
        )

        assert result["success"] is True
        assert result["backup"] is not None
        assert Path(result["backup"]).exists()

    def test_delete_file(self):
        """Test deleting file."""
        file_path = "temp.txt"
        (self.project_path / file_path).write_text("temporary")

        result = FileManager.delete_file(str(self.project_path), file_path)

        assert result["success"] is True
        assert result["deleted"] is True
        assert not (self.project_path / file_path).exists()

    def test_get_file_language(self):
        """Test language detection."""
        assert FileManager.get_file_language("main.py") == "python"
        assert FileManager.get_file_language("app.js") == "javascript"
        assert FileManager.get_file_language("App.tsx") == "typescript"
        assert FileManager.get_file_language("styles.css") == "css"
        assert FileManager.get_file_language("README.md") == "markdown"


class TestGitManager:
    """Test GitManager class."""

    def setup_method(self):
        """Setup test git repository."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = Path(self.temp_dir) / "test_repo"
        self.project_path.mkdir()

        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=self.project_path,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=self.project_path,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=self.project_path,
            capture_output=True,
        )

        # Create initial commit
        (self.project_path / "README.md").write_text("# Test Repo\n")
        subprocess.run(
            ["git", "add", "."],
            cwd=self.project_path,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=self.project_path,
            capture_output=True,
        )

    def teardown_method(self):
        """Cleanup test repository."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_is_git_repo(self):
        """Test checking if directory is git repo."""
        assert GitManager.is_git_repo(str(self.project_path)) is True

        # Non-git directory
        non_git = Path(self.temp_dir) / "not_git"
        non_git.mkdir()
        assert GitManager.is_git_repo(str(non_git)) is False

    def test_get_commits(self):
        """Test getting commit history."""
        commits = GitManager.get_commits(str(self.project_path), limit=10)

        assert len(commits) == 1
        assert commits[0]["message"] == "Initial commit"
        assert commits[0]["author_name"] == "Test User"
        assert commits[0]["author_email"] == "test@example.com"
        assert "hash" in commits[0]
        assert "timestamp" in commits[0]

    def test_get_commits_with_multiple(self):
        """Test getting multiple commits."""
        # Create second commit
        (self.project_path / "src").mkdir()
        (self.project_path / "src" / "main.py").write_text("print('hello')")
        subprocess.run(["git", "add", "."], cwd=self.project_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add main.py"],
            cwd=self.project_path,
            capture_output=True,
        )

        commits = GitManager.get_commits(str(self.project_path), limit=10)

        assert len(commits) == 2
        assert commits[0]["message"] == "Add main.py"
        assert commits[1]["message"] == "Initial commit"

    def test_get_status(self):
        """Test getting git status."""
        # Clean state
        status = GitManager.get_status(str(self.project_path))

        assert status["is_git_repo"] is True
        assert status["clean"] is True
        assert status["branch"] is not None

        # Add modified file
        (self.project_path / "README.md").write_text("# Modified\n")
        status = GitManager.get_status(str(self.project_path))

        assert status["clean"] is False
        assert "README.md" in status["modified"]

    def test_get_status_untracked(self):
        """Test status shows untracked files."""
        (self.project_path / "new.txt").write_text("new file")

        status = GitManager.get_status(str(self.project_path))

        assert "new.txt" in status["untracked"]

    def test_get_branches(self):
        """Test getting branches."""
        branches_info = GitManager.get_branches(str(self.project_path))

        assert branches_info["current"] is not None
        assert len(branches_info["branches"]) > 0

    def test_get_file_history(self):
        """Test getting file history."""
        # Modify file
        (self.project_path / "README.md").write_text("# Updated\n")
        subprocess.run(["git", "add", "."], cwd=self.project_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Update README"],
            cwd=self.project_path,
            capture_output=True,
        )

        history = GitManager.get_file_history(
            str(self.project_path),
            "README.md",
            limit=10,
        )

        assert len(history) == 2
        assert history[0]["message"] == "Update README"
        assert history[0]["file"] == "README.md"

    def test_get_diff(self):
        """Test getting diff."""
        # Modify file
        (self.project_path / "README.md").write_text("# Modified\n")

        diff = GitManager.get_diff(str(self.project_path))

        assert "diff" in diff
        assert "README.md" in diff["diff"]


class TestActivityTracker:
    """Test ActivityTracker class."""

    def setup_method(self):
        """Setup activity tracker."""
        self.tracker = ActivityTracker()

    def test_track_activity(self):
        """Test tracking an activity."""
        activity = self.tracker.track_activity(
            project_id=1,
            agent_id=5,
            activity_type=ActivityType.FILE_EDITED,
            details={"file": "main.py", "lines_added": 10},
        )

        assert activity["project_id"] == 1
        assert activity["agent_id"] == 5
        assert activity["type"] == ActivityType.FILE_EDITED.value
        assert activity["details"]["file"] == "main.py"
        assert "timestamp" in activity
        assert "id" in activity

    def test_get_activities(self):
        """Test getting activities."""
        # Track multiple activities
        self.tracker.track_activity(
            project_id=1,
            agent_id=5,
            activity_type=ActivityType.FILE_EDITED,
            details={"file": "main.py"},
        )
        self.tracker.track_activity(
            project_id=1,
            agent_id=5,
            activity_type=ActivityType.COMMIT,
            details={"message": "feat: add feature"},
        )

        activities = self.tracker.get_activities(project_id=1, limit=10)

        assert len(activities) == 2
        # Most recent first
        assert activities[0]["type"] == ActivityType.COMMIT.value
        assert activities[1]["type"] == ActivityType.FILE_EDITED.value

    def test_get_activities_filter_by_agent(self):
        """Test filtering activities by agent."""
        self.tracker.track_activity(
            project_id=1,
            agent_id=5,
            activity_type=ActivityType.FILE_EDITED,
            details={},
        )
        self.tracker.track_activity(
            project_id=1,
            agent_id=6,
            activity_type=ActivityType.COMMIT,
            details={},
        )

        # Filter by agent 5
        activities = self.tracker.get_activities(project_id=1, agent_id=5)
        assert len(activities) == 1
        assert activities[0]["agent_id"] == 5

    def test_get_activities_filter_by_type(self):
        """Test filtering activities by type."""
        self.tracker.track_activity(
            project_id=1,
            agent_id=5,
            activity_type=ActivityType.FILE_EDITED,
            details={},
        )
        self.tracker.track_activity(
            project_id=1,
            agent_id=5,
            activity_type=ActivityType.COMMIT,
            details={},
        )

        # Filter by FILE_EDITED
        activities = self.tracker.get_activities(
            project_id=1,
            activity_type=ActivityType.FILE_EDITED,
        )
        assert len(activities) == 1
        assert activities[0]["type"] == ActivityType.FILE_EDITED.value

    def test_get_agent_summary(self):
        """Test getting agent activity summary."""
        # Track various activities
        self.tracker.track_activity(
            project_id=1,
            agent_id=5,
            activity_type=ActivityType.FILE_EDITED,
            details={},
        )
        self.tracker.track_activity(
            project_id=1,
            agent_id=5,
            activity_type=ActivityType.FILE_EDITED,
            details={},
        )
        self.tracker.track_activity(
            project_id=1,
            agent_id=5,
            activity_type=ActivityType.COMMIT,
            details={},
        )

        summary = self.tracker.get_agent_summary(project_id=1, agent_id=5)

        assert summary["agent_id"] == 5
        assert summary["total_activities"] == 3
        assert summary["by_type"]["file_edited"] == 2
        assert summary["by_type"]["commit"] == 1
        assert summary["most_recent"] is not None

    def test_get_stats(self):
        """Test getting project statistics."""
        self.tracker.track_activity(
            project_id=1,
            agent_id=5,
            activity_type=ActivityType.FILE_EDITED,
            details={},
        )
        self.tracker.track_activity(
            project_id=1,
            agent_id=6,
            activity_type=ActivityType.COMMIT,
            details={},
        )

        stats = self.tracker.get_stats(project_id=1)

        assert stats["total"] == 2
        assert 5 in stats["agents"]
        assert 6 in stats["agents"]
        assert stats["by_type"]["file_edited"] == 1
        assert stats["by_type"]["commit"] == 1

    def test_clear_project_activities(self):
        """Test clearing project activities."""
        self.tracker.track_activity(
            project_id=1,
            agent_id=5,
            activity_type=ActivityType.FILE_EDITED,
            details={},
        )

        self.tracker.clear_project_activities(project_id=1)

        activities = self.tracker.get_activities(project_id=1)
        assert len(activities) == 0
