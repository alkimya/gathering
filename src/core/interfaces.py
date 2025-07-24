"""
Core interfaces and abstractions for the GatheRing framework.
These define the contracts that all implementations must follow.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union, Callable, AsyncGenerator
from datetime import datetime
import uuid
from enum import Enum


class ToolPermission(Enum):
    """Permissions that can be granted to tools."""

    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"


@dataclass
class Message:
    """Represents a message in a conversation."""

    role: str  # "user", "assistant", "system", "tool"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    """Result from tool execution."""

    success: bool
    output: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class IMemory(ABC):
    """Interface for agent memory systems."""

    @abstractmethod
    def add_message(self, message: Message) -> None:
        """Add a message to memory."""
        pass

    @abstractmethod
    def get_conversation_history(self, limit: Optional[int] = None) -> List[Message]:
        """Retrieve conversation history."""
        pass

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> List[Message]:
        """Search through memory for relevant messages."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all memory."""
        pass

    @abstractmethod
    def get_context_window(self, max_tokens: int = 4000) -> List[Message]:
        """Get messages that fit within token limit."""
        pass


class ITool(ABC):
    """Interface for external tools that agents can use."""

    def __init__(self, name: str, type: str, config: Dict[str, Any]):
        self.name = name
        self.type = type
        self.config = config
        self._permissions = set(config.get("permissions", []))

    @classmethod
    @abstractmethod
    def from_config(cls, config: Dict[str, Any]) -> "ITool":
        """Create a tool instance from configuration."""
        pass

    @abstractmethod
    def execute(self, input_data: Any) -> ToolResult:
        """Execute the tool with given input."""
        pass

    @abstractmethod
    async def execute_async(self, input_data: Any) -> ToolResult:
        """Execute the tool asynchronously."""
        pass

    @abstractmethod
    def validate_input(self, input_data: Any) -> bool:
        """Validate input before execution."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the tool is currently available."""
        pass

    def has_permission(self, permission: ToolPermission) -> bool:
        """Check if tool has specific permission."""
        return permission.value in self._permissions

    @abstractmethod
    def get_description(self) -> str:
        """Get human-readable description of the tool."""
        pass

    @abstractmethod
    def get_parameters_schema(self) -> Dict[str, Any]:
        """Get JSON schema for tool parameters."""
        pass


class IPersonalityBlock(ABC):
    """Interface for modular personality components."""

    def __init__(self, type: str, name: str, config: Dict[str, Any]):
        self.type = type
        self.name = name
        self.config = config
        self.intensity = config.get("intensity", 0.5)

    @classmethod
    @abstractmethod
    def from_config(cls, config: Dict[str, Any]) -> "IPersonalityBlock":
        """Create a personality block from configuration."""
        pass

    @abstractmethod
    def get_prompt_modifiers(self) -> str:
        """Get prompt modifications based on this personality trait."""
        pass

    @abstractmethod
    def influence_response(self, response: str) -> str:
        """Apply personality influence to a response."""
        pass

    @staticmethod
    def combine(blocks: List["IPersonalityBlock"]) -> str:
        """Combine multiple personality blocks into unified modifiers."""
        modifiers = []
        for block in blocks:
            modifiers.append(block.get_prompt_modifiers())
        return " ".join(modifiers)


class ICompetency(ABC):
    """Interface for agent competencies and skills."""

    def __init__(self, name: str, level: float = 0.5):
        self.name = name
        self.level = level  # 0.0 to 1.0

    @abstractmethod
    def get_prompt_enhancement(self) -> str:
        """Get prompt enhancements based on competency."""
        pass

    @abstractmethod
    def can_handle_task(self, task_description: str) -> float:
        """Return confidence score (0-1) for handling a task."""
        pass


