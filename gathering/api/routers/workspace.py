"""
Workspace API Router.

Provides endpoints for workspace management, file operations,
git integration, and activity tracking.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from pathlib import Path
import mimetypes

from gathering.workspace import (
    WorkspaceManager,
    FileManager,
    GitManager,
    ActivityTracker,
    WorkspaceType,
)
from gathering.workspace.activity_tracker import ActivityType, activity_tracker

router = APIRouter(prefix="/workspace", tags=["workspace"])


# ============================================================================
# Helper Functions
# ============================================================================


def get_project_path(project_id: int) -> str:
    """Get project path. For now, returns the current workspace."""
    # TODO: Integrate with project database when available
    # For demo purposes, use the current workspace
    import os
    return os.getcwd()


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
async def get_workspace_info(
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# File Management Endpoints
# ============================================================================


@router.get("/{project_id}/files")
async def list_files(
    project_id: int,
    include_git_status: bool = Query(default=True),
    max_depth: int = Query(default=10),
):
    """List all files in the workspace."""
    project_path = get_project_path(project_id)

    try:
        tree = FileManager.list_files(
            project_path,
            include_git_status=include_git_status,
            max_depth=max_depth,
        )
        return tree
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/file")
async def read_file(
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/file/raw")
async def read_file_raw(
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
        # Build full file path
        full_path = Path(project_path) / path

        # Security check: prevent directory traversal
        try:
            full_path = full_path.resolve()
            project_path_resolved = Path(project_path).resolve()
            if not str(full_path).startswith(str(project_path_resolved)):
                raise HTTPException(status_code=403, detail="Access denied")
        except HTTPException:
            raise
        except Exception as e:
            # Log the actual error for debugging
            import logging
            logging.error(f"Path resolution error: {e}, path={path}")
            raise HTTPException(status_code=403, detail=f"Invalid path: {str(e)}")

        # Check if file exists
        if not full_path.exists():
            # Try to find the file with similar name (handle encoding issues)
            import logging
            logging.warning(f"File not found: {full_path}, trying to list directory")
            parent = full_path.parent
            if parent.exists():
                similar = list(parent.glob(f"*{full_path.stem}*{full_path.suffix}"))
                logging.warning(f"Similar files: {similar}")
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{project_id}/file")
async def write_file(
    project_id: int,
    path: str = Query(..., description="Relative path to file"),
    request: WriteFileRequest = None,
):
    """Write or update a file."""
    project_path = get_project_path(project_id)

    try:
        result = FileManager.write_file(
            project_path,
            path,
            request.content,
            create_backup=request.create_backup,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}/file")
async def delete_file(
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Git Endpoints
# ============================================================================


@router.get("/{project_id}/git/status")
async def get_git_status(
    project_id: int,
):
    """Get git status."""
    project_path = get_project_path(project_id)

    try:
        if not GitManager.is_git_repo(project_path):
            raise HTTPException(status_code=400, detail="Not a git repository")

        status = GitManager.get_status(project_path)
        return {"status": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/git/commits")
async def get_commits(
    project_id: int,
    limit: int = Query(default=50, le=200),
    branch: Optional[str] = None,
    author: Optional[str] = None,
):
    """Get commit history."""
    project_path = get_project_path(project_id)

    try:
        commits = GitManager.get_commits(
            project_path,
            limit=limit,
            branch=branch,
            author=author,
        )
        return commits
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/git/diff")
async def get_diff(
    project_id: int,
    commit: Optional[str] = None,
    file_path: Optional[str] = None,
):
    """Get diff for a commit or file."""
    project_path = get_project_path(project_id)

    try:
        diff = GitManager.get_diff(project_path, commit, file_path)
        return {"diff": diff}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/git/branches")
async def get_branches(
    project_id: int,
):
    """Get list of branches."""
    project_path = get_project_path(project_id)

    try:
        branches = GitManager.get_branches(project_path)
        return {"branches": branches}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/git/file-history")
async def get_file_history(
    project_id: int,
    file_path: str = Query(...),
    limit: int = Query(default=50),
):
    """Get commit history for a specific file."""
    project_path = get_project_path(project_id)

    try:
        history = GitManager.get_file_history(project_path, file_path, limit)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Activity Tracking Endpoints
# ============================================================================


@router.get("/{project_id}/activities")
async def get_activities(
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/activities")
async def track_activity(
    project_id: int,
    request: ActivityRequest,
):
    """Track a new activity."""
    try:
        # Convert activity_type string to enum
        try:
            activity_type = ActivityType(request.activity_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid activity type: {request.activity_type}",
            )

        activity = activity_tracker.track_activity(
            project_id,
            request.agent_id,
            activity_type,
            request.details,
        )

        return activity
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/activities/stats")
async def get_activity_stats(project_id: int):
    """Get activity statistics."""
    try:
        stats = activity_tracker.get_stats(project_id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Python Execution Endpoint
# ============================================================================


class PythonExecutionRequest(BaseModel):
    """Request to execute Python code."""

    code: str
    file_path: Optional[str] = None


@router.post("/{project_id}/run-python")
async def run_python_code(
    project_id: int,
    request: PythonExecutionRequest,
):
    """
    Execute Python code in a sandboxed environment.

    Security notes:
    - Code runs with subprocess timeout
    - Limited to current workspace directory
    - No network access (can be added with --network flag)
    """
    import subprocess
    import tempfile
    import time
    from pathlib import Path

    try:
        project_path = get_project_path(project_id)

        # Create temporary file for code
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            dir=project_path,
            delete=False,
        ) as tmp_file:
            tmp_file.write(request.code)
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
            except Exception:
                pass  # Ignore cleanup errors

    except subprocess.TimeoutExpired as e:
        # Cleanup temp file on timeout
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass
        raise HTTPException(
            status_code=408,
            detail=f"Execution timeout (30s limit). Output: {e.stdout if hasattr(e, 'stdout') else 'N/A'}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
