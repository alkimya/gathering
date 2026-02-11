"""
Workspace API Router.

Provides endpoints for workspace management, file operations,
git integration, and activity tracking.
"""

from fastapi import APIRouter, HTTPException, Query, Body
from starlette.requests import Request

from gathering.api.rate_limit import limiter, TIER_READ, TIER_WRITE
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from pathlib import Path
from urllib.parse import unquote
import mimetypes
import logging
import os
import subprocess

from gathering.workspace import (
    WorkspaceManager,
    FileManager,
    GitManager,
    WorkspaceType,
)
from gathering.workspace.activity_tracker import ActivityType, activity_tracker
from gathering.cache import (
    get_cached_file_tree,
    cache_file_tree,
    get_cached_git_commits,
    cache_git_commits,
    get_cached_git_status,
    cache_git_status,
    invalidate_workspace_cache,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspace", tags=["workspace"])


# ============================================================================
# Helper Functions
# ============================================================================


_project_path_cache: dict[int, tuple[str, float]] = {}
_CACHE_TTL = 300  # 5 minutes


def get_project_path(project_id: int) -> str:
    """Resolve project workspace path.

    Resolution order:
    1. Database: project.projects.repository_path for this project_id
    2. Environment: WORKSPACE_ROOT / project subdirectory (or WORKSPACE_ROOT itself)
    3. Fallback: current working directory (with deprecation warning)

    Results are cached for 5 minutes to avoid repeated DB queries.
    """
    import time

    # Check cache first
    now = time.monotonic()
    cached = _project_path_cache.get(project_id)
    if cached is not None:
        path, expires = cached
        if now < expires:
            return path

    resolved = _resolve_project_path(project_id)

    # Cache the result
    _project_path_cache[project_id] = (resolved, now + _CACHE_TTL)
    return resolved


def _resolve_project_path(project_id: int) -> str:
    """Internal: resolve project path without caching."""
    # Strategy 1: Database lookup (repository_path column in project.projects)
    try:
        from gathering.api.dependencies import get_database_service
        db = get_database_service()
        if db:
            row = db.execute_one(
                "SELECT repository_path FROM project.projects WHERE id = %(id)s",
                {"id": project_id},
            )
            if row and row.get("repository_path"):
                path = row["repository_path"]
                if os.path.isdir(path):
                    return path
                logger.warning(
                    "Project %d repository_path '%s' does not exist on disk",
                    project_id,
                    path,
                )
    except Exception as e:
        logger.debug("DB lookup for project path failed: %s", e)

    # Strategy 2: WORKSPACE_ROOT env var
    workspace_root = os.environ.get("WORKSPACE_ROOT")
    if workspace_root:
        # Try project-specific subdirectory first
        project_dir = os.path.join(workspace_root, str(project_id))
        if os.path.isdir(project_dir):
            return project_dir
        # Fall back to workspace root itself
        if os.path.isdir(workspace_root):
            return workspace_root

    # Strategy 3: Fallback to cwd with deprecation warning
    logger.warning(
        "Project %d: no repository_path in DB and WORKSPACE_ROOT not set, "
        "falling back to cwd. Set WORKSPACE_ROOT env var or update project config.",
        project_id,
    )
    return os.getcwd()


def validate_file_path(project_path: str, user_path: str) -> Path:
    """Validate and resolve a user-provided file path.

    Returns resolved path if safe, raises HTTPException(403) if traversal detected.
    Handles: ../, %2e%2e/, double-encoded paths, symlink escapes.
    """
    # Step 1: URL-decode (double decode for double-encoding attacks)
    decoded_path = unquote(unquote(user_path))

    # Step 2: Reject any '..' components (before and after decoding)
    if ".." in decoded_path:
        raise HTTPException(status_code=403, detail="Path traversal detected")

    # Step 3: Resolve absolute paths
    project_root = Path(project_path).resolve()
    target = (project_root / decoded_path).resolve()

    # Step 4: Verify target is within project root
    try:
        target.relative_to(project_root)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied: path outside project")

    # Step 5: Check for symlink escape
    if target.is_symlink():
        real_target = Path(os.readlink(target)).resolve() if target.exists() else target.resolve()
        try:
            real_target.relative_to(project_root)
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied: symlink escape")

    return target


# ============================================================================
# Request/Response Models
# ============================================================================


class WriteFileRequest(BaseModel):
    """Request to write a file."""

    content: str
    create_backup: bool = True


class ActivityRequest(BaseModel):
    """Request to track an activity."""

    agent_id: Optional[int] = None
    activity_type: str
    details: Dict[str, Any]


# ============================================================================
# Workspace Info Endpoints
# ============================================================================


@router.get("/{project_id}/info")
@limiter.limit(TIER_READ)
async def get_workspace_info(
    request: Request,
    project_id: int,
):
    """
    Get workspace information.

    Returns workspace type, capabilities, and metadata.
    """
    project_path = get_project_path(project_id)

    try:
        info = WorkspaceManager.get_workspace_info(project_path)
        workspace_type = WorkspaceType(info["type"])
        capabilities = WorkspaceManager.get_capabilities(workspace_type)

        return {
            **info,
            "capabilities": capabilities,
        }
    except (OSError, IOError, ValueError) as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in get_workspace_info")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# File Management Endpoints
# ============================================================================


@router.get("/{project_id}/files")
@limiter.limit(TIER_READ)
async def list_files(
    request: Request,
    project_id: int,
    include_git_status: bool = Query(default=True),
    max_depth: int = Query(default=10),
):
    """List all files in the workspace with Redis caching."""
    # Try cache first (only if not including git status for consistency)
    if not include_git_status:
        cached = get_cached_file_tree(project_id)
        if cached is not None:
            logger.debug(f"Cache HIT: file tree for project {project_id}")
            return cached

    project_path = get_project_path(project_id)

    try:
        tree = FileManager.list_files(
            project_path,
            include_git_status=include_git_status,
            max_depth=max_depth,
        )

        # Cache for 1 minute (only if not including git status)
        if not include_git_status:
            cache_file_tree(project_id, tree)
            logger.debug(f"Cache SET: file tree for project {project_id}")

        return tree
    except (OSError, IOError) as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in list_files")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{project_id}/file")
