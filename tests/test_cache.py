"""
Tests for Redis Cache Manager.

Covers:
- CacheManager initialization and graceful degradation
- Embedding cache operations
- RAG results cache operations
- Circle context cache
- Cache invalidation
- Integration with MemoryManager
- Integration with EmbeddingService
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from gathering.cache import CacheManager, CacheConfig


class TestCacheConfig:
    """Test CacheConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = CacheConfig()
        assert config.host == "localhost"
        assert config.port == 6379
        assert config.db == 0
        assert config.password is None
        assert config.embedding_ttl == 86400
        assert config.rag_results_ttl == 300
        assert config.circle_context_ttl == 600
        assert config.enabled is True
        assert config.key_prefix == "gathering:"

    def test_custom_values(self):
        """Test custom configuration."""
        config = CacheConfig(
            host="redis.example.com",
            port=6380,
            db=1,
            password="secret",
            embedding_ttl=7200,
            enabled=False,
        )
        assert config.host == "redis.example.com"
        assert config.port == 6380
        assert config.db == 1
        assert config.password == "secret"
        assert config.embedding_ttl == 7200
        assert config.enabled is False


class TestCacheManagerInit:
    """Test CacheManager initialization."""

    @patch("gathering.cache.redis_manager.REDIS_AVAILABLE", False)
    def test_init_without_redis_library(self):
        """Test initialization when redis library not available."""
        config = CacheConfig()
        cache = CacheManager(config)

        assert cache.is_enabled() is False
        assert cache._client is None

    @patch("gathering.cache.redis_manager.REDIS_AVAILABLE", True)
    @patch("redis.Redis")
    def test_init_with_redis_connection_success(self, mock_redis_class):
        """Test successful Redis connection."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_redis_class.return_value = mock_client

        config = CacheConfig()
        cache = CacheManager(config)

        assert cache.is_enabled() is True
        assert cache._client == mock_client
        mock_redis_class.assert_called_once_with(
            host="localhost",
            port=6379,
            db=0,
            password=None,
            decode_responses=False,
        )
        mock_client.ping.assert_called_once()

    @patch("gathering.cache.redis_manager.REDIS_AVAILABLE", True)
    @patch("redis.Redis")
    def test_init_with_redis_connection_failure(self, mock_redis_class):
        """Test graceful degradation on Redis connection failure."""
        mock_client = Mock()
        mock_client.ping.side_effect = Exception("Connection failed")
        mock_redis_class.return_value = mock_client

        config = CacheConfig()
        cache = CacheManager(config)

        # Should degrade gracefully
        assert cache.is_enabled() is False
        assert cache._client is None

    def test_init_with_disabled_config(self):
        """Test initialization with cache disabled in config."""
        config = CacheConfig(enabled=False)
        cache = CacheManager(config)

        assert cache.is_enabled() is False


class TestGenericCacheOps:
    """Test generic cache operations (get, set, delete)."""

    def setup_method(self):
        """Setup mock cache for each test."""
        self.config = CacheConfig()
        self.cache = CacheManager(self.config)
        self.cache._enabled = True
        self.cache._client = Mock()

    def test_get_success(self):
        """Test successful cache get."""
        self.cache._client.get.return_value = b'{"value": "test"}'

        result = self.cache.get("test_key")

        assert result == {"value": "test"}
        self.cache._client.get.assert_called_once_with("test_key")

    def test_get_miss(self):
        """Test cache miss."""
        self.cache._client.get.return_value = None

        result = self.cache.get("test_key")

        assert result is None

    def test_get_when_disabled(self):
        """Test get when cache is disabled."""
        self.cache._enabled = False

        result = self.cache.get("test_key")

        assert result is None
        self.cache._client.get.assert_not_called()

    def test_get_with_error(self):
        """Test get with Redis error."""
        self.cache._client.get.side_effect = Exception("Redis error")

        result = self.cache.get("test_key")

        assert result is None

    def test_set_success(self):
        """Test successful cache set."""
        self.cache._client.setex.return_value = True

        result = self.cache.set("test_key", {"value": "test"}, ttl=300)

        assert result is True
        self.cache._client.setex.assert_called_once()

    def test_set_without_ttl(self):
        """Test cache set without TTL."""
        self.cache._client.set.return_value = True

        result = self.cache.set("test_key", {"value": "test"})

        assert result is True
        self.cache._client.set.assert_called_once()

    def test_set_when_disabled(self):
        """Test set when cache is disabled."""
        self.cache._enabled = False

        result = self.cache.set("test_key", {"value": "test"})

        assert result is False
        self.cache._client.set.assert_not_called()

    def test_delete_success(self):
        """Test successful cache delete."""
        self.cache._client.delete.return_value = 1

        result = self.cache.delete("test_key")

        assert result is True
        self.cache._client.delete.assert_called_once_with("test_key")

    def test_delete_pattern(self):
        """Test delete by pattern."""
        self.cache._client.keys.return_value = [b"key1", b"key2", b"key3"]
        self.cache._client.delete.return_value = 3

        result = self.cache.delete_pattern("gathering:test:*")

        assert result == 3
        self.cache._client.keys.assert_called_once_with("gathering:test:*")
        self.cache._client.delete.assert_called_once()


class TestEmbeddingCache:
    """Test embedding cache operations."""

    def setup_method(self):
        """Setup mock cache for each test."""
        self.config = CacheConfig()
        self.cache = CacheManager(self.config)
        self.cache._enabled = True
        self.cache._client = Mock()

    def test_set_and_get_embedding(self):
        """Test embedding cache roundtrip."""
        text = "Hello world"
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]

        # Mock the Redis operations
        self.cache._client.setex.return_value = True

        # Set embedding
        result = self.cache.set_embedding(text, embedding)
        assert result is True

        # Mock get
        import json
        self.cache._client.get.return_value = json.dumps(embedding).encode('utf-8')

        # Get embedding
        cached = self.cache.get_embedding(text)
        assert cached == embedding

    def test_get_embedding_miss(self):
        """Test embedding cache miss."""
        self.cache._client.get.return_value = None

        result = self.cache.get_embedding("unknown text")

        assert result is None

    def test_embedding_uses_text_hash(self):
        """Test that embedding cache uses text hash for key."""
        text = "Test text"
        embedding = [0.1, 0.2]

        self.cache._client.setex.return_value = True
        self.cache.set_embedding(text, embedding)

        # Verify key uses hash
        call_args = self.cache._client.setex.call_args
        key = call_args[0][0]
        assert key.startswith("gathering:embedding:")
        assert len(key.split(":")[-1]) == 16  # Hash is 16 chars


class TestRAGCache:
    """Test RAG results cache operations."""

    def setup_method(self):
        """Setup mock cache for each test."""
        self.config = CacheConfig()
        self.cache = CacheManager(self.config)
        self.cache._enabled = True
        self.cache._client = Mock()

    def test_set_and_get_rag_results(self):
        """Test RAG results cache roundtrip."""
        agent_id = 1
        query = "What is the user's preference?"
        results = [
            {"id": 1, "key": "pref1", "value": "Dark mode", "similarity": 0.95},
            {"id": 2, "key": "pref2", "value": "Large font", "similarity": 0.87},
        ]

        # Mock set
        self.cache._client.setex.return_value = True
        success = self.cache.set_rag_results(agent_id, query, results)
        assert success is True

        # Mock get
        import json
        self.cache._client.get.return_value = json.dumps(results).encode('utf-8')

        # Get results
        cached = self.cache.get_rag_results(agent_id, query)
        assert cached == results

    def test_invalidate_rag_results(self):
        """Test RAG cache invalidation."""
        agent_id = 1

        # Mock keys and delete
        self.cache._client.keys.return_value = [
            b"gathering:rag:agent:1:abc123",
            b"gathering:rag:agent:1:def456",
        ]
        self.cache._client.delete.return_value = 2

        deleted = self.cache.invalidate_rag_results(agent_id)

        assert deleted == 2
        self.cache._client.keys.assert_called_once()
        pattern = self.cache._client.keys.call_args[0][0]
        assert pattern == "gathering:rag:agent:1:*"


class TestCircleContextCache:
    """Test circle context cache operations."""

    def setup_method(self):
        """Setup mock cache for each test."""
        self.config = CacheConfig()
        self.cache = CacheManager(self.config)
        self.cache._enabled = True
        self.cache._client = Mock()

    def test_set_and_get_circle_context(self):
        """Test circle context cache roundtrip."""
        circle_id = 5
        context = {
            "name": "Research Team",
            "members": [1, 2, 3],
            "active_tasks": 5,
        }

        # Mock set
        self.cache._client.setex.return_value = True
        success = self.cache.set_circle_context(circle_id, context)
        assert success is True

        # Mock get
        import json
        self.cache._client.get.return_value = json.dumps(context).encode('utf-8')

        # Get context
        cached = self.cache.get_circle_context(circle_id)
        assert cached == context

    def test_invalidate_circle_context(self):
        """Test circle context invalidation."""
        circle_id = 5

        self.cache._client.delete.return_value = 1

        result = self.cache.invalidate_circle_context(circle_id)

        assert result is True
        self.cache._client.delete.assert_called_once()


class TestCacheStats:
    """Test cache statistics."""

    def setup_method(self):
        """Setup mock cache for each test."""
        self.config = CacheConfig()
        self.cache = CacheManager(self.config)
        self.cache._enabled = True
        self.cache._client = Mock()

    def test_get_stats_when_enabled(self):
        """Test getting cache stats when enabled."""
        self.cache._client.info.return_value = {
            "keyspace_hits": 100,
            "keyspace_misses": 20,
        }
        self.cache._client.keys.return_value = [b"key1", b"key2", b"key3"]

        stats = self.cache.get_stats()

        assert stats["enabled"] is True
        assert stats["total_keys"] == 3
        assert stats["hits"] == 100
        assert stats["misses"] == 20
        assert stats["hit_rate"] == 83.33

    def test_get_stats_when_disabled(self):
        """Test getting cache stats when disabled."""
        self.cache._enabled = False

        stats = self.cache.get_stats()

        assert stats["enabled"] is False
        assert "reason" in stats

    def test_calculate_hit_rate(self):
        """Test hit rate calculation."""
        # 80% hit rate
        info = {"keyspace_hits": 80, "keyspace_misses": 20}
        rate = self.cache._calculate_hit_rate(info)
        assert rate == 80.0

        # 0 hits
        info = {"keyspace_hits": 0, "keyspace_misses": 0}
        rate = self.cache._calculate_hit_rate(info)
        assert rate == 0.0


class TestCacheFromEnv:
    """Test CacheManager.from_env() factory method."""

    @patch.dict("os.environ", {
        "REDIS_HOST": "redis.example.com",
        "REDIS_PORT": "6380",
        "REDIS_DB": "2",
        "REDIS_PASSWORD": "secret123",
        "CACHE_ENABLED": "true",
    })
    @patch("gathering.cache.redis_manager.REDIS_AVAILABLE", True)
    @patch("redis.Redis")
    def test_from_env_with_custom_values(self, mock_redis_class):
        """Test creating cache from environment variables."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_redis_class.return_value = mock_client

        cache = CacheManager.from_env()

        assert cache.config.host == "redis.example.com"
        assert cache.config.port == 6380
        assert cache.config.db == 2
        assert cache.config.password == "secret123"
        assert cache.config.enabled is True

    @patch.dict("os.environ", {"CACHE_ENABLED": "false"})
    def test_from_env_with_disabled_cache(self):
        """Test creating disabled cache from env."""
        cache = CacheManager.from_env()

        assert cache.config.enabled is False
        assert cache.is_enabled() is False


