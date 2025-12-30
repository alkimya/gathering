"""
Tests for GatheRing RAG module.

Tests embedding service, vector store, and memory manager.
"""

import hashlib
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Skip tests if dependencies not available
pytest.importorskip("httpx")


class TestEmbeddingService:
    """Tests for EmbeddingService."""

    def test_init_requires_api_key(self):
        """Test that OpenAI provider requires API key."""
        from gathering.rag.embeddings import EmbeddingService, EmbeddingProvider

        with pytest.raises(ValueError, match="API key required"):
            EmbeddingService(provider=EmbeddingProvider.OPENAI, api_key=None)

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        from gathering.rag.embeddings import EmbeddingService, EmbeddingProvider

        service = EmbeddingService(
            provider=EmbeddingProvider.OPENAI,
            api_key="test-key",
        )
        assert service.provider == EmbeddingProvider.OPENAI
        assert service.api_key == "test-key"
        assert service.model == "text-embedding-3-small"

    def test_dimension_property(self):
        """Test dimension property returns correct value."""
        from gathering.rag.embeddings import EmbeddingService, EmbeddingProvider

        service = EmbeddingService(
            provider=EmbeddingProvider.OPENAI,
            api_key="test-key",
            model="text-embedding-3-small",
        )
        assert service.dimension == 1536

        service_large = EmbeddingService(
            provider=EmbeddingProvider.OPENAI,
            api_key="test-key",
            model="text-embedding-3-large",
        )
        assert service_large.dimension == 3072

    def test_cache_key_generation(self):
        """Test cache key is deterministic."""
        from gathering.rag.embeddings import EmbeddingService, EmbeddingProvider

        service = EmbeddingService(
            provider=EmbeddingProvider.OPENAI,
            api_key="test-key",
        )

        key1 = service._cache_key("Hello")
        key2 = service._cache_key("Hello")
        key3 = service._cache_key("World")

        assert key1 == key2
        assert key1 != key3

    def test_clear_cache(self):
        """Test cache clearing."""
        from gathering.rag.embeddings import EmbeddingService, EmbeddingProvider

        service = EmbeddingService(
            provider=EmbeddingProvider.OPENAI,
            api_key="test-key",
        )

        # Add to cache manually
        service._cache["test"] = [0.1, 0.2, 0.3]
        assert len(service._cache) == 1

        count = service.clear_cache()
        assert count == 1
        assert len(service._cache) == 0

    def test_cache_stats(self):
        """Test cache statistics."""
        from gathering.rag.embeddings import EmbeddingService, EmbeddingProvider

        service = EmbeddingService(
            provider=EmbeddingProvider.OPENAI,
            api_key="test-key",
        )

        service._cache["test1"] = [0.1]
        service._cache["test2"] = [0.2]

        stats = service.cache_stats()
        assert stats["entries"] == 2
        assert stats["model"] == "text-embedding-3-small"
        assert stats["provider"] == "openai"

    @pytest.mark.asyncio
    async def test_embed_uses_cache(self):
        """Test that embed uses cache when available."""
        from gathering.rag.embeddings import EmbeddingService, EmbeddingProvider

        service = EmbeddingService(
            provider=EmbeddingProvider.OPENAI,
            api_key="test-key",
        )

        # Pre-populate cache
        cache_key = service._cache_key("Hello")
        cached_embedding = [0.1, 0.2, 0.3]
        service._cache[cache_key] = cached_embedding

        # Should return cached value without API call
        result = await service.embed("Hello", use_cache=True)
        assert result == cached_embedding

    @pytest.mark.asyncio
    async def test_embed_skips_cache(self):
        """Test that embed can skip cache."""
        from gathering.rag.embeddings import EmbeddingService, EmbeddingProvider

        service = EmbeddingService(
            provider=EmbeddingProvider.OPENAI,
            api_key="test-key",
        )

        # Pre-populate cache
        cache_key = service._cache_key("Hello")
        service._cache[cache_key] = [0.1, 0.2, 0.3]

        # Mock API call
        mock_embedding = [0.4, 0.5, 0.6]
        with patch.object(service, "_generate_embeddings", new_callable=AsyncMock) as mock:
            mock.return_value = [mock_embedding]

            result = await service.embed("Hello", use_cache=False)

            mock.assert_called_once_with(["Hello"])
            assert result == mock_embedding

    @pytest.mark.asyncio
    async def test_embed_batch(self):
        """Test batch embedding."""
        from gathering.rag.embeddings import EmbeddingService, EmbeddingProvider

        service = EmbeddingService(
            provider=EmbeddingProvider.OPENAI,
            api_key="test-key",
        )

        mock_embeddings = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]

        with patch.object(service, "_generate_embeddings", new_callable=AsyncMock) as mock:
            mock.return_value = mock_embeddings

            result = await service.embed_batch(["a", "b", "c"], use_cache=False)

            assert len(result) == 3
            assert result == mock_embeddings

    @pytest.mark.asyncio
    async def test_embed_batch_uses_cache(self):
        """Test batch embedding uses cache for known texts."""
        from gathering.rag.embeddings import EmbeddingService, EmbeddingProvider

        service = EmbeddingService(
            provider=EmbeddingProvider.OPENAI,
            api_key="test-key",
        )

        # Cache one embedding
        cache_key = service._cache_key("cached")
        service._cache[cache_key] = [0.9, 0.9]

        with patch.object(service, "_generate_embeddings", new_callable=AsyncMock) as mock:
            mock.return_value = [[0.1, 0.2], [0.3, 0.4]]

            result = await service.embed_batch(["new1", "cached", "new2"], use_cache=True)

            # Only non-cached texts should be embedded
            mock.assert_called_once_with(["new1", "new2"])

            # Result should include cached value
            assert result[1] == [0.9, 0.9]

    def test_repr(self):
        """Test string representation."""
        from gathering.rag.embeddings import EmbeddingService, EmbeddingProvider

        service = EmbeddingService(
            provider=EmbeddingProvider.OPENAI,
            api_key="test-key",
        )
        assert "openai" in repr(service)
        assert "text-embedding-3-small" in repr(service)


