"""
Project Context - Persistent project information.
Stores conventions, tools, structure, and important notes about a project.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path


@dataclass
class ProjectContext:
    """
    Persistent context for a project.

    Stores everything an agent needs to know about a project:
    - Environment (venv, python version)
    - Tools and libraries used
    - Coding conventions
    - Important files
    - Frequent commands
    - Notes and decisions
    """

    id: Optional[int] = None
    name: str = ""
    path: str = ""

    # Environment
    venv_path: Optional[str] = None
    python_version: str = "3.11"

    # Tools and libraries
    tools: Dict[str, str] = field(default_factory=dict)
    # e.g., {"database": "picopg", "testing": "pytest", "orm": "sqlalchemy"}

    # Coding conventions
    conventions: Dict[str, Any] = field(default_factory=dict)
    # e.g., {"primary_keys": "IDENTITY", "imports": "absolute", "docstrings": "google"}

    # Important files/directories
    key_files: Dict[str, str] = field(default_factory=dict)
    # e.g., {"config": "src/config.py", "models": "src/models/"}

    # Frequent commands
    commands: Dict[str, str] = field(default_factory=dict)
    # e.g., {"test": "pytest tests/ -v", "lint": "ruff check ."}

    # Important notes (decisions, things to remember)
    notes: List[str] = field(default_factory=list)

    # Git info
    git_branch: Optional[str] = None
    git_remote: Optional[str] = None

    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_prompt(self) -> str:
        """
        Generate context for injection into prompts.

        Returns:
            Formatted string for LLM context
        """
        lines = [
            f"Projet: {self.name}",
            f"Chemin: {self.path}",
        ]

        # Python environment
        if self.venv_path:
            lines.append(f"\nEnvironnement Python:")
            lines.append(f"  - venv: {self.venv_path}")
            lines.append(f"  - Python: {self.python_version}")
            lines.append(
                "  - IMPORTANT: Toujours utiliser 'source venv/bin/activate' "
                "avant les commandes Python"
            )

        # Tools
        if self.tools:
            lines.append("\nOutils du projet:")
            for tool, lib in self.tools.items():
                lines.append(f"  - {tool}: {lib}")

        # Conventions
        if self.conventions:
            lines.append("\nConventions:")
            for key, value in self.conventions.items():
                lines.append(f"  - {key}: {value}")

        # Key files
        if self.key_files:
            lines.append("\nFichiers importants:")
            for name, path in self.key_files.items():
                lines.append(f"  - {name}: {path}")

        # Commands
        if self.commands:
            lines.append("\nCommandes fréquentes:")
            for name, cmd in self.commands.items():
                lines.append(f"  - {name}: {cmd}")

        # Notes
        if self.notes:
            lines.append("\nNotes importantes:")
            for note in self.notes:
                lines.append(f"  - {note}")

        # Git
        if self.git_branch or self.git_remote:
            lines.append("\nGit:")
            if self.git_branch:
                lines.append(f"  - Branche: {self.git_branch}")
            if self.git_remote:
                lines.append(f"  - Remote: {self.git_remote}")

        return "\n".join(lines)

    def add_note(self, note: str) -> None:
        """Add an important note."""
        if note not in self.notes:
            self.notes.append(note)

    def add_tool(self, name: str, library: str) -> None:
        """Register a tool/library used in the project."""
        self.tools[name] = library

    def add_convention(self, key: str, value: Any) -> None:
        """Add a coding convention."""
        self.conventions[key] = value

    def add_key_file(self, name: str, path: str) -> None:
        """Register an important file."""
        self.key_files[name] = path

    def add_command(self, name: str, command: str) -> None:
        """Register a frequent command."""
        self.commands[name] = command

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "venv_path": self.venv_path,
            "python_version": self.python_version,
            "tools": self.tools,
            "conventions": self.conventions,
            "key_files": self.key_files,
            "commands": self.commands,
            "notes": self.notes,
            "git_branch": self.git_branch,
            "git_remote": self.git_remote,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectContext":
        """Create from dictionary."""
        return cls(
            id=data.get("id"),
            name=data.get("name", ""),
            path=data.get("path", ""),
            venv_path=data.get("venv_path"),
            python_version=data.get("python_version", "3.11"),
            tools=data.get("tools", {}),
            conventions=data.get("conventions", {}),
            key_files=data.get("key_files", {}),
            commands=data.get("commands", {}),
            notes=data.get("notes", []),
            git_branch=data.get("git_branch"),
            git_remote=data.get("git_remote"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
        )

    @classmethod
    def from_path(cls, path: str, name: Optional[str] = None) -> "ProjectContext":
        """
        Create a ProjectContext by detecting project settings from a path.

        Args:
            path: Path to the project directory
            name: Optional project name (defaults to directory name)

        Returns:
            ProjectContext with detected settings
        """
        project_path = Path(path).resolve()

        if not project_path.exists():
            raise ValueError(f"Project path does not exist: {path}")

        # Auto-detect name
        if not name:
            name = project_path.name

        context = cls(name=name, path=str(project_path))

        # Detect venv
        for venv_name in ["venv", ".venv", "env", ".env"]:
            venv_path = project_path / venv_name
            if venv_path.exists() and (venv_path / "bin" / "python").exists():
                context.venv_path = str(venv_path)
                break

        # Detect Python version from venv
        if context.venv_path:
            python_bin = Path(context.venv_path) / "bin" / "python"
            if python_bin.exists():
                import subprocess
                try:
                    result = subprocess.run(
                        [str(python_bin), "--version"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0:
                        # "Python 3.11.5" -> "3.11"
                        version = result.stdout.strip().split()[1]
                        parts = version.split(".")
                        context.python_version = f"{parts[0]}.{parts[1]}"
                except Exception:
                    pass

        # Detect tools from requirements/pyproject
        context._detect_tools(project_path)

        # Detect git
        context._detect_git(project_path)

        # Add common commands
        if context.venv_path:
            context.commands["activate"] = f"source {context.venv_path}/bin/activate"

        if (project_path / "pytest.ini").exists() or (project_path / "tests").exists():
            context.commands["test"] = "pytest tests/ -v"
            context.tools["testing"] = "pytest"

        if (project_path / "pyproject.toml").exists():
            context.key_files["pyproject"] = "pyproject.toml"

        return context

    def _detect_tools(self, project_path: Path) -> None:
        """Detect tools from project files."""
        # Check requirements.txt
        req_file = project_path / "requirements.txt"
        if req_file.exists():
            self.key_files["requirements"] = "requirements.txt"
            content = req_file.read_text()

            # Common tools detection
            tool_patterns = {
                "pytest": "testing",
                "sqlalchemy": "orm",
                "pydantic": "validation",
                "fastapi": "web_framework",
                "flask": "web_framework",
                "django": "web_framework",
                "anthropic": "llm_provider",
                "openai": "llm_provider",
                "psycopg": "database_driver",
                "picopg": "database",
            }

            for pattern, category in tool_patterns.items():
                if pattern in content.lower():
                    self.tools[category] = pattern

        # Check pyproject.toml
        pyproject = project_path / "pyproject.toml"
        if pyproject.exists():
            try:
                import tomllib
                with open(pyproject, "rb") as f:
                    data = tomllib.load(f)
                    # Get project name
                    if "project" in data and "name" in data["project"]:
                        self.name = data["project"]["name"]
            except Exception:
                pass

    def _detect_git(self, project_path: Path) -> None:
        """Detect git information."""
        git_dir = project_path / ".git"
        if not git_dir.exists():
            return

        import subprocess

        # Get current branch
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                self.git_branch = result.stdout.strip()
        except Exception:
            pass

        # Get remote URL
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                self.git_remote = result.stdout.strip()
        except Exception:
            pass


# Pre-configured context for the Gathering project
GATHERING_PROJECT = ProjectContext(
    name="Gathering",
    path="/home/loc/workspace/gathering",
    venv_path="/home/loc/workspace/gathering/venv",
    python_version="3.13",
    tools={
        "database": "picopg",
        "testing": "pytest",
        "orm": "sqlalchemy",
        "validation": "pydantic",
        "llm_claude": "anthropic",
        "llm_deepseek": "openai-compatible",
    },
    conventions={
        "primary_keys": "BIGINT GENERATED ALWAYS AS IDENTITY",
        "imports": "absolute",
        "docstrings": "google style",
        "db_schema": "gathering",
    },
    key_files={
        "models": "gathering/db/models.py",
        "config": "gathering/core/config.py",
        "orchestration": "gathering/orchestration/",
        "skills": "gathering/skills/",
        "agents": "gathering/agents/",
    },
    commands={
        "test": "source venv/bin/activate && pytest tests/ -v",
        "test_orch": "source venv/bin/activate && pytest tests/test_orchestration.py -v",
    },
    notes=[
        "Toujours utiliser picopg pour les connexions DB",
        "Les tests doivent passer avant commit",
        "Review obligatoire par un autre agent",
        "Clés primaires en IDENTITY, pas UUID",
    ],
    git_branch="develop",
    git_remote="https://github.com/alkimya/gathering.git",
)
