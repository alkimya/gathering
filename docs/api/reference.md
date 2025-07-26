# GatheRing API Reference

## Core Interfaces

### IAgent

The main interface for AI agents in the GatheRing framework.

```python
from gathering.core import IAgent

agent = IAgent.from_config({
    "name": "Assistant",
    "llm_provider": "openai",
    "model": "gpt-4",
    "age": 30,
    "history": "10 years of experience"
})
```

#### Methods

##### `from_config(config: Dict[str, Any]) -> IAgent`

Create an agent from configuration dictionary.

**Parameters:**

- `config` (dict): Agent configuration
  - `name` (str, required): Agent name
  - `llm_provider` (str, required): LLM provider ("openai", "anthropic", "ollama")
  - `model` (str): Model name (default: "gpt-4")
  - `age` (int, optional): Agent age
  - `history` (str, optional): Agent background
  - `personality_blocks` (list, optional): List of personality trait names
  - `competencies` (list, optional): List of competency names
  - `tools` (list, optional): List of tool names

**Returns:** IAgent instance

**Raises:**

- `ConfigurationError`: If configuration is invalid

##### `process_message(message: str, context: Optional[Dict[str, Any]] = None) -> str`

Process a message and generate response.

**Parameters:**

- `message` (str): Input message
- `context` (dict, optional): Additional context

**Returns:** Response string

##### `add_tool(tool: ITool) -> None`

Add a tool to the agent's toolkit.

##### `add_personality_block(block: IPersonalityBlock) -> None`

Add a personality trait to the agent.

##### `get_system_prompt() -> str`

Get the complete system prompt including personality.

##### `get_tool_usage_history() -> List[Dict[str, Any]]`

Get history of tool usage.

### ILLMProvider

Interface for Language Model providers.

```python
from gathering.core import ILLMProvider

provider = ILLMProvider.create("openai", {
    "api_key": "your-api-key",
    "model": "gpt-4"
})
```

#### Methods

##### `create(provider_name: str, config: Dict[str, Any]) -> ILLMProvider`

Factory method to create provider instances.

**Supported Providers:**

- `openai`: OpenAI GPT models
- `anthropic`: Anthropic Claude models
- `ollama`: Local Ollama models

##### `complete(messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]`

Get completion from the LLM.

**Parameters:**

- `messages`: List of message dictionaries with "role" and "content"
- `tools`: Optional list of tool schemas

**Returns:** Response dictionary with "role" and "content"

##### `stream(messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> AsyncGenerator[str, None]`

Stream completion from the LLM.

### ITool

Interface for external tools.

```python
from gathering.core import CalculatorTool

calculator = CalculatorTool.from_config({
    "name": "calculator",
    "type": "calculator"
})

result = calculator.execute("15 * 25 + 10")
print(result.output)  # 385
```

#### Available Tools

##### CalculatorTool

Basic mathematical operations.

```python
calculator = CalculatorTool.from_config({"name": "calc"})
result = calculator.execute("15% of 2500")
# result.output = 375.0
```

##### FileSystemTool

File system operations with permission control.

```python
fs_tool = FileSystemTool.from_config({
    "name": "filesystem",
    "permissions": ["read", "write"],
    "base_path": "/tmp/data"
})

result = fs_tool.execute({
    "action": "read",
    "path": "file.txt"
})
```

#### Tool Result

```python
@dataclass
class ToolResult:
    success: bool
    output: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### IPersonalityBlock

Modular personality components for agents.

```python
from gathering.core import BasicPersonalityBlock

curious = BasicPersonalityBlock.from_config({
    "type": "trait",
    "name": "curious",
    "intensity": 0.8
})
```

#### Available Personality Traits

- `curious`: Asks questions to understand better
- `analytical`: Analyzes information step by step
- `empathetic`: Shows understanding and empathy
- `formal`: Maintains professional tone
- `creative`: Thinks creatively
- `logical`: Applies logical reasoning
- `cheerful`: Positive and cheerful
- `patient`: Patient in explanations
- `knowledgeable`: Demonstrates expertise
- `eager`: Shows enthusiasm

### IConversation

Manages conversations between agents.

```python
from gathering.core import BasicConversation

