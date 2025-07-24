"""
Pytest configuration and fixtures for GatheRing tests.
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from src.core.implementations import (
    BasicAgent,
    BasicMemory,
    MockLLMProvider,
    BasicPersonalityBlock,
    CalculatorTool,
    FileSystemTool,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def basic_agent_config():
    """Basic agent configuration for testing."""
    return {"name": "TestAgent", "llm_provider": "openai", "model": "gpt-4", "api_key": "test_key"}


@pytest.fixture
def agent_with_tools_config():
    """Agent configuration with tools."""
    return {
        "name": "ToolAgent",
        "llm_provider": "openai",
        "model": "gpt-4",
        "api_key": "test_key",
        "tools": ["calculator", "filesystem"],
    }


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    return MockLLMProvider.create("openai", {"api_key": "test_key", "model": "gpt-4"})


@pytest.fixture
def calculator_tool():
    """Create a calculator tool."""
    return CalculatorTool.from_config({"name": "calculator", "type": "calculator"})


@pytest.fixture
def filesystem_tool(temp_dir):
    """Create a filesystem tool with temp directory."""
    return FileSystemTool.from_config(
        {"name": "filesystem", "type": "filesystem", "permissions": ["read", "write"], "base_path": str(temp_dir)}
    )
