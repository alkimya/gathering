"""
Custom exceptions for the GatheRing framework.

This module provides a hierarchy of exceptions for different error scenarios:

- GatheringError: Base exception for all framework errors
  - ConfigurationError: Invalid or incomplete configuration
  - AgentError: Agent-related errors
  - LLMProviderError: LLM provider issues (API errors, timeouts)
  - ToolExecutionError: Tool execution failures
    - PermissionError: Permission denied for tool operation
    - SecurityError: Security violation detected
  - MemoryError: Memory system errors
  - PersonalityError: Personality block errors
  - CompetencyError: Competency errors
  - ConversationError: Conversation errors
  - RegistryError: Registry operations errors
  - ValidationError: Input validation errors
  - AuthenticationError: Authentication failures (invalid credentials, expired token)
  - AuthorizationError: Insufficient permissions for an action
  - DatabaseError: Database operation failures
"""

from typing import Optional, Any, Dict
from datetime import datetime
import traceback


class GatheringError(Exception):
    """
    Base exception for all GatheRing errors.

    Attributes:
        message: Human-readable error message
        details: Dictionary with additional context
        timestamp: When the error occurred
        traceback_str: Optional traceback string
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        capture_traceback: bool = False,
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now()
        self.traceback_str: Optional[str] = None

        if capture_traceback:
            self.traceback_str = traceback.format_exc()

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to a dictionary for logging/serialization."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "traceback": self.traceback_str,
        }

    def __str__(self) -> str:
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, details={self.details!r})"


class ConfigurationError(GatheringError):
    """
    Raised when configuration is invalid or incomplete.

    Attributes:
        field: The configuration field that caused the error
        value: The invalid value (if applicable)
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
        expected: Optional[str] = None,
    ):
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = repr(value)
        if expected:
            details["expected"] = expected

        super().__init__(message, details)
        self.field = field
        self.value = value
        self.expected = expected


class AgentError(GatheringError):
    """
    Base exception for agent-related errors.

    Attributes:
        agent_id: The ID of the agent that encountered the error
        agent_name: The name of the agent
    """

    def __init__(
        self,
        message: str,
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None,
    ):
        details = {}
        if agent_id:
            details["agent_id"] = agent_id
        if agent_name:
            details["agent_name"] = agent_name

        super().__init__(message, details)
        self.agent_id = agent_id
        self.agent_name = agent_name


class LLMProviderError(GatheringError):
    """
    Raised when LLM provider encounters an error.

    Attributes:
        provider: The name of the LLM provider
        status_code: HTTP status code (if applicable)
        is_retryable: Whether the error might be resolved by retrying
    """

    # Status codes that indicate retryable errors
    RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ):
        details = {}
        if provider:
            details["provider"] = provider
        if status_code:
            details["status_code"] = status_code
        if response_body:
            # Truncate long responses
            details["response_body"] = response_body[:500]

        super().__init__(message, details)
        self.provider = provider
        self.status_code = status_code
        self.response_body = response_body

    @property
    def is_retryable(self) -> bool:
        """Check if this error might be resolved by retrying."""
        if self.status_code:
            return self.status_code in self.RETRYABLE_STATUS_CODES
        return False

    @property
    def is_auth_error(self) -> bool:
        """Check if this is an authentication error."""
        return self.status_code in {401, 403}

    @property
    def is_rate_limit(self) -> bool:
        """Check if this is a rate limit error."""
        return self.status_code == 429


class ToolExecutionError(GatheringError):
    """
    Raised when tool execution fails.

    Attributes:
        tool_name: The name of the tool that failed
        input_data: The input that caused the failure
        error_type: Category of the error
    """

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        input_data: Any = None,
        error_type: Optional[str] = None,
    ):
        details = {}
        if tool_name:
            details["tool_name"] = tool_name
        if input_data is not None:
            # Truncate large inputs
            input_str = repr(input_data)
            if len(input_str) > 200:
                input_str = input_str[:200] + "..."
            details["input_data"] = input_str
        if error_type:
            details["error_type"] = error_type

        super().__init__(message, details)
        self.tool_name = tool_name
        self.input_data = input_data
        self.error_type = error_type


class ToolPermissionError(ToolExecutionError):
    """
    Raised when a tool operation is not permitted.

    Attributes:
        required_permission: The permission that was required
    """

    def __init__(self, message: str, tool_name: str, required_permission: str):
        super().__init__(message, tool_name=tool_name, error_type="permission_denied")
        self.details["required_permission"] = required_permission
        self.required_permission = required_permission


