"""
Basic implementations of core interfaces to make tests pass.
These will be refactored and enhanced in subsequent iterations.
"""

import json
import asyncio
import ast
import operator
from typing import List, Dict, Any, Optional, Union, AsyncGenerator
from datetime import datetime
from pathlib import Path
import re

from gathering.core.interfaces import (
    IAgent,
    ILLMProvider,
    ITool,
    IPersonalityBlock,
    ICompetency,
    IMemory,
    IConversation,
    Message,
    ToolResult,
    ToolPermission,
)
from gathering.core.exceptions import (
    ConfigurationError,
    LLMProviderError,
    ToolExecutionError,
    PermissionError,
    ValidationError,
)


class BasicMemory(IMemory):
    """Simple in-memory implementation of IMemory."""

    def __init__(self):
        self.messages: List[Message] = []

    def add_message(self, message: Message) -> None:
        self.messages.append(message)

    def get_conversation_history(self, limit: Optional[int] = None) -> List[Message]:
        if limit:
            return self.messages[-limit:]
        return self.messages.copy()

    def search(self, query: str, limit: int = 10) -> List[Message]:
        """Simple keyword search."""
        query_lower = query.lower()
        results = []
        for msg in reversed(self.messages):
            if query_lower in msg.content.lower():
                results.append(msg)
                if len(results) >= limit:
                    break
        return results

    def clear(self) -> None:
        self.messages.clear()

    def get_context_window(self, max_tokens: int = 4000) -> List[Message]:
        """Approximate token counting - 4 chars per token."""
        result = []
        total_chars = 0

        for msg in reversed(self.messages):
            msg_chars = len(msg.content) + len(msg.role) + 10  # overhead
            if total_chars + msg_chars > max_tokens * 4:
                break
            result.insert(0, msg)
            total_chars += msg_chars

        return result


class MockLLMProvider(ILLMProvider):
    """Mock LLM provider for testing."""

    @classmethod
    def create(cls, provider_name: str, config: Dict[str, Any]) -> "ILLMProvider":
        return cls(provider_name, config)

    def complete(
        self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None, **kwargs
    ) -> Dict[str, Any]:

        # Validate API key for testing
        if self.config.get("api_key") == "invalid_key":
            raise LLMProviderError("Invalid API key", provider=self.name, status_code=401)

        # Simple mock responses based on last message
        last_msg = messages[-1]["content"].lower()

        # Tool calling logic
        if tools and "weather" in last_msg:
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [{"name": "get_weather", "arguments": {"location": "Paris"}}],
            }

        # Memory test responses
        if "my name is" in last_msg:
            return {"role": "assistant", "content": "Nice to meet you! I'll remember your name."}
        elif "what is my name" in last_msg:
            # Search for name in previous messages
            for msg in messages:
                if "my name is" in msg.get("content", "").lower():
                    name = msg["content"].split("is")[-1].strip().rstrip(".")
                    return {"role": "assistant", "content": f"Your name is {name}."}
            return {"role": "assistant", "content": "I don't recall you telling me your name."}

        # Default response
        return {"role": "assistant", "content": f"I understand you said: {messages[-1]['content']}"}

    async def stream(
        self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None, **kwargs
    ) -> AsyncGenerator[str, None]:
        response = self.complete(messages, tools, **kwargs)
        content = response.get("content", "")

        # Simulate streaming by yielding words
        words = content.split()
        for word in words:
            yield word + " "
            await asyncio.sleep(0.01)

    def is_available(self) -> bool:
        return self.config.get("api_key") != "invalid_key"

    def get_token_count(self, text: str) -> int:
        # Rough approximation: 4 chars = 1 token
        return len(text) // 4

    def get_max_tokens(self) -> int:
        model_limits = {"gpt-4": 8000, "claude-3": 100000, "llama2": 4000}
        # Fixed: Use str key instead of Any | None
        model_name = str(self.model) if self.model else "default"
        return model_limits.get(model_name, 4000)


