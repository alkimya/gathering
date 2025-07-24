"""
LLM module for GatheRing framework.
Contains LLM provider implementations.
"""

from src.core.interfaces import ILLMProvider
from src.core.implementations import MockLLMProvider

# Import actual providers when implemented
# from src.llm.openai_provider import OpenAIProvider
# from src.llm.anthropic_provider import AnthropicProvider
# from src.llm.ollama_provider import OllamaProvider

__all__ = ["ILLMProvider", "MockLLMProvider"]