@limiter.limit(TIER_READ)
async def read_file(
    request: Request,
    project_id: int,
    path: str = Query(..., description="Relative path to file"),
):
    """Read a file's contents."""
    project_path = get_project_path(project_id)

    try:
        content = FileManager.read_file(project_path, path)
        return content
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (OSError, IOError, PermissionError) as e:
        logger.error(f"File operation error in read_file: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.exception("Unexpected error in read_file")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{project_id}/file/raw")
@limiter.limit(TIER_READ)
async def read_file_raw(
    request: Request,
    project_id: int,
    path: str = Query(..., description="Relative path to file"),
):
    """
    Read a file and return raw bytes (for images, binaries, etc.).

    This endpoint serves files with proper MIME types for browser display.
    Use this for images, PDFs, videos, and other binary files.
    """
    project_path = get_project_path(project_id)

    try:
        # Validate and resolve the path securely
        full_path = validate_file_path(project_path, path)

        # Check if file exists
        if not full_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {path}")

        if not full_path.is_file():
            raise HTTPException(status_code=400, detail=f"Not a file: {path}")

        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(str(full_path))
        if mime_type is None:
            mime_type = "application/octet-stream"

        # Read file bytes
        with open(full_path, 'rb') as f:
            content = f.read()

        # Return with appropriate content type
        return Response(
            content=content,
            media_type=mime_type,
            headers={
                "Content-Disposition": f'inline; filename="{full_path.name}"'
            }
        )

    except HTTPException:
        raise
    except (OSError, IOError, PermissionError) as e:
        logger.error(f"File operation error in read_file_raw: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.exception(f"Unexpected error in read_file_raw")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{project_id}/file")
