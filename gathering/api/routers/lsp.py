"""
LSP API Router - Language Server Protocol endpoints.

Provides REST API for LSP features like autocomplete, diagnostics, hover, etc.
"""

from fastapi import APIRouter, HTTPException, Query
from starlette.requests import Request

from gathering.api.rate_limit import limiter, TIER_READ, TIER_WRITE
from pydantic import BaseModel
from typing import Optional
import logging

from gathering.lsp.manager import LSPManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lsp", tags=["lsp"])


# ============================================================================
# Request/Response Models
# ============================================================================


class InitializeRequest(BaseModel):
    """Request to initialize an LSP server."""
    language: str
    workspace_path: str


class CompletionRequest(BaseModel):
    """Request for code completions."""
    file_path: str
    line: int  # 1-indexed
    character: int  # 0-indexed
    content: Optional[str] = None  # If None, reads from disk


class DiagnosticsRequest(BaseModel):
    """Request for code diagnostics."""
    file_path: str
    content: Optional[str] = None


class HoverRequest(BaseModel):
    """Request for hover information."""
    file_path: str
    line: int
    character: int
    content: Optional[str] = None


class DefinitionRequest(BaseModel):
    """Request for go-to-definition."""
    file_path: str
    line: int
    character: int
    content: Optional[str] = None


# ============================================================================
# LSP Endpoints
# ============================================================================


@router.post("/{project_id}/initialize")
@limiter.limit(TIER_WRITE)
async def initialize_lsp(
    request: Request,
    project_id: int,
    lsp_request: InitializeRequest
):
    """
    Initialize an LSP server for a project and language.

    Args:
        project_id: Project identifier
        request: Initialization parameters

    Returns:
        Server capabilities
    """
    try:
        capabilities = await LSPManager.initialize_server(
            project_id=project_id,
            language=lsp_request.language,
            workspace_path=lsp_request.workspace_path
        )

        return {
            "status": "initialized",
            "language": lsp_request.language,
            "capabilities": capabilities
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"LSP initialization error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize LSP: {str(e)}")


@router.post("/{project_id}/completions")
@limiter.limit(TIER_WRITE)
async def get_completions(
    request: Request,
    project_id: int,
    lsp_request: CompletionRequest,
    language: str = Query(default="python")
):
    """
    Get autocomplete suggestions.

    Args:
        project_id: Project identifier
        request: Completion request parameters
        language: Programming language

    Returns:
        List of completion items
    """
    try:
        server = LSPManager.get_server(project_id, language)

        completions = await server.get_completions(
            file_path=lsp_lsp_lsp_lsp_request.file_path,
            line=lsp_lsp_lsp_request.line,
            character=lsp_lsp_lsp_request.character,
            content=lsp_lsp_lsp_lsp_request.content
        )

        return {
            "completions": completions,
            "count": len(completions)
        }

    except Exception as e:
        logger.error(f"Completion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/diagnostics")
@limiter.limit(TIER_WRITE)
async def get_diagnostics(
    request: Request,
    project_id: int,
    lsp_request: DiagnosticsRequest,
    language: str = Query(default="python")
):
    """
    Get diagnostics (errors, warnings) for a file.

    Args:
        project_id: Project identifier
        request: Diagnostics request parameters
        language: Programming language

    Returns:
        List of diagnostic items
    """
    try:
        server = LSPManager.get_server(project_id, language)

        diagnostics = await server.get_diagnostics(
            file_path=lsp_lsp_lsp_lsp_request.file_path,
            content=lsp_lsp_lsp_lsp_request.content
        )

        return {
            "diagnostics": diagnostics,
            "count": len(diagnostics)
        }

    except Exception as e:
        logger.error(f"Diagnostics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/hover")
@limiter.limit(TIER_WRITE)
async def get_hover(
    request: Request,
    project_id: int,
    lsp_request: HoverRequest,
    language: str = Query(default="python")
):
    """
    Get hover information (documentation) at a position.

    Args:
        project_id: Project identifier
        request: Hover request parameters
        language: Programming language

    Returns:
        Hover information or null
    """
    try:
        server = LSPManager.get_server(project_id, language)

        hover = await server.get_hover(
            file_path=lsp_lsp_lsp_lsp_request.file_path,
            line=lsp_lsp_lsp_request.line,
            character=lsp_lsp_lsp_request.character,
            content=lsp_lsp_lsp_lsp_request.content
        )

        return hover if hover else {"contents": None}

    except Exception as e:
        logger.error(f"Hover error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/definition")
@limiter.limit(TIER_WRITE)
async def get_definition(
    request: Request,
    project_id: int,
    lsp_request: DefinitionRequest,
    language: str = Query(default="python")
):
    """
    Get definition location for a symbol.

    Args:
        project_id: Project identifier
        request: Definition request parameters
        language: Programming language

    Returns:
        Definition location or null
    """
    try:
        server = LSPManager.get_server(project_id, language)

        definition = await server.get_definition(
            file_path=lsp_lsp_lsp_lsp_request.file_path,
            line=lsp_lsp_lsp_request.line,
            character=lsp_lsp_lsp_request.character,
            content=lsp_lsp_lsp_lsp_request.content
        )

        return definition if definition else {"uri": None}

    except Exception as e:
        logger.error(f"Definition error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}/shutdown")
@limiter.limit(TIER_WRITE)
async def shutdown_lsp(
    request: Request,
    project_id: int,
    language: str = Query(default="python")
):
    """
    Shutdown an LSP server.

    Args:
        project_id: Project identifier
        language: Programming language

    Returns:
        Status message
    """
    try:
        await LSPManager.shutdown_server(project_id, language)

        return {
            "status": "shutdown",
            "project_id": project_id,
            "language": language
        }

    except Exception as e:
        logger.error(f"Shutdown error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/status")
@limiter.limit(TIER_READ)
async def get_lsp_status(
    request: Request,
    project_id: int,
    language: str = Query(default="python")
):
    """
    Get LSP server status.

    Args:
        project_id: Project identifier
        language: Programming language

    Returns:
        Server status information
    """
    try:
        key = f"{project_id}:{language}"
        active = key in LSPManager._servers

        return {
            "active": active,
            "project_id": project_id,
            "language": language
        }

    except Exception as e:
        logger.error(f"Status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
