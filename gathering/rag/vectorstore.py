"""
VectorStore for GatheRing RAG.

Provides vector storage and similarity search using PostgreSQL + pgvector.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any

# Import pycopg (local PostgreSQL wrapper)
try:
    from pycopg import Database
except ImportError:
    Database = None


@dataclass
class MemoryResult:
    """Result from memory search."""
    id: int
    key: str
    value: str
    memory_type: str
    similarity: float
    importance: float
    created_at: Optional[datetime] = None
    tags: Optional[List[str]] = None


@dataclass
class KnowledgeResult:
    """Result from knowledge base search."""
    id: int
    title: str
    content: str
    category: Optional[str]
    similarity: float
    tags: Optional[List[str]] = None


class VectorStore:
    """
    Vector storage and search interface for RAG.

    Uses PostgreSQL with pgvector for efficient similarity search.

    Example:
        store = VectorStore.from_env()

        # Add memory with embedding
        await store.add_memory(
            agent_id=1,
            key="user_preference",
            value="User prefers dark mode",
            embedding=embedding_vector,
            memory_type="preference",
        )

        # Search similar memories
        results = await store.search_memories(
            agent_id=1,
            query_embedding=query_vector,
            limit=5,
            threshold=0.7,
        )

        # Add to knowledge base
        await store.add_knowledge(
            title="API Documentation",
            content="...",
            embedding=embedding_vector,
            category="docs",
        )
    """

    def __init__(self, db: Database):
        """
        Initialize VectorStore.

        Args:
            db: PicoPG Database instance.
        """
        self.db = db

    @classmethod
    def from_env(cls, dotenv_path: Optional[str] = None) -> "VectorStore":
        """
        Create VectorStore from environment variables.

        Args:
            dotenv_path: Optional path to .env file.

        Returns:
            Configured VectorStore.
        """
        if Database is None:
            raise ImportError("pycopg is required for VectorStore")

        db = Database.from_env(dotenv_path)
        return cls(db)

    @classmethod
    def from_url(cls, url: str) -> "VectorStore":
        """
        Create VectorStore from database URL.

        Args:
            url: PostgreSQL connection URL.

        Returns:
            Configured VectorStore.
        """
        if Database is None:
            raise ImportError("pycopg is required for VectorStore")

        db = Database.from_url(url)
        return cls(db)

    # =========================================================================
    # MEMORY OPERATIONS
    # =========================================================================

    def add_memory(
        self,
        agent_id: int,
        key: str,
        value: str,
        embedding: List[float],
        memory_type: str = "fact",
        scope: str = "agent",
        scope_id: Optional[int] = None,
        tags: Optional[List[str]] = None,
        importance: float = 0.5,
        source_type: Optional[str] = None,
        source_id: Optional[int] = None,
    ) -> int:
        """
        Add a memory with embedding.

        Args:
            agent_id: Agent ID who owns this memory.
            key: Memory key/identifier.
            value: Memory content.
            embedding: Vector embedding.
            memory_type: Type of memory (fact, preference, etc.)
            scope: Memory scope (agent, circle, project, global).
            scope_id: Scope ID (defaults to agent_id for agent scope, or circle_id/project_id for other scopes).
            tags: Optional tags for filtering.
            importance: Importance score (0-1).
            source_type: Source of this memory.
            source_id: Source ID.

        Returns:
            ID of created memory.
        """
        tags_array = tags or []
        embedding_str = f"[{','.join(map(str, embedding))}]"

        # Default scope_id to agent_id if not provided
        actual_scope_id = scope_id if scope_id is not None else agent_id

        result = self.db.execute("""
            INSERT INTO memory.memories (
                agent_id, scope, scope_id, memory_type, key, value,
                embedding, tags, importance, source_type, source_id
            ) VALUES (
                %s, %s::memory_scope, %s, %s::memory_type, %s, %s,
                %s::vector, %s, %s, %s, %s
            )
            RETURNING id
        """, [
            agent_id, scope, actual_scope_id, memory_type, key, value,
            embedding_str, tags_array, importance, source_type, source_id
        ])

        return result[0]["id"]

    def search_memories(
        self,
        query_embedding: List[float],
        agent_id: Optional[int] = None,
        scope: Optional[str] = None,
        memory_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10,
        threshold: float = 0.7,
    ) -> List[MemoryResult]:
        """
        Search memories by semantic similarity.

        Args:
            query_embedding: Query vector.
            agent_id: Filter by agent ID.
            scope: Filter by scope.
            memory_type: Filter by memory type.
            tags: Filter by tags (any match).
            limit: Maximum results to return.
            threshold: Minimum similarity threshold.

        Returns:
            List of matching memories with similarity scores.
        """
        embedding_str = f"[{','.join(map(str, query_embedding))}]"

        # Build query with filters
        conditions = ["is_active = true", "embedding IS NOT NULL"]
        params: List[Any] = []

        if agent_id is not None:
            conditions.append("agent_id = %s")
            params.append(agent_id)

        if scope is not None:
            conditions.append("scope = %s::memory_scope")
            params.append(scope)

        if memory_type is not None:
            conditions.append("memory_type = %s::memory_type")
            params.append(memory_type)

        if tags:
            conditions.append("tags && %s")
            params.append(tags)

        where_clause = " AND ".join(conditions)

        # Build final params list:
        # 1. embedding_str for SELECT similarity
        # 2. filter params (agent_id, scope, memory_type, tags)
        # 3. embedding_str for threshold check
        # 4. threshold value
        # 5. embedding_str for ORDER BY
        # 6. limit
        final_params = [embedding_str] + params + [embedding_str, threshold, embedding_str, limit]

        results = self.db.execute(f"""
            SELECT
                id,
                key,
                value,
                memory_type,
                importance,
                tags,
                created_at,
                1 - (embedding <=> %s::vector) AS similarity
            FROM memory.memories
            WHERE {where_clause}
                AND (1 - (embedding <=> %s::vector)) >= %s
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, final_params)

        return [
            MemoryResult(
                id=r["id"],
                key=r["key"],
                value=r["value"],
                memory_type=r["memory_type"],
                similarity=r["similarity"],
                importance=r["importance"],
                created_at=r["created_at"],
                tags=r["tags"],
            )
            for r in results
        ]

    def update_memory_access(self, memory_id: int) -> None:
        """
        Update memory access timestamp and count.

        Args:
            memory_id: Memory ID.
        """
        self.db.execute("""
            UPDATE memory.memories
            SET access_count = access_count + 1,
                last_accessed_at = NOW()
            WHERE id = %s
        """, [memory_id])

    def delete_memory(self, memory_id: int) -> bool:
        """
        Soft delete a memory.

        Args:
            memory_id: Memory ID.

        Returns:
            True if deleted.
        """
        self.db.execute("""
            UPDATE memory.memories
            SET is_active = false
            WHERE id = %s
        """, [memory_id])
        return True

    # =========================================================================
    # KNOWLEDGE BASE OPERATIONS
    # =========================================================================

    def add_knowledge(
        self,
        title: str,
        content: str,
        embedding: List[float],
        category: Optional[str] = None,
        project_id: Optional[int] = None,
        circle_id: Optional[int] = None,
        is_global: bool = False,
        tags: Optional[List[str]] = None,
        source_url: Optional[str] = None,
        author_agent_id: Optional[int] = None,
    ) -> int:
        """
        Add knowledge base entry.

        Args:
            title: Knowledge title.
            content: Knowledge content.
            embedding: Vector embedding.
            category: Category (docs, best_practice, decision, faq).
            project_id: Associated project ID.
            circle_id: Associated circle ID.
            is_global: Whether globally accessible.
            tags: Optional tags.
            source_url: Source URL.
            author_agent_id: Author agent ID.

        Returns:
            ID of created entry.
        """
        tags_array = tags or []
        embedding_str = f"[{','.join(map(str, embedding))}]"

        result = self.db.execute("""
            INSERT INTO memory.knowledge_base (
                title, content, embedding, category,
                project_id, circle_id, is_global,
                tags, source_url, author_agent_id
            ) VALUES (
                %s, %s, %s::vector, %s,
                %s, %s, %s,
                %s, %s, %s
            )
            RETURNING id
        """, [
            title, content, embedding_str, category,
            project_id, circle_id, is_global,
            tags_array, source_url, author_agent_id
        ])

        return result[0]["id"]

    def search_knowledge(
        self,
        query_embedding: List[float],
        project_id: Optional[int] = None,
        circle_id: Optional[int] = None,
        category: Optional[str] = None,
        include_global: bool = True,
        limit: int = 10,
        threshold: float = 0.7,
    ) -> List[KnowledgeResult]:
        """
        Search knowledge base by semantic similarity.

        Args:
            query_embedding: Query vector.
            project_id: Filter by project.
            circle_id: Filter by circle.
            category: Filter by category.
            include_global: Include global knowledge.
            limit: Maximum results.
            threshold: Minimum similarity.

        Returns:
            List of matching knowledge entries.
        """
        embedding_str = f"[{','.join(map(str, query_embedding))}]"

        # Build scope conditions
        scope_conditions = []
        params: List[Any] = []

        if project_id is not None:
            scope_conditions.append("project_id = %s")
            params.append(project_id)

        if circle_id is not None:
            scope_conditions.append("circle_id = %s")
            params.append(circle_id)

        if include_global:
            scope_conditions.append("is_global = true")

        scope_clause = " OR ".join(scope_conditions) if scope_conditions else "true"

        # Category filter
        category_clause = ""
        if category is not None:
            category_clause = "AND category = %s"
            params.append(category)

        params.extend([embedding_str, threshold, embedding_str, limit])

        results = self.db.execute(f"""
            SELECT
                id,
                title,
                content,
                category,
                tags,
                1 - (embedding <=> %s::vector) AS similarity
            FROM memory.knowledge_base
            WHERE is_active = true
                AND embedding IS NOT NULL
                AND ({scope_clause})
                {category_clause}
                AND (1 - (embedding <=> %s::vector)) >= %s
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, params[:-4] + [embedding_str, embedding_str, threshold, embedding_str, limit])

        return [
            KnowledgeResult(
                id=r["id"],
                title=r["title"],
                content=r["content"],
                category=r["category"],
                similarity=r["similarity"],
                tags=r["tags"],
            )
            for r in results
        ]

    def list_knowledge(
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
        params: List[Any] = []
        category_clause = ""
        if category:
            category_clause = "AND category = %s"
            params.append(category)

        params.extend([limit, offset])

        results = self.db.execute(f"""
            SELECT
                id,
                title,
                content,
                category,
                tags,
                created_at
            FROM memory.knowledge_base
            WHERE is_active = true
            {category_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """, params)

        return [
            KnowledgeResult(
                id=r["id"],
                title=r["title"],
                content=r["content"],
                category=r["category"],
                similarity=0.0,
                tags=r["tags"],
            )
            for r in results
        ]

    def count_knowledge(self, category: Optional[str] = None) -> int:
        """
        Count knowledge base entries.

        Args:
            category: Filter by category.

        Returns:
            Total count.
        """
        params: List[Any] = []
        category_clause = ""
        if category:
            category_clause = "AND category = %s"
            params.append(category)

        result = self.db.execute(f"""
            SELECT COUNT(*) AS count
            FROM memory.knowledge_base
            WHERE is_active = true
            {category_clause}
        """, params)

        return result[0]["count"] if result else 0

    def get_knowledge_stats(self) -> Dict[str, Any]:
        """
        Get knowledge base statistics.

        Returns:
            Stats dict with total, by_category, and recent entries.
        """
        # Total count
        total_result = self.db.execute("""
            SELECT COUNT(*) AS count
            FROM memory.knowledge_base
            WHERE is_active = true
        """)
        total = total_result[0]["count"] if total_result else 0

        # By category
        category_result = self.db.execute("""
            SELECT category, COUNT(*) AS count
            FROM memory.knowledge_base
            WHERE is_active = true
            GROUP BY category
        """)
        by_category = {r["category"] or "uncategorized": r["count"] for r in category_result}

        # Recent entries
        recent_result = self.db.execute("""
            SELECT id, title, content, category, tags
            FROM memory.knowledge_base
            WHERE is_active = true
            ORDER BY created_at DESC
            LIMIT 5
        """)
        recent = [
            KnowledgeResult(
                id=r["id"],
                title=r["title"],
                content=r["content"],
                category=r["category"],
                similarity=0.0,
                tags=r["tags"],
            )
            for r in recent_result
        ]

        return {
            "total": total,
            "by_category": by_category,
            "recent": recent,
        }

    # =========================================================================
    # EMBEDDING CACHE
    # =========================================================================

    def get_cached_embedding(self, content_hash: str) -> Optional[List[float]]:
        """
        Get cached embedding by content hash.

        Args:
            content_hash: SHA256 hash of content.

        Returns:
            Embedding if cached, None otherwise.
        """
        result = self.db.execute("""
            SELECT embedding
            FROM memory.embeddings_cache
            WHERE content_hash = %s
        """, [content_hash])

        if result:
            # Update usage
            self.db.execute("""
                UPDATE memory.embeddings_cache
                SET usage_count = usage_count + 1,
                    last_used_at = NOW()
                WHERE content_hash = %s
            """, [content_hash])
            return result[0]["embedding"]

        return None

    def cache_embedding(
        self,
        content_hash: str,
        embedding: List[float],
        model: str,
        content_preview: Optional[str] = None,
    ) -> None:
        """
        Cache an embedding.

        Args:
            content_hash: SHA256 hash of content.
            embedding: Embedding vector.
            model: Model used to generate embedding.
            content_preview: Optional preview of content.
        """
        embedding_str = f"[{','.join(map(str, embedding))}]"

        self.db.execute("""
            INSERT INTO memory.embeddings_cache (
                content_hash, embedding, model, dimension, content_preview
            ) VALUES (
                %s, %s::vector, %s, %s, %s
            )
            ON CONFLICT (content_hash) DO UPDATE SET
                usage_count = memory.embeddings_cache.usage_count + 1,
                last_used_at = NOW()
        """, [content_hash, embedding_str, model, len(embedding), content_preview])

    # =========================================================================
    # UTILITIES
    # =========================================================================

    def get_memory_stats(self, agent_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get memory statistics.

        Args:
            agent_id: Optional agent ID filter.

        Returns:
            Statistics dict.
        """
        where_clause = "WHERE agent_id = %s" if agent_id else ""
        params = [agent_id] if agent_id else []

        result = self.db.execute(f"""
            SELECT
                COUNT(*) AS total_memories,
                COUNT(*) FILTER (WHERE is_active) AS active_memories,
                COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS embedded_memories,
                AVG(importance) AS avg_importance
            FROM memory.memories
            {where_clause}
        """, params)

        return result[0] if result else {}

    def close(self) -> None:
        """Close database connection."""
        self.db.close()

    def __enter__(self) -> "VectorStore":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"VectorStore(db={self.db})"