class TestVectorStoreDataclasses:
    """Tests for VectorStore dataclasses."""

    def test_memory_result(self):
        """Test MemoryResult dataclass."""
        from gathering.rag.vectorstore import MemoryResult

        result = MemoryResult(
            id=1,
            key="test",
            value="test value",
            memory_type="fact",
            similarity=0.95,
            importance=0.5,
        )

        assert result.id == 1
        assert result.key == "test"
        assert result.similarity == 0.95

    def test_knowledge_result(self):
        """Test KnowledgeResult dataclass."""
        from gathering.rag.vectorstore import KnowledgeResult

        result = KnowledgeResult(
            id=1,
            title="Test",
            content="Test content",
            category="docs",
            similarity=0.85,
        )

        assert result.id == 1
        assert result.title == "Test"
        assert result.similarity == 0.85


class TestMemoryManager:
    """Tests for MemoryManager."""

    @pytest.fixture
    def mock_embedder(self):
        """Create mock embedding service."""
        embedder = MagicMock()
        embedder.embed = AsyncMock(return_value=[0.1, 0.2, 0.3] * 512)
        embedder.embed_batch = AsyncMock(return_value=[[0.1] * 1536, [0.2] * 1536])
        embedder.cache_stats.return_value = {"entries": 0}
        return embedder

    @pytest.fixture
    def mock_store(self):
        """Create mock vector store."""
        store = MagicMock()
        store.add_memory.return_value = 1
        store.add_knowledge.return_value = 1
        store.get_memory_stats.return_value = {"total": 10}
        return store

    @pytest.fixture
    def manager(self, mock_embedder, mock_store):
        """Create MemoryManager with mocks."""
        from gathering.rag.memory_manager import MemoryManager
        return MemoryManager(mock_embedder, mock_store)

    @pytest.mark.asyncio
    async def test_remember(self, manager, mock_embedder, mock_store):
        """Test remembering a memory."""
        memory_id = await manager.remember(
            agent_id=1,
            content="User prefers dark mode",
            memory_type="preference",
            key="theme",
        )

        assert memory_id == 1
        mock_embedder.embed.assert_called_once()
        mock_store.add_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_remember_generates_key(self, manager):
        """Test that remember generates key if not provided."""
        await manager.remember(
            agent_id=1,
            content="Some content",
        )

        # Key should be hash of content
        call_args = manager.store.add_memory.call_args
        key = call_args.kwargs.get("key") or call_args[1].get("key")
        assert key is not None
        assert len(key) == 16

    @pytest.mark.asyncio
    async def test_recall(self, manager, mock_embedder, mock_store):
        """Test recalling memories."""
        from gathering.rag.vectorstore import MemoryResult

        mock_store.search_memories.return_value = [
            MemoryResult(
                id=1,
                key="theme",
                value="User prefers dark mode",
                memory_type="preference",
                similarity=0.95,
                importance=0.5,
            )
        ]

        results = await manager.recall(
            agent_id=1,
            query="What are user preferences?",
        )

        assert len(results) == 1
        assert results[0].value == "User prefers dark mode"
        mock_embedder.embed.assert_called_once()
        mock_store.search_memories.assert_called_once()

    @pytest.mark.asyncio
    async def test_recall_updates_access(self, manager, mock_store):
        """Test that recall updates access timestamps."""
        from gathering.rag.vectorstore import MemoryResult

        mock_store.search_memories.return_value = [
            MemoryResult(id=1, key="k", value="v", memory_type="fact", similarity=0.9, importance=0.5),
            MemoryResult(id=2, key="k2", value="v2", memory_type="fact", similarity=0.8, importance=0.5),
        ]

        await manager.recall(agent_id=1, query="test", update_access=True)

        assert mock_store.update_memory_access.call_count == 2

    @pytest.mark.asyncio
    async def test_forget(self, manager, mock_store):
        """Test forgetting a memory."""
        mock_store.delete_memory.return_value = True

        result = await manager.forget(memory_id=1)

        assert result is True
        mock_store.delete_memory.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_add_knowledge(self, manager, mock_embedder, mock_store):
        """Test adding knowledge."""
        kb_id = await manager.add_knowledge(
            title="API Guide",
            content="How to use the API...",
            category="docs",
        )

        assert kb_id == 1
        mock_embedder.embed.assert_called_once()
        mock_store.add_knowledge.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_knowledge(self, manager, mock_embedder, mock_store):
        """Test searching knowledge."""
        from gathering.rag.vectorstore import KnowledgeResult

        mock_store.search_knowledge.return_value = [
            KnowledgeResult(
                id=1,
                title="API Guide",
                content="...",
                category="docs",
                similarity=0.9,
            )
        ]

        results = await manager.search_knowledge(query="How to use API?")

        assert len(results) == 1
        assert results[0].title == "API Guide"

    @pytest.mark.asyncio
    async def test_remember_batch(self, manager, mock_embedder, mock_store):
        """Test batch remember."""
        memories = [
            {"content": "Memory 1"},
            {"content": "Memory 2", "memory_type": "preference"},
        ]

        mock_store.add_memory.side_effect = [1, 2]

        ids = await manager.remember_batch(agent_id=1, memories=memories)

        assert ids == [1, 2]
        mock_embedder.embed_batch.assert_called_once()
        assert mock_store.add_memory.call_count == 2

    def test_get_stats(self, manager, mock_embedder, mock_store):
        """Test getting statistics."""
        stats = manager.get_stats(agent_id=1)

        assert "memories" in stats
        assert "embedding_cache" in stats


class TestIntegration:
    """Integration tests (require database)."""

    @pytest.fixture
    def db_available(self):
        """Check if database is available."""
        try:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent / "picopg"))
            from picopg import Database
            db = Database.from_env()
            db.execute("SELECT 1")
            return True
        except Exception:
            return False

    @pytest.mark.skipif(
        not os.environ.get("DATABASE_URL"),
        reason="DATABASE_URL not set"
    )
    def test_vectorstore_connection(self, db_available):
        """Test VectorStore can connect to database."""
        if not db_available:
            pytest.skip("Database not available")

        from gathering.rag.vectorstore import VectorStore

        store = VectorStore.from_env()
        stats = store.get_memory_stats()
        assert "total_memories" in stats


# Run with: pytest tests/test_rag.py -v
