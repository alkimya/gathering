"""
Project management endpoints.
Allows users to create, browse, and manage project folders from the dashboard.
Uses the existing project.projects schema.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from gathering.api.dependencies import get_database_service, DatabaseService
from gathering.agents.project_context import ProjectContext
from gathering.utils.sql import safe_update_builder


router = APIRouter(prefix="/projects", tags=["projects"])


# =============================================================================
# Schemas
# =============================================================================


class ProjectCreate(BaseModel):
    """Request to create a new project."""
    name: str = Field(..., min_length=1, max_length=200)
    path: str = Field(..., min_length=1, description="Local path to the project")
    description: Optional[str] = None
    auto_detect: bool = Field(default=True, description="Auto-detect project settings from path")


class ProjectUpdate(BaseModel):
    """Request to update a project."""
    name: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    venv_path: Optional[str] = None
    python_version: Optional[str] = None
    tools: Optional[Dict[str, Any]] = None
    conventions: Optional[Dict[str, Any]] = None
    key_files: Optional[Dict[str, str]] = None
    commands: Optional[Dict[str, str]] = None
    notes: Optional[List[str]] = None


class ProjectResponse(BaseModel):
    """Project response."""
    id: int
    name: str
    display_name: Optional[str] = None
    path: str
    description: Optional[str] = None
    repository_url: Optional[str] = None
    branch: str = "main"
    status: str = "active"
    tech_stack: List[str] = []
    languages: List[str] = []
    frameworks: List[str] = []
    venv_path: Optional[str] = None
    python_version: Optional[str] = None
    tools: Dict[str, Any] = {}
    conventions: Dict[str, Any] = {}
    key_files: Dict[str, str] = {}
    commands: Dict[str, str] = {}
    notes: List[str] = []
    circle_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None


class ProjectListResponse(BaseModel):
    """List of projects response."""
    projects: List[ProjectResponse]
    total: int


class FolderEntry(BaseModel):
    """A file or folder entry."""
    name: str
    path: str
    is_dir: bool
    is_project: bool = False
    size: Optional[int] = None
    modified: Optional[datetime] = None


class FolderBrowseResponse(BaseModel):
    """Response for folder browsing."""
    current_path: str
    parent_path: Optional[str]
    entries: List[FolderEntry]
    can_create_project: bool = False


# =============================================================================
# Helper Functions
# =============================================================================


def _is_project_folder(path: Path) -> bool:
    """Check if a folder looks like a project."""
    project_indicators = [
        "pyproject.toml",
        "setup.py",
        "package.json",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "Makefile",
        ".git",
    ]
    return any((path / indicator).exists() for indicator in project_indicators)


def _parse_json_field(value: Any, default: Any = None) -> Any:
    """Parse a JSON field from database."""
    if value is None:
        return default if default is not None else {}
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default if default is not None else {}
    return value


def _parse_array_field(value: Any) -> List[str]:
    """Parse an array field from database."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        if value.startswith("{") and value.endswith("}"):
            return [x.strip() for x in value[1:-1].split(",") if x.strip()]
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return []
    return []


def _project_from_row(row: Dict[str, Any]) -> ProjectResponse:
    """Convert database row to ProjectResponse."""
    return ProjectResponse(
        id=row["id"],
        name=row["name"],
        display_name=row.get("display_name"),
        path=row.get("local_path", ""),
        description=row.get("description"),
        repository_url=row.get("repository_url"),
        branch=row.get("branch", "main"),
        status=row.get("status", "active"),
        tech_stack=_parse_array_field(row.get("tech_stack")),
        languages=_parse_array_field(row.get("languages")),
        frameworks=_parse_array_field(row.get("frameworks")),
        venv_path=row.get("venv_path"),
        python_version=row.get("python_version"),
        tools=_parse_json_field(row.get("tools"), {}),
        conventions=_parse_json_field(row.get("conventions"), {}),
        key_files=_parse_json_field(row.get("key_files"), {}),
        commands=_parse_json_field(row.get("commands"), {}),
        notes=_parse_array_field(row.get("notes")),
        circle_count=row.get("circle_count", 0),
        created_at=row.get("created_at") or datetime.now(timezone.utc),
        updated_at=row.get("updated_at"),
    )


