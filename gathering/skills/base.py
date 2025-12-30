"""
Base classes for GatheRing skills.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime


class SkillPermission(str, Enum):
    """Permissions that skills may require."""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    NETWORK = "network"
    GIT = "git"
    DEPLOY = "deploy"
    ADMIN = "admin"


@dataclass
class SkillResponse:
    """
    Standardized response from skill execution.
    """
    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[str] = None

    # For confirmation workflows
    needs_confirmation: bool = False
    confirmation_type: Optional[str] = None  # "user", "admin", "destructive"
    confirmation_message: Optional[str] = None

    # Metadata
    skill_name: Optional[str] = None
    tool_name: Optional[str] = None
    duration_ms: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "error": self.error,
            "needs_confirmation": self.needs_confirmation,
            "confirmation_type": self.confirmation_type,
            "confirmation_message": self.confirmation_message,
            "skill_name": self.skill_name,
            "tool_name": self.tool_name,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class BaseSkill(ABC):
    """
    Abstract base class for all skills.

    Skills are modular action capabilities that agents can use.
    Each skill provides a set of tools with defined schemas.
    """

    # Skill metadata (override in subclasses)
    name: str = "base"
    description: str = "Base skill"
    version: str = "1.0.0"

    # Required permissions
    required_permissions: List[SkillPermission] = []

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize skill with optional configuration.

        Args:
            config: Skill-specific configuration
        """
        self.config = config or {}
        self._initialized = False

    def initialize(self) -> None:
        """
        Lazy initialization hook.
        Called once before first use.
        Override in subclasses for setup logic.
        """
        self._initialized = True

    def ensure_initialized(self) -> None:
        """Ensure skill is initialized before use."""
        if not self._initialized:
            self.initialize()

    @abstractmethod
    def get_tools_definition(self) -> List[Dict[str, Any]]:
        """
        Return tool definitions for LLM function calling.

        Returns:
            List of tool definitions in Anthropic/OpenAI format:
            [
                {
                    "name": "tool_name",
                    "description": "What this tool does",
                    "input_schema": {
                        "type": "object",
                        "properties": {...},
                        "required": [...]
                    }
                }
            ]
        """
        pass

    @abstractmethod
    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> SkillResponse:
        """
        Execute a tool with given input.

        Args:
            tool_name: Name of the tool to execute
            tool_input: Tool input parameters

        Returns:
            SkillResponse with results
        """
        pass

    async def execute_async(
        self, tool_name: str, tool_input: Dict[str, Any]
    ) -> SkillResponse:
        """
        Async version of execute.
        Default implementation calls sync version.
        Override for true async operations.
        """
        return self.execute(tool_name, tool_input)

    def validate_permissions(
        self, granted_permissions: List[SkillPermission]
    ) -> bool:
        """
        Check if granted permissions satisfy requirements.

        Args:
            granted_permissions: List of permissions granted to the agent

        Returns:
            True if all required permissions are granted
        """
        return all(
            perm in granted_permissions
            for perm in self.required_permissions
        )

    def get_tool_names(self) -> List[str]:
        """Get list of available tool names."""
        return [tool["name"] for tool in self.get_tools_definition()]

    def has_tool(self, tool_name: str) -> bool:
        """Check if skill provides a specific tool."""
        return tool_name in self.get_tool_names()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name} version={self.version}>"
