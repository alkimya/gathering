"""
Pydantic schemas for configuration validation in the GatheRing framework.
These schemas ensure type safety and validation for all configuration objects.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum


class LLMProviderType(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


class ToolType(str, Enum):
    """Supported tool types."""

    CALCULATOR = "calculator"
    FILESYSTEM = "filesystem"
    WEB_SEARCH = "web_search"
    DATABASE = "database"
    CUSTOM = "custom"


class PersonalityTrait(str, Enum):
    """Predefined personality traits."""

    CURIOUS = "curious"
    ANALYTICAL = "analytical"
    EMPATHETIC = "empathetic"
    FORMAL = "formal"
    CREATIVE = "creative"
    LOGICAL = "logical"
    CHEERFUL = "cheerful"
    PATIENT = "patient"
    KNOWLEDGEABLE = "knowledgeable"
    EAGER = "eager"


class ToolPermissionType(str, Enum):
    """Tool permission types."""

    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"


# =============================================================================
# Tool Schemas
# =============================================================================


class ToolConfig(BaseModel):
    """Base configuration for tools."""

    name: str = Field(..., min_length=1, max_length=100, description="Tool name")
    type: ToolType = Field(..., description="Tool type")
    permissions: List[ToolPermissionType] = Field(
        default_factory=list, description="Tool permissions"
    )
    enabled: bool = Field(default=True, description="Whether the tool is enabled")

    class Config:
        use_enum_values = True


class CalculatorToolConfig(ToolConfig):
    """Calculator tool configuration."""

    type: Literal[ToolType.CALCULATOR] = ToolType.CALCULATOR
    max_expression_length: int = Field(
        default=1000, ge=1, le=10000, description="Maximum expression length"
    )


class FileSystemToolConfig(ToolConfig):
    """Filesystem tool configuration."""

    type: Literal[ToolType.FILESYSTEM] = ToolType.FILESYSTEM
    base_path: str = Field(
        default="/tmp/gathering", description="Base path for file operations"
    )
    max_file_size_mb: int = Field(
        default=10, ge=1, le=100, description="Maximum file size in MB"
    )
    allowed_extensions: Optional[List[str]] = Field(
        default=None, description="Allowed file extensions (None = all)"
    )


# =============================================================================
# Personality Schemas
# =============================================================================


class PersonalityBlockConfig(BaseModel):
    """Configuration for a personality block."""

    type: Literal["trait", "emotion", "behavior"] = Field(
        ..., description="Type of personality block"
    )
    name: str = Field(..., min_length=1, max_length=50, description="Block name")
    intensity: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Intensity of the trait (0.0 to 1.0)"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Additional parameters"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and normalize the personality block name."""
        return v.lower().strip()


# =============================================================================
# Competency Schemas
# =============================================================================


class CompetencyConfig(BaseModel):
    """Configuration for an agent competency."""

    name: str = Field(..., min_length=1, max_length=100, description="Competency name")
    level: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Competency level (0.0 to 1.0)"
    )
    description: Optional[str] = Field(
        default=None, max_length=500, description="Competency description"
    )
    keywords: List[str] = Field(
        default_factory=list, description="Keywords associated with this competency"
    )


# =============================================================================
# LLM Provider Schemas
# =============================================================================


class LLMProviderConfig(BaseModel):
    """Base configuration for LLM providers."""

    provider: LLMProviderType = Field(..., description="LLM provider type")
    model: str = Field(..., min_length=1, description="Model name")
    api_key: Optional[str] = Field(
        default=None, description="API key (loaded from env if not provided)"
    )
    temperature: float = Field(
        default=0.7, ge=0.0, le=2.0, description="Sampling temperature"
    )
    max_tokens: Optional[int] = Field(
        default=None, ge=1, le=100000, description="Maximum tokens in response"
    )
    timeout: int = Field(default=60, ge=1, le=600, description="Request timeout in seconds")

    class Config:
        use_enum_values = True


class OpenAIProviderConfig(LLMProviderConfig):
    """OpenAI-specific provider configuration."""

    provider: Literal[LLMProviderType.OPENAI] = LLMProviderType.OPENAI
    model: str = Field(default="gpt-4", description="OpenAI model name")
    org_id: Optional[str] = Field(default=None, description="OpenAI organization ID")


class AnthropicProviderConfig(LLMProviderConfig):
    """Anthropic-specific provider configuration."""

    provider: Literal[LLMProviderType.ANTHROPIC] = LLMProviderType.ANTHROPIC
    model: str = Field(default="claude-3-opus-20240229", description="Anthropic model name")


