"""
Embedding Service for GatheRing RAG.

Generates vector embeddings from text using various providers.
Supports OpenAI, and extensible to other providers.
"""

from __future__ import annotations

import hashlib
import os
from enum import Enum
from typing import Optional, List, Dict, Any

import httpx

# Import cache (optional dependency)
try:
    from gathering.cache import CacheManager
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    CacheManager = None


class EmbeddingProvider(str, Enum):
    """Supported embedding providers."""
    OPENAI = "openai"
    # Future: COHERE = "cohere"
    # Future: LOCAL = "local"  # sentence-transformers


class EmbeddingService:
    """
    Service for generating text embeddings.

    Supports multiple providers and includes caching for efficiency.

    Example:
        service = EmbeddingService.from_env()

        # Single embedding
        embedding = await service.embed("Hello, world!")

        # Batch embeddings
        embeddings = await service.embed_batch(["Hello", "World"])

        # With caching
        embedding = await service.embed("Hello", use_cache=True)
    """

    # Default models per provider
    DEFAULT_MODELS = {
        EmbeddingProvider.OPENAI: "text-embedding-3-small",
    }

    # Embedding dimensions per model
    DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    def __init__(
        self,
        provider: EmbeddingProvider = EmbeddingProvider.OPENAI,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        cache_manager: Optional[Any] = None,  # CacheManager type hint would create circular import
    ):
        """
        Initialize embedding service.

        Args:
            provider: Embedding provider to use.
            api_key: API key for the provider.
            model: Model name (uses default if not specified).
            base_url: Override base URL for API.
            timeout: Request timeout in seconds.
            max_retries: Maximum retry attempts.
            cache_manager: Optional CacheManager for Redis caching.
        """
        self.provider = provider
        self.api_key = api_key
        self.model = model or self.DEFAULT_MODELS.get(provider)
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries

        # Redis cache (preferred) or fallback to in-memory
        self._redis_cache = cache_manager
        self._memory_cache: Dict[str, List[float]] = {}

        # Validate configuration
        if self.provider == EmbeddingProvider.OPENAI and not self.api_key:
            raise ValueError("OpenAI API key required for OpenAI embeddings")

    @classmethod
    def from_env(
        cls,
        provider: EmbeddingProvider = EmbeddingProvider.OPENAI,
        use_redis_cache: bool = True,
    ) -> "EmbeddingService":
        """
        Create service from environment variables.

        Environment variables:
            - OPENAI_API_KEY: OpenAI API key
            - OPENAI_EMBEDDING_MODEL: Model name (optional)
            - CACHE_ENABLED: Enable Redis cache (default: true)

        Args:
            provider: Embedding provider to use.
            use_redis_cache: Enable Redis caching (default: True).

        Returns:
            Configured EmbeddingService.
        """
        # Initialize cache if enabled
        cache_manager = None
        if use_redis_cache and CACHE_AVAILABLE:
            try:
                cache_manager = CacheManager.from_env()
                if not cache_manager.is_enabled():
                    cache_manager = None
            except Exception:
                # Graceful degradation - cache unavailable
                cache_manager = None

        if provider == EmbeddingProvider.OPENAI:
            return cls(
                provider=provider,
                api_key=os.environ.get("OPENAI_API_KEY"),
                model=os.environ.get("OPENAI_EMBEDDING_MODEL"),
                cache_manager=cache_manager,
            )
        raise ValueError(f"Unsupported provider: {provider}")

    @property
    def dimension(self) -> int:
        """Get embedding dimension for current model."""
        return self.DIMENSIONS.get(self.model, 1536)

    def _cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.sha256(f"{self.model}:{text}".encode()).hexdigest()

    async def embed(
        self,
        text: str,
        use_cache: bool = True,
    ) -> List[float]:
        """
        Generate embedding for a single text.

        Uses Redis cache (if available) for better performance and persistence.
        Falls back to in-memory cache if Redis unavailable.

        Args:
            text: Text to embed.
            use_cache: Whether to use/update cache.

        Returns:
            Embedding vector as list of floats.
        """
        # Check Redis cache first
        if use_cache and self._redis_cache:
            cached = self._redis_cache.get_embedding(text)
            if cached is not None:
                return cached

        # Check memory cache as fallback
        if use_cache:
            cache_key = self._cache_key(text)
            if cache_key in self._memory_cache:
                return self._memory_cache[cache_key]

        # Generate embedding (cache miss)
        embeddings = await self._generate_embeddings([text])
        embedding = embeddings[0]

        # Update caches
        if use_cache:
            # Redis cache (persistent, shared)
            if self._redis_cache:
                self._redis_cache.set_embedding(text, embedding)

            # Memory cache (fast, local fallback)
            cache_key = self._cache_key(text)
            self._memory_cache[cache_key] = embedding

        return embedding

    async def embed_batch(
        self,
        texts: List[str],
        use_cache: bool = True,
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed.
            use_cache: Whether to use/update cache.

        Returns:
            List of embedding vectors.
        """
        if not texts:
            return []

        # Check cache for each text
        results: List[Optional[List[float]]] = [None] * len(texts)
        texts_to_embed: List[tuple[int, str]] = []

        if use_cache:
            for i, text in enumerate(texts):
                cache_key = self._cache_key(text)
                if cache_key in self._memory_cache:
                    results[i] = self._memory_cache[cache_key]
                else:
                    texts_to_embed.append((i, text))
        else:
            texts_to_embed = list(enumerate(texts))

        # Generate embeddings for non-cached texts
        if texts_to_embed:
            indices, texts_batch = zip(*texts_to_embed)
            embeddings = await self._generate_embeddings(list(texts_batch))

            for idx, embedding in zip(indices, embeddings):
                results[idx] = embedding
                if use_cache:
                    cache_key = self._cache_key(texts[idx])
                    self._memory_cache[cache_key] = embedding

        return results  # type: ignore

    async def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings from provider API.

        Args:
            texts: Texts to embed.

        Returns:
            List of embeddings.
        """
        if self.provider == EmbeddingProvider.OPENAI:
            return await self._openai_embeddings(texts)
        raise ValueError(f"Unsupported provider: {self.provider}")

    async def _openai_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings using OpenAI API.

        Args:
            texts: Texts to embed.

        Returns:
            List of embeddings.
        """
        url = self.base_url or "https://api.openai.com/v1/embeddings"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "input": texts,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries):
                try:
                    response = await client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    data = response.json()

                    # Extract embeddings in order
                    embeddings = [None] * len(texts)
                    for item in data["data"]:
                        embeddings[item["index"]] = item["embedding"]

                    return embeddings  # type: ignore

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        # Rate limited, wait and retry
                        import asyncio
                        wait_time = 2 ** attempt
                        await asyncio.sleep(wait_time)
                        continue
                    raise
                except httpx.RequestError:
                    if attempt < self.max_retries - 1:
                        import asyncio
                        await asyncio.sleep(1)
                        continue
                    raise

        raise RuntimeError("Failed to generate embeddings after retries")

    def clear_cache(self) -> int:
        """
        Clear embedding cache.

        Returns:
            Number of entries cleared.
        """
        count = len(self._memory_cache)
        self._memory_cache.clear()
        return count

    def cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats.
        """
        return {
            "entries": len(self._memory_cache),
            "model": self.model,
            "provider": self.provider.value,
        }

    def __repr__(self) -> str:
        return f"EmbeddingService(provider={self.provider.value}, model={self.model})"
