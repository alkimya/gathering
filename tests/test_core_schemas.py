"""
Tests for gathering/core/schemas.py - Pydantic configuration schemas.
"""

import pytest
from pydantic import ValidationError

from gathering.core.schemas import (
    # Enums
    LLMProviderType,
    ToolType,
    PersonalityTrait,
    ToolPermissionType,
    MessageRole,
    # Tool configs
    ToolConfig,
    CalculatorToolConfig,
    FileSystemToolConfig,
    # Other configs
    PersonalityBlockConfig,
    CompetencyConfig,
    LLMProviderConfig,
    OpenAIProviderConfig,
    AnthropicProviderConfig,
    OllamaProviderConfig,
    AgentConfig,
    ConversationConfig,
    MessageConfig,
    # Utility functions
    validate_agent_config,
    validate_tool_config,
)


class TestEnums:
    """Test enum definitions."""

    def test_llm_provider_type_values(self):
        """Test LLMProviderType enum values."""
        assert LLMProviderType.OPENAI.value == "openai"
        assert LLMProviderType.ANTHROPIC.value == "anthropic"
        assert LLMProviderType.OLLAMA.value == "ollama"

    def test_tool_type_values(self):
        """Test ToolType enum values."""
        assert ToolType.CALCULATOR.value == "calculator"
        assert ToolType.FILESYSTEM.value == "filesystem"
        assert ToolType.WEB_SEARCH.value == "web_search"
        assert ToolType.DATABASE.value == "database"
        assert ToolType.CUSTOM.value == "custom"

    def test_personality_trait_values(self):
        """Test PersonalityTrait enum values."""
        expected_traits = [
            "curious", "analytical", "empathetic", "formal", "creative",
            "logical", "cheerful", "patient", "knowledgeable", "eager"
        ]
        for trait in expected_traits:
            assert hasattr(PersonalityTrait, trait.upper())
            assert getattr(PersonalityTrait, trait.upper()).value == trait

    def test_tool_permission_type_values(self):
        """Test ToolPermissionType enum values."""
        assert ToolPermissionType.READ.value == "read"
        assert ToolPermissionType.WRITE.value == "write"
        assert ToolPermissionType.EXECUTE.value == "execute"
        assert ToolPermissionType.DELETE.value == "delete"

    def test_message_role_values(self):
        """Test MessageRole enum values."""
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
        assert MessageRole.SYSTEM.value == "system"
        assert MessageRole.TOOL.value == "tool"


class TestToolConfig:
    """Test ToolConfig base class."""

    def test_tool_config_creation(self):
        """Test creating a basic tool config."""
        config = ToolConfig(
            name="my_tool",
            type=ToolType.CUSTOM,
        )
        assert config.name == "my_tool"
        assert config.type == ToolType.CUSTOM
        assert config.permissions == []
        assert config.enabled is True

    def test_tool_config_with_permissions(self):
        """Test tool config with permissions."""
        config = ToolConfig(
            name="file_tool",
            type=ToolType.FILESYSTEM,
            permissions=[ToolPermissionType.READ, ToolPermissionType.WRITE],
            enabled=False,
        )
        assert len(config.permissions) == 2
        assert config.enabled is False

    def test_tool_config_name_validation(self):
        """Test tool name length validation."""
        # Empty name should fail
        with pytest.raises(ValidationError):
            ToolConfig(name="", type=ToolType.CUSTOM)

        # Name too long should fail
        with pytest.raises(ValidationError):
            ToolConfig(name="a" * 101, type=ToolType.CUSTOM)

    def test_tool_config_invalid_type(self):
        """Test invalid tool type."""
        with pytest.raises(ValidationError):
            ToolConfig(name="test", type="invalid_type")


class TestCalculatorToolConfig:
    """Test CalculatorToolConfig."""

    def test_calculator_config_defaults(self):
        """Test calculator config with defaults."""
        config = CalculatorToolConfig(name="calc")
        assert config.type == ToolType.CALCULATOR
        assert config.max_expression_length == 1000

    def test_calculator_config_custom_length(self):
        """Test calculator config with custom expression length."""
        config = CalculatorToolConfig(
            name="calc",
            max_expression_length=5000,
        )
        assert config.max_expression_length == 5000

    def test_calculator_config_invalid_length(self):
        """Test calculator config with invalid expression length."""
        # Too small
        with pytest.raises(ValidationError):
            CalculatorToolConfig(name="calc", max_expression_length=0)

        # Too large
        with pytest.raises(ValidationError):
            CalculatorToolConfig(name="calc", max_expression_length=20000)