class SafeExpressionEvaluator:
    """
    Safe mathematical expression evaluator using AST parsing.
    Only allows basic arithmetic operations, no code execution.
    """

    # Supported operators
    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    # Maximum allowed values to prevent resource exhaustion
    MAX_VALUE = 10**100
    MAX_POWER = 1000

    @classmethod
    def evaluate(cls, expression: str) -> float:
        """
        Safely evaluate a mathematical expression.

        Args:
            expression: A string containing a mathematical expression

        Returns:
            The result of the evaluation

        Raises:
            ValueError: If the expression is invalid or contains disallowed operations
        """
        if not expression or not isinstance(expression, str):
            raise ValueError("Expression must be a non-empty string")

        # Limit expression length to prevent DoS
        if len(expression) > 1000:
            raise ValueError("Expression too long (max 1000 characters)")

        # Clean the expression
        expression = expression.strip()

        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as e:
            raise ValueError(f"Invalid expression syntax: {e}")

        return cls._evaluate_node(tree.body)

    @classmethod
    def _evaluate_node(cls, node: ast.AST) -> float:
        """Recursively evaluate an AST node."""
        if isinstance(node, ast.Constant):
            # Python 3.8+ uses ast.Constant for numbers
            if isinstance(node.value, (int, float)):
                if abs(node.value) > cls.MAX_VALUE:
                    raise ValueError(f"Number too large (max {cls.MAX_VALUE})")
                return float(node.value)
            raise ValueError(f"Unsupported constant type: {type(node.value).__name__}")

        # Note: ast.Num is deprecated in Python 3.8+ in favor of ast.Constant
        # We only handle ast.Constant above, which covers Python 3.8+

        elif isinstance(node, ast.BinOp):
            left = cls._evaluate_node(node.left)
            right = cls._evaluate_node(node.right)

            op_type = type(node.op)
            if op_type not in cls.OPERATORS:
                raise ValueError(f"Unsupported operator: {op_type.__name__}")

            # Special check for power operations
            if op_type == ast.Pow:
                if abs(right) > cls.MAX_POWER:
                    raise ValueError(f"Exponent too large (max {cls.MAX_POWER})")

            # Special check for division by zero
            if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
                raise ValueError("Division by zero")

            result = cls.OPERATORS[op_type](left, right)

            if abs(result) > cls.MAX_VALUE:
                raise ValueError(f"Result too large (max {cls.MAX_VALUE})")

            return result

        elif isinstance(node, ast.UnaryOp):
            operand = cls._evaluate_node(node.operand)
            op_type = type(node.op)

            if op_type not in cls.OPERATORS:
                raise ValueError(f"Unsupported unary operator: {op_type.__name__}")

            return cls.OPERATORS[op_type](operand)

        elif isinstance(node, ast.Expression):
            return cls._evaluate_node(node.body)

        else:
            raise ValueError(f"Unsupported expression type: {type(node).__name__}")


class CalculatorTool(ITool):
    """
    Secure calculator tool implementation.
    Uses AST-based evaluation instead of eval() to prevent code injection.
    """

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "ITool":
        return cls(config["name"], config.get("type", "calculator"), config)

    def execute(self, input_data: Any) -> ToolResult:
        """
        Execute a mathematical calculation.

        Supports:
        - Basic arithmetic: +, -, *, /, //, %, **
        - Parentheses for grouping
        - Percentage expressions: "15% of 2500"
        - Negative numbers

        Args:
            input_data: A string expression to evaluate

        Returns:
            ToolResult with the calculation result or error
        """
        if not isinstance(input_data, str):
            return ToolResult(
                success=False,
                output=None,
                error="Input must be a string expression",
            )

        try:
            expression = input_data.strip()

            # Handle percentage expressions: "15% of 2500"
            percentage_match = re.match(
                r"^\s*(\d+(?:\.\d+)?)\s*%\s*of\s*(\d+(?:\.\d+)?)\s*$",
                expression,
                re.IGNORECASE,
            )
            if percentage_match:
                percent = float(percentage_match.group(1))
                value = float(percentage_match.group(2))
                result = (percent / 100) * value
                return ToolResult(success=True, output=result)

            # Use safe AST-based evaluation
            result = SafeExpressionEvaluator.evaluate(expression)
            return ToolResult(success=True, output=result)

        except ValueError as e:
            return ToolResult(success=False, output=None, error=str(e))
        except (TypeError, AttributeError) as e:
            return ToolResult(success=False, output=None, error=f"Invalid expression: {e}")

    async def execute_async(self, input_data: Any) -> ToolResult:
        """Execute calculation asynchronously."""
        return self.execute(input_data)

    def validate_input(self, input_data: Any) -> bool:
        """Validate that input is a string."""
        return isinstance(input_data, str) and len(input_data) <= 1000

    def is_available(self) -> bool:
        """Calculator is always available."""
        return True

    def get_description(self) -> str:
        """Get tool description."""
        return "A secure calculator for basic mathematical operations (+, -, *, /, //, %, **)"

    def get_parameters_schema(self) -> Dict[str, Any]:
        """Get JSON schema for tool parameters."""
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate (e.g., '2 + 2', '15% of 2500')",
                    "maxLength": 1000,
                }
            },
            "required": ["expression"],
        }