class OllamaProviderConfig(LLMProviderConfig):
    """Ollama-specific provider configuration."""

    provider: Literal[LLMProviderType.OLLAMA] = LLMProviderType.OLLAMA
    model: str = Field(default="llama2", description="Ollama model name")
    base_url: str = Field(
        default="http://localhost:11434", description="Ollama server URL"
    )


# =============================================================================
# Agent Schemas
# =============================================================================


class AgentConfig(BaseModel):
    """Complete configuration for an agent."""

    # Identity
    name: str = Field(
        ..., min_length=1, max_length=100, description="Agent name"
    )
    age: Optional[int] = Field(
        default=None, ge=0, le=200, description="Agent age"
    )
    history: str = Field(
        default="", max_length=5000, description="Agent background/history"
    )
    description: Optional[str] = Field(
        default=None, max_length=1000, description="Agent description"
    )

    # LLM Configuration
    llm_provider: LLMProviderType = Field(..., description="LLM provider to use")
    model: str = Field(..., min_length=1, description="Model name")
    api_key: Optional[str] = Field(
        default=None, description="API key (uses env variable if not provided)"
    )

    # Personality
    personality_blocks: List[str] = Field(
        default_factory=list, description="List of personality trait names"
    )

    # Competencies
    competencies: List[str] = Field(
        default_factory=list, description="List of competency names"
    )

    # Tools
    tools: List[str] = Field(
        default_factory=list, description="List of tool names to enable"
    )

    # Advanced settings
    temperature: float = Field(
        default=0.7, ge=0.0, le=2.0, description="LLM temperature"
    )
    max_tokens: Optional[int] = Field(
        default=None, ge=1, description="Max response tokens"
    )
    system_prompt_prefix: Optional[str] = Field(
        default=None, max_length=2000, description="Prefix for system prompt"
    )
    system_prompt_suffix: Optional[str] = Field(
        default=None, max_length=2000, description="Suffix for system prompt"
    )

    class Config:
        use_enum_values = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate agent name."""
        v = v.strip()
        if not v:
            raise ValueError("Agent name cannot be empty")
        return v

    @field_validator("personality_blocks")
    @classmethod
    def validate_personality_blocks(cls, v: List[str]) -> List[str]:
        """Normalize personality block names."""
        return [block.lower().strip() for block in v]

    @model_validator(mode="after")
    def validate_model(self) -> "AgentConfig":
        """Validate model configuration based on provider."""
        provider = self.llm_provider
        model = self.model

        # Provider-specific model validation
        if provider == LLMProviderType.OPENAI:
            valid_prefixes = ("gpt-", "o1-", "text-", "davinci", "curie", "babbage", "ada")
            if not any(model.startswith(p) for p in valid_prefixes):
                # Just a warning, don't block - new models appear frequently
                pass

        elif provider == LLMProviderType.ANTHROPIC:
            valid_prefixes = ("claude-",)
            if not any(model.startswith(p) for p in valid_prefixes):
                pass

        return self


# =============================================================================
# Conversation Schemas
# =============================================================================


class ConversationConfig(BaseModel):
    """Configuration for a conversation."""

    agent_ids: List[str] = Field(
        ..., min_length=1, description="List of agent IDs to include"
    )
    max_turns: Optional[int] = Field(
        default=None, ge=1, le=1000, description="Maximum conversation turns"
    )
    save_history: bool = Field(
        default=True, description="Whether to save conversation history"
    )
    history_path: Optional[str] = Field(
        default=None, description="Path to save history"
    )


# =============================================================================
# Message Schemas
# =============================================================================


class MessageRole(str, Enum):
    """Valid message roles."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class MessageConfig(BaseModel):
    """Configuration for a message."""

    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., min_length=1, description="Message content")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    class Config:
        use_enum_values = True


# =============================================================================
# Utility Functions
# =============================================================================


def validate_agent_config(config: Dict[str, Any]) -> AgentConfig:
    """
    Validate and parse an agent configuration dictionary.

    Args:
        config: Raw configuration dictionary

    Returns:
        Validated AgentConfig

    Raises:
        ValidationError: If configuration is invalid
    """
    return AgentConfig(**config)


def validate_tool_config(config: Dict[str, Any]) -> ToolConfig:
    """
    Validate and parse a tool configuration dictionary.

    Args:
        config: Raw configuration dictionary

    Returns:
        Validated ToolConfig (or subclass)

    Raises:
        ValidationError: If configuration is invalid
    """
    tool_type = config.get("type", "").lower()

    if tool_type == "calculator":
        return CalculatorToolConfig(**config)
    elif tool_type == "filesystem":
        return FileSystemToolConfig(**config)
    else:
        return ToolConfig(**config)