# =============================================================================
# CRUD Endpoints
# =============================================================================


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: DatabaseService = Depends(get_database_service),
) -> ProjectListResponse:
    """List all projects."""
    sql = """
        SELECT p.*,
               COUNT(DISTINCT cp.circle_id) as circle_count
        FROM project.projects p
        LEFT JOIN project.circle_projects cp ON p.id = cp.project_id
        WHERE 1=1
    """
    params: Dict[str, Any] = {}

    if status_filter:
        sql += " AND p.status = %(status)s"
        params["status"] = status_filter

    sql += " GROUP BY p.id ORDER BY p.updated_at DESC NULLS LAST, p.created_at DESC"

    rows = db.fetch_all(sql, params)
    projects = [_project_from_row(row) for row in rows]
    return ProjectListResponse(projects=projects, total=len(projects))


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    db: DatabaseService = Depends(get_database_service),
) -> ProjectResponse:
    """
    Create a new project.

    If auto_detect is True, project settings will be automatically
    detected from the project path (venv, git, tools, etc.).
    """
    project_path = Path(data.path).expanduser().resolve()
    if not project_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Path does not exist: {data.path}",
        )

    if not project_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Path is not a directory: {data.path}",
        )

    existing = db.fetch_one(
        "SELECT id FROM project.projects WHERE local_path = %(path)s",
        {"path": str(project_path)},
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Project already exists for path: {data.path}",
        )

    context = None
    if data.auto_detect:
        try:
            context = ProjectContext.from_path(str(project_path), name=data.name)
        except Exception:
            context = ProjectContext(name=data.name, path=str(project_path))
    else:
        context = ProjectContext(name=data.name, path=str(project_path))

    languages = []
    frameworks = []
    if "testing" in context.tools and context.tools["testing"] == "pytest":
        languages.append("python")
    if "web_framework" in context.tools:
        frameworks.append(context.tools["web_framework"])

    now = datetime.now(timezone.utc)
    result = db.execute("""
        INSERT INTO project.projects (
            name, display_name, description, local_path, branch,
            venv_path, python_version, tools, conventions, key_files,
            commands, notes, languages, frameworks, status,
            created_at, updated_at
        ) VALUES (
            %(name)s, %(display_name)s, %(description)s, %(local_path)s, %(branch)s,
            %(venv_path)s, %(python_version)s, %(tools)s, %(conventions)s, %(key_files)s,
            %(commands)s, %(notes)s, %(languages)s, %(frameworks)s, %(status)s,
            %(created_at)s, %(updated_at)s
        )
        RETURNING id
    """, {
        "name": context.name,
        "display_name": data.name,
        "description": data.description,
        "local_path": str(project_path),
        "branch": context.git_branch or "main",
        "venv_path": context.venv_path,
        "python_version": context.python_version,
        "tools": json.dumps(context.tools),
        "conventions": json.dumps(context.conventions),
        "key_files": json.dumps(context.key_files),
        "commands": json.dumps(context.commands),
        "notes": context.notes,
        "languages": languages,
        "frameworks": frameworks,
        "status": "active",
        "created_at": now,
        "updated_at": now,
    })

    project_id = result[0]["id"] if result else None
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project",
        )

    return ProjectResponse(
        id=project_id,
        name=context.name,
        display_name=data.name,
        path=str(project_path),
        description=data.description,
        branch=context.git_branch or "main",
        status="active",
        languages=languages,
        frameworks=frameworks,
        venv_path=context.venv_path,
        python_version=context.python_version,
        tools=context.tools,
        conventions=context.conventions,
        key_files=context.key_files,
        commands=context.commands,
        notes=context.notes,
        circle_count=0,
        created_at=now,
        updated_at=now,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: DatabaseService = Depends(get_database_service),
) -> ProjectResponse:
    """Get project details by ID."""
    row = db.fetch_one("""
        SELECT p.*,
               COUNT(DISTINCT cp.circle_id) as circle_count
        FROM project.projects p
        LEFT JOIN project.circle_projects cp ON p.id = cp.project_id
        WHERE p.id = %(id)s
        GROUP BY p.id
    """, {"id": project_id})

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    return _project_from_row(row)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    data: ProjectUpdate,
    db: DatabaseService = Depends(get_database_service),
) -> ProjectResponse:
    """Update a project."""
    existing = db.fetch_one(
        "SELECT * FROM project.projects WHERE id = %(id)s",
        {"id": project_id},
    )
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    PROJECT_UPDATE_COLUMNS = {
        "name", "display_name", "description", "status",
        "venv_path", "python_version", "tools", "conventions",
        "key_files", "commands", "notes",
    }

    update_dict: Dict[str, Any] = {}

    if data.name is not None:
        update_dict["name"] = data.name
    if data.display_name is not None:
        update_dict["display_name"] = data.display_name
    if data.description is not None:
        update_dict["description"] = data.description
    if data.status is not None:
        update_dict["status"] = data.status
    if data.venv_path is not None:
        update_dict["venv_path"] = data.venv_path
    if data.python_version is not None:
        update_dict["python_version"] = data.python_version
    if data.tools is not None:
        update_dict["tools"] = json.dumps(data.tools)
    if data.conventions is not None:
        update_dict["conventions"] = json.dumps(data.conventions)
    if data.key_files is not None:
        update_dict["key_files"] = json.dumps(data.key_files)
    if data.commands is not None:
        update_dict["commands"] = json.dumps(data.commands)
    if data.notes is not None:
        update_dict["notes"] = data.notes

    if update_dict:
        set_clause, params = safe_update_builder(
            PROJECT_UPDATE_COLUMNS, update_dict,
            always_set={"updated_at": "CURRENT_TIMESTAMP"},
        )
        params["id"] = project_id
        db.execute(
            f"UPDATE project.projects SET {set_clause} WHERE id = %(id)s",
            params,
        )

    return await get_project(project_id, db)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    db: DatabaseService = Depends(get_database_service),
):
    """Delete a project."""
    result = db.execute(
        "DELETE FROM project.projects WHERE id = %(id)s RETURNING id",
        {"id": project_id},
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )


