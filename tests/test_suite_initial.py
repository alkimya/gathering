"""
Test suite for GatheRing core abstractions.
Following TDD principles - tests written before implementation.
"""

import pytest
from unittest.mock import Mock, patch
from typing import List, Dict, Any

# These imports will fail until we implement the classes
# This is intentional - TDD approach
from src.core.interfaces import IAgent, ILLMProvider, ITool, IPersonalityBlock, ICompetency, IMemory, IConversation
from src.core.exceptions import AgentError, LLMProviderError, ToolExecutionError, ConfigurationError


class TestIAgent:
    """Test cases for the Agent interface."""

    def test_agent_creation_with_minimal_config(self):
        """Test creating an agent with minimal configuration."""
        # Arrange
        config = {"name": "TestAgent", "llm_provider": "openai", "model": "gpt-4"}

        # Act
        agent = IAgent.from_config(config)

        # Assert
        assert agent.name == "TestAgent"
        assert agent.id is not None
        assert len(agent.id) == 36  # UUID format
        assert agent.age is None
        assert agent.history == ""
        assert len(agent.personality_blocks) == 0
        assert len(agent.competencies) == 0
        assert len(agent.tools) == 0

    def test_agent_creation_with_full_config(self):
        """Test creating an agent with complete configuration."""
        # Arrange
        config = {
            "name": "MarineExpert",
            "age": 45,
            "history": "20 years of experience in marine biology",
            "llm_provider": "anthropic",
            "model": "claude-3-opus",
            "personality_blocks": ["analytical", "curious", "patient"],
            "competencies": ["marine_biology", "data_analysis"],
            "tools": ["filesystem", "database"],
        }

        # Act
        agent = IAgent.from_config(config)

        # Assert
        assert agent.name == "MarineExpert"
        assert agent.age == 45
        assert agent.history == "20 years of experience in marine biology"
        assert len(agent.personality_blocks) == 3
        assert len(agent.competencies) == 2
        assert len(agent.tools) == 2

    def test_agent_invalid_config_raises_error(self):
        """Test that invalid configuration raises appropriate errors."""
        # Arrange
        invalid_configs = [
            {},  # Missing required fields
            {"name": ""},  # Empty name
            {"name": "Test", "llm_provider": "invalid"},  # Invalid provider
            {"name": "Test", "age": -5},  # Invalid age
        ]

        # Act & Assert
        for config in invalid_configs:
            with pytest.raises(ConfigurationError):
                IAgent.from_config(config)

    def test_agent_process_message(self):
        """Test agent processing a message."""
        # Arrange
        agent = IAgent.from_config({"name": "Assistant", "llm_provider": "openai", "model": "gpt-4"})
        message = "What is the weather today?"

        # Act
        response = agent.process_message(message)

        # Assert
        assert isinstance(response, str)
        assert len(response) > 0
        assert agent.memory.get_conversation_history()[-1]["role"] == "assistant"

    def test_agent_with_tools_execution(self):
        """Test agent executing tools when needed."""
        # Arrange
        agent = IAgent.from_config(
            {"name": "ToolUser", "llm_provider": "openai", "model": "gpt-4", "tools": ["calculator", "web_search"]}
        )
        message = "Calculate 15% of 2500"

        # Act
        response = agent.process_message(message)

        # Assert
        assert "375" in response
        assert agent.get_tool_usage_history()[-1]["tool"] == "calculator"

    def test_agent_memory_persistence(self):
        """Test that agent maintains conversation memory."""
        # Arrange
        agent = IAgent.from_config({"name": "MemoryAgent", "llm_provider": "openai", "model": "gpt-4"})

        # Act
        response1 = agent.process_message("My name is John")
        response2 = agent.process_message("What is my name?")

        # Assert
        assert "John" in response2
        assert len(agent.memory.get_conversation_history()) == 4  # 2 user + 2 assistant