class PathTraversalError(Exception):
    """Raised when a path traversal attack is detected."""

    pass


class FileSystemTool(ITool):
    """
    Secure filesystem tool implementation with path traversal protection.

    All file operations are sandboxed to the configured base_path.
    """

    # Maximum file size in bytes (10 MB default)
    MAX_FILE_SIZE = 10 * 1024 * 1024

    # Allowed file extensions (if None, all are allowed)
    ALLOWED_EXTENSIONS: Optional[set] = None

    # Blocked file patterns
    BLOCKED_PATTERNS = {
        ".env",
        ".git",
        ".ssh",
        "id_rsa",
        "id_ed25519",
        ".pem",
        ".key",
        "credentials",
        "secrets",
        "password",
        ".htpasswd",
        "shadow",
        "passwd",
    }

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "ITool":
        return cls(config["name"], "filesystem", config)

    def _get_base_path(self) -> Path:
        """Get the sandboxed base path for file operations."""
        base = self.config.get("base_path", "/tmp/gathering")
        return Path(base).resolve()

    def _validate_path(self, requested_path: str) -> Path:
        """
        Validate and resolve a path, ensuring it stays within the sandbox.

        Args:
            requested_path: The path requested by the user

        Returns:
            Resolved absolute path within the sandbox

        Raises:
            PathTraversalError: If the path attempts to escape the sandbox
            ValueError: If the path contains blocked patterns
        """
        if not requested_path:
            raise ValueError("Path cannot be empty")

        # Normalize the path string
        requested_path = requested_path.strip()

        # Check for obviously malicious patterns
        dangerous_patterns = ["..", "~", "${", "$(",  "%(", "`"]
        for pattern in dangerous_patterns:
            if pattern in requested_path:
                raise PathTraversalError(
                    f"Potentially dangerous pattern '{pattern}' detected in path"
                )

        # Check for blocked file patterns
        path_lower = requested_path.lower()
        for blocked in self.BLOCKED_PATTERNS:
            if blocked in path_lower:
                raise ValueError(f"Access to '{blocked}' files is not permitted")

        base_path = self._get_base_path()

        # Resolve the full path
        if Path(requested_path).is_absolute():
            # If absolute path, it must be within base_path
            full_path = Path(requested_path).resolve()
        else:
            # Relative path - join with base_path
            full_path = (base_path / requested_path).resolve()

        # Critical security check: ensure path is within sandbox
        try:
            full_path.relative_to(base_path)
        except ValueError:
            raise PathTraversalError(
                f"Path traversal detected: '{requested_path}' resolves outside sandbox"
            )

        return full_path

    def execute(self, input_data: Any) -> ToolResult:
        """
        Execute a filesystem operation.

        Supported actions:
        - read: Read file contents
        - write: Write content to a file
        - list: List directory contents
        - exists: Check if path exists
        - delete: Delete a file (requires DELETE permission)

        Args:
            input_data: Dict with 'action', 'path', and optionally 'content'

        Returns:
            ToolResult with operation outcome
        """
        if not isinstance(input_data, dict):
            return ToolResult(
                success=False,
                output=None,
                error="Input must be a dictionary with 'action' and 'path'",
            )

        action = input_data.get("action", "").lower()
        requested_path = input_data.get("path", "")

        # Validate the path first
        try:
            safe_path = self._validate_path(requested_path)
        except PathTraversalError as e:
            raise ToolExecutionError(
                str(e),
                tool_name=self.name,
                input_data=input_data,
                error_type="path_traversal",
            )
        except ValueError as e:
            return ToolResult(success=False, output=None, error=str(e))

        # Permission checks
        if action == "write" and not self.has_permission(ToolPermission.WRITE):
            raise ToolExecutionError(
                "Write permission denied",
                tool_name=self.name,
                error_type="permission_denied",
            )

        if action == "delete" and not self.has_permission(ToolPermission.DELETE):
            raise ToolExecutionError(
                "Delete permission denied",
                tool_name=self.name,
                error_type="permission_denied",
            )

        # Execute the action
        try:
            if action == "read":
                return self._read_file(safe_path)
            elif action == "write":
                content = input_data.get("content", "")
                return self._write_file(safe_path, content)
            elif action == "list":
                return self._list_directory(safe_path)
            elif action == "exists":
                return ToolResult(success=True, output=safe_path.exists())
            elif action == "delete":
                return self._delete_file(safe_path)
            else:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Unknown action: {action}. Supported: read, write, list, exists, delete",
                )
        except OSError as e:
            return ToolResult(success=False, output=None, error=f"OS error: {e}")

    def _read_file(self, path: Path) -> ToolResult:
        """Read file contents safely."""
        if not path.exists():
            return ToolResult(success=False, output=None, error=f"File not found: {path.name}")

        if not path.is_file():
            return ToolResult(success=False, output=None, error="Path is not a file")

        # Check file size
        if path.stat().st_size > self.MAX_FILE_SIZE:
            return ToolResult(
                success=False,
                output=None,
                error=f"File too large (max {self.MAX_FILE_SIZE // 1024 // 1024} MB)",
            )

        try:
            content = path.read_text(encoding="utf-8")
            return ToolResult(success=True, output=content)
        except UnicodeDecodeError:
            return ToolResult(
                success=False,
                output=None,
                error="Cannot read file: not a valid UTF-8 text file",
            )

    def _write_file(self, path: Path, content: str) -> ToolResult:
        """Write content to file safely."""
        # Check content size
        if len(content.encode("utf-8")) > self.MAX_FILE_SIZE:
            return ToolResult(
                success=False,
                output=None,
                error=f"Content too large (max {self.MAX_FILE_SIZE // 1024 // 1024} MB)",
            )

        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        path.write_text(content, encoding="utf-8")
        return ToolResult(success=True, output=f"File written: {path.name}")

    def _list_directory(self, path: Path) -> ToolResult:
        """List directory contents safely."""
        if not path.exists():
            return ToolResult(success=False, output=None, error=f"Directory not found: {path.name}")

        if not path.is_dir():
            return ToolResult(success=False, output=None, error="Path is not a directory")

        entries = []
        for entry in path.iterdir():
            entries.append({
                "name": entry.name,
                "is_file": entry.is_file(),
                "is_dir": entry.is_dir(),
                "size": entry.stat().st_size if entry.is_file() else None,
            })

        return ToolResult(success=True, output=entries)

    def _delete_file(self, path: Path) -> ToolResult:
        """Delete a file safely."""
        if not path.exists():
            return ToolResult(success=False, output=None, error=f"File not found: {path.name}")

        if not path.is_file():
            return ToolResult(success=False, output=None, error="Can only delete files, not directories")

        path.unlink()
        return ToolResult(success=True, output=f"File deleted: {path.name}")

    async def execute_async(self, input_data: Any) -> ToolResult:
        """Execute filesystem operation asynchronously."""
        return self.execute(input_data)

    def validate_input(self, input_data: Any) -> bool:
        """Validate input data structure."""
        if not isinstance(input_data, dict):
            return False
        if "action" not in input_data:
            return False
        if "path" not in input_data:
            return False
        if input_data["action"] == "write" and "content" not in input_data:
            return False
        return True

    def is_available(self) -> bool:
        """Check if the filesystem tool is available."""
        base_path = self._get_base_path()
        # Ensure base path exists or can be created
        try:
            base_path.mkdir(parents=True, exist_ok=True)
            return True
        except OSError:
            return False

    def get_description(self) -> str:
        """Get tool description."""
        return "Secure filesystem tool for reading, writing, and listing files within a sandboxed directory"

    def get_parameters_schema(self) -> Dict[str, Any]:
        """Get JSON schema for tool parameters."""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["read", "write", "list", "exists", "delete"],
                    "description": "The filesystem action to perform",
                },
                "path": {
                    "type": "string",
                    "description": "Relative path within the sandbox directory",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write (required for 'write' action)",
                },
            },
            "required": ["action", "path"],
        }


