"""
Tests for gathering/agents/project_context.py - Project Context.
"""

import pytest
from datetime import datetime, timezone
import tempfile
import os
from pathlib import Path

from gathering.agents.project_context import (
    ProjectContext,
    GATHERING_PROJECT,
)


class TestProjectContext:
    """Test ProjectContext dataclass."""

    def test_minimal_creation(self):
        """Test creating a minimal project context."""
        ctx = ProjectContext()
        assert ctx.id is None
        assert ctx.name == ""
        assert ctx.path == ""
        assert ctx.venv_path is None
        assert ctx.python_version == "3.11"
        assert ctx.tools == {}
        assert ctx.conventions == {}
        assert ctx.key_files == {}
        assert ctx.commands == {}
        assert ctx.notes == []

    def test_full_creation(self):
        """Test creating a project context with all fields."""
        now = datetime.now(timezone.utc)
        ctx = ProjectContext(
            id=1,
            name="MyProject",
            path="/home/user/myproject",
            venv_path="/home/user/myproject/venv",
            python_version="3.12",
            tools={"testing": "pytest", "orm": "sqlalchemy"},
            conventions={"style": "google"},
            key_files={"config": "config.py"},
            commands={"test": "pytest tests/"},
            notes=["Important note"],
            git_branch="main",
            git_remote="https://github.com/user/repo.git",
            created_at=now,
            updated_at=now,
        )
        assert ctx.id == 1
        assert ctx.name == "MyProject"
        assert ctx.python_version == "3.12"
        assert len(ctx.tools) == 2
        assert ctx.git_branch == "main"


class TestProjectContextMethods:
    """Test ProjectContext methods."""

    def test_add_note(self):
        """Test adding a note."""
        ctx = ProjectContext(name="Test")
        ctx.add_note("First note")
        assert "First note" in ctx.notes

        # Adding duplicate should not add again
        ctx.add_note("First note")
        assert ctx.notes.count("First note") == 1

        # Adding different note should work
        ctx.add_note("Second note")
        assert len(ctx.notes) == 2

    def test_add_tool(self):
        """Test adding a tool."""
        ctx = ProjectContext(name="Test")
        ctx.add_tool("testing", "pytest")
        assert ctx.tools["testing"] == "pytest"

        # Overwriting should work
        ctx.add_tool("testing", "unittest")
        assert ctx.tools["testing"] == "unittest"

    def test_add_convention(self):
        """Test adding a convention."""
        ctx = ProjectContext(name="Test")
        ctx.add_convention("style", "google")
        assert ctx.conventions["style"] == "google"

        ctx.add_convention("imports", "absolute")
        assert len(ctx.conventions) == 2

    def test_add_key_file(self):
        """Test adding a key file."""
        ctx = ProjectContext(name="Test")
        ctx.add_key_file("config", "src/config.py")
        assert ctx.key_files["config"] == "src/config.py"

    def test_add_command(self):
        """Test adding a command."""
        ctx = ProjectContext(name="Test")
        ctx.add_command("test", "pytest tests/ -v")
        assert ctx.commands["test"] == "pytest tests/ -v"