class TestFileSystemToolConfig:
    """Test FileSystemToolConfig."""

    def test_filesystem_config_defaults(self):
        """Test filesystem config with defaults."""
        config = FileSystemToolConfig(name="fs")
        assert config.type == ToolType.FILESYSTEM
        assert config.base_path == "/tmp/gathering"
        assert config.max_file_size_mb == 10
        assert config.allowed_extensions is None

    def test_filesystem_config_custom(self):
        """Test filesystem config with custom values."""
        config = FileSystemToolConfig(
            name="fs",
            base_path="/home/user/data",
            max_file_size_mb=50,
            allowed_extensions=[".txt", ".json", ".csv"],
        )
        assert config.base_path == "/home/user/data"
        assert config.max_file_size_mb == 50
        assert len(config.allowed_extensions) == 3

    def test_filesystem_config_invalid_size(self):
        """Test filesystem config with invalid file size."""
        with pytest.raises(ValidationError):
            FileSystemToolConfig(name="fs", max_file_size_mb=0)

        with pytest.raises(ValidationError):
            FileSystemToolConfig(name="fs", max_file_size_mb=200)


class TestPersonalityBlockConfig:
    """Test PersonalityBlockConfig."""

    def test_personality_block_creation(self):
        """Test creating a personality block."""
        block = PersonalityBlockConfig(
            type="trait",
            name="Curious",
        )
        assert block.type == "trait"
        assert block.name == "curious"  # normalized to lowercase
        assert block.intensity == 0.5
        assert block.parameters == {}

    def test_personality_block_all_types(self):
        """Test all personality block types."""
        for block_type in ["trait", "emotion", "behavior"]:
            block = PersonalityBlockConfig(type=block_type, name="test")
            assert block.type == block_type

    def test_personality_block_invalid_type(self):
        """Test invalid personality block type."""
        with pytest.raises(ValidationError):
            PersonalityBlockConfig(type="invalid", name="test")

    def test_personality_block_intensity_bounds(self):
        """Test intensity bounds."""
        # Valid intensities
        for intensity in [0.0, 0.5, 1.0]:
            block = PersonalityBlockConfig(type="trait", name="test", intensity=intensity)
            assert block.intensity == intensity

        # Invalid intensities
        with pytest.raises(ValidationError):
            PersonalityBlockConfig(type="trait", name="test", intensity=-0.1)

        with pytest.raises(ValidationError):
            PersonalityBlockConfig(type="trait", name="test", intensity=1.1)

    def test_personality_block_name_normalized(self):
        """Test that name is normalized to lowercase and stripped."""
        block = PersonalityBlockConfig(type="trait", name="  CURIOUS  ")
        assert block.name == "curious"

    def test_personality_block_with_parameters(self):
        """Test personality block with custom parameters."""
        block = PersonalityBlockConfig(
            type="behavior",
            name="analytical",
            parameters={"depth": "high", "focus": "details"},
        )
        assert block.parameters["depth"] == "high"
        assert block.parameters["focus"] == "details"


class TestCompetencyConfig:
    """Test CompetencyConfig."""

    def test_competency_config_minimal(self):
        """Test minimal competency config."""
        config = CompetencyConfig(name="python")
        assert config.name == "python"
        assert config.level == 0.5
        assert config.description is None
        assert config.keywords == []

    def test_competency_config_full(self):
        """Test full competency config."""
        config = CompetencyConfig(
            name="Machine Learning",
            level=0.9,
            description="Expert in ML algorithms and frameworks",
            keywords=["tensorflow", "pytorch", "sklearn"],
        )
        assert config.name == "Machine Learning"
        assert config.level == 0.9
        assert config.description == "Expert in ML algorithms and frameworks"
        assert len(config.keywords) == 3

    def test_competency_level_bounds(self):
        """Test competency level bounds."""
        with pytest.raises(ValidationError):
            CompetencyConfig(name="test", level=-0.1)

        with pytest.raises(ValidationError):
            CompetencyConfig(name="test", level=1.5)


