"""
Memory Manager for GatheRing RAG.

High-level API for agent memory operations combining embeddings and vector store.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from gathering.rag.embeddings import EmbeddingService, EmbeddingProvider
from gathering.rag.vectorstore import VectorStore, KnowledgeResult
from gathering.events import event_bus, Event, EventType

# Import cache (optional dependency)
try:
    from gathering.cache import CacheManager
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    CacheManager = None


@dataclass
class RecallResult:
    """Result from memory recall with full context."""
    id: int
    key: str
    value: str
    memory_type: str
    similarity: float
    importance: float


class MemoryManager:
    """
    High-level memory management for agents.

    Combines embedding generation and vector storage into a simple API.

    Example:
        memory = MemoryManager.from_env()

        # Remember something
        await memory.remember(
            agent_id=1,
            content="User prefers dark mode",
            memory_type="preference",
            key="theme_preference",
        )

        # Recall relevant memories
        results = await memory.recall(
            agent_id=1,
            query="What are the user's preferences?",
            limit=5,
        )

        # Add to knowledge base
        await memory.add_knowledge(
            title="API Usage Guide",
            content="...",
            category="docs",
        )

        # Search knowledge
        results = await memory.search_knowledge(
            query="How to use the API?",
            limit=5,
        )
    """

    def __init__(
        self,
        embedder: EmbeddingService,
        store: VectorStore,
        cache_manager: Optional[Any] = None,
    ):
        """
        Initialize MemoryManager.

        Args:
            embedder: Embedding service for generating vectors.
            store: Vector store for storage and search.
            cache_manager: Optional CacheManager for RAG result caching.
        """
        self.embedder = embedder
        self.store = store
        self._cache = cache_manager

        # Subscribe to memory events for cache invalidation
        if self._cache:
            event_bus.subscribe(EventType.MEMORY_CREATED, self._on_memory_created)
            event_bus.subscribe(EventType.MEMORY_SHARED, self._on_memory_created)

    @classmethod
    def from_env(
        cls,
        embedding_provider: EmbeddingProvider = EmbeddingProvider.OPENAI,
        dotenv_path: Optional[str] = None,
    ) -> "MemoryManager":
        """
        Create MemoryManager from environment variables.

        Args:
            embedding_provider: Provider for embeddings.
            dotenv_path: Optional .env file path.

        Returns:
            Configured MemoryManager.
        """
        embedder = EmbeddingService.from_env(embedding_provider, dotenv_path)
        store = VectorStore.from_env(dotenv_path)

        # Initialize cache if available
        cache_manager = None
        if CACHE_AVAILABLE:
            try:
                cache_manager = CacheManager.from_env(dotenv_path)
                if not cache_manager.is_enabled():
                    cache_manager = None
            except Exception:
                # Cache initialization failed, continue without it
                cache_manager = None

        return cls(embedder, store, cache_manager)

    # =========================================================================
    # AGENT MEMORY OPERATIONS
    # =========================================================================

    async def remember(
        self,
        agent_id: int,
        content: str,
        memory_type: str = "fact",
        key: Optional[str] = None,
        tags: Optional[List[str]] = None,
        importance: float = 0.5,
        source_type: Optional[str] = None,
        source_id: Optional[int] = None,
        scope: str = "agent",
        scope_id: Optional[int] = None,
        use_cache: bool = True,
    ) -> int:
        """
        Store a memory for an agent.

        Args:
            agent_id: Agent ID.
            content: Memory content to store.
            memory_type: Type (fact, preference, context, decision, error, feedback, learning).
            key: Optional key (auto-generated if not provided).
            tags: Optional tags for filtering.
            importance: Importance score (0-1).
            source_type: Source of memory (conversation, task, etc.)
            source_id: Source ID.
            scope: Memory scope (agent, circle, project, global). Default: agent.
            scope_id: Scope ID (circle_id for circle scope, project_id for project scope, etc.).
            use_cache: Use embedding cache.

        Returns:
            ID of created memory.
        """
        # Generate embedding
        embedding = await self.embedder.embed(content, use_cache=use_cache)

        # Generate key if not provided
        if key is None:
            key = hashlib.sha256(content.encode()).hexdigest()[:16]

        # Store memory
        memory_id = self.store.add_memory(
            agent_id=agent_id,
            key=key,
            value=content,
            embedding=embedding,
            memory_type=memory_type,
            scope=scope,
            scope_id=scope_id,
            tags=tags,
            importance=importance,
            source_type=source_type,
            source_id=source_id,
        )

        # Invalidate RAG cache for this agent (memory just changed)
        if self._cache:
            self._cache.invalidate_rag_results(agent_id)

        # Publish event if memory is shared (circle/project scope)
        if scope in ("circle", "project"):
            await event_bus.publish(Event(
                type=EventType.MEMORY_SHARED,
                data={
                    "memory_id": memory_id,
                    "content": content,
                    "memory_type": memory_type,
                    "scope": scope,
                    "scope_id": scope_id,
                    "importance": importance,
                },
                source_agent_id=agent_id,
                circle_id=scope_id if scope == "circle" else None,
                project_id=scope_id if scope == "project" else None,
            ))
        else:
            # Publish generic memory created event
            await event_bus.publish(Event(
                type=EventType.MEMORY_CREATED,
                data={
                    "memory_id": memory_id,
                    "memory_type": memory_type,
                    "importance": importance,
                },
                source_agent_id=agent_id,
            ))

        return memory_id

    async def recall(
        self,
        agent_id: int,
        query: str,
        memory_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10,
        threshold: float = 0.7,
        update_access: bool = True,
    ) -> List[RecallResult]:
        """
        Recall relevant memories for an agent.

        Args:
            agent_id: Agent ID.
            query: Query text to find similar memories.
            memory_type: Filter by memory type.
            tags: Filter by tags.
            limit: Maximum results.
            threshold: Minimum similarity threshold.
            update_access: Update access timestamps.

        Returns:
            List of relevant memories.
        """
        # Check cache first (only for unfiltered queries)
        if self._cache and not memory_type and not tags:
            cached = self._cache.get_rag_results(agent_id, query)
            if cached is not None:
                # Return cached results
                return [RecallResult(**r) for r in cached]

        # Generate query embedding
        query_embedding = await self.embedder.embed(query, use_cache=True)

        # Search memories
        results = self.store.search_memories(
            query_embedding=query_embedding,
            agent_id=agent_id,
            memory_type=memory_type,
            tags=tags,
            limit=limit,
            threshold=threshold,
        )

        # Update access if requested
        if update_access:
            for result in results:
                self.store.update_memory_access(result.id)

        # Convert to RecallResult
        recall_results = [
            RecallResult(
                id=r.id,
                key=r.key,
                value=r.value,
                memory_type=r.memory_type,
                similarity=r.similarity,
                importance=r.importance,
            )
            for r in results
        ]

        # Cache results (only for unfiltered queries)
        if self._cache and not memory_type and not tags:
            serializable = [
                {
                    "id": r.id,
                    "key": r.key,
                    "value": r.value,
                    "memory_type": r.memory_type,
                    "similarity": r.similarity,
                    "importance": r.importance,
                }
                for r in recall_results
            ]
            self._cache.set_rag_results(agent_id, query, serializable)

        return recall_results

    async def forget(self, memory_id: int, agent_id: Optional[int] = None) -> bool:
        """
        Forget (soft delete) a memory.

        Args:
            memory_id: Memory ID.
            agent_id: Optional agent ID for cache invalidation.

        Returns:
            True if forgotten.
        """
        result = self.store.delete_memory(memory_id)

        # Invalidate cache if agent_id provided
        if result and agent_id and self._cache:
            self._cache.invalidate_rag_results(agent_id)

        return result

    def invalidate_cache(self, agent_id: int) -> None:
        """
        Invalidate RAG cache for an agent.

        Called when agent's memories change.

        Args:
            agent_id: Agent ID to invalidate cache for.
        """
        if self._cache:
            self._cache.invalidate_rag_results(agent_id)

    async def _on_memory_created(self, event: Event) -> None:
        """
        Event handler for memory creation.

        Invalidates RAG cache for the affected agent.

        Args:
            event: Memory creation event.
        """
        # Extract agent_id from event
        agent_id = event.source_agent_id
        if agent_id and self._cache:
            self._cache.invalidate_rag_results(agent_id)

    # =========================================================================
    # KNOWLEDGE BASE OPERATIONS
    # =========================================================================

    async def add_knowledge(
        self,
        title: str,
        content: str,
        category: Optional[str] = None,
        project_id: Optional[int] = None,
        circle_id: Optional[int] = None,
        is_global: bool = False,
        tags: Optional[List[str]] = None,
        source_url: Optional[str] = None,
        author_agent_id: Optional[int] = None,
        use_cache: bool = True,
    ) -> int:
        """
        Add entry to knowledge base.

        Args:
            title: Knowledge title.
            content: Knowledge content.
            category: Category (docs, best_practice, decision, faq).
            project_id: Associated project.
            circle_id: Associated circle.
            is_global: Globally accessible.
            tags: Optional tags.
            source_url: Source URL.
            author_agent_id: Author agent.
            use_cache: Use embedding cache.

        Returns:
            ID of created entry.
        """
        # Generate embedding from title + content
        text = f"{title}\n\n{content}"
        embedding = await self.embedder.embed(text, use_cache=use_cache)

        return self.store.add_knowledge(
            title=title,
            content=content,
            embedding=embedding,
            category=category,
            project_id=project_id,
            circle_id=circle_id,
            is_global=is_global,
            tags=tags,
            source_url=source_url,
            author_agent_id=author_agent_id,
        )

    async def search_knowledge(
        self,
        query: str,
        project_id: Optional[int] = None,
        circle_id: Optional[int] = None,
        category: Optional[str] = None,
        include_global: bool = True,
        limit: int = 10,
        threshold: float = 0.7,
    ) -> List[KnowledgeResult]:
        """
        Search knowledge base.

        Args:
            query: Search query.
            project_id: Filter by project.
            circle_id: Filter by circle.
            category: Filter by category.
            include_global: Include global knowledge.
            limit: Maximum results.
            threshold: Minimum similarity.

        Returns:
            List of relevant knowledge entries.
        """
        query_embedding = await self.embedder.embed(query, use_cache=True)

        return self.store.search_knowledge(
            query_embedding=query_embedding,
            project_id=project_id,
            circle_id=circle_id,
            category=category,
            include_global=include_global,
            limit=limit,
            threshold=threshold,
        )

    async def list_knowledge(
        self,
        category: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[KnowledgeResult]:
        """
        List knowledge base entries with pagination.

        Args:
            category: Filter by category.
            limit: Maximum results.
            offset: Pagination offset.

        Returns:
            List of knowledge entries.
        """
        return self.store.list_knowledge(
            category=category,
            limit=limit,
            offset=offset,
        )

    async def count_knowledge(
        self,
        category: Optional[str] = None,
    ) -> int:
        """
        Count knowledge base entries.

        Args:
            category: Filter by category.

        Returns:
            Total count.
        """
        return self.store.count_knowledge(category=category)

    async def get_knowledge_stats(self) -> Dict[str, Any]:
        """
        Get knowledge base statistics.

        Returns:
            Stats dict with total, by_category, and recent entries.
        """
        return self.store.get_knowledge_stats()

    # =========================================================================
    # BATCH OPERATIONS
    # =========================================================================

    async def remember_batch(
        self,
        agent_id: int,
        memories: List[Dict[str, Any]],
    ) -> List[int]:
        """
        Store multiple memories at once.

        Args:
            agent_id: Agent ID.
            memories: List of memory dicts with keys:
                - content (required)
                - memory_type (optional)
                - key (optional)
                - tags (optional)
                - importance (optional)

        Returns:
            List of created memory IDs.
        """
        # Extract contents for batch embedding
        contents = [m["content"] for m in memories]
        embeddings = await self.embedder.embed_batch(contents, use_cache=True)

        # Store each memory
        ids = []
        for memory, embedding in zip(memories, embeddings):
            key = memory.get("key") or hashlib.sha256(memory["content"].encode()).hexdigest()[:16]

            memory_id = self.store.add_memory(
                agent_id=agent_id,
                key=key,
                value=memory["content"],
                embedding=embedding,
                memory_type=memory.get("memory_type", "fact"),
                tags=memory.get("tags"),
                importance=memory.get("importance", 0.5),
            )
            ids.append(memory_id)

        return ids

    # =========================================================================
    # UTILITIES
    # =========================================================================

    def get_stats(self, agent_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get memory statistics.

        Args:
            agent_id: Optional agent filter.

        Returns:
            Statistics dict.
        """
        memory_stats = self.store.get_memory_stats(agent_id)
        cache_stats = self.embedder.cache_stats()

        return {
            "memories": memory_stats,
            "embedding_cache": cache_stats,
        }

    def close(self) -> None:
        """Close connections."""
        self.store.close()

    def __enter__(self) -> "MemoryManager":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"MemoryManager(embedder={self.embedder}, store={self.store})"