class TestToPrompt:
    """Test to_prompt method."""

    def test_minimal_prompt(self):
        """Test prompt with minimal context."""
        ctx = ProjectContext(name="MyProject", path="/home/user/project")
        prompt = ctx.to_prompt()
        assert "Projet: MyProject" in prompt
        assert "Chemin: /home/user/project" in prompt

    def test_prompt_with_venv(self):
        """Test prompt includes venv info."""
        ctx = ProjectContext(
            name="Test",
            path="/tmp/test",
            venv_path="/tmp/test/venv",
            python_version="3.12",
        )
        prompt = ctx.to_prompt()
        assert "Environnement Python:" in prompt
        assert "venv: /tmp/test/venv" in prompt
        assert "Python: 3.12" in prompt
        assert "source venv/bin/activate" in prompt

    def test_prompt_with_tools(self):
        """Test prompt includes tools."""
        ctx = ProjectContext(
            name="Test",
            path="/tmp/test",
            tools={"testing": "pytest", "orm": "sqlalchemy"},
        )
        prompt = ctx.to_prompt()
        assert "Outils du projet:" in prompt
        assert "testing: pytest" in prompt
        assert "orm: sqlalchemy" in prompt

    def test_prompt_with_conventions(self):
        """Test prompt includes conventions."""
        ctx = ProjectContext(
            name="Test",
            path="/tmp/test",
            conventions={"style": "google", "imports": "absolute"},
        )
        prompt = ctx.to_prompt()
        assert "Conventions:" in prompt
        assert "style: google" in prompt
        assert "imports: absolute" in prompt

    def test_prompt_with_key_files(self):
        """Test prompt includes key files."""
        ctx = ProjectContext(
            name="Test",
            path="/tmp/test",
            key_files={"config": "config.py", "models": "models/"},
        )
        prompt = ctx.to_prompt()
        assert "Fichiers importants:" in prompt
        assert "config: config.py" in prompt

    def test_prompt_with_commands(self):
        """Test prompt includes commands."""
        ctx = ProjectContext(
            name="Test",
            path="/tmp/test",
            commands={"test": "pytest", "lint": "ruff check ."},
        )
        prompt = ctx.to_prompt()
        assert "Commandes fréquentes:" in prompt
        assert "test: pytest" in prompt
        assert "lint: ruff check ." in prompt

    def test_prompt_with_notes(self):
        """Test prompt includes notes."""
        ctx = ProjectContext(
            name="Test",
            path="/tmp/test",
            notes=["Note 1", "Note 2"],
        )
        prompt = ctx.to_prompt()
        assert "Notes importantes:" in prompt
        assert "Note 1" in prompt
        assert "Note 2" in prompt

    def test_prompt_with_git(self):
        """Test prompt includes git info."""
        ctx = ProjectContext(
            name="Test",
            path="/tmp/test",
            git_branch="main",
            git_remote="https://github.com/user/repo.git",
        )
        prompt = ctx.to_prompt()
        assert "Git:" in prompt
        assert "Branche: main" in prompt
        assert "Remote: https://github.com/user/repo.git" in prompt

    def test_prompt_with_only_branch(self):
        """Test prompt with only git branch."""
        ctx = ProjectContext(
            name="Test",
            path="/tmp/test",
            git_branch="develop",
        )
        prompt = ctx.to_prompt()
        assert "Git:" in prompt
        assert "Branche: develop" in prompt


class TestToDict:
    """Test to_dict method."""

    def test_to_dict_minimal(self):
        """Test converting minimal context to dict."""
        ctx = ProjectContext(name="Test", path="/tmp/test")
        d = ctx.to_dict()
        assert d["name"] == "Test"
        assert d["path"] == "/tmp/test"
        assert d["id"] is None
        assert d["venv_path"] is None
        assert d["tools"] == {}
        assert d["created_at"] is None

    def test_to_dict_with_timestamps(self):
        """Test to_dict with timestamps."""
        now = datetime.now(timezone.utc)
        ctx = ProjectContext(
            name="Test",
            path="/tmp/test",
            created_at=now,
            updated_at=now,
        )
        d = ctx.to_dict()
        assert d["created_at"] is not None
        assert d["updated_at"] is not None
        # Should be ISO format strings
        assert "T" in d["created_at"]

    def test_to_dict_full(self):
        """Test to_dict with all fields."""
        ctx = ProjectContext(
            id=1,
            name="Test",
            path="/tmp/test",
            venv_path="/tmp/test/venv",
            python_version="3.12",
            tools={"a": "b"},
            conventions={"c": "d"},
            key_files={"e": "f"},
            commands={"g": "h"},
            notes=["note1"],
            git_branch="main",
            git_remote="url",
        )
        d = ctx.to_dict()
        assert d["id"] == 1
        assert d["python_version"] == "3.12"
        assert d["tools"] == {"a": "b"}
        assert d["notes"] == ["note1"]