# =============================================================================
# Folder Browsing
# =============================================================================


@router.get("/browse/folders", response_model=FolderBrowseResponse)
async def browse_folders(
    path: Optional[str] = Query(None, description="Path to browse (default: home directory)"),
    show_hidden: bool = Query(False, description="Show hidden files/folders"),
) -> FolderBrowseResponse:
    """
    Browse folders on the filesystem.

    This allows dashboard users to navigate the filesystem to select
    a project folder without needing to know the exact path.
    """
    # Default to home directory
    if not path:
        path = str(Path.home())

    browse_path = Path(path).expanduser().resolve()

    if not browse_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Path does not exist: {path}",
        )

    if not browse_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Path is not a directory: {path}",
        )

    # Security: prevent browsing system directories
    forbidden_paths = ["/proc", "/sys", "/dev", "/boot", "/root"]
    for forbidden in forbidden_paths:
        if str(browse_path).startswith(forbidden):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to system directory: {path}",
            )

    entries = []
    try:
        for entry in sorted(browse_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            # Skip hidden files unless requested
            if entry.name.startswith(".") and not show_hidden:
                continue

            # Skip system/cache directories
            skip_dirs = ["__pycache__", "node_modules", ".git", ".venv", "venv", ".cache"]
            if entry.is_dir() and entry.name in skip_dirs:
                continue

            try:
                stat = entry.stat()
                entries.append(FolderEntry(
                    name=entry.name,
                    path=str(entry),
                    is_dir=entry.is_dir(),
                    is_project=entry.is_dir() and _is_project_folder(entry),
                    size=stat.st_size if entry.is_file() else None,
                    modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                ))
            except PermissionError:
                continue
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {path}",
        )

    # Get parent path
    parent = browse_path.parent
    parent_path = str(parent) if parent != browse_path else None

    return FolderBrowseResponse(
        current_path=str(browse_path),
        parent_path=parent_path,
        entries=entries,
        can_create_project=_is_project_folder(browse_path),
    )


# =============================================================================
# Project-Circle Association (agents work via circles)
# =============================================================================


@router.post("/{project_id}/circles/{circle_id}", status_code=status.HTTP_201_CREATED)
async def link_circle_to_project(
    project_id: int,
    circle_id: int,
    is_primary: bool = False,
    db: DatabaseService = Depends(get_database_service),
) -> dict:
    """Link a circle (team of agents) to a project."""
    project = db.fetch_one(
        "SELECT id, name FROM project.projects WHERE id = %(id)s",
        {"id": project_id},
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    existing = db.fetch_one(
        "SELECT id FROM project.circle_projects WHERE project_id = %(project_id)s AND circle_id = %(circle_id)s",
        {"project_id": project_id, "circle_id": circle_id},
    )
    if existing:
        return {"status": "already_linked", "project_id": project_id, "circle_id": circle_id}

    db.execute("""
        INSERT INTO project.circle_projects (project_id, circle_id, is_primary, linked_at)
        VALUES (%(project_id)s, %(circle_id)s, %(is_primary)s, %(linked_at)s)
    """, {
        "project_id": project_id,
        "circle_id": circle_id,
        "is_primary": is_primary,
        "linked_at": datetime.now(timezone.utc),
    })

    return {"status": "linked", "project_id": project_id, "circle_id": circle_id}


@router.delete("/{project_id}/circles/{circle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_circle_from_project(
    project_id: int,
    circle_id: int,
    db: DatabaseService = Depends(get_database_service),
):
    """Remove a circle from a project."""
    result = db.execute("""
        DELETE FROM project.circle_projects
        WHERE project_id = %(project_id)s AND circle_id = %(circle_id)s
        RETURNING id
    """, {"project_id": project_id, "circle_id": circle_id})

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circle {circle_id} is not linked to project {project_id}",
        )


