"""
Memories API Router for GatheRing.

Provides endpoints for agent memory operations and knowledge base management.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from starlette.requests import Request

from gathering.api.rate_limit import limiter, TIER_READ, TIER_WRITE
from pydantic import BaseModel, Field

from gathering.utils.document_extractor import DocumentExtractor, chunk_text

router = APIRouter(prefix="/memories", tags=["memories"])


# =============================================================================
# SCHEMAS
# =============================================================================


class MemoryCreate(BaseModel):
    """Request to create a memory."""
    content: str = Field(..., description="Memory content")
    memory_type: str = Field(default="fact", description="Type: fact, preference, context, decision, error, feedback, learning")
    key: Optional[str] = Field(None, description="Memory key (auto-generated if not provided)")
    tags: Optional[List[str]] = Field(None, description="Tags for filtering")
    importance: float = Field(default=0.5, ge=0, le=1, description="Importance score (0-1)")


class MemoryResponse(BaseModel):
    """Memory response."""
    id: int
    key: str
    value: str
    memory_type: str
    similarity: Optional[float] = None
    importance: float


class RecallRequest(BaseModel):
    """Request to recall memories."""
    query: str = Field(..., description="Query text to find similar memories")
    memory_type: Optional[str] = Field(None, description="Filter by memory type")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum results")
    threshold: float = Field(default=0.7, ge=0, le=1, description="Minimum similarity threshold")


class RecallResponse(BaseModel):
    """Recall response."""
    query: str
    memories: List[MemoryResponse]
    total: int


class KnowledgeCreate(BaseModel):
    """Request to create knowledge entry."""
    title: str = Field(..., description="Knowledge title")
    content: str = Field(..., description="Knowledge content")
    category: Optional[str] = Field(None, description="Category: docs, best_practice, decision, faq")
    project_id: Optional[int] = Field(None, description="Associated project")
    circle_id: Optional[int] = Field(None, description="Associated circle")
    is_global: bool = Field(default=False, description="Globally accessible")
    tags: Optional[List[str]] = Field(None, description="Tags")
    source_url: Optional[str] = Field(None, description="Source URL")


class KnowledgeResponse(BaseModel):
    """Knowledge response."""
    id: int
    title: str
    content: str
    category: Optional[str]
    similarity: Optional[float] = None
    tags: Optional[List[str]] = None


class KnowledgeSearchRequest(BaseModel):
    """Request to search knowledge base."""
    query: str = Field(..., description="Search query")
    project_id: Optional[int] = Field(None, description="Filter by project")
    circle_id: Optional[int] = Field(None, description="Filter by circle")
    category: Optional[str] = Field(None, description="Filter by category")
    include_global: bool = Field(default=True, description="Include global knowledge")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum results")
    threshold: float = Field(default=0.7, ge=0, le=1, description="Minimum similarity")


class KnowledgeSearchResponse(BaseModel):
    """Knowledge search response."""
    query: str
    results: List[KnowledgeResponse]
    total: int


class KnowledgeListResponse(BaseModel):
    """Knowledge list response."""
    entries: List[KnowledgeResponse]
    total: int
    page: int
    page_size: int


class KnowledgeStats(BaseModel):
    """Knowledge base statistics."""
    total_entries: int
    by_category: dict
    recent_entries: List[KnowledgeResponse]


class MemoryStats(BaseModel):
    """Memory statistics."""
    total_memories: int
    active_memories: int
    embedded_memories: int
    avg_importance: Optional[float]


class DocumentUploadResponse(BaseModel):
    """Response after uploading a document."""
    id: int
    title: str
    filename: str
    format: str
    char_count: int
    chunk_count: int
    category: Optional[str] = None
    tags: Optional[List[str]] = None


# =============================================================================
# DEPENDENCIES
# =============================================================================


def get_memory_manager():
    """Get MemoryManager instance."""
    try:
        from gathering.rag import MemoryManager
        return MemoryManager.from_env()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Memory service unavailable: {str(e)}"
        )


# =============================================================================
# AGENT MEMORY ENDPOINTS
# =============================================================================


@router.post("/agents/{agent_id}/remember", response_model=MemoryResponse)
@limiter.limit(TIER_WRITE)
async def remember(
    request: Request,
    agent_id: int,
    memory: MemoryCreate,
):
    """
    Store a memory for an agent.

    The memory content is embedded and stored for semantic search.
    """
    try:
        manager = get_memory_manager()

        memory_id = await manager.remember(
            agent_id=agent_id,
            content=memory.content,
            memory_type=memory.memory_type,
            key=memory.key,
            tags=memory.tags,
            importance=memory.importance,
        )

        return MemoryResponse(
            id=memory_id,
            key=memory.key or f"auto_{memory_id}",
            value=memory.content,
            memory_type=memory.memory_type,
            importance=memory.importance,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/{agent_id}/recall", response_model=RecallResponse)
@limiter.limit(TIER_WRITE)
async def recall(
    request: Request,
    agent_id: int,
    recall_request: RecallRequest,
):
    """
    Recall relevant memories for an agent.

    Uses semantic similarity to find memories related to the query.
    """
    try:
        manager = get_memory_manager()

        results = await manager.recall(
            agent_id=agent_id,
            query=recall_request.query,
            memory_type=recall_request.memory_type,
            tags=recall_request.tags,
            limit=recall_request.limit,
            threshold=recall_request.threshold,
        )

        memories = [
            MemoryResponse(
                id=r.id,
                key=r.key,
                value=r.value,
                memory_type=r.memory_type,
                similarity=r.similarity,
                importance=r.importance,
            )
            for r in results
        ]

        return RecallResponse(
            query=recall_request.query,
            memories=memories,
            total=len(memories),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/agents/{agent_id}/memories/{memory_id}")
@limiter.limit(TIER_WRITE)
async def forget(
    request: Request,
    agent_id: int,
    memory_id: int,
):
    """
    Forget (soft delete) a memory.
    """
    try:
        manager = get_memory_manager()
        await manager.forget(memory_id)
        return {"status": "forgotten", "memory_id": memory_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}/stats", response_model=MemoryStats)
@limiter.limit(TIER_READ)
async def get_agent_memory_stats(
    request: Request,
    agent_id: int,
):
    """
    Get memory statistics for an agent.
    """
    try:
        manager = get_memory_manager()
        stats = manager.get_stats(agent_id)
        memory_stats = stats.get("memories", {})

        return MemoryStats(
            total_memories=memory_stats.get("total_memories", 0),
            active_memories=memory_stats.get("active_memories", 0),
            embedded_memories=memory_stats.get("embedded_memories", 0),
            avg_importance=memory_stats.get("avg_importance"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# KNOWLEDGE BASE ENDPOINTS
# =============================================================================


@router.post("/knowledge", response_model=KnowledgeResponse)
@limiter.limit(TIER_WRITE)
async def add_knowledge(
    request: Request,
    knowledge: KnowledgeCreate,
    author_agent_id: Optional[int] = Query(None, description="Author agent ID"),
):
    """
    Add entry to knowledge base.

    The content is embedded for semantic search.
    """
    try:
        manager = get_memory_manager()

        kb_id = await manager.add_knowledge(
            title=knowledge.title,
            content=knowledge.content,
            category=knowledge.category,
            project_id=knowledge.project_id,
            circle_id=knowledge.circle_id,
            is_global=knowledge.is_global,
            tags=knowledge.tags,
            source_url=knowledge.source_url,
            author_agent_id=author_agent_id,
        )

        return KnowledgeResponse(
            id=kb_id,
            title=knowledge.title,
            content=knowledge.content,
            category=knowledge.category,
            tags=knowledge.tags,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge/search", response_model=KnowledgeSearchResponse)
@limiter.limit(TIER_WRITE)
async def search_knowledge(
    request: Request,
    search_request: KnowledgeSearchRequest,
):
    """
    Search knowledge base using semantic similarity.
    """
    try:
        manager = get_memory_manager()

        results = await manager.search_knowledge(
            query=search_request.query,
            project_id=search_request.project_id,
            circle_id=search_request.circle_id,
            category=search_request.category,
            include_global=search_request.include_global,
            limit=search_request.limit,
            threshold=search_request.threshold,
        )

        knowledge_results = [
            KnowledgeResponse(
                id=r.id,
                title=r.title,
                content=r.content,
                category=r.category,
                similarity=r.similarity,
                tags=r.tags,
            )
            for r in results
        ]

        return KnowledgeSearchResponse(
            query=search_request.query,
            results=knowledge_results,
            total=len(knowledge_results),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge", response_model=KnowledgeListResponse)
@limiter.limit(TIER_READ)
async def list_knowledge(
    request: Request,
    category: Optional[str] = Query(None, description="Filter by category"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """
    List knowledge base entries with pagination.
    """
    try:
        manager = get_memory_manager()

        # Get entries from the knowledge base
        entries = await manager.list_knowledge(
            category=category,
            limit=page_size,
            offset=(page - 1) * page_size,
        )

        total = await manager.count_knowledge(category=category)

        return KnowledgeListResponse(
            entries=[
                KnowledgeResponse(
                    id=e.id,
                    title=e.title,
                    content=e.content,
                    category=e.category,
                    tags=e.tags,
                )
                for e in entries
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/stats", response_model=KnowledgeStats)
@limiter.limit(TIER_READ)
async def get_knowledge_stats(request: Request):
    """
    Get knowledge base statistics.
    """
    try:
        manager = get_memory_manager()

        stats = await manager.get_knowledge_stats()

        return KnowledgeStats(
            total_entries=stats.get("total", 0),
            by_category=stats.get("by_category", {}),
            recent_entries=[
                KnowledgeResponse(
                    id=e.id,
                    title=e.title,
                    content=e.content,
                    category=e.category,
                    tags=e.tags,
                )
                for e in stats.get("recent", [])
            ],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# BATCH OPERATIONS
# =============================================================================


class BatchMemoryCreate(BaseModel):
    """Batch memory creation request."""
    memories: List[MemoryCreate] = Field(..., description="List of memories to create")


class BatchMemoryResponse(BaseModel):
    """Batch memory creation response."""
    created: List[int]
    total: int


@router.post("/agents/{agent_id}/remember/batch", response_model=BatchMemoryResponse)
@limiter.limit(TIER_WRITE)
async def remember_batch(
    request: Request,
    agent_id: int,
    batch_request: BatchMemoryCreate,
):
    """
    Store multiple memories at once.

    More efficient than individual calls for bulk operations.
    """
    try:
        manager = get_memory_manager()

        memories = [
            {
                "content": m.content,
                "memory_type": m.memory_type,
                "key": m.key,
                "tags": m.tags,
                "importance": m.importance,
            }
            for m in batch_request.memories
        ]

        ids = await manager.remember_batch(agent_id=agent_id, memories=memories)

        return BatchMemoryResponse(
            created=ids,
            total=len(ids),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DOCUMENT UPLOAD
# =============================================================================


@router.post("/knowledge/upload", response_model=DocumentUploadResponse)
@limiter.limit(TIER_WRITE)
async def upload_document(
    request: Request,
    file: UploadFile = File(..., description="Document file (MD, CSV, PDF, TXT)"),
    title: Optional[str] = Form(None, description="Document title (defaults to filename)"),
    category: Optional[str] = Form(None, description="Category: docs, best_practice, decision, faq"),
    tags: Optional[str] = Form(None, description="Comma-separated tags"),
    is_global: bool = Form(False, description="Globally accessible"),
    author_agent_id: Optional[int] = Form(None, description="Author agent ID"),
    chunk_large_docs: bool = Form(True, description="Chunk large documents for better search"),
):
    """
    Upload a document to the knowledge base.

    Supported formats:
    - Markdown (.md, .markdown)
    - CSV (.csv)
    - PDF (.pdf) - requires pypdf
    - Plain text (.txt)

    Large documents are automatically chunked for better semantic search.
    """
    # Validate file format
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    if not DocumentExtractor.is_supported(file.filename, file.content_type):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Supported: {', '.join(DocumentExtractor.SUPPORTED_EXTENSIONS)}"
        )

    try:
        # Read file content
        content = await file.read()

        # Extract text
        extracted_text, metadata = DocumentExtractor.extract(
            content=content,
            filename=file.filename,
            content_type=file.content_type,
        )

        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="Document is empty or could not be parsed")

        # Parse tags
        tag_list = [t.strip() for t in tags.split(',')] if tags else None

        # Use filename as title if not provided
        doc_title = title or file.filename

        manager = get_memory_manager()

        # Chunk large documents
        chunks = []
        if chunk_large_docs and len(extracted_text) > 3000:
            chunks = chunk_text(extracted_text, chunk_size=2000, overlap=200)
        else:
            chunks = [{'content': extracted_text, 'index': 0}]

        # Store main document
        main_id = await manager.add_knowledge(
            title=doc_title,
            content=extracted_text if len(chunks) == 1 else f"[Document with {len(chunks)} chunks]\n\n{extracted_text[:500]}...",
            category=category,
            is_global=is_global,
            tags=tag_list,
            source_url=f"file://{file.filename}",
            author_agent_id=author_agent_id,
        )

        # Store chunks as separate entries if document was chunked
        if len(chunks) > 1:
            for chunk in chunks:
                chunk_title = f"{doc_title} (chunk {chunk['index'] + 1}/{len(chunks)})"
                await manager.add_knowledge(
                    title=chunk_title,
                    content=chunk['content'],
                    category=category,
                    is_global=is_global,
                    tags=(tag_list or []) + [f"doc:{main_id}", "chunk"],
                    source_url=f"file://{file.filename}#chunk-{chunk['index']}",
                    author_agent_id=author_agent_id,
                )

        return DocumentUploadResponse(
            id=main_id,
            title=doc_title,
            filename=file.filename,
            format=metadata.get('format', 'unknown'),
            char_count=len(extracted_text),
            chunk_count=len(chunks),
            category=category,
            tags=tag_list,
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