class TestLLMProviderConfig:
    """Test LLM provider configurations."""

    def test_base_llm_provider_config(self):
        """Test base LLM provider config."""
        config = LLMProviderConfig(
            provider=LLMProviderType.OPENAI,
            model="gpt-4",
        )
        assert config.provider == LLMProviderType.OPENAI
        assert config.model == "gpt-4"
        assert config.api_key is None
        assert config.temperature == 0.7
        assert config.max_tokens is None
        assert config.timeout == 60

    def test_openai_provider_config(self):
        """Test OpenAI provider config."""
        config = OpenAIProviderConfig(
            api_key="sk-test",
            org_id="org-123",
        )
        assert config.provider == LLMProviderType.OPENAI
        assert config.model == "gpt-4"  # default
        assert config.org_id == "org-123"

    def test_anthropic_provider_config(self):
        """Test Anthropic provider config."""
        config = AnthropicProviderConfig(
            api_key="sk-ant-test",
        )
        assert config.provider == LLMProviderType.ANTHROPIC
        assert config.model == "claude-3-opus-20240229"

    def test_ollama_provider_config(self):
        """Test Ollama provider config."""
        config = OllamaProviderConfig(
            base_url="http://localhost:11434",
        )
        assert config.provider == LLMProviderType.OLLAMA
        assert config.model == "llama2"
        assert config.base_url == "http://localhost:11434"

    def test_temperature_bounds(self):
        """Test temperature bounds."""
        # Valid temperatures
        config = LLMProviderConfig(
            provider=LLMProviderType.OPENAI,
            model="gpt-4",
            temperature=0.0,
        )
        assert config.temperature == 0.0

        config = LLMProviderConfig(
            provider=LLMProviderType.OPENAI,
            model="gpt-4",
            temperature=2.0,
        )
        assert config.temperature == 2.0

        # Invalid temperatures
        with pytest.raises(ValidationError):
            LLMProviderConfig(
                provider=LLMProviderType.OPENAI,
                model="gpt-4",
                temperature=-0.1,
            )

        with pytest.raises(ValidationError):
            LLMProviderConfig(
                provider=LLMProviderType.OPENAI,
                model="gpt-4",
                temperature=2.5,
            )

    def test_timeout_bounds(self):
        """Test timeout bounds."""
        with pytest.raises(ValidationError):
            LLMProviderConfig(
                provider=LLMProviderType.OPENAI,
                model="gpt-4",
                timeout=0,
            )

        with pytest.raises(ValidationError):
            LLMProviderConfig(
                provider=LLMProviderType.OPENAI,
                model="gpt-4",
                timeout=700,
            )


class TestAgentConfig:
    """Test AgentConfig."""

    def test_agent_config_minimal(self):
        """Test minimal agent config."""
        config = AgentConfig(
            name="TestAgent",
            llm_provider=LLMProviderType.OPENAI,
            model="gpt-4",
        )
        assert config.name == "TestAgent"
        assert config.llm_provider == LLMProviderType.OPENAI
        assert config.model == "gpt-4"
        assert config.age is None
        assert config.history == ""
        assert config.personality_blocks == []
        assert config.competencies == []
        assert config.tools == []
        assert config.temperature == 0.7

    def test_agent_config_full(self):
        """Test full agent config."""
        config = AgentConfig(
            name="ExpertAgent",
            age=35,
            history="Expert in data science with 10 years experience",
            description="A helpful data science assistant",
            llm_provider=LLMProviderType.ANTHROPIC,
            model="claude-3-opus",
            api_key="test-key",
            personality_blocks=["analytical", "Patient", "CURIOUS"],
            competencies=["python", "ml"],
            tools=["calculator", "web_search"],
            temperature=0.5,
            max_tokens=2000,
            system_prompt_prefix="You are an expert.",
            system_prompt_suffix="Always be helpful.",
        )
        assert config.name == "ExpertAgent"
        assert config.age == 35
        assert config.description == "A helpful data science assistant"
        # Personality blocks normalized to lowercase
        assert config.personality_blocks == ["analytical", "patient", "curious"]

    def test_agent_config_name_validation(self):
        """Test agent name validation."""
        # Empty name should fail
        with pytest.raises(ValidationError):
            AgentConfig(
                name="",
                llm_provider=LLMProviderType.OPENAI,
                model="gpt-4",
            )

        # Whitespace-only name should fail
        with pytest.raises(ValidationError):
            AgentConfig(
                name="   ",
                llm_provider=LLMProviderType.OPENAI,
                model="gpt-4",
            )

        # Name is stripped
        config = AgentConfig(
            name="  Agent  ",
            llm_provider=LLMProviderType.OPENAI,
            model="gpt-4",
        )
        assert config.name == "Agent"

    def test_agent_config_age_bounds(self):
        """Test agent age bounds."""
        # Valid ages
        config = AgentConfig(
            name="Agent",
            llm_provider=LLMProviderType.OPENAI,
            model="gpt-4",
            age=0,
        )
        assert config.age == 0

        config = AgentConfig(
            name="Agent",
            llm_provider=LLMProviderType.OPENAI,
            model="gpt-4",
            age=200,
        )
        assert config.age == 200

        # Invalid ages
        with pytest.raises(ValidationError):
            AgentConfig(
                name="Agent",
                llm_provider=LLMProviderType.OPENAI,
                model="gpt-4",
                age=-1,
            )

        with pytest.raises(ValidationError):
            AgentConfig(
                name="Agent",
                llm_provider=LLMProviderType.OPENAI,
                model="gpt-4",
                age=201,
            )

    def test_agent_config_model_validation(self):
        """Test model validator runs without errors for valid models."""
        # OpenAI model
        config = AgentConfig(
            name="Agent",
            llm_provider=LLMProviderType.OPENAI,
            model="gpt-4-turbo",
        )
        assert config.model == "gpt-4-turbo"

        # Anthropic model
        config = AgentConfig(
            name="Agent",
            llm_provider=LLMProviderType.ANTHROPIC,
            model="claude-3-sonnet",
        )
        assert config.model == "claude-3-sonnet"

        # Ollama model (no validation)
        config = AgentConfig(
            name="Agent",
            llm_provider=LLMProviderType.OLLAMA,
            model="custom-model",
        )
        assert config.model == "custom-model"