@router.get("/{project_id}/circles")
async def list_project_circles(
    project_id: int,
    db: DatabaseService = Depends(get_database_service),
) -> dict:
    """List all circles linked to a project."""
    project = db.fetch_one(
        "SELECT id, name FROM project.projects WHERE id = %(id)s",
        {"id": project_id},
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    rows = db.fetch_all("""
        SELECT cp.circle_id, c.name as circle_name, cp.is_primary, cp.linked_at
        FROM project.circle_projects cp
        JOIN circle.circles c ON c.id = cp.circle_id
        WHERE cp.project_id = %(project_id)s
        ORDER BY cp.is_primary DESC, cp.linked_at DESC
    """, {"project_id": project_id})

    return {
        "project_id": project_id,
        "project_name": project["name"],
        "circles": [
            {
                "circle_id": row["circle_id"],
                "circle_name": row["circle_name"],
                "is_primary": row["is_primary"],
                "linked_at": row["linked_at"],
            }
            for row in rows
        ],
        "total": len(rows),
    }


# =============================================================================
# Project Detection & Refresh
# =============================================================================


@router.post("/{project_id}/refresh", response_model=ProjectResponse)
async def refresh_project(
    project_id: int,
    db: DatabaseService = Depends(get_database_service),
) -> ProjectResponse:
    """
    Refresh project settings by re-detecting from the filesystem.

    Useful when project structure has changed (new tools, git branch, etc.).
    """
    existing = db.fetch_one(
        "SELECT * FROM project.projects WHERE id = %(id)s",
        {"id": project_id},
    )
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    project_path = Path(existing["local_path"])
    if not project_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project path no longer exists: {existing['local_path']}",
        )

    try:
        context = ProjectContext.from_path(str(project_path), name=existing["name"])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect project settings: {str(e)}",
        )

    now = datetime.now(timezone.utc)
    db.execute("""
        UPDATE project.projects SET
            venv_path = %(venv_path)s,
            python_version = %(python_version)s,
            tools = %(tools)s,
            conventions = %(conventions)s,
            key_files = %(key_files)s,
            commands = %(commands)s,
            branch = %(branch)s,
            updated_at = %(updated_at)s
        WHERE id = %(id)s
    """, {
        "id": project_id,
        "venv_path": context.venv_path,
        "python_version": context.python_version,
        "tools": json.dumps(context.tools),
        "conventions": json.dumps(context.conventions),
        "key_files": json.dumps(context.key_files),
        "commands": json.dumps(context.commands),
        "branch": context.git_branch or "main",
        "updated_at": now,
    })

    return await get_project(project_id, db)


@router.get("/{project_id}/context")
async def get_project_context(
    project_id: int,
    db: DatabaseService = Depends(get_database_service),
) -> dict:
    """
    Get the project context formatted for LLM injection.

    Returns the project information in a format suitable for
    adding to agent system prompts.
    """
    row = db.fetch_one(
        "SELECT * FROM project.projects WHERE id = %(id)s",
        {"id": project_id},
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    context = ProjectContext(
        id=row["id"],
        name=row["name"],
        path=row.get("local_path", ""),
        venv_path=row.get("venv_path"),
        python_version=row.get("python_version", "3.11"),
        tools=_parse_json_field(row.get("tools"), {}),
        conventions=_parse_json_field(row.get("conventions"), {}),
        key_files=_parse_json_field(row.get("key_files"), {}),
        commands=_parse_json_field(row.get("commands"), {}),
        notes=_parse_array_field(row.get("notes")),
        git_branch=row.get("branch"),
        git_remote=row.get("repository_url"),
    )

    return {
        "project_id": project_id,
        "project_name": context.name,
        "prompt_context": context.to_prompt(),
        "raw": context.to_dict(),
    }
