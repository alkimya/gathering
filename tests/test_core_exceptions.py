"""
Tests for gathering/core/exceptions.py - Custom exceptions.
"""

import pytest
from datetime import datetime

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
)


class TestGatheringError:
    """Test base GatheringError class."""

    def test_basic_creation(self):
        """Test creating a basic error."""
        err = GatheringError("Something went wrong")
        assert str(err) == "Something went wrong"
        assert err.message == "Something went wrong"
        assert err.details == {}
        assert isinstance(err.timestamp, datetime)
        assert err.traceback_str is None

    def test_with_details(self):
        """Test creating error with details."""
        err = GatheringError("Error", details={"key": "value", "count": 42})
        assert err.details["key"] == "value"
        assert err.details["count"] == 42
        # __str__ includes details
        assert "key=value" in str(err)

    def test_with_traceback(self):
        """Test creating error with traceback capture."""
        try:
            raise ValueError("original error")
        except ValueError:
            err = GatheringError("Wrapper error", capture_traceback=True)
            assert err.traceback_str is not None
            assert "ValueError" in err.traceback_str

    def test_to_dict(self):
        """Test converting to dictionary."""
        err = GatheringError("Test error", details={"foo": "bar"})
        d = err.to_dict()
        assert d["error_type"] == "GatheringError"
        assert d["message"] == "Test error"
        assert d["details"]["foo"] == "bar"
        assert "timestamp" in d
        assert d["traceback"] is None


class TestConfigurationError:
    """Test ConfigurationError class."""

    def test_basic_creation(self):
        """Test creating a configuration error."""
        err = ConfigurationError("Invalid config")
        assert err.message == "Invalid config"
        assert err.field is None
        assert err.value is None

    def test_with_field(self):
        """Test with field specified."""
        err = ConfigurationError("Invalid value", field="api_key")
        assert err.field == "api_key"
        assert "api_key" in err.details.get("field", "")

    def test_with_value(self):
        """Test with value specified."""
        err = ConfigurationError("Invalid value", field="port", value=99999)
        assert err.value == 99999
        assert "99999" in err.details.get("value", "")

    def test_with_expected(self):
        """Test with expected value."""
        err = ConfigurationError(
            "Invalid port",
            field="port",
            value=-1,
            expected="positive integer",
        )
        assert err.expected == "positive integer"
        assert err.details["expected"] == "positive integer"


class TestAgentError:
    """Test AgentError class."""

    def test_basic_creation(self):
        """Test creating an agent error."""
        err = AgentError("Agent failed")
        assert err.message == "Agent failed"
        assert err.agent_id is None
        assert err.agent_name is None

    def test_with_agent_info(self):
        """Test with agent info."""
        err = AgentError(
            "Processing failed",
            agent_id="agent-123",
            agent_name="Claude",
        )
        assert err.agent_id == "agent-123"
        assert err.agent_name == "Claude"
        assert err.details["agent_id"] == "agent-123"
        assert err.details["agent_name"] == "Claude"


class TestLLMProviderError:
    """Test LLMProviderError class."""

    def test_basic_creation(self):
        """Test creating an LLM provider error."""
        err = LLMProviderError("API call failed")
        assert err.message == "API call failed"
        assert err.provider is None
        assert err.status_code is None

    def test_with_provider_info(self):
        """Test with provider information."""
        err = LLMProviderError(
            "Rate limited",
            provider="openai",
            status_code=429,
        )
        assert err.provider == "openai"
        assert err.status_code == 429
        assert err.details["provider"] == "openai"

    def test_response_body_truncation(self):
        """Test that long response bodies are truncated."""
        long_body = "x" * 1000
        err = LLMProviderError("Error", response_body=long_body)
        assert len(err.details["response_body"]) == 500

    def test_is_retryable_true(self):
        """Test is_retryable for retryable status codes."""
        for code in [429, 500, 502, 503, 504]:
            err = LLMProviderError("Error", status_code=code)
            assert err.is_retryable is True

    def test_is_retryable_false(self):
        """Test is_retryable for non-retryable status codes."""
        for code in [400, 401, 403, 404]:
            err = LLMProviderError("Error", status_code=code)
            assert err.is_retryable is False

    def test_is_retryable_no_status(self):
        """Test is_retryable with no status code."""
        err = LLMProviderError("Error")
        assert err.is_retryable is False

    def test_is_auth_error(self):
        """Test is_auth_error property."""
        err401 = LLMProviderError("Unauthorized", status_code=401)
        assert err401.is_auth_error is True

        err403 = LLMProviderError("Forbidden", status_code=403)
        assert err403.is_auth_error is True

        err429 = LLMProviderError("Rate limited", status_code=429)
        assert err429.is_auth_error is False

    def test_is_rate_limit(self):
        """Test is_rate_limit property."""
        err = LLMProviderError("Rate limited", status_code=429)
        assert err.is_rate_limit is True

        err2 = LLMProviderError("Server error", status_code=500)
        assert err2.is_rate_limit is False


class TestToolExecutionError:
    """Test ToolExecutionError class."""

    def test_basic_creation(self):
        """Test creating a tool execution error."""
        err = ToolExecutionError("Tool failed")
        assert err.message == "Tool failed"
        assert err.tool_name is None
        assert err.input_data is None

    def test_with_tool_info(self):
        """Test with tool information."""
        err = ToolExecutionError(
            "Execution failed",
            tool_name="calculator",
            error_type="runtime_error",
        )
        assert err.tool_name == "calculator"
        assert err.error_type == "runtime_error"

    def test_input_data_truncation(self):
        """Test that large input data is truncated."""
        large_input = {"data": "x" * 500}
        err = ToolExecutionError("Error", input_data=large_input)
        assert len(err.details["input_data"]) <= 203  # 200 + "..."