class TestConversationConfig:
    """Test ConversationConfig."""

    def test_conversation_config_minimal(self):
        """Test minimal conversation config."""
        config = ConversationConfig(agent_ids=["agent-1"])
        assert len(config.agent_ids) == 1
        assert config.max_turns is None
        assert config.save_history is True
        assert config.history_path is None

    def test_conversation_config_full(self):
        """Test full conversation config."""
        config = ConversationConfig(
            agent_ids=["agent-1", "agent-2"],
            max_turns=50,
            save_history=False,
            history_path="/tmp/history.json",
        )
        assert len(config.agent_ids) == 2
        assert config.max_turns == 50
        assert config.save_history is False
        assert config.history_path == "/tmp/history.json"

    def test_conversation_config_empty_agents(self):
        """Test conversation config requires at least one agent."""
        with pytest.raises(ValidationError):
            ConversationConfig(agent_ids=[])

    def test_conversation_config_max_turns_bounds(self):
        """Test max_turns bounds."""
        with pytest.raises(ValidationError):
            ConversationConfig(agent_ids=["agent-1"], max_turns=0)

        with pytest.raises(ValidationError):
            ConversationConfig(agent_ids=["agent-1"], max_turns=1001)


class TestMessageConfig:
    """Test MessageConfig."""

    def test_message_config_creation(self):
        """Test creating a message config."""
        config = MessageConfig(
            role=MessageRole.USER,
            content="Hello, world!",
        )
        assert config.role == MessageRole.USER
        assert config.content == "Hello, world!"
        assert config.metadata == {}

    def test_message_config_with_metadata(self):
        """Test message config with metadata."""
        config = MessageConfig(
            role=MessageRole.ASSISTANT,
            content="I can help with that.",
            metadata={"timestamp": "2024-01-01", "agent_id": "agent-1"},
        )
        assert config.metadata["timestamp"] == "2024-01-01"
        assert config.metadata["agent_id"] == "agent-1"

    def test_message_config_empty_content(self):
        """Test message config with empty content."""
        with pytest.raises(ValidationError):
            MessageConfig(role=MessageRole.USER, content="")

    def test_message_config_all_roles(self):
        """Test all message roles."""
        for role in MessageRole:
            config = MessageConfig(role=role, content="test")
            assert config.role == role


class TestUtilityFunctions:
    """Test utility functions."""

    def test_validate_agent_config_valid(self):
        """Test validate_agent_config with valid config."""
        config_dict = {
            "name": "TestAgent",
            "llm_provider": "openai",
            "model": "gpt-4",
        }
        config = validate_agent_config(config_dict)
        assert isinstance(config, AgentConfig)
        assert config.name == "TestAgent"

    def test_validate_agent_config_invalid(self):
        """Test validate_agent_config with invalid config."""
        with pytest.raises(ValidationError):
            validate_agent_config({})

        with pytest.raises(ValidationError):
            validate_agent_config({"name": ""})

    def test_validate_tool_config_calculator(self):
        """Test validate_tool_config returns CalculatorToolConfig."""
        config_dict = {
            "name": "calc",
            "type": "calculator",
            "max_expression_length": 500,
        }
        config = validate_tool_config(config_dict)
        assert isinstance(config, CalculatorToolConfig)
        assert config.max_expression_length == 500

    def test_validate_tool_config_filesystem(self):
        """Test validate_tool_config returns FileSystemToolConfig."""
        config_dict = {
            "name": "fs",
            "type": "filesystem",
            "base_path": "/data",
        }
        config = validate_tool_config(config_dict)
        assert isinstance(config, FileSystemToolConfig)
        assert config.base_path == "/data"

    def test_validate_tool_config_custom(self):
        """Test validate_tool_config returns base ToolConfig for custom type."""
        config_dict = {
            "name": "custom_tool",
            "type": "custom",
        }
        config = validate_tool_config(config_dict)
        assert isinstance(config, ToolConfig)
        assert not isinstance(config, CalculatorToolConfig)
        assert not isinstance(config, FileSystemToolConfig)

    def test_validate_tool_config_unknown_type(self):
        """Test validate_tool_config with unknown type falls back to ToolConfig."""
        config_dict = {
            "name": "unknown",
            "type": "web_search",  # Valid enum but no specific subclass
        }
        config = validate_tool_config(config_dict)
        assert isinstance(config, ToolConfig)