class TestFromDict:
    """Test from_dict class method."""

    def test_from_dict_minimal(self):
        """Test creating from minimal dict."""
        data = {"name": "Test", "path": "/tmp/test"}
        ctx = ProjectContext.from_dict(data)
        assert ctx.name == "Test"
        assert ctx.path == "/tmp/test"
        assert ctx.python_version == "3.11"  # default

    def test_from_dict_full(self):
        """Test creating from full dict."""
        now = datetime.now(timezone.utc)
        data = {
            "id": 1,
            "name": "Test",
            "path": "/tmp/test",
            "venv_path": "/tmp/test/venv",
            "python_version": "3.12",
            "tools": {"testing": "pytest"},
            "conventions": {"style": "google"},
            "key_files": {"config": "config.py"},
            "commands": {"test": "pytest"},
            "notes": ["note1", "note2"],
            "git_branch": "main",
            "git_remote": "https://github.com/user/repo.git",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        ctx = ProjectContext.from_dict(data)
        assert ctx.id == 1
        assert ctx.python_version == "3.12"
        assert ctx.tools["testing"] == "pytest"
        assert len(ctx.notes) == 2
        assert ctx.created_at is not None

    def test_from_dict_empty(self):
        """Test creating from empty dict."""
        ctx = ProjectContext.from_dict({})
        assert ctx.name == ""
        assert ctx.path == ""

    def test_roundtrip(self):
        """Test to_dict -> from_dict roundtrip."""
        original = ProjectContext(
            id=1,
            name="Test",
            path="/tmp/test",
            tools={"a": "b"},
            notes=["note1"],
        )
        d = original.to_dict()
        restored = ProjectContext.from_dict(d)
        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.tools == original.tools
        assert restored.notes == original.notes


class TestFromPath:
    """Test from_path class method."""

    def test_from_path_nonexistent(self):
        """Test from_path with nonexistent path."""
        with pytest.raises(ValueError) as exc_info:
            ProjectContext.from_path("/nonexistent/path/12345")
        assert "does not exist" in str(exc_info.value)

    def test_from_path_basic(self):
        """Test from_path with basic directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = ProjectContext.from_path(tmpdir)
            assert ctx.path == tmpdir
            # Name should be the directory name
            assert ctx.name == Path(tmpdir).name

    def test_from_path_with_name(self):
        """Test from_path with custom name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = ProjectContext.from_path(tmpdir, name="CustomName")
            assert ctx.name == "CustomName"

    def test_from_path_with_venv(self):
        """Test from_path detects venv."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a fake venv structure
            venv_path = Path(tmpdir) / "venv" / "bin"
            venv_path.mkdir(parents=True)
            (venv_path / "python").touch()

            ctx = ProjectContext.from_path(tmpdir)
            assert ctx.venv_path == str(Path(tmpdir) / "venv")

    def test_from_path_with_tests(self):
        """Test from_path detects tests directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tests_dir = Path(tmpdir) / "tests"
            tests_dir.mkdir()

            ctx = ProjectContext.from_path(tmpdir)
            assert "test" in ctx.commands
            assert ctx.tools.get("testing") == "pytest"

    def test_from_path_with_pyproject(self):
        """Test from_path detects pyproject.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pyproject = Path(tmpdir) / "pyproject.toml"
            pyproject.write_text('[project]\nname = "my-package"\n')

            ctx = ProjectContext.from_path(tmpdir)
            assert "pyproject" in ctx.key_files

    def test_from_path_with_requirements(self):
        """Test from_path detects requirements.txt and tools."""
        with tempfile.TemporaryDirectory() as tmpdir:
            req = Path(tmpdir) / "requirements.txt"
            req.write_text("pytest>=7.0\nfastapi>=0.100\npydantic>=2.0\n")

            ctx = ProjectContext.from_path(tmpdir)
            assert "requirements" in ctx.key_files
            assert ctx.tools.get("testing") == "pytest"
            assert ctx.tools.get("web_framework") == "fastapi"
            assert ctx.tools.get("validation") == "pydantic"

    def test_from_path_with_git(self):
        """Test from_path detects git info."""
        # Use the actual project directory which has git
        project_path = Path(__file__).parent.parent
        if (project_path / ".git").exists():
            ctx = ProjectContext.from_path(str(project_path))
            # Should detect git branch
            assert ctx.git_branch is not None or ctx.git_remote is not None


class TestGatheringProject:
    """Test the pre-configured GATHERING_PROJECT constant."""

    @pytest.fixture
    def gathering_project(self):
        """Get GATHERING_PROJECT, skip if not available."""
        if GATHERING_PROJECT is None:
            pytest.skip("GATHERING_PROJECT not available (no project path in CI)")
        return GATHERING_PROJECT

    def test_gathering_project_exists(self, gathering_project):
        """Test that GATHERING_PROJECT is defined."""
        assert gathering_project is not None
        assert gathering_project.name.lower() == "gathering"

    def test_gathering_project_has_tools(self, gathering_project):
        """Test that GATHERING_PROJECT has tools defined."""
        assert len(gathering_project.tools) > 0
        assert "database" in gathering_project.tools
        assert "testing" in gathering_project.tools

    def test_gathering_project_has_conventions(self, gathering_project):
        """Test that GATHERING_PROJECT has conventions."""
        assert len(gathering_project.conventions) > 0

    def test_gathering_project_has_notes(self, gathering_project):
        """Test that GATHERING_PROJECT has notes."""
        assert len(gathering_project.notes) > 0

    def test_gathering_project_prompt(self, gathering_project):
        """Test that GATHERING_PROJECT can generate a prompt."""
        prompt = gathering_project.to_prompt()
        assert "gathering" in prompt.lower()
        assert "pycopg" in prompt.lower() or "picopg" in prompt.lower()
