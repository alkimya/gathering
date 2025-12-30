"""
LLM (Large Language Model) providers for the GatheRing framework.

This module provides implementations for various LLM providers:
- OpenAI (GPT-4, GPT-3.5, etc.)
- Anthropic (Claude 3 models)
- DeepSeek (DeepSeek-Coder, DeepSeek-Chat)
- Ollama (Local LLM inference)
- Mock (For testing)

Usage:
    from gathering.llm import LLMProviderFactory

    # Create a provider
    provider = LLMProviderFactory.create("openai", {
        "model": "gpt-4",
        "api_key": os.environ["OPENAI_API_KEY"],
    })

    # Create DeepSeek provider
    deepseek = LLMProviderFactory.create("deepseek", {
        "model": "deepseek-coder",
        "api_key": os.environ["DEEPSEEK_API_KEY"],
    })

    # Get a completion
    response = provider.complete([
        {"role": "user", "content": "Hello!"}
    ])

    # Stream a response
    async for chunk in provider.stream(messages):
        print(chunk, end="")
"""

from gathering.core.interfaces import ILLMProvider

from gathering.llm.providers import (
    LLMProviderFactory,
    OpenAIProvider,
    AnthropicProvider,
    DeepSeekProvider,
    OllamaProvider,
    MockLLMProvider,
    BaseLLMProvider,
    RateLimiter,
    LRUCache,
)

__all__ = [
    # Interface
    "ILLMProvider",
    # Factory
    "LLMProviderFactory",
    # Providers
    "OpenAIProvider",
    "AnthropicProvider",
    "DeepSeekProvider",
    "OllamaProvider",
    "MockLLMProvider",
    "BaseLLMProvider",
    # Utilities
    "RateLimiter",
    "LRUCache",
]
