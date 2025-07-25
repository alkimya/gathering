# GatheRing Developer Guide

This guide covers the technical aspects of developing with and extending the GatheRing framework.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Development Setup](#development-setup)
3. [Core Concepts](#core-concepts)
4. [Extending the Framework](#extending-the-framework)
5. [Testing Guidelines](#testing-guidelines)
6. [Contributing](#contributing)
7. [Advanced Topics](#advanced-topics)

## Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Web Interface                         │
│              (Flask → Django/React/Vue)                  │
├─────────────────────────────────────────────────────────┤
│                    API Layer                             │
│              (RESTful + WebSocket)                       │
├─────────────────────────────────────────────────────────┤
│                 Core Framework                           │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐ │
│  │Agent Manager│  │Tool Registry │  │  Conversation  │ │
│  │             │  │              │  │    Manager     │ │
│  └─────────────┘  └──────────────┘  └────────────────┘ │
├─────────────────────────────────────────────────────────┤
│                  Agent Layer                             │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐ │
│  │ Personality │  │ Competencies │  │     Tools      │ │
│  │   Blocks    │  │              │  │   Interface    │ │
│  └─────────────┘  └──────────────┘  └────────────────┘ │
├─────────────────────────────────────────────────────────┤
│                   LLM Layer                              │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐ │
│  │   OpenAI    │  │  Anthropic   │  │ Ollama (Local) │ │
│  │   Mistral   │  │   Others     │  │                │ │
│  └─────────────┘  └──────────────┘  └────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Directory Structure

```
GatheRing/
├── src/
│   ├── core/           # Core interfaces and base implementations
│   ├── agents/         # Agent implementations
│   ├── llm/            # LLM provider implementations
│   ├── tools/          # Tool implementations
│   └── web/            # Web interface
├── tests/
│   ├── unit/           # Unit tests
│   ├── integration/    # Integration tests
│   └── e2e/            # End-to-end tests
├── docs/               # Documentation
├── examples/           # Example code
└── benchmarks/         # Performance benchmarks
```

## Development Setup

### Prerequisites

- Python 3.11+
- Git
- Virtual environment tool (venv, conda, etc.)
- PostgreSQL (for production)

### Setting Up Development Environment

1. **Clone and setup:**

   ```bash
   git clone https://github.com/yourusername/gathering.git
   cd gathering
   git checkout develop  # Always work on develop branch
   ```

2. **Create virtual environment:**

   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install in development mode:**

   ```bash
   pip install -r requirements.txt
   pip install -e .  # Editable install
   ```

4. **Install pre-commit hooks:**

   ```bash
   pre-commit install
   ```

5. **Run tests to verify:**

   ```bash
   pytest
   make lint
   ```

### Development Tools

- **Black**: Code formatting
- **Flake8**: Linting
- **MyPy**: Type checking
- **Pytest**: Testing
- **Coverage.py**: Code coverage

Configuration files:

- `pyproject.toml`: Project metadata and tool configs
- `setup.cfg`: Tool-specific settings
- `.pre-commit-config.yaml`: Pre-commit hooks

## Core Concepts

### Interfaces vs Implementations

GatheRing uses abstract interfaces with concrete implementations:

```python
# Interface (abstract)
from abc import ABC, abstractmethod

class IAgent(ABC):
    @abstractmethod
    def process_message(self, message: str) -> str:
        pass

# Implementation (concrete)
class BasicAgent(IAgent):
    def process_message(self, message: str) -> str:
        # Actual implementation
        return response
```

### Dependency Injection

Use dependency injection for flexibility:

```python
class Agent:
    def __init__(self, llm_provider: ILLMProvider, memory: IMemory):
        self.llm_provider = llm_provider
        self.memory = memory
```

### Factory Pattern

Use factories for object creation:

```python
@classmethod
def from_config(cls, config: Dict[str, Any]) -> "IAgent":
    # Validate config
    # Create dependencies
    # Return instance
    return cls(config)
```

## Extending the Framework

### Creating a New LLM Provider

1. **Implement the interface:**

```python
# src/llm/custom_provider.py
from src.core.interfaces import ILLMProvider
from typing import List, Dict, Any, AsyncGenerator

class CustomLLMProvider(ILLMProvider):
    
    @classmethod
    def create(cls, provider_name: str, config: Dict[str, Any]) -> "CustomLLMProvider":
        return cls(provider_name, config)
    
    def complete(self, messages: List[Dict[str, str]], 
                tools: Optional[List[Dict[str, Any]]] = None, 
                **kwargs) -> Dict[str, Any]:
        # Your implementation
        response = self._call_api(messages)
        return {
            "role": "assistant",
            "content": response.text
        }
    
    async def stream(self, messages: List[Dict[str, str]], 
                    tools: Optional[List[Dict[str, Any]]] = None,
                    **kwargs) -> AsyncGenerator[str, None]:
        # Streaming implementation
        async for chunk in self._stream_api(messages):
            yield chunk
    
    def is_available(self) -> bool:
        # Check if provider is accessible
        return self._test_connection()
    
    def get_token_count(self, text: str) -> int:
        # Token counting logic
        return len(text.split())
    
    def get_max_tokens(self) -> int:
        return 4096  # Your model's limit
```

2. **Register the provider:**

```python
# src/llm/registry.py
PROVIDERS = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "custom": CustomLLMProvider  # Add your provider
}
```

3. **Write tests:**

```python
# tests/unit/test_custom_provider.py
def test_custom_provider_completion():
    provider = CustomLLMProvider.create("custom", {"api_key": "test"})
    response = provider.complete([{"role": "user", "content": "Hello"}])
    assert response["role"] == "assistant"
    assert len(response["content"]) > 0
```

### Creating a New Tool

1. **Implement ITool interface:**

```python
# src/tools/web_search_tool.py
from src.core.interfaces import ITool, ToolResult
import httpx

class WebSearchTool(ITool):
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "WebSearchTool":
        return cls(config["name"], "web_search", config)
    
    def execute(self, input_data: Any) -> ToolResult:
        if not isinstance(input_data, dict) or "query" not in input_data:
            return ToolResult(
                success=False,
                error="Query required"
            )
        
        try:
            results = self._search(input_data["query"])
            return ToolResult(
                success=True,
                output=results
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e)
            )
    
    async def execute_async(self, input_data: Any) -> ToolResult:
        # Async implementation
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.search.com",
                params={"q": input_data["query"]}
            )
            return ToolResult(success=True, output=response.json())
    
    def validate_input(self, input_data: Any) -> bool:
        return isinstance(input_data, dict) and "query" in input_data
    
    def is_available(self) -> bool:
        return True  # Check API availability
    
    def get_description(self) -> str:
        return "Search the web for information"
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "max_results": {
                    "type": "integer",
                    "default": 10
                }
            },
            "required": ["query"]
        }
```

2. **Add to tool factory:**

```python
# src/core/implementations.py
def create_tool_from_string(tool_name: str) -> Optional[ITool]:
    tool_map = {
        "calculator": lambda: CalculatorTool.from_config({"name": "calculator"}),
        "filesystem": lambda: FileSystemTool.from_config({...}),
        "web_search": lambda: WebSearchTool.from_config({"name": "web_search"})  # Add
    }
    return tool_map.get(tool_name, lambda: None)()
```

### Creating a New Personality Block

```python
# src/agents/personalities/professional.py
class ProfessionalPersonality(IPersonalityBlock):
    
    def get_prompt_modifiers(self) -> str:
        modifiers = []
        
        if self.name == "executive":
            modifiers.append("Communicate with executive presence")
            modifiers.append("Be decisive and action-oriented")
        elif self.name == "academic":
            modifiers.append("Use precise academic language")
            modifiers.append("Cite sources when possible")
        
        # Adjust for intensity
        if self.intensity > 0.7:
            modifiers.append("Strongly embody these traits")
        
        return " ".join(modifiers)
    
    def influence_response(self, response: str) -> str:
        # Post-process response to match personality
        if self.name == "executive":
            # Make more concise
            sentences = response.split(". ")
            key_points = sentences[:3]  # Keep main points
            return ". ".join(key_points) + "."
        return response
```

## Testing Guidelines

### Test Structure

Follow the Arrange-Act-Assert pattern:

```python
def test_agent_processes_message():
    # Arrange
    agent = BasicAgent.from_config({
        "name": "Test",
        "llm_provider": "openai"
    })
    message = "Hello"
    
    # Act
    response = agent.process_message(message)
    
    # Assert
    assert isinstance(response, str)
    assert len(response) > 0
```

### Test Categories

1. **Unit Tests** (`tests/unit/`)
   - Test individual components in isolation
   - Mock external dependencies
   - Should be fast (<0.1s per test)

```python
# tests/unit/test_memory.py
def test_memory_stores_messages():
    memory = BasicMemory()
    message = Message(role="user", content="Hello")
    
    memory.add_message(message)
    
    history = memory.get_conversation_history()
    assert len(history) == 1
    assert history[0].content == "Hello"
```

2. **Integration Tests** (`tests/integration/`)
   - Test component interactions
   - Use real implementations where possible
   - May use test databases/services

```python
# tests/integration/test_agent_with_tools.py
def test_agent_uses_calculator():
    agent = BasicAgent.from_config({
        "name": "MathBot",
        "llm_provider": "openai",
        "tools": ["calculator"]
    })
    
    response = agent.process_message("Calculate 2 + 2")
    
    assert "4" in response
    assert len(agent.get_tool_usage_history()) > 0
```

3. **End-to-End Tests** (`tests/e2e/`)
   - Test complete user scenarios
   - Include web interface tests
   - May be slower, run separately

### Mocking and Fixtures

Use pytest fixtures for reusable test data:

```python
# tests/conftest.py
@pytest.fixture
def mock_agent():
    return BasicAgent.from_config({
        "name": "TestAgent",
        "llm_provider": "openai"
    })

@pytest.fixture
def mock_llm_response():
    return {
        "role": "assistant",
        "content": "Test response"
    }
```

Mock external services:

```python
from unittest.mock import patch, Mock

@patch('src.llm.openai_provider.OpenAI')
def test_openai_provider(mock_openai):
    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.complete.return_value = {"content": "Response"}
    
    provider = OpenAIProvider.create("openai", {"api_key": "test"})
    response = provider.complete([{"role": "user", "content": "Hi"}])
    
    assert response["content"] == "Response"
```

### Performance Testing

Use pytest-benchmark for performance tests:

```python
# tests/benchmarks/test_performance.py
def test_agent_response_time(benchmark):
    agent = BasicAgent.from_config({...})
    
    result = benchmark(agent.process_message, "Hello")
    
    assert result is not None
    assert benchmark.stats['mean'] < 0.2  # 200ms limit
```

## Contributing

### Development Workflow

1. **Create feature branch:**

   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature
   ```

2. **Write tests first (TDD):**

   ```python
   # Write failing test
   def test_new_feature():
       result = new_feature()
       assert result == expected
   
   # Run test - should fail
   pytest tests/unit/test_new_feature.py::test_new_feature
   ```

3. **Implement feature:**
   - Write minimal code to pass test
   - Refactor while keeping tests green

4. **Ensure quality:**

   ```bash
   # Format code
   black src tests
   
   # Lint
   flake8 src tests
   
   # Type check
   mypy src
   
   # Run all tests
   pytest
   
   # Check coverage
   pytest --cov=src --cov-report=html
   ```

5. **Commit with conventional commits:**

   ```bash
   git add -p  # Review changes
   git commit -m "feat(agents): add emotion tracking
   
   - Implement EmotionalState class
   - Add emotion transitions
   - Update agent interface
   - Closes #123"
   ```

6. **Push and create PR:**

   ```bash
   git push origin feature/your-feature
   # Create PR on GitHub
   ```

### Code Style Guide

1. **Follow PEP 8** with these additions:
   - Line length: 100 characters
   - Use type hints for all public functions
   - Docstrings for all public classes/methods

2. **Naming conventions:**
   - Classes: `PascalCase`
   - Functions/variables: `snake_case`
   - Constants: `UPPER_SNAKE_CASE`
   - Private: `_leading_underscore`

3. **Docstring format:**

   ```python
   def process_message(self, message: str, context: Optional[Dict] = None) -> str:
       """
       Process a message and generate response.
       
       Args:
           message: The input message to process
           context: Optional context dictionary
           
       Returns:
           The agent's response string
           
       Raises:
           AgentError: If processing fails
           
       Example:
           >>> agent.process_message("Hello")
           "Hello! How can I help?"
       """
   ```

4. **Import organization:**

   ```python
   # Standard library
   import os
   import sys
   from typing import List, Dict
   
   # Third party
   import pytest
   from langchain import LLMChain
   
   # Local
   from src.core import IAgent
   from src.tools import CalculatorTool
   ```

### Pull Request Guidelines

1. **PR Title**: Use conventional commit format
2. **Description**: Explain what and why
3. **Tests**: All new code must have tests
4. **Documentation**: Update relevant docs
5. **Review**: Address all feedback

Template:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guide
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] Coverage maintained >80%
```

## Advanced Topics

### Memory Management

Implement custom memory systems:

```python
class VectorMemory(IMemory):
    def __init__(self, embedding_model):
        self.embeddings = []
        self.messages = []
        self.model = embedding_model
    
    def add_message(self, message: Message) -> None:
        embedding = self.model.embed(message.content)
        self.embeddings.append(embedding)
        self.messages.append(message)
    
    def search(self, query: str, limit: int = 10) -> List[Message]:
        query_embedding = self.model.embed(query)
        similarities = self._compute_similarities(query_embedding)
        top_indices = np.argsort(similarities)[-limit:]
        return [self.messages[i] for i in top_indices]
```

### Custom Agent Types

Create specialized agent types:

```python
class ResearchAgent(BasicAgent):
    def __init__(self, config):
        super().__init__(config)
        self.research_tools = ["web_search", "arxiv", "wikipedia"]
        self.research_memory = ResearchMemory()
    
    def conduct_research(self, topic: str) -> Dict[str, Any]:
        # Gather sources
        sources = self._gather_sources(topic)
        
        # Analyze information
        analysis = self._analyze_sources(sources)
        
        # Synthesize findings
        report = self._synthesize_report(analysis)
        
        return {
            "topic": topic,
            "sources": sources,
            "analysis": analysis,
            "report": report
        }
```

### Plugin System

Implement a plugin architecture:

```python
class PluginRegistry:
    def __init__(self):
        self.plugins = {}
    
    def register(self, name: str, plugin: IPlugin):
        self.plugins[name] = plugin
    
    def load_plugins(self, directory: str):
        for file in Path(directory).glob("*.py"):
            module = import_module(file.stem)
            if hasattr(module, "plugin"):
                self.register(module.plugin.name, module.plugin)
```

### Performance Optimization

1. **Caching responses:**

   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=1000)
   def get_cached_response(message_hash: str) -> str:
       return self._generate_response(message_hash)
   ```

2. **Async processing:**

   ```python
   async def process_messages_async(self, messages: List[str]):
       tasks = [self.process_message_async(msg) for msg in messages]
       return await asyncio.gather(*tasks)
   ```

3. **Connection pooling:**

   ```python
   class LLMConnectionPool:
       def __init__(self, size: int = 10):
           self.pool = asyncio.Queue(maxsize=size)
           self._initialize_connections()
   ```

### Security Considerations

1. **Input validation:**

   ```python
   def validate_input(self, message: str) -> str:
       # Remove potential injection attempts
       cleaned = re.sub(r'[<>\"\'&]', '', message)
       
       # Length limits
       if len(cleaned) > 10000:
           raise ValidationError("Message too long")
       
       return cleaned
   ```

2. **Tool sandboxing:**

   ```python
   class SandboxedTool(ITool):
       def execute(self, input_data: Any) -> ToolResult:
           with self._create_sandbox() as sandbox:
               return sandbox.run(self._execute_internal, input_data)
   ```

3. **API key management:**

   ```python
   from cryptography.fernet import Fernet
   
   class SecureConfig:
       def __init__(self, key: bytes):
           self.cipher = Fernet(key)
       
       def get_api_key(self, provider: str) -> str:
           encrypted = self._load_from_secure_storage(provider)
           return self.cipher.decrypt(encrypted).decode()
   ```

## Debugging Tips

1. **Enable debug logging:**

   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Use debugger:**

   ```python
   import pdb; pdb.set_trace()  # Breakpoint
   ```

3. **Profile code:**

   ```python
   import cProfile
   cProfile.run('agent.process_message("test")')
   ```

4. **Memory profiling:**

   ```python
   from memory_profiler import profile
   
   @profile
   def memory_intensive_function():
       # Your code
   ```

Happy developing! 🚀
