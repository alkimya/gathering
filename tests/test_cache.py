"""
Tests for Redis Cache.

Covers:
- RedisCache initialization and graceful degradation
- Get/Set operations
- Workspace cache helpers
- Cache invalidation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestRedisCacheInit:
    """Test RedisCache initialization."""

    @patch("gathering.cache.redis_cache.REDIS_AVAILABLE", False)
    def test_init_without_redis_library(self):
        """Test initialization when redis library not available."""
        from gathering.cache import RedisCache

        cache = RedisCache()

        assert cache.enabled is False
        assert cache.client is None

    @patch("gathering.cache.redis_cache.REDIS_AVAILABLE", True)
    @patch("gathering.cache.redis_cache.redis")
    def test_init_with_redis_connection_success(self, mock_redis_module):
        """Test successful Redis connection."""
        from gathering.cache import RedisCache

        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_redis_module.Redis.return_value = mock_client

        cache = RedisCache(host="localhost", port=6379, db=0)

        assert cache.enabled is True
        assert cache.client == mock_client
        mock_redis_module.Redis.assert_called_once()
        mock_client.ping.assert_called_once()

    @patch("gathering.cache.redis_cache.REDIS_AVAILABLE", True)
    @patch("gathering.cache.redis_cache.redis")
    def test_init_with_redis_connection_failure(self, mock_redis_module):
        """Test graceful degradation on Redis connection failure."""
        from gathering.cache import RedisCache

        mock_client = Mock()
        mock_client.ping.side_effect = Exception("Connection failed")
        mock_redis_module.Redis.return_value = mock_client

        cache = RedisCache()

        # Should degrade gracefully
        assert cache.enabled is False
        assert cache.client is None


class TestRedisCacheOperations:
    """Test RedisCache get/set operations."""

    def setup_method(self):
        """Setup mock cache for each test."""
        with patch("gathering.cache.redis_cache.REDIS_AVAILABLE", True):
            with patch("gathering.cache.redis_cache.redis") as mock_redis:
                mock_client = Mock()
                mock_client.ping.return_value = True
                mock_redis.Redis.return_value = mock_client

                from gathering.cache import RedisCache
                self.cache = RedisCache()
                self.cache.client = mock_client
                self.cache.enabled = True

    def test_get_success(self):
        """Test successful cache get."""
        self.cache.client.get.return_value = '{"value": "test"}'

        result = self.cache.get("workspace", "test_key")

        assert result == {"value": "test"}
        self.cache.client.get.assert_called_once()

    def test_get_miss(self):
        """Test cache miss."""
        self.cache.client.get.return_value = None

        result = self.cache.get("workspace", "test_key")

        assert result is None

    def test_get_when_disabled(self):
        """Test get when cache is disabled."""
        self.cache.enabled = False

        result = self.cache.get("workspace", "test_key")

        assert result is None

    def test_get_with_error(self):
        """Test get with Redis error."""
        self.cache.client.get.side_effect = Exception("Redis error")

        result = self.cache.get("workspace", "test_key")

        assert result is None

    def test_set_success(self):
        """Test successful cache set."""
        self.cache.client.setex.return_value = True

        result = self.cache.set("workspace", "test_key", {"value": "test"}, ttl=300)

        assert result is True
        self.cache.client.setex.assert_called_once()

    def test_set_when_disabled(self):
        """Test set when cache is disabled."""
        self.cache.enabled = False

        result = self.cache.set("workspace", "test_key", {"value": "test"})

        assert result is False

    def test_delete_success(self):
        """Test successful cache delete."""
        self.cache.client.delete.return_value = 1

        result = self.cache.delete("workspace", "test_key")

        assert result is True
        self.cache.client.delete.assert_called_once()

    def test_delete_multiple_keys(self):
        """Test deleting multiple keys."""
        self.cache.client.delete.return_value = 1

        # Delete multiple keys
        result1 = self.cache.delete("workspace", "key1")
        result2 = self.cache.delete("workspace", "key2")

        assert result1 is True
        assert result2 is True
        assert self.cache.client.delete.call_count == 2


class TestWorkspaceCacheHelpers:
    """Test workspace-specific cache helpers."""

    def setup_method(self):
        """Setup mock cache for each test."""
        with patch("gathering.cache.redis_cache.REDIS_AVAILABLE", True):
            with patch("gathering.cache.redis_cache.redis") as mock_redis:
                mock_client = Mock()
                mock_client.ping.return_value = True
                mock_redis.Redis.return_value = mock_client

                from gathering.cache.redis_cache import (
                    cache_file_tree,
                    get_cached_file_tree,
                    cache_git_commits,
                    get_cached_git_commits,
                    cache_git_status,
                    get_cached_git_status,
                    invalidate_workspace_cache,
                    get_cache,
                )

                self.cache_file_tree = cache_file_tree
                self.get_cached_file_tree = get_cached_file_tree
                self.cache_git_commits = cache_git_commits
                self.get_cached_git_commits = get_cached_git_commits
                self.cache_git_status = cache_git_status
                self.get_cached_git_status = get_cached_git_status
                self.invalidate_workspace_cache = invalidate_workspace_cache

                # Get the singleton cache and mock it
                cache = get_cache()
                cache.client = mock_client
                cache.enabled = True
                self.mock_client = mock_client

    def test_file_tree_cache_roundtrip(self):
        """Test file tree cache set and get."""
        project_id = 1
        tree = {"name": "root", "children": [{"name": "src"}]}

        # Mock set
        self.mock_client.setex.return_value = True
        self.cache_file_tree(project_id, tree)
        self.mock_client.setex.assert_called()

        # Mock get
        import json
        self.mock_client.get.return_value = json.dumps(tree)
        result = self.get_cached_file_tree(project_id)
        assert result == tree

    def test_git_commits_cache_roundtrip(self):
        """Test git commits cache set and get."""
        project_id = 1
        commits = [{"hash": "abc123", "message": "Initial commit"}]

        # Mock set
        self.mock_client.setex.return_value = True
        self.cache_git_commits(project_id, commits)
        self.mock_client.setex.assert_called()

        # Mock get
        import json
        self.mock_client.get.return_value = json.dumps(commits)
        result = self.get_cached_git_commits(project_id)
        assert result == commits

    def test_git_status_cache_roundtrip(self):
        """Test git status cache set and get."""
        project_id = 1
        status = {"branch": "main", "clean": True}

        # Mock set
        self.mock_client.setex.return_value = True
        self.cache_git_status(project_id, status)
        self.mock_client.setex.assert_called()

        # Mock get
        import json
        self.mock_client.get.return_value = json.dumps(status)
        result = self.get_cached_git_status(project_id)
        assert result == status

    def test_invalidate_workspace_cache(self):
        """Test workspace cache invalidation."""
        project_id = 1

        # Mock keys and delete
        self.mock_client.keys.return_value = [
            "gathering:workspace:1:tree",
            "gathering:git:1:commits",
        ]
        self.mock_client.delete.return_value = 2

        self.invalidate_workspace_cache(project_id)

        # Should have called delete for multiple patterns
        assert self.mock_client.keys.called or self.mock_client.delete.called


class TestCacheKeyGeneration:
    """Test cache key generation."""

    def test_make_key(self):
        """Test key generation with namespace."""
        with patch("gathering.cache.redis_cache.REDIS_AVAILABLE", False):
            from gathering.cache import RedisCache
            cache = RedisCache(prefix="test")

            key = cache._make_key("workspace", "project:1")
            assert key == "test:workspace:project:1"

    def test_hash_key(self):
        """Test hash key generation."""
        with patch("gathering.cache.redis_cache.REDIS_AVAILABLE", False):
            from gathering.cache import RedisCache
            cache = RedisCache()

            hash1 = cache._hash_key({"data": "test"})
            hash2 = cache._hash_key({"data": "test"})
            hash3 = cache._hash_key({"data": "different"})

            # Same input should produce same hash
            assert hash1 == hash2
            # Different input should produce different hash
            assert hash1 != hash3


class TestCacheGracefulDegradation:
    """Test cache graceful degradation when disabled."""

    def test_operations_return_none_when_disabled(self):
        """Test all operations gracefully return None/False when disabled."""
        with patch("gathering.cache.redis_cache.REDIS_AVAILABLE", False):
            from gathering.cache import RedisCache
            cache = RedisCache()

            assert cache.get("ns", "key") is None
            assert cache.set("ns", "key", "value") is False
            assert cache.delete("ns", "key") is False
