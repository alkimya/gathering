"""
Memories API Router for GatheRing.

Provides endpoints for agent memory operations and knowledge base management.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

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


class MemoryStats(BaseModel):
    """Memory statistics."""
    total_memories: int
    active_memories: int
    embedded_memories: int
    avg_importance: Optional[float]


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
async def remember(
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
async def recall(
    agent_id: int,
    request: RecallRequest,
):
    """
    Recall relevant memories for an agent.

    Uses semantic similarity to find memories related to the query.
    """
    try:
        manager = get_memory_manager()

        results = await manager.recall(
            agent_id=agent_id,
            query=request.query,
            memory_type=request.memory_type,
            tags=request.tags,
            limit=request.limit,
            threshold=request.threshold,
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
            query=request.query,
            memories=memories,
            total=len(memories),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/agents/{agent_id}/memories/{memory_id}")
async def forget(
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
async def get_agent_memory_stats(
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
async def add_knowledge(
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
async def search_knowledge(
    request: KnowledgeSearchRequest,
):
    """
    Search knowledge base using semantic similarity.
    """
    try:
        manager = get_memory_manager()

        results = await manager.search_knowledge(
            query=request.query,
            project_id=request.project_id,
            circle_id=request.circle_id,
            category=request.category,
            include_global=request.include_global,
            limit=request.limit,
            threshold=request.threshold,
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
            query=request.query,
            results=knowledge_results,
            total=len(knowledge_results),
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
async def remember_batch(
    agent_id: int,
    request: BatchMemoryCreate,
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
            for m in request.memories
        ]

        ids = await manager.remember_batch(agent_id=agent_id, memories=memories)

        return BatchMemoryResponse(
            created=ids,
            total=len(ids),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
