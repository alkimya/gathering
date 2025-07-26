"""
LLM module for GatheRing framework.
Contains LLM provider implementations.
"""

from gathering.core.interfaces import ILLMProvider
from gathering.core.implementations import MockLLMProvider

# Import actual providers when implemented
# from gathering.llm.openai_provider import OpenAIProvider
# from gathering.llm.anthropic_provider import AnthropicProvider
# from gathering.llm.ollama_provider import OllamaProvider

__all__ = ["ILLMProvider", "MockLLMProvider"]