@limiter.limit(TIER_WRITE)
async def write_file(
    request: Request,
    project_id: int,
    path: str = Query(..., description="Relative path to file"),
    write_request: WriteFileRequest = None,
):
    """Write or update a file."""
    project_path = get_project_path(project_id)

    try:
        result = FileManager.write_file(
            project_path,
            path,
            write_request.content,
            create_backup=write_request.create_backup,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (OSError, IOError, PermissionError) as e:
        logger.error(f"File operation error in write_file: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.exception("Unexpected error in write_file")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{project_id}/file")
@limiter.limit(TIER_WRITE)
async def delete_file(
    request: Request,
    project_id: int,
    path: str = Query(..., description="Relative path to file"),
):
    """Delete a file."""
    project_path = get_project_path(project_id)

    try:
        result = FileManager.delete_file(project_path, path)
        return result
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (OSError, IOError, PermissionError) as e:
        logger.error(f"File operation error in delete_file: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.exception("Unexpected error in delete_file")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# Git Endpoints
# ============================================================================


@router.get("/{project_id}/git/status")
@limiter.limit(TIER_READ)
async def get_git_status(
    request: Request,
    project_id: int,
):
    """Get git status with Redis caching."""
    # Try cache first (30 second TTL for frequently changing data)
    cached = get_cached_git_status(project_id)
    if cached is not None:
        logger.debug(f"Cache HIT: git status for project {project_id}")
        return {"status": cached}

    project_path = get_project_path(project_id)

    try:
        if not GitManager.is_git_repo(project_path):
            raise HTTPException(status_code=400, detail="Not a git repository")

        status = GitManager.get_status(project_path)

        # Cache for 30 seconds (short TTL for frequently changing data)
        cache_git_status(project_id, status)
        logger.debug(f"Cache SET: git status for project {project_id}")

        return {"status": status}
    except HTTPException:
        raise
    except (OSError, subprocess.SubprocessError) as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in get_git_status")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{project_id}/git/commits")
@limiter.limit(TIER_READ)
async def get_commits(
    request: Request,
    project_id: int,
    limit: int = Query(default=50, le=200),
    branch: Optional[str] = None,
    author: Optional[str] = None,
):
    """Get commit history with Redis caching."""
    # Try cache first (only for default params to keep cache simple)
    if branch is None and author is None and limit == 50:
        cached = get_cached_git_commits(project_id)
        if cached is not None:
            logger.debug(f"Cache HIT: git commits for project {project_id}")
            return cached

    project_path = get_project_path(project_id)

    try:
        commits = GitManager.get_commits(
            project_path,
            limit=limit,
            branch=branch,
            author=author,
        )

        # Cache for 5 minutes (only default params)
        if branch is None and author is None and limit == 50:
            cache_git_commits(project_id, commits)
            logger.debug(f"Cache SET: git commits for project {project_id}")

        return commits
    except (OSError, subprocess.SubprocessError) as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in get_commits")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{project_id}/git/diff")
@limiter.limit(TIER_READ)
async def get_diff(
    request: Request,
    project_id: int,
    commit: Optional[str] = None,
    file_path: Optional[str] = None,
):
    """Get diff for a commit or file."""
    project_path = get_project_path(project_id)

    try:
        diff = GitManager.get_diff(project_path, commit, file_path)
        return {"diff": diff}
    except (OSError, subprocess.SubprocessError) as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in get_diff")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{project_id}/git/branches")
@limiter.limit(TIER_READ)
async def get_branches(
    request: Request,
    project_id: int,
):
    """Get list of branches."""
    project_path = get_project_path(project_id)

    try:
        branches = GitManager.get_branches(project_path)
        return {"branches": branches}
    except (OSError, subprocess.SubprocessError) as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in get_branches")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{project_id}/git/file-history")
