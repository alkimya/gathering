"""
Workspace API Router.

Provides endpoints for workspace management, file operations,
git integration, and activity tracking.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

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