class TestILLMProvider:
    """Test cases for LLM Provider interface."""

    def test_llm_provider_factory(self):
        """Test creating different LLM providers."""
        # Arrange
        providers = [
            ("openai", {"api_key": "test_key", "model": "gpt-4"}),
            ("anthropic", {"api_key": "test_key", "model": "claude-3"}),
            ("ollama", {"base_url": "http://localhost:11434", "model": "llama2"}),
        ]

        # Act & Assert
        for provider_name, config in providers:
            provider = ILLMProvider.create(provider_name, config)
            assert provider.name == provider_name
            assert provider.is_available()

    def test_llm_provider_completion(self):
        """Test LLM provider completion."""
        # Arrange
        provider = ILLMProvider.create("openai", {"api_key": "test_key", "model": "gpt-4"})
        messages = [{"role": "user", "content": "Hello, how are you?"}]

        # Act
        response = provider.complete(messages)

        # Assert
        assert isinstance(response, dict)
        assert "content" in response
        assert "role" in response
        assert response["role"] == "assistant"

    def test_llm_provider_with_tools(self):
        """Test LLM provider with tool calling."""
        # Arrange
        provider = ILLMProvider.create("openai", {"api_key": "test_key", "model": "gpt-4"})
        tools = [
            {
                "name": "get_weather",
                "description": "Get weather for a location",
                "parameters": {"location": {"type": "string", "required": True}},
            }
        ]
        messages = [{"role": "user", "content": "What's the weather in Paris?"}]

        # Act
        response = provider.complete(messages, tools=tools)

        # Assert
        assert "tool_calls" in response or "content" in response

    def test_llm_provider_streaming(self):
        """Test LLM provider streaming responses."""
        # Arrange
        provider = ILLMProvider.create("anthropic", {"api_key": "test_key", "model": "claude-3"})
        messages = [{"role": "user", "content": "Write a short story"}]

        # Act
        chunks = []
        for chunk in provider.stream(messages):
            chunks.append(chunk)

        # Assert
        assert len(chunks) > 1
        assert all(isinstance(chunk, str) for chunk in chunks)

    def test_llm_provider_error_handling(self):
        """Test LLM provider error handling."""
        # Arrange
        provider = ILLMProvider.create("openai", {"api_key": "invalid_key", "model": "gpt-4"})

        # Act & Assert
        with pytest.raises(LLMProviderError):
            provider.complete([{"role": "user", "content": "test"}])


class TestITool:
    """Test cases for Tool interface."""

    def test_tool_creation(self):
        """Test creating different types of tools."""
        # Arrange
        tool_configs = [
            {
                "name": "filesystem",
                "type": "filesystem",
                "permissions": ["read", "write"],
                "base_path": "/tmp/gathering",
            },
            {"name": "calculator", "type": "calculator", "precision": 10},
            {"name": "database", "type": "postgresql", "connection_string": "postgresql://localhost/test"},
        ]

        # Act & Assert
        for config in tool_configs:
            tool = ITool.from_config(config)
            assert tool.name == config["name"]
            assert tool.type == config["type"]
            assert tool.is_available()

    def test_tool_execution(self):
        """Test tool execution with various inputs."""
        # Arrange
        calculator = ITool.from_config({"name": "calculator", "type": "calculator"})

        # Act
        result = calculator.execute("15 * 25 + 10")

        # Assert
        assert result["success"] is True
        assert result["output"] == 385
        assert "error" not in result

    def test_tool_validation(self):
        """Test tool input validation."""
        # Arrange
        filesystem = ITool.from_config(
            {"name": "filesystem", "type": "filesystem", "permissions": ["read"], "base_path": "/tmp/gathering"}
        )

        # Act & Assert
        # Should fail - no write permission
        with pytest.raises(ToolExecutionError):
            filesystem.execute({"action": "write", "path": "test.txt", "content": "data"})

        # Should succeed - read permission granted
        result = filesystem.execute({"action": "read", "path": "test.txt"})
        assert result["success"] is True or "not found" in str(result.get("error", ""))

    def test_tool_async_execution(self):
        """Test asynchronous tool execution."""
        # Arrange
        api_tool = ITool.from_config({"name": "api_caller", "type": "http", "timeout": 30})

        # Act
        import asyncio

        async def test_async():
            result = await api_tool.execute_async({"url": "https://api.example.com/data", "method": "GET"})
            return result

        # Assert
        result = asyncio.run(test_async())
        assert "success" in result