@pytest.mark.asyncio
class TestCacheIntegrationWithMemory:
    """Test cache integration with MemoryManager."""

    async def test_memory_recall_uses_cache(self):
        """Test that MemoryManager.recall() uses cache."""
        from gathering.rag.memory_manager import MemoryManager
        from gathering.rag.embeddings import EmbeddingService
        from gathering.rag.vectorstore import VectorStore
        from unittest.mock import AsyncMock

        # Create mock components
        embedder = Mock(spec=EmbeddingService)
        store = Mock(spec=VectorStore)
        cache = Mock(spec=CacheManager)

        # Setup cache to return cached results
        cache.get_rag_results.return_value = [
            {
                "id": 1,
                "key": "test",
                "value": "cached result",
                "memory_type": "fact",
                "similarity": 0.95,
                "importance": 0.8,
            }
        ]

        # Create MemoryManager with cache
        memory = MemoryManager(embedder, store, cache)

        # Call recall
        results = await memory.recall(agent_id=1, query="test query")

        # Verify cache was checked
        cache.get_rag_results.assert_called_once_with(1, "test query")

        # Verify embedder and store were NOT called (cache hit)
        embedder.embed.assert_not_called()
        store.search_memories.assert_not_called()

        # Verify results came from cache
        assert len(results) == 1
        assert results[0].value == "cached result"

    async def test_memory_recall_cache_miss(self):
        """Test MemoryManager.recall() on cache miss."""
        from gathering.rag.memory_manager import MemoryManager, RecallResult
        from gathering.rag.embeddings import EmbeddingService
        from gathering.rag.vectorstore import VectorStore, MemoryResult
        from unittest.mock import AsyncMock

        # Create mock components
        embedder = Mock(spec=EmbeddingService)
        embedder.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])

        store = Mock(spec=VectorStore)
        store.search_memories.return_value = [
            MemoryResult(
                id=1,
                key="test",
                value="fresh result",
                memory_type="fact",
                similarity=0.9,
                importance=0.7,
            )
        ]
        store.update_memory_access = Mock()

        cache = Mock(spec=CacheManager)
        cache.get_rag_results.return_value = None  # Cache miss

        # Create MemoryManager
        memory = MemoryManager(embedder, store, cache)

        # Call recall
        results = await memory.recall(agent_id=1, query="test query")

        # Verify cache was checked
        cache.get_rag_results.assert_called_once()

        # Verify embedder and store were called (cache miss)
        embedder.embed.assert_called_once()
        store.search_memories.assert_called_once()

        # Verify results were cached
        cache.set_rag_results.assert_called_once()

        # Verify results
        assert len(results) == 1
        assert results[0].value == "fresh result"

    async def test_memory_invalidation_on_remember(self):
        """Test cache invalidation when memory is created."""
        from gathering.rag.memory_manager import MemoryManager
        from gathering.rag.embeddings import EmbeddingService
        from gathering.rag.vectorstore import VectorStore
        from unittest.mock import AsyncMock

        # Create mock components
        embedder = Mock(spec=EmbeddingService)
        embedder.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])

        store = Mock(spec=VectorStore)
        store.add_memory.return_value = 123

        cache = Mock(spec=CacheManager)

        # Create MemoryManager
        memory = MemoryManager(embedder, store, cache)

        # Remember something
        await memory.remember(
            agent_id=1,
            content="Test memory",
            memory_type="fact",
        )

        # Verify cache was invalidated (called in remember() directly)
        # Note: Also called via event handler, but that's tested elsewhere
        assert cache.invalidate_rag_results.called
        assert cache.invalidate_rag_results.call_args[0][0] == 1


class TestCacheClearAll:
    """Test clearing all cache."""

    def setup_method(self):
        """Setup mock cache for each test."""
        self.config = CacheConfig()
        self.cache = CacheManager(self.config)
        self.cache._enabled = True
        self.cache._client = Mock()

    def test_clear_all(self):
        """Test clearing all GatheRing cache."""
        self.cache._client.keys.return_value = [
            b"gathering:embedding:abc",
            b"gathering:rag:agent:1:def",
            b"gathering:circle:context:5",
        ]
        self.cache._client.delete.return_value = 3

        deleted = self.cache.clear_all()

        assert deleted == 3
        self.cache._client.keys.assert_called_once_with("gathering:*")
        self.cache._client.delete.assert_called_once()