# Dummy tool for testing unknown types
class DummyTool(ITool):
    """Dummy tool for testing."""

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "ITool":
        return cls(config["name"], config.get("type", "dummy"), config)

    def execute(self, input_data: Any) -> ToolResult:
        return ToolResult(success=True, output="Dummy tool executed")

    async def execute_async(self, input_data: Any) -> ToolResult:
        return self.execute(input_data)

    def validate_input(self, input_data: Any) -> bool:
        return True

    def is_available(self) -> bool:
        return True

    def get_description(self) -> str:
        return "A dummy tool for testing"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}


class BasicPersonalityBlock(IPersonalityBlock):
    """Basic personality block implementation."""

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "IPersonalityBlock":
        return cls(config["type"], config["name"], config)

    def get_prompt_modifiers(self) -> str:
        modifiers = {
            "curious": "Be curious and ask questions to understand better.",
            "analytical": "Analyze information carefully and think step by step.",
            "empathetic": "Show understanding and empathy in responses.",
            "formal": "Maintain a professional and formal tone.",
            "creative": "Think creatively and explore innovative solutions.",
            "logical": "Apply logical reasoning and structured thinking.",
            "cheerful": "Be positive and cheerful in interactions.",
            "patient": "Be patient and thorough in explanations.",
            "knowledgeable": "Demonstrate deep knowledge and expertise.",
            "eager": "Show enthusiasm and eagerness to learn.",
        }

        base_modifier = modifiers.get(self.name, f"Be {self.name} in your responses.")

        # Adjust based on intensity
        if self.intensity > 0.7:
            return f"Strongly {base_modifier.lower()}"
        elif self.intensity < 0.3:
            return f"Subtly {base_modifier.lower()}"
        else:
            return base_modifier

    def influence_response(self, response: str) -> str:
        # Simple implementation - in real system would be more sophisticated
        return response


