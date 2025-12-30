"""
Tests for PostgresMemoryStore.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from gathering.agents.postgres_store import PostgresMemoryStore


class TestPostgresMemoryStore:
    """Test PostgresMemoryStore functionality."""

    def test_valid_memory_types(self):
        """Test that valid memory types are defined."""
        assert "fact" in PostgresMemoryStore.VALID_MEMORY_TYPES
        assert "preference" in PostgresMemoryStore.VALID_MEMORY_TYPES
        assert "learning" in PostgresMemoryStore.VALID_MEMORY_TYPES
        assert "context" in PostgresMemoryStore.VALID_MEMORY_TYPES
        assert "decision" in PostgresMemoryStore.VALID_MEMORY_TYPES
        assert "error" in PostgresMemoryStore.VALID_MEMORY_TYPES
        assert "feedback" in PostgresMemoryStore.VALID_MEMORY_TYPES

    def test_type_mapping(self):
        """Test that type mappings are defined."""
        assert "conversation" in PostgresMemoryStore.TYPE_MAPPING
        assert PostgresMemoryStore.TYPE_MAPPING["conversation"] == "context"
        assert "general" in PostgresMemoryStore.TYPE_MAPPING
        assert PostgresMemoryStore.TYPE_MAPPING["general"] == "fact"

    def test_normalize_memory_type_valid(self):
        """Test normalizing valid memory types."""
        mock_manager = MagicMock()
        store = PostgresMemoryStore(mock_manager)

        assert store._normalize_memory_type("fact") == "fact"
        assert store._normalize_memory_type("learning") == "learning"
        assert store._normalize_memory_type("preference") == "preference"

    def test_normalize_memory_type_mapped(self):
        """Test normalizing mapped memory types."""
        mock_manager = MagicMock()
        store = PostgresMemoryStore(mock_manager)

        assert store._normalize_memory_type("conversation") == "context"
        assert store._normalize_memory_type("general") == "fact"

    def test_normalize_memory_type_unknown(self):
        """Test normalizing unknown memory types defaults to fact."""
        mock_manager = MagicMock()
        store = PostgresMemoryStore(mock_manager)

        assert store._normalize_memory_type("unknown_type") == "fact"
        assert store._normalize_memory_type("random") == "fact"

    @pytest.mark.asyncio
    async def test_store_memory(self):
        """Test storing a memory."""
        mock_manager = MagicMock()
        mock_manager.remember = AsyncMock(return_value=42)

        store = PostgresMemoryStore(mock_manager)

        memory_id = await store.store_memory(
            agent_id=1,
            content="Test content",
            memory_type="learning",
            metadata={"importance": 0.8},
        )

        assert memory_id == 42
        mock_manager.remember.assert_called_once_with(
            agent_id=1,
            content="Test content",
            memory_type="learning",
            tags=None,
            importance=0.8,
            source_type=None,
            source_id=None,
        )

    @pytest.mark.asyncio
    async def test_store_memory_normalizes_type(self):
        """Test that store_memory normalizes memory type."""
        mock_manager = MagicMock()
        mock_manager.remember = AsyncMock(return_value=1)

        store = PostgresMemoryStore(mock_manager)

        await store.store_memory(
            agent_id=1,
            content="Test",
            memory_type="conversation",  # Should be normalized to "context"
            metadata={},
        )

        # Check that "conversation" was normalized to "context"
        call_args = mock_manager.remember.call_args
        assert call_args.kwargs["memory_type"] == "context"

    @pytest.mark.asyncio
    async def test_search_memories(self):
        """Test searching memories."""
        from gathering.rag.memory_manager import RecallResult

        mock_manager = MagicMock()
        mock_manager.recall = AsyncMock(return_value=[
            RecallResult(
                id=1,
                key="key1",
                value="Test memory content",
                memory_type="fact",
                similarity=0.85,
                importance=0.7,
            ),
        ])

        store = PostgresMemoryStore(mock_manager)

        results = await store.search_memories(
            agent_id=1,
            query="test query",
            limit=5,
        )

        assert len(results) == 1
        assert results[0]["id"] == 1
        assert results[0]["content"] == "Test memory content"
        assert results[0]["type"] == "fact"

    @pytest.mark.asyncio
    async def test_search_memories_with_filter(self):
        """Test searching memories with type filter."""
        mock_manager = MagicMock()
        mock_manager.recall = AsyncMock(return_value=[])

        store = PostgresMemoryStore(mock_manager)

        await store.search_memories(
            agent_id=1,
            query="test",
            memory_types=["learning"],
            limit=10,
        )

        call_args = mock_manager.recall.call_args
        assert call_args.kwargs["memory_type"] == "learning"

    @pytest.mark.asyncio
    async def test_get_recent_memories(self):
        """Test getting recent memories."""
        from gathering.rag.memory_manager import RecallResult

        mock_manager = MagicMock()
        mock_manager.recall = AsyncMock(return_value=[
            RecallResult(
                id=1,
                key="key1",
                value="Recent memory",
                memory_type="fact",
                similarity=0.5,
                importance=0.6,
            ),
        ])

        store = PostgresMemoryStore(mock_manager)

        results = await store.get_recent_memories(
            agent_id=1,
            limit=10,
        )

        assert len(results) == 1
        assert results[0]["content"] == "Recent memory"

    def test_close(self):
        """Test closing the store."""
        mock_manager = MagicMock()
        store = PostgresMemoryStore(mock_manager)

        store.close()

        mock_manager.close.assert_called_once()

    def test_context_manager(self):
        """Test using store as context manager."""
        mock_manager = MagicMock()

        with PostgresMemoryStore(mock_manager) as store:
            assert store is not None

        mock_manager.close.assert_called_once()


class TestPostgresMemoryStoreIntegration:
    """Integration tests for PostgresMemoryStore."""

    @pytest.mark.asyncio
    async def test_search_fallback_on_error(self):
        """Test that search falls back to keyword search on error."""
        mock_manager = MagicMock()
        mock_manager.recall = AsyncMock(side_effect=Exception("Search failed"))

        store = PostgresMemoryStore(mock_manager, fallback_to_keyword=True)

        # Should not raise, returns empty list on fallback
        results = await store.search_memories(
            agent_id=1,
            query="test",
            limit=5,
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_store_memory_error_handling(self):
        """Test error handling when storing memory fails."""
        mock_manager = MagicMock()
        mock_manager.remember = AsyncMock(side_effect=Exception("Store failed"))

        store = PostgresMemoryStore(mock_manager)

        with pytest.raises(Exception) as exc_info:
            await store.store_memory(
                agent_id=1,
                content="Test",
                memory_type="fact",
                metadata={},
            )

        assert "Store failed" in str(exc_info.value)
