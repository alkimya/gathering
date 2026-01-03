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
    description: str = ""  # Project description for agent context

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
        ]

        # Add description if available
        if self.description:
            lines.append(f"\n{self.description}")

        lines.append(f"\nChemin: {self.path}")

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
            "description": self.description,
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
            description=data.get("description", ""),
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
                "pycopg": "database",
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


def load_project_from_db(project_id: Optional[int] = None, project_name: Optional[str] = None) -> Optional[ProjectContext]:
    """
    Load project context from database.

    Args:
        project_id: Project ID to load
        project_name: Project name to load (alternative to ID)

    Returns:
        ProjectContext if found, None otherwise
    """
    try:
        from pycopg import Database

        db = Database.from_env()

        if project_id:
            row = db.fetch_one(
                "SELECT * FROM project.projects WHERE id = %s",
                [project_id]
            )
        elif project_name:
            row = db.fetch_one(
                "SELECT * FROM project.projects WHERE name = %s",
                [project_name]
            )
        else:
            return None

        if not row:
            return None

        # Build venv_path
        venv_path = None
        if row.get("venv_path") and row.get("local_path"):
            venv = row["venv_path"]
            if not venv.startswith("/"):
                venv_path = str(Path(row["local_path"]) / venv)
            else:
                venv_path = venv

        context = ProjectContext(
            id=row.get("id"),
            name=row.get("name", ""),
            path=row.get("local_path", ""),
            description=row.get("description") or "",
            venv_path=venv_path,
            python_version=row.get("python_version", "3.11"),
            tools=row.get("tools") or {},
            conventions=row.get("conventions") or {},
            key_files=row.get("key_files") or {},
            commands=row.get("commands") or {},
            notes=row.get("notes") or [],
            git_branch=row.get("branch"),
            git_remote=row.get("repository_url"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

        return context

    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to load project from DB: {e}")
        return None


def load_project_from_yaml(project_path: str) -> Optional[ProjectContext]:
    """
    Load project context from .gathering/project.yaml file.

    Args:
        project_path: Path to the project directory

    Returns:
        ProjectContext if YAML exists, None otherwise
    """
    yaml_path = Path(project_path) / ".gathering" / "project.yaml"

    if not yaml_path.exists():
        return None

    try:
        import yaml
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)

        context = ProjectContext(
            name=data.get("name", ""),
            path=data.get("path", project_path),
        )

        # Python environment
        python_config = data.get("python", {})
        if isinstance(python_config, dict):
            context.python_version = python_config.get("version", "3.11")
            venv = python_config.get("venv")
            if venv:
                context.venv_path = str(Path(project_path) / venv)

        # Simple mappings
        context.tools = data.get("tools", {})
        context.conventions = data.get("conventions", {})
        context.key_files = data.get("key_files", {})
        context.commands = data.get("commands", {})
        context.notes = data.get("notes", [])

        # Git
        git_config = data.get("git", {})
        if isinstance(git_config, dict):
            context.git_branch = git_config.get("branch")
            context.git_remote = git_config.get("remote")

        return context

    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to load project.yaml: {e}")
        return None


def load_project_context(
    project_id: Optional[int] = None,
    project_name: Optional[str] = None,
    project_path: Optional[str] = None,
) -> ProjectContext:
    """
    Load project context with fallback chain:
    1. Database (by ID or name)
    2. YAML file (.gathering/project.yaml)
    3. Auto-detection from path

    Args:
        project_id: Project ID to load from DB
        project_name: Project name to load from DB
        project_path: Path for YAML/auto-detection fallback

    Returns:
        ProjectContext from best available source
    """
    # Try database first
    if project_id or project_name:
        context = load_project_from_db(project_id, project_name)
        if context:
            return context

    # Try YAML if path provided
    if project_path:
        context = load_project_from_yaml(project_path)
        if context:
            return context

        # Fallback to auto-detection
        return ProjectContext.from_path(project_path)

    # Default: try gathering from DB, then from path
    context = load_project_from_db(project_name="gathering")
    if context:
        return context

    return ProjectContext.from_path("/home/loc/workspace/gathering")


# Lazy-loaded project context
_gathering_project: Optional[ProjectContext] = None


def get_gathering_project() -> ProjectContext:
    """Get the Gathering project context (lazy-loaded)."""
    global _gathering_project
    if _gathering_project is None:
        _gathering_project = load_project_context()
    return _gathering_project


# For backwards compatibility - now loads from YAML
GATHERING_PROJECT = load_project_context()
