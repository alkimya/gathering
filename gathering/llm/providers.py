"""
LLM Provider implementations for the GatheRing framework.

This module provides concrete implementations of ILLMProvider for:
- OpenAI (GPT-4, GPT-3.5, etc.)
- Anthropic (Claude 3, etc.)
- Ollama (Local LLM)
- Mock (for testing)

Usage:
    from gathering.llm.providers import LLMProviderFactory

    provider = LLMProviderFactory.create("openai", {
        "model": "gpt-4",
        "api_key": "sk-..."
    })

    response = provider.complete([{"role": "user", "content": "Hello!"}])
"""

import asyncio
import time
from abc import ABC
from typing import List, Dict, Any, Optional, AsyncGenerator
from functools import lru_cache
from collections import OrderedDict
import hashlib
import json

from gathering.core.interfaces import ILLMProvider
from gathering.core.exceptions import LLMProviderError, ConfigurationError


class RateLimiter:
    """
    Token bucket rate limiter for API calls.

    Attributes:
        max_requests: Maximum requests allowed in the time window
        time_window: Time window in seconds
    """

    def __init__(self, max_requests: int = 60, time_window: float = 60.0):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: List[float] = []

    def acquire(self) -> bool:
        """
        Try to acquire a request slot.

        Returns:
            True if request is allowed, False if rate limited
        """
        now = time.time()

        # Remove expired requests
        self.requests = [t for t in self.requests if now - t < self.time_window]

        if len(self.requests) >= self.max_requests:
            return False

        self.requests.append(now)
        return True

    def wait_time(self) -> float:
        """Get time to wait before next request is allowed."""
        if len(self.requests) < self.max_requests:
            return 0.0

        oldest = min(self.requests)
        return max(0.0, self.time_window - (time.time() - oldest))