class TestToolPermissionError:
    """Test ToolPermissionError class."""

    def test_creation(self):
        """Test creating a permission error."""
        err = ToolPermissionError(
            "Permission denied",
            tool_name="file_writer",
            required_permission="write",
        )
        assert err.tool_name == "file_writer"
        assert err.required_permission == "write"
        assert err.error_type == "permission_denied"
        assert err.details["required_permission"] == "write"


class TestSecurityError:
    """Test SecurityError class."""

    def test_basic_creation(self):
        """Test creating a security error."""
        err = SecurityError("Security violation detected")
        assert err.message == "Security violation detected"
        assert err.error_type == "security_violation"

    def test_with_violation_type(self):
        """Test with violation type."""
        err = SecurityError(
            "Path traversal detected",
            tool_name="file_reader",
            violation_type="path_traversal",
        )
        assert err.tool_name == "file_reader"
        assert err.violation_type == "path_traversal"
        assert err.details["violation_type"] == "path_traversal"


class TestMemoryOperationError:
    """Test MemoryOperationError class."""

    def test_basic_creation(self):
        """Test creating a memory error."""
        err = MemoryOperationError("Memory operation failed")
        assert err.message == "Memory operation failed"
        assert err.operation is None

    def test_with_operation(self):
        """Test with operation specified."""
        err = MemoryOperationError("Failed to add", operation="add")
        assert err.operation == "add"
        assert err.details["operation"] == "add"


class TestPersonalityError:
    """Test PersonalityError class."""

    def test_basic_creation(self):
        """Test creating a personality error."""
        err = PersonalityError("Personality error")
        assert err.message == "Personality error"
        assert err.block_type is None
        assert err.block_name is None

    def test_with_block_info(self):
        """Test with block information."""
        err = PersonalityError(
            "Block creation failed",
            block_type="trait",
            block_name="curious",
        )
        assert err.block_type == "trait"
        assert err.block_name == "curious"


class TestCompetencyError:
    """Test CompetencyError class."""

    def test_basic_creation(self):
        """Test creating a competency error."""
        err = CompetencyError("Competency error")
        assert err.message == "Competency error"
        assert err.competency_name is None

    def test_with_competency_name(self):
        """Test with competency name."""
        err = CompetencyError("Invalid level", competency_name="python")
        assert err.competency_name == "python"
        assert err.details["competency_name"] == "python"


class TestConversationError:
    """Test ConversationError class."""

    def test_basic_creation(self):
        """Test creating a conversation error."""
        err = ConversationError("Conversation error")
        assert err.message == "Conversation error"
        assert err.conversation_id is None

    def test_with_conversation_id(self):
        """Test with conversation ID."""
        err = ConversationError("Not found", conversation_id="conv-123")
        assert err.conversation_id == "conv-123"
        assert err.details["conversation_id"] == "conv-123"


class TestRegistryError:
    """Test RegistryError class."""

    def test_basic_creation(self):
        """Test creating a registry error."""
        err = RegistryError("Registry error")
        assert err.message == "Registry error"
        assert err.registry_type is None
        assert err.item_name is None

    def test_with_registry_info(self):
        """Test with registry information."""
        err = RegistryError(
            "Item not found",
            registry_type="tool",
            item_name="calculator",
        )
        assert err.registry_type == "tool"
        assert err.item_name == "calculator"


class TestValidationError:
    """Test ValidationError class."""

    def test_basic_creation(self):
        """Test creating a validation error."""
        err = ValidationError("Validation failed")
        assert err.message == "Validation failed"
        assert err.validation_errors == {}

    def test_with_validation_errors(self):
        """Test with validation errors."""
        errors = {
            "name": "required",
            "age": "must be positive",
        }
        err = ValidationError("Invalid input", validation_errors=errors)
        assert err.validation_errors == errors

    def test_get_error_messages_simple(self):
        """Test get_error_messages with simple errors."""
        errors = {
            "name": "required",
            "email": "invalid format",
        }
        err = ValidationError("Invalid input", validation_errors=errors)
        messages = err.get_error_messages()
        assert len(messages) == 2
        assert "name: required" in messages
        assert "email: invalid format" in messages

    def test_get_error_messages_with_list(self):
        """Test get_error_messages with list errors."""
        errors = {
            "name": ["required", "too short"],
            "age": "must be positive",
        }
        err = ValidationError("Invalid input", validation_errors=errors)
        messages = err.get_error_messages()
        assert len(messages) == 3
        assert "name: required" in messages
        assert "name: too short" in messages
        assert "age: must be positive" in messages


class TestExceptionInheritance:
    """Test exception inheritance hierarchy."""

    def test_all_inherit_from_gathering_error(self):
        """Test all exceptions inherit from GatheringError."""
        exceptions = [
            ConfigurationError("test"),
            AgentError("test"),
            LLMProviderError("test"),
            ToolExecutionError("test"),
            ToolPermissionError("test", "tool", "perm"),
            SecurityError("test"),
            MemoryOperationError("test"),
            PersonalityError("test"),
            CompetencyError("test"),
            ConversationError("test"),
            RegistryError("test"),
            ValidationError("test"),
        ]
        for err in exceptions:
            assert isinstance(err, GatheringError)

    def test_tool_errors_inherit_properly(self):
        """Test tool error inheritance."""
        perm_err = ToolPermissionError("test", "tool", "write")
        sec_err = SecurityError("test")

        assert isinstance(perm_err, ToolExecutionError)
        assert isinstance(sec_err, ToolExecutionError)

    def test_can_be_caught_as_exception(self):
        """Test exceptions can be caught as base Exception."""
        try:
            raise GatheringError("test")
        except Exception as e:
            assert isinstance(e, GatheringError)
