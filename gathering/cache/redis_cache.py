"""
Redis Cache Manager

Provides centralized caching for workspace data:
- File tree cache (1 minute TTL)
- Git data cache (5 minutes TTL)
- LSP responses cache (10 minutes TTL)
- File contents cache (30 seconds TTL)
"""

import json
import logging
from typing import Any, Optional
from functools import wraps
import hashlib

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None  # type: ignore

logger = logging.getLogger(__name__)


class RedisCache:
    """
    Redis-based cache manager with automatic fallback to no-cache.

    Features:
    - Automatic serialization/deserialization
    - TTL (Time To Live) support
    - Namespace prefixes
    - Hash-based cache keys
    - Graceful fallback if Redis unavailable
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        prefix: str = "gathering"
    ):
        """
        Initialize Redis cache.

        Args:
            host: Redis server host
            port: Redis server port
            db: Redis database number (0-15)
            prefix: Key prefix for namespace isolation
        """
        self.prefix = prefix
        self.enabled = REDIS_AVAILABLE
        self.client: Optional[Any] = None

        if not REDIS_AVAILABLE:
            logger.warning("Redis not available - caching disabled")
            return

        try:
            self.client = redis.Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            # Test connection
            self.client.ping()
            logger.info(f"✓ Redis connected: {host}:{port}/{db}")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e} - caching disabled")
            self.enabled = False
            self.client = None

    def _make_key(self, namespace: str, key: str) -> str:
        """
        Create namespaced cache key.

        Args:
            namespace: Category (workspace, git, lsp, etc.)
            key: Specific identifier

        Returns:
            Prefixed key: "gathering:workspace:12345"
        """
        return f"{self.prefix}:{namespace}:{key}"

    def _hash_key(self, data: Any) -> str:
        """
        Create hash from data for cache key.

        Args:
            data: Any JSON-serializable data

        Returns:
            MD5 hash string
        """
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(json_str.encode()).hexdigest()

    def get(self, namespace: str, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            namespace: Cache namespace
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if not self.enabled or not self.client:
            return None

        try:
            cache_key = self._make_key(namespace, key)
            value = self.client.get(cache_key)

            if value is None:
                return None

            # Deserialize JSON
            return json.loads(value)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl: int = 300
    ) -> bool:
        """
        Set value in cache with TTL.

        Args:
            namespace: Cache namespace
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: Time to live in seconds (default 5 minutes)

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.client:
            return False

        try:
            cache_key = self._make_key(namespace, key)
            json_value = json.dumps(value)
            self.client.setex(cache_key, ttl, json_value)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    def delete(self, namespace: str, key: str) -> bool:
        """
        Delete value from cache.

        Args:
            namespace: Cache namespace
            key: Cache key

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.client:
            return False

        try:
            cache_key = self._make_key(namespace, key)
            self.client.delete(cache_key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    def clear_namespace(self, namespace: str) -> int:
        """
        Clear all keys in namespace.

        Args:
            namespace: Namespace to clear

        Returns:
            Number of keys deleted
        """
        if not self.enabled or not self.client:
            return 0

        try:
            pattern = self._make_key(namespace, "*")
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return 0

    def invalidate_project(self, project_id: int):
        """
        Invalidate all cache for a project.

        Args:
            project_id: Project ID
        """
        namespaces = ["workspace", "git", "files"]
        for ns in namespaces:
            self.clear_namespace(f"{ns}:{project_id}")


# Global cache instance
_cache_instance: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    """
    Get global Redis cache instance.

    Returns:
        RedisCache instance (may be disabled if Redis unavailable)
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache()
    return _cache_instance


def cached(
    namespace: str,
    ttl: int = 300,
    key_func: Optional[callable] = None
):
    """
    Decorator for caching function results.

    Args:
        namespace: Cache namespace
        ttl: Time to live in seconds
        key_func: Optional function to generate cache key from args
                  Default: uses all function arguments

    Example:
        @cached("git", ttl=300)
        async def get_commits(project_id: int, limit: int = 50):
            # Expensive operation
            return commits
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache()

            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default: hash all arguments
                cache_key = cache._hash_key({
                    "args": args,
                    "kwargs": kwargs
                })

            # Try cache first
            cached_value = cache.get(namespace, cache_key)
            if cached_value is not None:
                logger.debug(f"Cache HIT: {namespace}:{cache_key}")
                return cached_value

            # Cache miss - execute function
            logger.debug(f"Cache MISS: {namespace}:{cache_key}")
            result = await func(*args, **kwargs)

            # Store in cache
            cache.set(namespace, cache_key, result, ttl)

            return result

        return wrapper
    return decorator


# Convenience functions for common cache operations

def cache_file_tree(project_id: int, tree_data: dict):
    """Cache file tree for a project."""
    cache = get_cache()
    cache.set("workspace", f"{project_id}:filetree", tree_data, ttl=60)


def get_cached_file_tree(project_id: int) -> Optional[dict]:
    """Get cached file tree."""
    cache = get_cache()
    return cache.get("workspace", f"{project_id}:filetree")


def cache_git_commits(project_id: int, commits: list):
    """Cache git commits."""
    cache = get_cache()
    cache.set("git", f"{project_id}:commits", commits, ttl=300)


def get_cached_git_commits(project_id: int) -> Optional[list]:
    """Get cached git commits."""
    cache = get_cache()
    return cache.get("git", f"{project_id}:commits")


def cache_git_status(project_id: int, status: dict):
    """Cache git status."""
    cache = get_cache()
    cache.set("git", f"{project_id}:status", status, ttl=30)


def get_cached_git_status(project_id: int) -> Optional[dict]:
    """Get cached git status."""
    cache = get_cache()
    return cache.get("git", f"{project_id}:status")


def invalidate_workspace_cache(project_id: int):
    """Invalidate all workspace-related cache."""
    cache = get_cache()
    cache.invalidate_project(project_id)
