"""
Custom exceptions for the GatheRing framework.
"""

from typing import Optional, Any, Dict


class GatheringError(Exception):
    """Base exception for all GatheRing errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(GatheringError):
    """Raised when configuration is invalid or incomplete."""

    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = value
        super().__init__(message, details)


class AgentError(GatheringError):
    """Base exception for agent-related errors."""

    def __init__(self, message: str, agent_id: Optional[str] = None, agent_name: Optional[str] = None):
        details = {}
        if agent_id:
            details["agent_id"] = agent_id
        if agent_name:
            details["agent_name"] = agent_name
        super().__init__(message, details)


class LLMProviderError(GatheringError):
    """Raised when LLM provider encounters an error."""

    def __init__(self, message: str, provider: Optional[str] = None, status_code: Optional[int] = None):
        details = {}
        if provider:
            details["provider"] = provider
        if status_code:
            details["status_code"] = status_code
        super().__init__(message, details)


class ToolExecutionError(GatheringError):
    """Raised when tool execution fails."""

    def __init__(
        self, message: str, tool_name: Optional[str] = None, input_data: Any = None, error_type: Optional[str] = None
    ):
        details = {}
        if tool_name:
            details["tool_name"] = tool_name
        if input_data is not None:
            details["input_data"] = input_data
        if error_type:
            details["error_type"] = error_type
        super().__init__(message, details)


class PermissionError(ToolExecutionError):
    """Raised when a tool operation is not permitted."""

    def __init__(self, message: str, tool_name: str, required_permission: str):
        super().__init__(message, tool_name=tool_name, error_type="permission_denied")
        self.details["required_permission"] = required_permission


class MemoryError(GatheringError):
    """Raised when memory operations fail."""

    def __init__(self, message: str, operation: Optional[str] = None):
        details = {}
        if operation:
            details["operation"] = operation
        super().__init__(message, details)


class PersonalityError(GatheringError):
    """Raised when personality block operations fail."""

    def __init__(self, message: str, block_type: Optional[str] = None, block_name: Optional[str] = None):
        details = {}
        if block_type:
            details["block_type"] = block_type
        if block_name:
            details["block_name"] = block_name
        super().__init__(message, details)


class CompetencyError(GatheringError):
    """Raised when competency operations fail."""

    def __init__(self, message: str, competency_name: Optional[str] = None):
        details = {}
        if competency_name:
            details["competency_name"] = competency_name
        super().__init__(message, details)


class ConversationError(GatheringError):
    """Raised when conversation operations fail."""

    def __init__(self, message: str, conversation_id: Optional[str] = None):
        details = {}
        if conversation_id:
            details["conversation_id"] = conversation_id
        super().__init__(message, details)


class RegistryError(GatheringError):
    """Raised when registry operations fail."""

    def __init__(self, message: str, registry_type: Optional[str] = None, item_name: Optional[str] = None):
        details = {}
        if registry_type:
            details["registry_type"] = registry_type
        if item_name:
            details["item_name"] = item_name
        super().__init__(message, details)


class ValidationError(GatheringError):
    """Raised when validation fails."""

    def __init__(self, message: str, validation_errors: Optional[Dict[str, Any]] = None):
        super().__init__(message, validation_errors)