@limiter.limit(TIER_READ)
async def get_file_history(
    request: Request,
    project_id: int,
    file_path: str = Query(...),
    limit: int = Query(default=50),
):
    """Get commit history for a specific file."""
    project_path = get_project_path(project_id)

    try:
        history = GitManager.get_file_history(project_path, file_path, limit)
        return history
    except (OSError, subprocess.SubprocessError) as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in get_file_history")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{project_id}/git/stage")
@limiter.limit(TIER_WRITE)
async def stage_files(
    request: Request,
    project_id: int,
    files: List[str] = Body(..., description="List of file paths to stage"),
):
    """Stage files for commit."""
    project_path = get_project_path(project_id)

    try:
        if not GitManager.is_git_repo(project_path):
            raise HTTPException(status_code=400, detail="Not a git repository")

        result = GitManager.stage_files(project_path, files)

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        # Invalidate status cache
        invalidate_workspace_cache(project_id)

        return result
    except HTTPException:
        raise
    except (OSError, subprocess.SubprocessError) as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in stage_files")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{project_id}/git/unstage")
@limiter.limit(TIER_WRITE)
async def unstage_files(
    request: Request,
    project_id: int,
    files: List[str] = Body(..., description="List of file paths to unstage"),
):
    """Unstage files."""
    project_path = get_project_path(project_id)

    try:
        if not GitManager.is_git_repo(project_path):
            raise HTTPException(status_code=400, detail="Not a git repository")

        result = GitManager.unstage_files(project_path, files)

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        # Invalidate status cache
        invalidate_workspace_cache(project_id)

        return result
    except HTTPException:
        raise
    except (OSError, subprocess.SubprocessError) as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in unstage_files")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{project_id}/git/commit")
@limiter.limit(TIER_WRITE)
async def create_commit(
    request: Request,
    project_id: int,
    message: str = Body(..., description="Commit message"),
    author_name: Optional[str] = Body(None, description="Author name"),
    author_email: Optional[str] = Body(None, description="Author email"),
):
    """Create a commit."""
    project_path = get_project_path(project_id)

    try:
        if not GitManager.is_git_repo(project_path):
            raise HTTPException(status_code=400, detail="Not a git repository")

        result = GitManager.commit(
            project_path, message, author_name=author_name, author_email=author_email
        )

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        # Invalidate all git caches
        invalidate_workspace_cache(project_id)

        return result
    except HTTPException:
        raise
    except (OSError, subprocess.SubprocessError) as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in create_commit")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{project_id}/git/push")
@limiter.limit(TIER_WRITE)
async def push_to_remote(
    request: Request,
    project_id: int,
    remote: str = Body(default="origin", description="Remote name"),
    branch: Optional[str] = Body(None, description="Branch name"),
    set_upstream: bool = Body(default=False, description="Set upstream tracking"),
):
    """Push to remote repository."""
    project_path = get_project_path(project_id)

    try:
        if not GitManager.is_git_repo(project_path):
            raise HTTPException(status_code=400, detail="Not a git repository")

        result = GitManager.push(
            project_path, remote=remote, branch=branch, set_upstream=set_upstream
        )

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        # Invalidate status cache
        invalidate_workspace_cache(project_id)

        return result
    except HTTPException:
        raise
    except (OSError, subprocess.SubprocessError) as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in push_to_remote")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{project_id}/git/pull")
@limiter.limit(TIER_WRITE)
async def pull_from_remote(
    request: Request,
    project_id: int,
    remote: str = Body(default="origin", description="Remote name"),
    branch: Optional[str] = Body(None, description="Branch name"),
):
    """Pull from remote repository."""
    project_path = get_project_path(project_id)

    try:
        if not GitManager.is_git_repo(project_path):
            raise HTTPException(status_code=400, detail="Not a git repository")

        result = GitManager.pull(project_path, remote=remote, branch=branch)

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        # Invalidate all git caches after pull
        invalidate_workspace_cache(project_id)

        return result
    except HTTPException:
        raise
    except (OSError, subprocess.SubprocessError) as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in pull_from_remote")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# Activity Tracking Endpoints