# Tool factory function
def create_tool_from_string(tool_name: str) -> Optional[ITool]:
    """Create a tool from a string name."""
    tool_map = {
        "calculator": lambda: CalculatorTool.from_config({"name": "calculator"}),
        "filesystem": lambda: FileSystemTool.from_config({"name": "filesystem", "permissions": ["read", "write"]}),
        "web_search": lambda: DummyTool.from_config({"name": "web_search", "type": "web_search"}),
        "database": lambda: DummyTool.from_config({"name": "database", "type": "database"}),
    }

    if tool_name in tool_map:
        return tool_map[tool_name]()
    return None


class BasicAgent(IAgent):
    """
    Basic agent implementation with LLM provider injection.

    Supports:
    - Multiple LLM providers via factory pattern
    - Competency-based task matching
    - Personality-influenced responses
    - Tool usage with proper tracking
    - Both sync and async message processing
    """

    # Default provider factory - can be overridden for testing
    _provider_factory = None

    @classmethod
    def set_provider_factory(cls, factory) -> None:
        """Set the provider factory for dependency injection."""
        cls._provider_factory = factory

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "IAgent":
        """
        Create an agent from configuration.

        Args:
            config: Agent configuration dictionary

        Required config keys:
            - name: Agent name
            - llm_provider: Provider name (openai, anthropic, ollama, mock)

        Optional config keys:
            - model: LLM model name
            - api_key: API key for the provider
            - age: Agent age
            - history: Agent background
            - tools: List of tool names
            - personality_blocks: List of personality trait names
            - competencies: List of competency names

        Returns:
            Configured BasicAgent instance

        Raises:
            ConfigurationError: If configuration is invalid
        """
        # Validate required fields
        if not config.get("name"):
            raise ConfigurationError("Agent name is required", field="name")
        if config.get("name") == "":
            raise ConfigurationError("Agent name cannot be empty", field="name")
        if not config.get("llm_provider"):
            raise ConfigurationError("LLM provider is required", field="llm_provider")

        age = config.get("age")
        if age is not None and age < 0:
            raise ConfigurationError("Age must be non-negative", field="age", value=age)

        # Validate provider - now includes 'mock' for testing
        valid_providers = ["openai", "anthropic", "ollama", "mock"]
        if config["llm_provider"] not in valid_providers:
            raise ConfigurationError(
                f"Invalid LLM provider: {config['llm_provider']}",
                field="llm_provider",
                value=config["llm_provider"],
            )

        # Create instance
        instance = cls(config)

        # Initialize tools from config
        tool_names = config.get("tools", [])
        for tool_name in tool_names:
            tool = create_tool_from_string(tool_name)
            if tool:
                instance.add_tool(tool)

        # Initialize personality blocks from config
        personality_names = config.get("personality_blocks", [])
        for block_name in personality_names:
            block = BasicPersonalityBlock.from_config({
                "type": "trait",
                "name": block_name,
                "intensity": 0.7,
            })
            instance.add_personality_block(block)

        # Initialize competencies from config
        competency_names = config.get("competencies", [])
        for comp_name in competency_names:
            try:
                from gathering.core.competencies import CompetencyRegistry
                competency = CompetencyRegistry.create(comp_name)
                instance.add_competency(competency)
            except Exception:
                # If competency module not available, skip
                pass

        return instance

    def _create_memory(self, config: Dict[str, Any]) -> IMemory:
        """Create memory system for the agent."""
        return BasicMemory()

    def _create_llm_provider(self, config: Dict[str, Any]) -> ILLMProvider:
        """
        Create LLM provider using factory pattern.

        Uses the configured provider factory if set, otherwise falls back
        to MockLLMProvider for backward compatibility.

        For development/testing, always uses MockLLMProvider unless a real
        API key is provided and the USE_REAL_LLM config is set.
        """
        provider_name = config.get("llm_provider", "mock")
        api_key = config.get("api_key", "test_key")

        provider_config = {
            "api_key": api_key,
            "model": config.get("model", "gpt-4"),
            "temperature": config.get("temperature", 0.7),
            "max_tokens": config.get("max_tokens"),
            "rate_limit_per_minute": config.get("rate_limit_per_minute", 60),
            "enable_cache": config.get("enable_cache", True),
        }

        # Use injected factory if available
        if self._provider_factory:
            return self._provider_factory.create(provider_name, provider_config)

        # Check if we should use real providers
        use_real_llm = config.get("use_real_llm", False)
        is_test_key = api_key in ("test_key", "test-key", None, "")

        # If it's a test key or not explicitly requesting real LLM, use mock
        if is_test_key or not use_real_llm:
            return MockLLMProvider.create(provider_name, provider_config)

        # Try to use LLMProviderFactory for real providers
        try:
            from gathering.llm.providers import LLMProviderFactory
            return LLMProviderFactory.create(provider_name, provider_config)
        except (ImportError, Exception):
            # Fall back to mock provider
            return MockLLMProvider.create(provider_name, provider_config)

    def _build_messages(self, user_message: str) -> List[Dict[str, str]]:
        """Build the message list for the LLM, including system prompt."""
        messages = []

        # Add system prompt
        system_prompt = self.get_system_prompt()
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Add conversation history
        history = self.memory.get_conversation_history()
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})

        return messages

    def _get_tool_schemas(self, message: str) -> Optional[List[Dict[str, Any]]]:
        """Get tool schemas if tools might be needed for this message."""
        if not self.tools:
            return None

        # Keywords that might indicate tool usage
        tool_keywords = ["calculate", "compute", "save", "file", "read", "write", "search"]

        if any(keyword in message.lower() for keyword in tool_keywords):
            return [
                {
                    "name": tool.name,
                    "description": tool.get_description(),
                    "parameters": tool.get_parameters_schema(),
                }
                for tool in self.tools.values()
            ]

        return None

    def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]], original_message: str) -> List[ToolResult]:
        """Execute tool calls and track usage."""
        results = []

        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            arguments = tool_call.get("arguments", {})

            if tool_name in self.tools:
                tool = self.tools[tool_name]
                # Use arguments if provided, otherwise use message
                input_data = arguments if arguments else original_message
                result = tool.execute(input_data)
                results.append(result)

                # Track tool usage
                self._tool_usage_history.append({
                    "tool": tool_name,
                    "input": input_data,
                    "output": result.output,
                    "success": result.success,
                    "timestamp": datetime.now(),
                })

        return results

    def process_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Process an incoming message and generate a response.

        Args:
            message: The user's message
            context: Optional additional context

        Returns:
            The agent's response
        """
        # Add user message to memory
        self.memory.add_message(Message(role="user", content=message))

        # Build messages for LLM
        messages = self._build_messages(message)

        # Get tool schemas if needed
        tool_schemas = self._get_tool_schemas(message)

        # Get response from LLM
        response = self.llm_provider.complete(messages, tools=tool_schemas)

        # Handle tool calls if present
        if "tool_calls" in response and response["tool_calls"]:
            tool_results = self._execute_tool_calls(response["tool_calls"], message)
            # Could add tool results to context for follow-up

        # Get content from response
        content = response.get("content") or "I've processed your request."

        # Apply personality influence if blocks are defined
        for block in self.personality_blocks:
            content = block.influence_response(content)

        # Add response to memory
        self.memory.add_message(Message(role="assistant", content=content))

        return content

    async def process_message_async(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Process a message asynchronously.

        Uses async LLM streaming when available for better responsiveness.

        Args:
            message: The user's message
            context: Optional additional context

        Returns:
            The agent's response
        """
        # Add user message to memory
        self.memory.add_message(Message(role="user", content=message))

        # Build messages for LLM
        messages = self._build_messages(message)

        # Get tool schemas if needed
        tool_schemas = self._get_tool_schemas(message)

        # Try async completion if available
        try:
            # Collect streamed response
            content_parts = []
            async for chunk in self.llm_provider.stream(messages, tools=tool_schemas):
                content_parts.append(chunk)

            content = "".join(content_parts).strip()

            if not content:
                content = "I've processed your request."

        except (NotImplementedError, AttributeError):
            # Fall back to sync completion
            response = self.llm_provider.complete(messages, tools=tool_schemas)
            content = response.get("content") or "I've processed your request."

            # Handle tool calls
            if "tool_calls" in response and response["tool_calls"]:
                self._execute_tool_calls(response["tool_calls"], message)

        # Apply personality influence
        for block in self.personality_blocks:
            content = block.influence_response(content)

        # Add response to memory
        self.memory.add_message(Message(role="assistant", content=content))

        return content

    def add_tool(self, tool: ITool) -> None:
        self.tools[tool.name] = tool

    def remove_tool(self, tool_name: str) -> None:
        if tool_name in self.tools:
            del self.tools[tool_name]

    def add_personality_block(self, block: IPersonalityBlock) -> None:
        self.personality_blocks.append(block)

    def add_competency(self, competency: ICompetency) -> None:
        self.competencies.append(competency)

    def get_system_prompt(self) -> str:
        prompt_parts = [f"You are {self.name}"]

        if self.age:
            prompt_parts.append(f", {self.age} years old")

        if self.history:
            prompt_parts.append(f". {self.history}")

        if self.personality_blocks:
            modifiers = IPersonalityBlock.combine(self.personality_blocks)
            prompt_parts.append(f"\n\nPersonality: {modifiers}")

        if self.competencies:
            comp_names = [c.name for c in self.competencies]
            prompt_parts.append(f"\n\nCompetencies: {', '.join(comp_names)}")

        return "".join(prompt_parts)

    def collaborate_with(self, other_agent: "IAgent", message: str) -> str:
        # Simple implementation for testing
        return f"{self.name} collaborates with {other_agent.name} on: {message}"