conversation = BasicConversation.create([agent1, agent2])
conversation.add_message(agent1, "Hello!")
responses = conversation.process_turn()
```

#### Methods

##### `create(agents: List[IAgent]) -> IConversation`

Create a new conversation.

##### `add_message(agent: IAgent, content: str) -> None`

Add a message to the conversation.

##### `process_turn() -> List[Dict[str, Any]]`

Process one turn, getting responses from other agents.

##### `get_history() -> List[Dict[str, Any]]`

Get complete conversation history.

## Data Classes

### Message

```python
@dataclass
class Message:
    role: str  # "user", "assistant", "system", "tool"
    content: str
    timestamp: datetime
    metadata: Dict[str, Any]
```

### ToolPermission

```python
class ToolPermission(Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
```

## Exceptions

### ConfigurationError

Raised when configuration is invalid.

```python
try:
    agent = IAgent.from_config({"name": ""})
except ConfigurationError as e:
    print(f"Config error: {e.message}")
    print(f"Field: {e.details.get('field')}")
```

### LLMProviderError

Raised when LLM provider encounters an error.

```python
try:
    response = provider.complete(messages)
except LLMProviderError as e:
    print(f"Provider: {e.details.get('provider')}")
    print(f"Status: {e.details.get('status_code')}")
```

### ToolExecutionError

Raised when tool execution fails.

```python
try:
    result = tool.execute(invalid_input)
except ToolExecutionError as e:
    print(f"Tool: {e.details.get('tool_name')}")
    print(f"Error: {e.message}")
```

## Complete Examples

### Creating a Research Assistant

```python
from gathering.core import BasicAgent, CalculatorTool, FileSystemTool

# Create agent with tools and personality
researcher = BasicAgent.from_config({
    "name": "Dr. Research",
    "age": 35,
    "history": "PhD in Data Science, 10 years experience",
    "llm_provider": "openai",
    "model": "gpt-4",
    "personality_blocks": ["analytical", "curious", "patient"],
    "tools": ["calculator", "filesystem"]
})

# Process a research request
response = researcher.process_message(
    "Calculate the statistical significance of a 15% improvement "
    "over a baseline of 2500 data points"
)

# Check tool usage
for usage in researcher.get_tool_usage_history():
    print(f"Used {usage['tool']} at {usage['timestamp']}")
```

### Multi-Agent Collaboration

```python
from gathering.core import BasicAgent, BasicConversation

# Create teacher and student agents
teacher = BasicAgent.from_config({
    "name": "Professor Smith",
    "age": 50,
    "llm_provider": "openai",
    "personality_blocks": ["patient", "knowledgeable"],
    "competencies": ["teaching", "mathematics"]
})

student = BasicAgent.from_config({
    "name": "Alice",
    "age": 20,
    "llm_provider": "anthropic",
    "personality_blocks": ["curious", "eager"],
    "competencies": ["learning"]
})

# Create conversation
lesson = BasicConversation.create([teacher, student])

# Student asks question
lesson.add_message(student, "Can you explain derivatives?")

# Teacher responds
responses = lesson.process_turn()
for resp in responses:
    print(f"{resp['agent'].name}: {resp['content']}")

# Continue conversation
lesson.add_message(student, "Can you give an example?")
responses = lesson.process_turn()
```

### Custom Tool Integration

```python
from gathering.core import ITool, ToolResult
from typing import Any

class WeatherTool(ITool):
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "WeatherTool":
        return cls(config["name"], "weather", config)
    
    def execute(self, input_data: Any) -> ToolResult:
        # Mock weather data
        if isinstance(input_data, dict) and "location" in input_data:
            return ToolResult(
                success=True,
                output=f"Weather in {input_data['location']}: Sunny, 22°C"
            )
        return ToolResult(
            success=False,
            error="Location required"
        )
    
    # ... implement other required methods

# Use with agent
weather_agent = BasicAgent.from_config({
    "name": "WeatherBot",
    "llm_provider": "openai"
})
weather_agent.add_tool(WeatherTool.from_config({"name": "weather"}))
```
