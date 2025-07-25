"""
Core module for GatheRing framework.
Contains all base interfaces and implementations.
"""

from core.interfaces import (
    IAgent,
    ILLMProvider,
    ITool,
    IPersonalityBlock,
    ICompetency,
    IMemory,
    IConversation,
    IAgentManager,
    IToolRegistry,
    Message,
    ToolResult,
    ToolPermission,
)

from core.exceptions import (
    GatheringError,
    ConfigurationError,
    AgentError,
    LLMProviderError,
    ToolExecutionError,
    PermissionError,
    MemoryError,
    PersonalityError,
    CompetencyError,
    ConversationError,
    RegistryError,
    ValidationError,
)

from core.implementations import (
    BasicAgent,
    BasicMemory,
    MockLLMProvider,
    BasicPersonalityBlock,
    BasicConversation,
    CalculatorTool,
    FileSystemTool,
)

__all__ = [
    # Interfaces
    "IAgent",
    "ILLMProvider",
    "ITool",
    "IPersonalityBlock",
    "ICompetency",
    "IMemory",
    "IConversation",
    "IAgentManager",
    "IToolRegistry",
    # Data classes
    "Message",
    "ToolResult",
    "ToolPermission",
    # Exceptions
    "GatheringError",
    "ConfigurationError",
    "AgentError",
    "LLMProviderError",
    "ToolExecutionError",
    "PermissionError",
    "MemoryError",
    "PersonalityError",
    "CompetencyError",
    "ConversationError",
    "RegistryError",
    "ValidationError",
    # Basic implementations
    "BasicAgent",
    "BasicMemory",
    "MockLLMProvider",
    "BasicPersonalityBlock",
    "BasicConversation",
    "CalculatorTool",
    "FileSystemTool",
]
