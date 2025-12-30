"""
Core module for GatheRing framework.
Contains all base interfaces, implementations, and utilities.

Usage:
    from gathering.core import BasicAgent, CalculatorTool
    from gathering.core.config import get_settings
    from gathering.core.schemas import AgentConfig
"""

# Interfaces
from gathering.core.interfaces import (
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

# Exceptions
from gathering.core.exceptions import (
    GatheringError,
    ConfigurationError,
    AgentError,
    LLMProviderError,
    ToolExecutionError,
    ToolPermissionError,
    SecurityError,
    MemoryOperationError,
    PersonalityError,
    CompetencyError,
    ConversationError,
    RegistryError,
    ValidationError,
    # Backward compatibility aliases
    PermissionError,
    MemoryError,
)

# Implementations
from gathering.core.implementations import (
    BasicAgent,
    BasicMemory,
    MockLLMProvider,
    BasicPersonalityBlock,
    BasicConversation,
    CalculatorTool,
    FileSystemTool,
    SafeExpressionEvaluator,
    PathTraversalError,
)

__all__ = [
    # ==========================================================================
    # Interfaces (Abstract Base Classes)
    # ==========================================================================
    "IAgent",
    "ILLMProvider",
    "ITool",
    "IPersonalityBlock",
    "ICompetency",
    "IMemory",
    "IConversation",
    "IAgentManager",
    "IToolRegistry",
    # ==========================================================================
    # Data Classes
    # ==========================================================================
    "Message",
    "ToolResult",
    "ToolPermission",
    # ==========================================================================
    # Exceptions
    # ==========================================================================
    "GatheringError",
    "ConfigurationError",
    "AgentError",
    "LLMProviderError",
    "ToolExecutionError",
    "ToolPermissionError",
    "SecurityError",
    "MemoryOperationError",
    "PersonalityError",
    "CompetencyError",
    "ConversationError",
    "RegistryError",
    "ValidationError",
    # Backward compatibility
    "PermissionError",
    "MemoryError",
    # ==========================================================================
    # Basic Implementations
    # ==========================================================================
    "BasicAgent",
    "BasicMemory",
    "MockLLMProvider",
    "BasicPersonalityBlock",
    "BasicConversation",
    # ==========================================================================
    # Tools
    # ==========================================================================
    "CalculatorTool",
    "FileSystemTool",
    "SafeExpressionEvaluator",
    "PathTraversalError",
]