class ILLMProvider(ABC):
    """Interface for Language Model providers."""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.model = config.get("model")

    @classmethod
    @abstractmethod
    def create(cls, provider_name: str, config: Dict[str, Any]) -> "ILLMProvider":
        """Factory method to create provider instances."""
        pass

    @abstractmethod
    def complete(
        self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None, **kwargs
    ) -> Dict[str, Any]:
        """Get completion from the LLM."""
        pass

    @abstractmethod
    def stream(
        self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None, **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream completion from the LLM."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available."""
        pass

    @abstractmethod
    def get_token_count(self, text: str) -> int:
        """Count tokens in text."""
        pass

    @abstractmethod
    def get_max_tokens(self) -> int:
        """Get maximum token limit for this model."""
        pass


class IAgent(ABC):
    """Interface for AI agents."""

    def __init__(self, config: Dict[str, Any]):
        self.id = str(uuid.uuid4())
        self.name = config["name"]
        self.age = config.get("age")
        self.history = config.get("history", "")
        self.created_at = datetime.now()

        # Components
        self.memory: IMemory = self._create_memory(config)
        self.llm_provider: ILLMProvider = self._create_llm_provider(config)
        self.personality_blocks: List[IPersonalityBlock] = []
        self.competencies: List[ICompetency] = []
        self.tools: Dict[str, ITool] = {}

        # Tool usage tracking
        self._tool_usage_history: List[Dict[str, Any]] = []

    @classmethod
    @abstractmethod
    def from_config(cls, config: Dict[str, Any]) -> "IAgent":
        """Create an agent from configuration."""
        pass

    @abstractmethod
    def _create_memory(self, config: Dict[str, Any]) -> IMemory:
        """Create memory system for the agent."""
        pass

    @abstractmethod
    def _create_llm_provider(self, config: Dict[str, Any]) -> ILLMProvider:
        """Create LLM provider for the agent."""
        pass

    @abstractmethod
    def process_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Process an incoming message and generate response."""
        pass

    @abstractmethod
    async def process_message_async(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Process message asynchronously."""
        pass

    @abstractmethod
    def add_tool(self, tool: ITool) -> None:
        """Add a tool to the agent's toolkit."""
        pass

    @abstractmethod
    def remove_tool(self, tool_name: str) -> None:
        """Remove a tool from the agent's toolkit."""
        pass

    @abstractmethod
    def add_personality_block(self, block: IPersonalityBlock) -> None:
        """Add a personality block to the agent."""
        pass

    @abstractmethod
    def add_competency(self, competency: ICompetency) -> None:
        """Add a competency to the agent."""
        pass

    def get_tool_usage_history(self) -> List[Dict[str, Any]]:
        """Get history of tool usage."""
        return self._tool_usage_history.copy()

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Generate system prompt based on agent configuration."""
        pass

    @abstractmethod
    def collaborate_with(self, other_agent: "IAgent", message: str) -> str:
        """Collaborate with another agent on a task."""
        pass


class IConversation(ABC):
    """Interface for managing conversations between agents."""

    def __init__(self, agents: List[IAgent]):
        self.id = str(uuid.uuid4())
        self.agents = agents
        self.messages: List[Dict[str, Any]] = []
        self.created_at = datetime.now()

    @classmethod
    @abstractmethod
    def create(cls, agents: List[IAgent]) -> "IConversation":
        """Create a new conversation."""
        pass

    @abstractmethod
    def add_message(self, agent: IAgent, content: str) -> None:
        """Add a message from an agent to the conversation."""
        pass

    @abstractmethod
    def process_turn(self) -> List[Dict[str, Any]]:
        """Process one turn of conversation, getting responses from agents."""
        pass

    @abstractmethod
    def get_history(self) -> List[Dict[str, Any]]:
        """Get the conversation history."""
        pass

    @abstractmethod
    def save(self, path: str) -> None:
        """Save conversation to file."""
        pass

    @abstractmethod
    def load(self, path: str) -> None:
        """Load conversation from file."""
        pass


class IAgentManager(ABC):
    """Interface for managing multiple agents."""

    def __init__(self):
        self.agents: Dict[str, IAgent] = {}
        self.conversations: Dict[str, IConversation] = {}

    @abstractmethod
    def create_agent(self, config: Dict[str, Any]) -> IAgent:
        """Create and register a new agent."""
        pass

    @abstractmethod
    def get_agent(self, agent_id: str) -> Optional[IAgent]:
        """Retrieve an agent by ID."""
        pass

    @abstractmethod
    def list_agents(self) -> List[IAgent]:
        """List all registered agents."""
        pass

    @abstractmethod
    def remove_agent(self, agent_id: str) -> None:
        """Remove an agent from the system."""
        pass

    @abstractmethod
    def create_conversation(self, agent_ids: List[str]) -> IConversation:
        """Create a conversation between specified agents."""
        pass

    @abstractmethod
    def find_best_agent(self, task: str) -> Optional[IAgent]:
        """Find the best agent for a given task based on competencies."""
        pass


class IToolRegistry(ABC):
    """Interface for tool registry and management."""

    def __init__(self):
        self.tools: Dict[str, type] = {}
        self.instances: Dict[str, ITool] = {}

    @abstractmethod
    def register_tool_type(self, tool_type: str, tool_class: type) -> None:
        """Register a new tool type."""
        pass

    @abstractmethod
    def create_tool(self, config: Dict[str, Any]) -> ITool:
        """Create a tool instance from configuration."""
        pass

    @abstractmethod
    def get_tool(self, tool_name: str) -> Optional[ITool]:
        """Get a tool instance by name."""
        pass

    @abstractmethod
    def list_available_tools(self) -> List[str]:
        """List all available tool types."""
        pass

    @abstractmethod
    def get_tool_schema(self, tool_type: str) -> Dict[str, Any]:
        """Get configuration schema for a tool type."""
        pass