class BasicConversation(IConversation):
    """Basic conversation implementation."""

    @classmethod
    def create(cls, agents: List[IAgent]) -> "IConversation":
        return cls(agents)

    def add_message(self, agent: IAgent, content: str) -> None:
        self.messages.append(
            {"agent": agent, "agent_name": agent.name, "content": content, "timestamp": datetime.now()}
        )

    def process_turn(self) -> List[Dict[str, Any]]:
        if not self.messages:
            return []

        # Get last message
        last_msg = self.messages[-1]
        responses = []

        # Get response from other agents
        for agent in self.agents:
            if agent != last_msg["agent"]:
                response = agent.process_message(last_msg["content"])
                response_data = {"agent": agent, "content": response, "timestamp": datetime.now()}
                responses.append(response_data)
                self.messages.append(response_data)

        return responses

    def get_history(self) -> List[Dict[str, Any]]:
        return self.messages.copy()

    def save(self, path: str) -> None:
        # Simplified for testing
        with open(path, "w") as f:
            json.dump(self.get_history(), f, default=str)

    # Fixed: Made this an instance method, not a class method
    def load(self, path: str) -> None:
        """Load conversation from file into current instance."""
        with open(path, "r") as f:
            data = json.load(f)
        # Clear current messages and replace with loaded data
        self.messages = data
