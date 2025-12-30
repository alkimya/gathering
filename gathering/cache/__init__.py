"""
Cache - Redis-based caching for performance optimization.

Provides caching for expensive operations:
- Embeddings (API calls)
- RAG search results
- Circle context
- LLM responses (optional)
"""

from gathering.cache.redis_manager import (
    CacheManager,
    CacheConfig,
)

__all__ = [
    "CacheManager",
    "CacheConfig",
]
