"""
Redis Cache Manager for GatheRing.

Provides high-performance caching for:
- Embeddings (expensive API calls)
- RAG search results
- Circle context
- LLM responses (optional)

Design principles:
- Simple API (get/set/delete)
- Automatic TTL management
- JSON serialization
- Event-based invalidation
- Graceful degradation (works without Redis)
"""

import os
import json
import hashlib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    import redis
    from redis import Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    Redis = None


@dataclass
class CacheConfig:
    """Configuration for Redis cache."""

    # Connection
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None

    # TTL defaults (in seconds)
    embedding_ttl: int = 86400  # 24 hours
    rag_results_ttl: int = 300  # 5 minutes
    circle_context_ttl: int = 600  # 10 minutes
    llm_response_ttl: int = 3600  # 1 hour

    # Behavior
    enabled: bool = True
    key_prefix: str = "gathering:"


class CacheManager:
    """
    Redis-based cache manager with graceful degradation.

    Features:
    - Automatic TTL management
    - JSON serialization
    - Key namespacing
    - Graceful degradation (no-op if Redis unavailable)
    - Event-based cache invalidation

    Example:
        cache = CacheManager.from_env()

        # Cache an embedding
        cache.set_embedding("Hello world", [0.1, 0.2, ...])

        # Retrieve it
        embedding = cache.get_embedding("Hello world")

        # Cache RAG results
        cache.set_rag_results("query", agent_id=1, results=[...])

        # Invalidate on memory change
        cache.invalidate_rag_results(agent_id=1)
    """

    def __init__(self, config: CacheConfig):
        """
        Initialize CacheManager.

        Args:
            config: Cache configuration.
        """
        self.config = config
        self._client: Optional[Redis] = None
        self._enabled = config.enabled and REDIS_AVAILABLE

        if self._enabled:
            try:
                self._client = redis.Redis(
                    host=config.host,
                    port=config.port,
                    db=config.db,
                    password=config.password,
                    decode_responses=False,  # We handle JSON encoding
                )
                # Test connection
                self._client.ping()
            except Exception as e:
                print(f"[CacheManager] Redis connection failed: {e}")
                print("[CacheManager] Running without cache (degraded mode)")
                self._enabled = False
                self._client = None

    @classmethod
    def from_env(cls, dotenv_path: Optional[str] = None) -> "CacheManager":
        """
        Create CacheManager from environment variables.

        Environment variables:
        - REDIS_HOST: Redis host (default: localhost)
        - REDIS_PORT: Redis port (default: 6379)
        - REDIS_DB: Redis database (default: 0)
        - REDIS_PASSWORD: Redis password (optional)
        - CACHE_ENABLED: Enable cache (default: true)

        Args:
            dotenv_path: Optional .env file path.

        Returns:
            Configured CacheManager.
        """
        if dotenv_path:
            from dotenv import load_dotenv
            load_dotenv(dotenv_path)

        config = CacheConfig(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            password=os.getenv("REDIS_PASSWORD"),
            enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
        )
        return cls(config)

    def _make_key(self, namespace: str, *parts: str) -> str:
        """
        Create a namespaced cache key.

        Args:
            namespace: Key namespace (embedding, rag, circle, etc.)
            *parts: Key parts to join.

        Returns:
            Full cache key.

        Example:
            _make_key("embedding", "text_hash") → "gathering:embedding:text_hash"
        """
        key = f"{self.config.key_prefix}{namespace}:" + ":".join(str(p) for p in parts)
        return key

    def _hash_text(self, text: str) -> str:
        """Create a hash of text for cache key."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def _serialize(self, value: Any) -> bytes:
        """Serialize value to bytes."""
        return json.dumps(value).encode('utf-8')

    def _deserialize(self, data: bytes) -> Any:
        """Deserialize bytes to value."""
        if data is None:
            return None
        return json.loads(data.decode('utf-8'))

    # =========================================================================
    # GENERIC CACHE OPERATIONS
    # =========================================================================

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key.

        Returns:
            Cached value or None.
        """
        if not self._enabled or not self._client:
            return None

        try:
            data = self._client.get(key)
            return self._deserialize(data)
        except Exception as e:
            print(f"[CacheManager] Get error: {e}")
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set value in cache with TTL.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Time-to-live in seconds (optional).

        Returns:
            True if cached successfully.
        """
        if not self._enabled or not self._client:
            return False

        try:
            data = self._serialize(value)
            if ttl:
                self._client.setex(key, ttl, data)
            else:
                self._client.set(key, data)
            return True
        except Exception as e:
            print(f"[CacheManager] Set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key.

        Returns:
            True if deleted.
        """
        if not self._enabled or not self._client:
            return False

        try:
            self._client.delete(key)
            return True
        except Exception as e:
            print(f"[CacheManager] Delete error: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.

        Args:
            pattern: Key pattern (e.g., "gathering:rag:agent:1:*")

        Returns:
            Number of keys deleted.
        """
        if not self._enabled or not self._client:
            return 0

        try:
            keys = self._client.keys(pattern)
            if keys:
                return self._client.delete(*keys)
            return 0
        except Exception as e:
            print(f"[CacheManager] Delete pattern error: {e}")
            return 0

    # =========================================================================
    # EMBEDDING CACHE
    # =========================================================================

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Get cached embedding for text.

        Args:
            text: Text to get embedding for.

        Returns:
            Embedding vector or None.
        """
        text_hash = self._hash_text(text)
        key = self._make_key("embedding", text_hash)
        return self.get(key)

    def set_embedding(
        self,
        text: str,
        embedding: List[float],
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Cache an embedding.

        Args:
            text: Text that was embedded.
            embedding: Embedding vector.
            ttl: Time-to-live (default: 24h).

        Returns:
            True if cached.
        """
        text_hash = self._hash_text(text)
        key = self._make_key("embedding", text_hash)
        ttl = ttl or self.config.embedding_ttl
        return self.set(key, embedding, ttl)

    # =========================================================================
    # RAG RESULTS CACHE
    # =========================================================================

    def get_rag_results(
        self,
        agent_id: int,
        query: str,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached RAG search results.

        Args:
            agent_id: Agent ID.
            query: Search query.

        Returns:
            Cached results or None.
        """
        query_hash = self._hash_text(query)
        key = self._make_key("rag", "agent", str(agent_id), query_hash)
        return self.get(key)

    def set_rag_results(
        self,
        agent_id: int,
        query: str,
        results: List[Dict[str, Any]],
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Cache RAG search results.

        Args:
            agent_id: Agent ID.
            query: Search query.
            results: Search results.
            ttl: Time-to-live (default: 5min).

        Returns:
            True if cached.
        """
        query_hash = self._hash_text(query)
        key = self._make_key("rag", "agent", str(agent_id), query_hash)
        ttl = ttl or self.config.rag_results_ttl
        return self.set(key, results, ttl)

    def invalidate_rag_results(self, agent_id: int) -> int:
        """
        Invalidate all RAG results for an agent.

        Called when agent's memories change.

        Args:
            agent_id: Agent ID.

        Returns:
            Number of keys deleted.
        """
        pattern = self._make_key("rag", "agent", str(agent_id), "*")
        return self.delete_pattern(pattern)

    # =========================================================================
    # CIRCLE CONTEXT CACHE
    # =========================================================================

    def get_circle_context(self, circle_id: int) -> Optional[Dict[str, Any]]:
        """
        Get cached circle context.

        Args:
            circle_id: Circle ID.

        Returns:
            Circle context or None.
        """
        key = self._make_key("circle", "context", str(circle_id))
        return self.get(key)

    def set_circle_context(
        self,
        circle_id: int,
        context: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Cache circle context.

        Args:
            circle_id: Circle ID.
            context: Circle context data.
            ttl: Time-to-live (default: 10min).

        Returns:
            True if cached.
        """
        key = self._make_key("circle", "context", str(circle_id))
        ttl = ttl or self.config.circle_context_ttl
        return self.set(key, context, ttl)

    def invalidate_circle_context(self, circle_id: int) -> bool:
        """
        Invalidate circle context.

        Called when circle state changes.

        Args:
            circle_id: Circle ID.

        Returns:
            True if invalidated.
        """
        key = self._make_key("circle", "context", str(circle_id))
        return self.delete(key)

    # =========================================================================
    # LLM RESPONSE CACHE (Optional)
    # =========================================================================

    def get_llm_response(
        self,
        prompt_hash: str,
    ) -> Optional[str]:
        """
        Get cached LLM response.

        Args:
            prompt_hash: Hash of the prompt.

        Returns:
            Cached response or None.
        """
        key = self._make_key("llm", prompt_hash)
        return self.get(key)

    def set_llm_response(
        self,
        prompt_hash: str,
        response: str,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Cache LLM response.

        Args:
            prompt_hash: Hash of the prompt.
            response: LLM response.
            ttl: Time-to-live (default: 1h).

        Returns:
            True if cached.
        """
        key = self._make_key("llm", prompt_hash)
        ttl = ttl or self.config.llm_response_ttl
        return self.set(key, response, ttl)

    # =========================================================================
    # UTILITIES
    # =========================================================================

    def clear_all(self) -> int:
        """
        Clear all GatheRing cache.

        WARNING: This deletes all keys with the configured prefix.

        Returns:
            Number of keys deleted.
        """
        pattern = f"{self.config.key_prefix}*"
        return self.delete_pattern(pattern)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats.
        """
        if not self._enabled or not self._client:
            return {
                "enabled": False,
                "reason": "Redis unavailable or disabled",
            }

        try:
            info = self._client.info("stats")
            return {
                "enabled": True,
                "host": self.config.host,
                "port": self.config.port,
                "db": self.config.db,
                "total_keys": len(self._client.keys(f"{self.config.key_prefix}*")),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(info),
            }
        except Exception as e:
            return {
                "enabled": True,
                "error": str(e),
            }

    def _calculate_hit_rate(self, info: Dict[str, Any]) -> float:
        """Calculate cache hit rate."""
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        if total == 0:
            return 0.0
        return round(hits / total * 100, 2)

    def is_enabled(self) -> bool:
        """Check if cache is enabled and working."""
        return self._enabled

    def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            self._client.close()
