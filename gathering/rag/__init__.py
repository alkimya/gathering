"""
RAG (Retrieval-Augmented Generation) module for GatheRing.

Provides embedding generation and vector search capabilities for semantic memory.

Components:
    - EmbeddingService: Generate embeddings via OpenAI or other providers
    - VectorStore: Interface for storing and searching vector embeddings
    - MemoryManager: High-level API for agent memory operations

Usage:
    from gathering.rag import EmbeddingService, VectorStore, MemoryManager

    # Create embedding service
    embedder = EmbeddingService.from_env()
    embedding = await embedder.embed("Hello, world!")

    # Use vector store
    store = VectorStore.from_env()
    await store.add_memory(agent_id=1, key="greeting", value="Hello!", embedding=embedding)
    results = await store.search(agent_id=1, query_embedding=embedding, limit=5)

    # High-level memory manager
    memory = MemoryManager.from_env()
    await memory.remember(agent_id=1, content="User prefers dark mode", memory_type="preference")
    memories = await memory.recall(agent_id=1, query="user preferences", limit=5)
"""

from gathering.rag.embeddings import EmbeddingService, EmbeddingProvider
from gathering.rag.vectorstore import VectorStore
from gathering.rag.memory_manager import MemoryManager

__all__ = [
    "EmbeddingService",
    "EmbeddingProvider",
    "VectorStore",
    "MemoryManager",
]