class LRUCache:
    """
    LRU Cache for LLM responses.

    Caches responses based on message hash to avoid redundant API calls.
    """

    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()

    def _hash_messages(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Create a hash key from messages and parameters."""
        data = {
            "messages": messages,
            "kwargs": {k: v for k, v in kwargs.items() if k not in ["stream"]}
        }
        content = json.dumps(data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def get(self, messages: List[Dict[str, str]], **kwargs) -> Optional[Dict[str, Any]]:
        """Get cached response if available."""
        key = self._hash_messages(messages, **kwargs)
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    def set(self, messages: List[Dict[str, str]], response: Dict[str, Any], **kwargs) -> None:
        """Cache a response."""
        key = self._hash_messages(messages, **kwargs)

        # Remove oldest if at capacity
        if len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)

        self.cache[key] = response

    def clear(self) -> None:
        """Clear the cache."""
        self.cache.clear()


class BaseLLMProvider(ILLMProvider):
    """
    Base class for LLM providers with common functionality.

    Provides:
    - Rate limiting
    - Response caching
    - Error handling
    - Retry logic
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)

        # Rate limiting
        rate_limit = config.get("rate_limit_per_minute", 60)
        self.rate_limiter = RateLimiter(max_requests=rate_limit)

        # Caching
        cache_size = config.get("cache_size", 100)
        self.cache = LRUCache(max_size=cache_size) if config.get("enable_cache", True) else None

        # Retry settings
        self.max_retries = config.get("max_retries", 3)
        self.retry_delay = config.get("retry_delay", 1.0)

    def _check_rate_limit(self) -> None:
        """Check rate limit and wait if necessary."""
        if not self.rate_limiter.acquire():
            wait_time = self.rate_limiter.wait_time()
            raise LLMProviderError(
                f"Rate limit exceeded. Try again in {wait_time:.1f}s",
                provider=self.name,
                status_code=429,
            )

    def _get_cached(self, messages: List[Dict[str, str]], **kwargs) -> Optional[Dict[str, Any]]:
        """Get cached response if available."""
        if self.cache:
            return self.cache.get(messages, **kwargs)
        return None

    def _set_cached(self, messages: List[Dict[str, str]], response: Dict[str, Any], **kwargs) -> None:
        """Cache a response."""
        if self.cache:
            self.cache.set(messages, response, **kwargs)


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI API provider implementation.

    Supports GPT-4, GPT-3.5-turbo, and other OpenAI models.
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.api_key = config.get("api_key")
        self.org_id = config.get("org_id")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self._client = None

    @classmethod
    def create(cls, provider_name: str, config: Dict[str, Any]) -> "OpenAIProvider":
        return cls(provider_name, config)

    def _get_client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.api_key,
                    organization=self.org_id,
                    base_url=self.base_url if self.base_url != "https://api.openai.com/v1" else None,
                )
            except ImportError:
                raise LLMProviderError(
                    "OpenAI package not installed. Run: pip install openai",
                    provider=self.name,
                )
        return self._client

    def complete(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Get completion from OpenAI."""
        # Check cache first
        cached = self._get_cached(messages, tools=tools, **kwargs)
        if cached:
            return cached

        # Rate limiting
        self._check_rate_limit()

        try:
            client = self._get_client()

            # Build request
            request_kwargs = {
                "model": self.model or "gpt-4",
                "messages": messages,
                "temperature": kwargs.get("temperature", self.config.get("temperature", 0.7)),
                "max_tokens": kwargs.get("max_tokens", self.config.get("max_tokens")),
            }

            # Remove None values
            request_kwargs = {k: v for k, v in request_kwargs.items() if v is not None}

            # Add tools if provided
            if tools:
                request_kwargs["tools"] = [
                    {"type": "function", "function": tool} for tool in tools
                ]

            response = client.chat.completions.create(**request_kwargs)

            # Parse response
            message = response.choices[0].message
            result = {
                "role": "assistant",
                "content": message.content,
            }

            # Handle tool calls
            if message.tool_calls:
                result["tool_calls"] = [
                    {
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments),
                    }
                    for tc in message.tool_calls
                ]

            # Cache response
            self._set_cached(messages, result, tools=tools, **kwargs)

            return result

        except Exception as e:
            error_msg = str(e)
            status_code = getattr(e, "status_code", None)
            raise LLMProviderError(error_msg, provider=self.name, status_code=status_code)

    async def stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream completion from OpenAI."""
        self._check_rate_limit()

        try:
            client = self._get_client()

            request_kwargs = {
                "model": self.model or "gpt-4",
                "messages": messages,
                "stream": True,
                "temperature": kwargs.get("temperature", self.config.get("temperature", 0.7)),
            }

            response = client.chat.completions.create(**request_kwargs)

            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            raise LLMProviderError(str(e), provider=self.name)

    def is_available(self) -> bool:
        """Check if OpenAI is available."""
        return self.api_key is not None

    def get_token_count(self, text: str) -> int:
        """Count tokens using tiktoken."""
        try:
            import tiktoken
            encoding = tiktoken.encoding_for_model(self.model or "gpt-4")
            return len(encoding.encode(text))
        except ImportError:
            # Fallback to approximation
            return len(text) // 4

    def get_max_tokens(self) -> int:
        """Get max tokens for the model."""
        model_limits = {
            "gpt-4": 8192,
            "gpt-4-turbo": 128000,
            "gpt-4o": 128000,
            "gpt-3.5-turbo": 16385,
            "gpt-3.5-turbo-16k": 16385,
        }
        return model_limits.get(self.model or "gpt-4", 8192)


class AnthropicProvider(BaseLLMProvider):
    """
    Anthropic API provider implementation.

    Supports Claude 3 models (Opus, Sonnet, Haiku).
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.api_key = config.get("api_key")
        self._client = None

    @classmethod
    def create(cls, provider_name: str, config: Dict[str, Any]) -> "AnthropicProvider":
        return cls(provider_name, config)

    def _get_client(self):
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            try:
                from anthropic import Anthropic
                self._client = Anthropic(api_key=self.api_key)
            except ImportError:
                raise LLMProviderError(
                    "Anthropic package not installed. Run: pip install anthropic",
                    provider=self.name,
                )
        return self._client

    def complete(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Get completion from Anthropic."""
        # Check cache first
        cached = self._get_cached(messages, tools=tools, **kwargs)
        if cached:
            return cached

        # Rate limiting
        self._check_rate_limit()

        try:
            client = self._get_client()

            # Anthropic uses a different message format
            # Extract system message and convert tool messages
            system_msg = None
            chat_messages = []

            for msg in messages:
                if msg["role"] == "system":
                    system_msg = msg["content"]
                elif msg["role"] == "tool":
                    # Convert tool result to Anthropic format
                    chat_messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": msg.get("tool_use_id", msg.get("name", "")),
                            "content": msg.get("content", ""),
                        }],
                    })
                elif msg["role"] == "assistant" and "tool_calls" in msg:
                    # Convert assistant message with tool_calls to Anthropic format
                    content_blocks = []
                    if msg.get("content"):
                        content_blocks.append({
                            "type": "text",
                            "text": msg["content"],
                        })
                    for tc in msg["tool_calls"]:
                        content_blocks.append({
                            "type": "tool_use",
                            "id": tc.get("id", tc.get("name", "")),
                            "name": tc["name"],
                            "input": tc.get("arguments", {}),
                        })
                    chat_messages.append({
                        "role": "assistant",
                        "content": content_blocks,
                    })
                else:
                    chat_messages.append(msg)

            request_kwargs = {
                "model": self.model or "claude-3-opus-20240229",
                "messages": chat_messages,
                "max_tokens": kwargs.get("max_tokens", self.config.get("max_tokens", 4096)),
                "temperature": kwargs.get("temperature", self.config.get("temperature", 0.7)),
            }

            if system_msg:
                request_kwargs["system"] = system_msg

            # Add tools if provided
            if tools:
                request_kwargs["tools"] = [
                    {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "input_schema": tool.get("parameters", {}),
                    }
                    for tool in tools
                ]

            response = client.messages.create(**request_kwargs)

            # Parse response
            result = {
                "role": "assistant",
                "content": response.content[0].text if response.content else "",
            }

            # Handle tool use
            for block in response.content:
                if hasattr(block, "type") and block.type == "tool_use":
                    if "tool_calls" not in result:
                        result["tool_calls"] = []
                    result["tool_calls"].append({
                        "id": block.id,  # Required for tool_result
                        "name": block.name,
                        "arguments": block.input,
                    })

            # Cache response
            self._set_cached(messages, result, tools=tools, **kwargs)

            return result

        except Exception as e:
            raise LLMProviderError(str(e), provider=self.name)

    async def stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream completion from Anthropic."""
        self._check_rate_limit()

        try:
            client = self._get_client()

            # Extract system message
            system_msg = None
            chat_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_msg = msg["content"]
                else:
                    chat_messages.append(msg)

            request_kwargs = {
                "model": self.model or "claude-3-opus-20240229",
                "messages": chat_messages,
                "max_tokens": kwargs.get("max_tokens", 4096),
                "stream": True,
            }

            if system_msg:
                request_kwargs["system"] = system_msg

            with client.messages.stream(**request_kwargs) as stream:
                for text in stream.text_stream:
                    yield text

        except Exception as e:
            raise LLMProviderError(str(e), provider=self.name)

    def is_available(self) -> bool:
        """Check if Anthropic is available."""
        return self.api_key is not None

    def get_token_count(self, text: str) -> int:
        """Approximate token count for Claude."""
        # Claude uses a similar tokenization to GPT
        # Approximation: ~4 chars per token
        return len(text) // 4

    def get_max_tokens(self) -> int:
        """Get max tokens for the model."""
        model_limits = {
            "claude-3-opus-20240229": 200000,
            "claude-3-sonnet-20240229": 200000,
            "claude-3-haiku-20240307": 200000,
            "claude-2.1": 200000,
            "claude-2.0": 100000,
        }
        return model_limits.get(self.model or "claude-3-opus-20240229", 200000)


class OllamaProvider(BaseLLMProvider):
    """
    Ollama provider for local LLM inference.

    Supports any model available in Ollama (Llama, Mistral, etc.)
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.base_url = config.get("base_url", "http://localhost:11434")
        self._client = None

    @classmethod
    def create(cls, provider_name: str, config: Dict[str, Any]) -> "OllamaProvider":
        return cls(provider_name, config)

    def _get_client(self):
        """Lazy initialization of Ollama client."""
        if self._client is None:
            try:
                from ollama import Client
                self._client = Client(host=self.base_url)
            except ImportError:
                raise LLMProviderError(
                    "Ollama package not installed. Run: pip install ollama",
                    provider=self.name,
                )
        return self._client

    def complete(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Get completion from Ollama."""
        # Check cache first
        cached = self._get_cached(messages, **kwargs)
        if cached:
            return cached

        try:
            client = self._get_client()

            response = client.chat(
                model=self.model or "llama2",
                messages=messages,
                options={
                    "temperature": kwargs.get("temperature", self.config.get("temperature", 0.7)),
                },
            )

            result = {
                "role": "assistant",
                "content": response["message"]["content"],
            }

            # Cache response
            self._set_cached(messages, result, **kwargs)

            return result

        except Exception as e:
            raise LLMProviderError(str(e), provider=self.name)

    async def stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream completion from Ollama."""
        try:
            client = self._get_client()

            stream = client.chat(
                model=self.model or "llama2",
                messages=messages,
                stream=True,
            )

            for chunk in stream:
                if chunk["message"]["content"]:
                    yield chunk["message"]["content"]
                    await asyncio.sleep(0)  # Yield control

        except Exception as e:
            raise LLMProviderError(str(e), provider=self.name)

    def is_available(self) -> bool:
        """Check if Ollama server is available."""
        try:
            import httpx
            response = httpx.get(f"{self.base_url}/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    def get_token_count(self, text: str) -> int:
        """Approximate token count."""
        return len(text) // 4

    def get_max_tokens(self) -> int:
        """Get max tokens (varies by model)."""
        return self.config.get("max_tokens", 4096)


class DeepSeekProvider(BaseLLMProvider):
    """
    DeepSeek API provider implementation.

    Supports DeepSeek-Coder, DeepSeek-Chat, and other DeepSeek models.
    DeepSeek uses an OpenAI-compatible API.
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url", "https://api.deepseek.com/v1")
        self._client = None

    @classmethod
    def create(cls, provider_name: str, config: Dict[str, Any]) -> "DeepSeekProvider":
        return cls(provider_name, config)

    def _get_client(self):
        """Lazy initialization of DeepSeek client (uses OpenAI SDK)."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                )
            except ImportError:
                raise LLMProviderError(
                    "OpenAI package not installed. Run: pip install openai",
                    provider=self.name,
                )
        return self._client

    def complete(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Get completion from DeepSeek."""
        # Check cache first
        cached = self._get_cached(messages, tools=tools, **kwargs)
        if cached:
            return cached

        # Rate limiting
        self._check_rate_limit()

        try:
            client = self._get_client()

            # Build request - DeepSeek uses OpenAI-compatible format
            request_kwargs = {
                "model": self.model or "deepseek-chat",
                "messages": messages,
                "temperature": kwargs.get("temperature", self.config.get("temperature", 0.7)),
                "max_tokens": kwargs.get("max_tokens", self.config.get("max_tokens")),
            }

            # Remove None values
            request_kwargs = {k: v for k, v in request_kwargs.items() if v is not None}

            # Add tools if provided (DeepSeek supports function calling)
            if tools:
                request_kwargs["tools"] = [
                    {"type": "function", "function": tool} for tool in tools
                ]

            response = client.chat.completions.create(**request_kwargs)

            # Parse response
            message = response.choices[0].message
            result = {
                "role": "assistant",
                "content": message.content,
            }

            # Handle tool calls
            if hasattr(message, "tool_calls") and message.tool_calls:
                result["tool_calls"] = [
                    {
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments),
                    }
                    for tc in message.tool_calls
                ]

            # Cache response
            self._set_cached(messages, result, tools=tools, **kwargs)

            return result

        except Exception as e:
            error_msg = str(e)
            status_code = getattr(e, "status_code", None)
            raise LLMProviderError(error_msg, provider=self.name, status_code=status_code)

    async def stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream completion from DeepSeek."""
        self._check_rate_limit()

        try:
            client = self._get_client()

            request_kwargs = {
                "model": self.model or "deepseek-chat",
                "messages": messages,
                "stream": True,
                "temperature": kwargs.get("temperature", self.config.get("temperature", 0.7)),
            }

            response = client.chat.completions.create(**request_kwargs)

            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            raise LLMProviderError(str(e), provider=self.name)

    def is_available(self) -> bool:
        """Check if DeepSeek is available."""
        return self.api_key is not None

    def get_token_count(self, text: str) -> int:
        """Approximate token count (DeepSeek uses similar tokenization to GPT)."""
        # DeepSeek uses a similar tokenizer to GPT models
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except ImportError:
            return len(text) // 4

    def get_max_tokens(self) -> int:
        """Get max tokens for DeepSeek models."""
        model_limits = {
            "deepseek-chat": 32768,
            "deepseek-coder": 16384,
            "deepseek-coder-instruct": 16384,
            "deepseek-reasoner": 64000,
        }
        model_name = str(self.model) if self.model else "deepseek-chat"
        return model_limits.get(model_name, 32768)


class MockLLMProvider(BaseLLMProvider):
    """
    Mock LLM provider for testing.

    Provides deterministic responses for testing purposes.
    """

    @classmethod
    def create(cls, provider_name: str, config: Dict[str, Any]) -> "MockLLMProvider":
        return cls(provider_name, config)

    def complete(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Get mock completion."""
        # Validate API key for testing error handling
        if self.config.get("api_key") == "invalid_key":
            raise LLMProviderError("Invalid API key", provider=self.name, status_code=401)

        last_msg = messages[-1]["content"].lower()

        # Tool calling logic
        if tools and "weather" in last_msg:
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [{"name": "get_weather", "arguments": {"location": "Paris"}}],
            }

        # Memory test responses
        if "my name is" in last_msg:
            return {"role": "assistant", "content": "Nice to meet you! I'll remember your name."}
        elif "what is my name" in last_msg:
            for msg in messages:
                if "my name is" in msg.get("content", "").lower():
                    name = msg["content"].split("is")[-1].strip().rstrip(".")
                    return {"role": "assistant", "content": f"Your name is {name}."}
            return {"role": "assistant", "content": "I don't recall you telling me your name."}

        # Default response
        return {"role": "assistant", "content": f"I understand you said: {messages[-1]['content']}"}

    async def stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream mock completion."""
        response = self.complete(messages, tools, **kwargs)
        content = response.get("content", "")

        if content:
            words = content.split()
            for word in words:
                yield word + " "
                await asyncio.sleep(0.01)

    def is_available(self) -> bool:
        """Mock is always available unless configured otherwise."""
        return self.config.get("api_key") != "invalid_key"

    def get_token_count(self, text: str) -> int:
        """Approximate token count."""
        return len(text) // 4

    def get_max_tokens(self) -> int:
        """Get max tokens."""
        model_limits = {"gpt-4": 8000, "claude-3": 100000, "llama2": 4000}
        model_name = str(self.model) if self.model else "default"
        return model_limits.get(model_name, 4000)


class LLMProviderFactory:
    """
    Factory for creating LLM provider instances.

    Supports dependency injection and provider registration.

    Usage:
        # Create with default providers
        provider = LLMProviderFactory.create("openai", {"model": "gpt-4", "api_key": "..."})

        # Register custom provider
        LLMProviderFactory.register("custom", MyCustomProvider)
        provider = LLMProviderFactory.create("custom", config)
    """

    _providers: Dict[str, type] = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "deepseek": DeepSeekProvider,
        "ollama": OllamaProvider,
        "mock": MockLLMProvider,
    }

    @classmethod
    def register(cls, name: str, provider_class: type) -> None:
        """Register a new provider type."""
        if not issubclass(provider_class, ILLMProvider):
            raise ConfigurationError(
                f"Provider class must implement ILLMProvider",
                field="provider_class",
                value=provider_class.__name__,
            )
        cls._providers[name] = provider_class

    @classmethod
    def create(cls, provider_name: str, config: Dict[str, Any]) -> ILLMProvider:
        """
        Create a provider instance.

        Args:
            provider_name: Name of the provider (openai, anthropic, ollama, mock)
            config: Provider configuration

        Returns:
            Configured provider instance

        Raises:
            ConfigurationError: If provider is not registered
        """
        if provider_name not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ConfigurationError(
                f"Unknown provider: {provider_name}. Available: {available}",
                field="provider_name",
                value=provider_name,
            )

        provider_class = cls._providers[provider_name]
        return provider_class.create(provider_name, config)

    @classmethod
    def list_providers(cls) -> List[str]:
        """List all registered providers."""
        return list(cls._providers.keys())

    @classmethod
    def get_provider_class(cls, name: str) -> Optional[type]:
        """Get the provider class for a given name."""
        return cls._providers.get(name)