class SecurityError(ToolExecutionError):
    """
    Raised when a security violation is detected.

    This includes:
    - Path traversal attempts
    - Code injection attempts
    - Access to blocked resources
    """

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        violation_type: Optional[str] = None,
    ):
        super().__init__(
            message,
            tool_name=tool_name,
            error_type="security_violation",
        )
        if violation_type:
            self.details["violation_type"] = violation_type
        self.violation_type = violation_type


class MemoryOperationError(GatheringError):
    """
    Raised when memory operations fail.

    Attributes:
        operation: The operation that failed (add, search, clear, etc.)
    """

    def __init__(self, message: str, operation: Optional[str] = None):
        details = {}
        if operation:
            details["operation"] = operation

        super().__init__(message, details)
        self.operation = operation


class PersonalityError(GatheringError):
    """
    Raised when personality block operations fail.

    Attributes:
        block_type: The type of personality block
        block_name: The name of the personality block
    """

    def __init__(
        self,
        message: str,
        block_type: Optional[str] = None,
        block_name: Optional[str] = None,
    ):
        details = {}
        if block_type:
            details["block_type"] = block_type
        if block_name:
            details["block_name"] = block_name

        super().__init__(message, details)
        self.block_type = block_type
        self.block_name = block_name


class CompetencyError(GatheringError):
    """
    Raised when competency operations fail.

    Attributes:
        competency_name: The name of the competency
    """

    def __init__(self, message: str, competency_name: Optional[str] = None):
        details = {}
        if competency_name:
            details["competency_name"] = competency_name

        super().__init__(message, details)
        self.competency_name = competency_name


class ConversationError(GatheringError):
    """
    Raised when conversation operations fail.

    Attributes:
        conversation_id: The ID of the conversation
    """

    def __init__(self, message: str, conversation_id: Optional[str] = None):
        details = {}
        if conversation_id:
            details["conversation_id"] = conversation_id

        super().__init__(message, details)
        self.conversation_id = conversation_id


class RegistryError(GatheringError):
    """
    Raised when registry operations fail.

    Attributes:
        registry_type: The type of registry (tool, agent, etc.)
        item_name: The name of the item that caused the error
    """

    def __init__(
        self,
        message: str,
        registry_type: Optional[str] = None,
        item_name: Optional[str] = None,
    ):
        details = {}
        if registry_type:
            details["registry_type"] = registry_type
        if item_name:
            details["item_name"] = item_name

        super().__init__(message, details)
        self.registry_type = registry_type
        self.item_name = item_name


class ValidationError(GatheringError):
    """
    Raised when input validation fails.

    Attributes:
        validation_errors: Dictionary mapping field names to error messages
    """

    def __init__(
        self,
        message: str,
        validation_errors: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, validation_errors)
        self.validation_errors = validation_errors or {}

    def get_error_messages(self) -> list[str]:
        """Get a list of all validation error messages."""
        messages = []
        for field, error in self.validation_errors.items():
            if isinstance(error, list):
                for e in error:
                    messages.append(f"{field}: {e}")
            else:
                messages.append(f"{field}: {error}")
        return messages


class AuthenticationError(GatheringError):
    """Raised when authentication fails (invalid credentials, expired token, etc.)."""

    def __init__(self, message: str, reason: Optional[str] = None):
        details = {}
        if reason:
            details["reason"] = reason
        super().__init__(message, details)
        self.reason = reason


class AuthorizationError(GatheringError):
    """Raised when an authenticated user lacks permission for an action."""

    def __init__(
        self,
        message: str,
        required_role: Optional[str] = None,
        user_role: Optional[str] = None,
    ):
        details = {}
        if required_role:
            details["required_role"] = required_role
        if user_role:
            details["user_role"] = user_role
        super().__init__(message, details)
        self.required_role = required_role
        self.user_role = user_role


class DatabaseError(GatheringError):
    """Raised when database operations fail unexpectedly."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        table: Optional[str] = None,
    ):
        details = {}
        if operation:
            details["operation"] = operation
        if table:
            details["table"] = table
        super().__init__(message, details)
        self.operation = operation
        self.table = table


# =============================================================================
# Backward Compatibility Aliases
# =============================================================================

# Keep old names as aliases for backward compatibility
PermissionError = ToolPermissionError  # noqa: A001 (shadowing builtin intentionally)
MemoryError = MemoryOperationError  # noqa: A001 (shadowing builtin intentionally)
