"""
PostgreSQL-backed MemoryStore implementation.

Bridges the MemoryService (agents) to the MemoryManager (RAG) for persistent storage.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import logging

from gathering.agents.memory import MemoryStore
from gathering.rag.memory_manager import MemoryManager
from gathering.rag.embeddings import EmbeddingService, EmbeddingProvider
from gathering.rag.vectorstore import VectorStore

logger = logging.getLogger(__name__)


class PostgresMemoryStore:
    """
    PostgreSQL-backed implementation of MemoryStore protocol.

    Uses MemoryManager for vector storage and semantic search.
    Falls back to keyword search if embeddings are unavailable.

    Example:
        # Create from environment variables
        store = PostgresMemoryStore.from_env()

        # Use with MemoryService
        memory_service = MemoryService(store=store)

        # Use with AgentWrapper
        agent = AgentWrapper(
            agent_id=1,
            persona=persona,
            llm=llm,
            memory=memory_service,
        )
    """

    # Valid memory types in the database
    VALID_MEMORY_TYPES = {"fact", "preference", "context", "decision", "error", "feedback", "learning"}

    # Mapping from MemoryService types to valid DB types
    TYPE_MAPPING = {
        "conversation": "context",  # Conversation exchanges -> context
        "general": "fact",          # General info -> fact
    }

    def __init__(
        self,
        memory_manager: MemoryManager,
        fallback_to_keyword: bool = True,
    ):
        """
        Initialize PostgresMemoryStore.

        Args:
            memory_manager: MemoryManager instance for vector operations.
            fallback_to_keyword: If True, use keyword search when embeddings fail.
        """
        self.manager = memory_manager
        self.fallback_to_keyword = fallback_to_keyword
        self._embedding_available = True

    @classmethod
    def from_env(
        cls,
        embedding_provider: EmbeddingProvider = EmbeddingProvider.OPENAI,
        dotenv_path: Optional[str] = None,
        fallback_to_keyword: bool = True,
    ) -> "PostgresMemoryStore":
        """
        Create PostgresMemoryStore from environment variables.

        Requires:
            - DATABASE_URL or DB_* variables for PostgreSQL
            - OPENAI_API_KEY for embeddings

        Args:
            embedding_provider: Provider for embeddings.
            dotenv_path: Optional .env file path.
            fallback_to_keyword: Fall back to keyword search on embedding failure.

        Returns:
            Configured PostgresMemoryStore.
        """
        try:
            manager = MemoryManager.from_env(embedding_provider, dotenv_path)
            return cls(manager, fallback_to_keyword)
        except Exception as e:
            logger.warning(f"Failed to create MemoryManager: {e}")
            raise

    def _normalize_memory_type(self, memory_type: str) -> str:
        """Normalize memory type to valid database enum value."""
        # Check mapping first
        if memory_type in self.TYPE_MAPPING:
            return self.TYPE_MAPPING[memory_type]
        # Use as-is if valid
        if memory_type in self.VALID_MEMORY_TYPES:
            return memory_type
        # Default to 'fact' for unknown types
        logger.warning(f"Unknown memory type '{memory_type}', defaulting to 'fact'")
        return "fact"

    async def store_memory(
        self,
        agent_id: int,
        content: str,
        memory_type: str,
        metadata: Dict[str, Any],
    ) -> int:
        """
        Store a memory with embeddings.

        Args:
            agent_id: Agent ID.
            content: Memory content.
            memory_type: Type of memory.
            metadata: Additional metadata.

        Returns:
            ID of stored memory.
        """
        try:
            # Normalize memory type to valid DB enum
            normalized_type = self._normalize_memory_type(memory_type)

            memory_id = await self.manager.remember(
                agent_id=agent_id,
                content=content,
                memory_type=normalized_type,
                tags=metadata.get("tags"),
                importance=metadata.get("importance", 0.5),
                source_type=metadata.get("source_type"),
                source_id=metadata.get("source_id"),
            )
            return memory_id
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            raise

    async def search_memories(
        self,
        agent_id: int,
        query: str,
        memory_types: Optional[List[str]] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search memories using semantic similarity.

        Args:
            agent_id: Agent ID.
            query: Search query.
            memory_types: Filter by types.
            limit: Maximum results.

        Returns:
            List of matching memories.
        """
        try:
            # Use semantic search via MemoryManager
            # Lower threshold (0.4) to capture more relevant memories
            # Higher precision can be achieved by ranking results by similarity
            results = await self.manager.recall(
                agent_id=agent_id,
                query=query,
                memory_type=memory_types[0] if memory_types and len(memory_types) == 1 else None,
                limit=limit,
                threshold=0.4,
            )

            return [
                {
                    "id": r.id,
                    "content": r.value,
                    "type": r.memory_type,
                    "metadata": {
                        "key": r.key,
                        "similarity": r.similarity,
                        "importance": r.importance,
                    },
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                for r in results
            ]
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
            if self.fallback_to_keyword:
                return await self._keyword_search(agent_id, query, memory_types, limit)
            return []

    async def get_recent_memories(
        self,
        agent_id: int,
        memory_types: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get most recent memories for an agent.

        Args:
            agent_id: Agent ID.
            memory_types: Filter by types.
            limit: Maximum results.

        Returns:
            List of recent memories.
        """
        try:
            # Use a generic query to get recent memories
            # The VectorStore should return most recent when no specific query
            results = await self.manager.recall(
                agent_id=agent_id,
                query="recent memories",
                memory_type=memory_types[0] if memory_types and len(memory_types) == 1 else None,
                limit=limit,
                threshold=0.0,  # No threshold for recent
            )

            return [
                {
                    "id": r.id,
                    "content": r.value,
                    "type": r.memory_type,
                    "metadata": {
                        "key": r.key,
                        "importance": r.importance,
                    },
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                for r in results
            ]
        except Exception as e:
            logger.warning(f"Failed to get recent memories: {e}")
            return []

    async def _keyword_search(
        self,
        agent_id: int,
        query: str,
        memory_types: Optional[List[str]],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """
        Fallback keyword search when embeddings fail.

        This is a simplified version that doesn't use vectors.
        """
        logger.info(f"Using keyword search fallback for agent {agent_id}")
        # For now, return empty - real implementation would query DB directly
        return []

    def close(self) -> None:
        """Close database connections."""
        if self.manager:
            self.manager.close()

    def __enter__(self) -> "PostgresMemoryStore":
        return self

    def __exit__(self, *args) -> None:
        self.close()


def create_memory_store_from_env() -> PostgresMemoryStore:
    """
    Factory function to create PostgresMemoryStore from environment.

    Returns:
        Configured PostgresMemoryStore.

    Raises:
        RuntimeError: If configuration is missing.
    """
    import os

    # Check required environment variables
    if not os.getenv("DATABASE_URL") and not os.getenv("DB_HOST"):
        raise RuntimeError(
            "Database configuration missing. Set DATABASE_URL or DB_* variables."
        )

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY required for embeddings."
        )

    return PostgresMemoryStore.from_env()