class TestIPersonalityBlock:
    """Test cases for Personality Block interface."""

    def test_personality_block_creation(self):
        """Test creating personality blocks."""
        # Arrange
        blocks = [
            {"type": "trait", "name": "curious", "intensity": 0.8},
            {"type": "emotion", "name": "empathetic", "intensity": 0.9},
            {"type": "behavior", "name": "analytical", "parameters": {"depth": "high"}},
        ]

        # Act & Assert
        for block_config in blocks:
            block = IPersonalityBlock.from_config(block_config)
            assert block.type == block_config["type"]
            assert block.name == block_config["name"]

    def test_personality_block_influence(self):
        """Test how personality blocks influence responses."""
        # Arrange
        curious_block = IPersonalityBlock.from_config({"type": "trait", "name": "curious", "intensity": 0.9})

        formal_block = IPersonalityBlock.from_config({"type": "behavior", "name": "formal", "intensity": 0.8})

        # Act
        curious_modifiers = curious_block.get_prompt_modifiers()
        formal_modifiers = formal_block.get_prompt_modifiers()

        # Assert
        assert "ask questions" in curious_modifiers.lower()
        assert "professional" in formal_modifiers.lower() or "formal" in formal_modifiers.lower()

    def test_personality_block_combination(self):
        """Test combining multiple personality blocks."""
        # Arrange
        blocks = [
            IPersonalityBlock.from_config({"type": "trait", "name": "creative", "intensity": 0.7}),
            IPersonalityBlock.from_config({"type": "trait", "name": "logical", "intensity": 0.8}),
            IPersonalityBlock.from_config({"type": "emotion", "name": "cheerful", "intensity": 0.6}),
        ]

        # Act
        combined_modifiers = IPersonalityBlock.combine(blocks)

        # Assert
        assert isinstance(combined_modifiers, str)
        assert len(combined_modifiers) > 50  # Should have substantial content
        assert all(block.name in combined_modifiers.lower() for block in blocks)


class TestIntegration:
    """Integration tests for the complete system."""

    def test_multi_agent_conversation(self):
        """Test conversation between multiple agents."""
        # Arrange
        teacher = IAgent.from_config(
            {
                "name": "Professor Smith",
                "age": 50,
                "llm_provider": "openai",
                "model": "gpt-4",
                "personality_blocks": ["patient", "knowledgeable"],
                "competencies": ["teaching", "mathematics"],
            }
        )

        student = IAgent.from_config(
            {
                "name": "Alice",
                "age": 20,
                "llm_provider": "anthropic",
                "model": "claude-3",
                "personality_blocks": ["curious", "eager"],
                "competencies": ["learning"],
            }
        )

        # Act
        conversation = IConversation.create([teacher, student])
        conversation.add_message(student, "Can you explain calculus to me?")
        responses = conversation.process_turn()

        # Assert
        assert len(responses) > 0
        assert responses[0]["agent"] == teacher
        assert "calculus" in responses[0]["content"].lower()

    def test_agent_using_multiple_tools(self):
        """Test agent using multiple tools in sequence."""
        # Arrange
        researcher = IAgent.from_config(
            {
                "name": "Dr. Research",
                "llm_provider": "openai",
                "model": "gpt-4",
                "tools": ["web_search", "calculator", "filesystem"],
                "competencies": ["research", "analysis"],
            }
        )

        # Act
        response = researcher.process_message(
            "Search for the current population of Paris, calculate 15% of it, " "and save the result to a file."
        )

        # Assert
        assert "paris" in response.lower()
        assert "population" in response.lower()
        assert "15%" in response or "0.15" in response
        assert "saved" in response.lower() or "file" in response.lower()

        # Verify tools were used
        tool_history = researcher.get_tool_usage_history()
        tool_names = [usage["tool"] for usage in tool_history]
        assert "web_search" in tool_names
        assert "calculator" in tool_names
        assert "filesystem" in tool_names