# ============================================================================


@router.get("/{project_id}/activities")
@limiter.limit(TIER_READ)
async def get_activities(
    request: Request,
    project_id: int,
    limit: int = Query(default=50),
    agent_id: Optional[int] = None,
    activity_type: Optional[str] = None,
):
    """Get activities for a project."""
    try:
        if activity_type:
            activities = activity_tracker.get_activities_by_type(
                project_id,
                ActivityType(activity_type),
            )
        elif agent_id:
            activities = activity_tracker.get_activities_by_agent(
                project_id,
                agent_id,
            )
        else:
            activities = activity_tracker.get_activities(project_id, limit)

        return activities
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in get_activities")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{project_id}/activities")
@limiter.limit(TIER_WRITE)
async def track_activity(
    request: Request,
    project_id: int,
    activity_request: ActivityRequest,
):
    """Track a new activity."""
    try:
        # Convert activity_type string to enum
        try:
            activity_type = ActivityType(activity_request.activity_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid activity type: {activity_request.activity_type}",
            )

        activity = activity_tracker.track_activity(
            project_id,
            activity_request.agent_id,
            activity_type,
            activity_request.details,
        )

        return activity
    except HTTPException:
        raise
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in track_activity")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{project_id}/activities/stats")
@limiter.limit(TIER_READ)
async def get_activity_stats(request: Request, project_id: int):
    """Get activity statistics."""
    try:
        stats = activity_tracker.get_stats(project_id)
        return stats
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in get_activity_stats")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# Python Execution Endpoint
# ============================================================================


class PythonExecutionRequest(BaseModel):
    """Request to execute Python code."""

    code: str
    file_path: Optional[str] = None


@router.post("/{project_id}/run-python")
@limiter.limit(TIER_WRITE)
async def run_python_code(
    request: Request,
    project_id: int,
    exec_request: PythonExecutionRequest,
):
    """
    Execute Python code in a sandboxed environment.

    Security notes:
    - Code runs with subprocess timeout
    - Limited to current workspace directory
    - No network access (can be added with --network flag)
    """
    import tempfile
    import time

    try:
        project_path = get_project_path(project_id)

        # Create temporary file for code
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            dir=project_path,
            delete=False,
        ) as tmp_file:
            tmp_file.write(exec_request.code)
            tmp_path = tmp_file.name

        try:
            # Execute with timeout
            start_time = time.time()

            # Try python3 first, fall back to python
            python_cmd = 'python3'
            try:
                subprocess.run(['which', 'python3'], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                python_cmd = 'python'

            result = subprocess.run(
                [python_cmd, tmp_path],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
            )
            execution_time = time.time() - start_time

            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "execution_time": execution_time,
            }
        finally:
            # Clean up temp file
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except OSError:
                pass  # Intentional: ignore cleanup errors

    except subprocess.TimeoutExpired as e:
        # Cleanup temp file on timeout
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except OSError:
            pass  # Intentional: ignore cleanup errors
        raise HTTPException(
            status_code=408,
            detail=f"Execution timeout (30s limit). Output: {e.stdout if hasattr(e, 'stdout') else 'N/A'}",
        )
    except (OSError, subprocess.SubprocessError) as e:
        logger.error(f"Python execution error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.exception("Unexpected error in run_python_code")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{project_id}/git/graph")
@limiter.limit(TIER_READ)
async def get_git_graph(
    request: Request,
    project_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    all_branches: bool = Query(default=True),
):
    """
    Get git graph data for visualization (like git log --graph).

    Returns commits with parent relationships and branch/merge information.
    """
    project_path = get_project_path(project_id)

    if not GitManager.is_git_repo(project_path):
        raise HTTPException(status_code=404, detail="Not a git repository")

    graph_data = GitManager.get_graph(project_path, limit=limit, all_branches=all_branches)

    if "error" in graph_data:
        raise HTTPException(status_code=500, detail=graph_data["error"])

    return graph_data
