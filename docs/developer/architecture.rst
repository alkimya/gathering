Architecture Overview
=====================

This guide covers the technical architecture and development practices for the GatheRing framework.

.. contents:: Table of Contents
   :local:
   :depth: 3

System Architecture
-------------------

High-Level Architecture
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   ┌─────────────────────────────────────────────────────────┐
   │                    Web Interface                        │
   │              (Flask → Django/React/Vue)                 │
   ├─────────────────────────────────────────────────────────┤
   │                    API Layer                            │
   │              (RESTful + WebSocket)                      │
   ├─────────────────────────────────────────────────────────┤
   │                 Core Framework                          │
   │  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
   │  │Agent Manager│  │Tool Registry │  │  Conversation  │  │
   │  │             │  │              │  │    Manager     │  │
   │  └─────────────┘  └──────────────┘  └────────────────┘  │
   ├─────────────────────────────────────────────────────────┤
   │                  Agent Layer                            │
   │  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
   │  │ Personality │  │ Competencies │  │     Tools      │  │
   │  │   Blocks    │  │              │  │   Interface    │  │
   │  └─────────────┘  └──────────────┘  └────────────────┘  │
   ├─────────────────────────────────────────────────────────┤
   │                   LLM Layer                             │
   │  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
   │  │   OpenAI    │  │  Anthropic   │  │ Ollama (Local) │  │
   │  │   Mistral   │  │   Others     │  │                │  │
   │  └─────────────┘  └──────────────┘  └────────────────┘  │
   └─────────────────────────────────────────────────────────┘

Directory Structure
~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   GatheRing/
   ├── gathering/
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

Core Concepts
-------------

Interfaces vs Implementations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

GatheRing uses abstract interfaces with concrete implementations:

.. code-block:: python

   # Interface (abstract)
   from abc import ABC, abstractmethod

   class IAgent(ABC):
       @abstractmethod
       def process_message(self, message: str) -> str:
           """Process a message and return response."""
           pass

   # Implementation (concrete)
   class BasicAgent(IAgent):
       def process_message(self, message: str) -> str:
           # Actual implementation
           return response

This approach provides:

- **Flexibility**: Easy to swap implementations
- **Testability**: Mock implementations for testing
- **Extensibility**: Add new implementations without breaking existing code

Dependency Injection
~~~~~~~~~~~~~~~~~~~~

Use dependency injection for loose coupling:

.. code-block:: python

   class Agent:
       def __init__(self, 
                    llm_provider: ILLMProvider, 
                    memory: IMemory,
                    tools: Dict[str, ITool]):
           self.llm_provider = llm_provider
           self.memory = memory
           self.tools = tools

Benefits:

- **Testability**: Inject mocks for testing
- **Configurability**: Change dependencies at runtime
- **Modularity**: Components remain independent

Factory Pattern
~~~~~~~~~~~~~~~

Use factories for object creation:

.. code-block:: python

   @classmethod
   def from_config(cls, config: Dict[str, Any]) -> "IAgent":
       """Create agent from configuration."""
       # Validate config
       cls._validate_config(config)
       
       # Create dependencies
       memory = cls._create_memory(config)
       llm_provider = cls._create_llm_provider(config)
       
       # Return instance
       return cls(config, memory, llm_provider)

Development Setup
-----------------

Prerequisites
~~~~~~~~~~~~~

- Python 3.11+
- Git
- Virtual environment tool (venv, conda, etc.)
- PostgreSQL (for production)
- Redis (for caching)

Setting Up Development Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Clone and setup:**

   .. code-block:: bash

      git clone https://github.com/alkimya/gathering.git
      cd gathering
      git checkout develop  # Always work on develop branch

2. **Create virtual environment:**

   .. code-block:: bash

      python -m venv venv
      source venv/bin/activate

3. **Install in development mode:**

   .. code-block:: bash

      pip install -r requirements.txt
      pip install -e .  # Editable install

4. **Install pre-commit hooks:**

   .. code-block:: bash

      pre-commit install

5. **Run tests to verify:**

   .. code-block:: bash

      pytest
      make lint

Development Tools
~~~~~~~~~~~~~~~~~

.. list-table:: Development Tools
   :widths: 20 80
   :header-rows: 1

   * - Tool
     - Purpose
   * - Black
     - Code formatting
   * - Flake8
     - Linting
   * - MyPy
     - Type checking
   * - Pytest
     - Testing framework
   * - Coverage.py
     - Code coverage analysis
   * - Sphinx
     - Documentation generation

Configuration Files
~~~~~~~~~~~~~~~~~~~

- ``pyproject.toml``: Project metadata and tool configs
- ``setup.cfg``: Tool-specific settings
- ``.pre-commit-config.yaml``: Pre-commit hooks
- ``pytest.ini``: Pytest configuration
- ``Makefile``: Common development tasks

Extending the Framework
-----------------------

Creating a New LLM Provider
~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Implement the interface:**

   .. code-block:: python

      # gathering/llm/custom_provider.py
      from gathering.core.interfaces import ILLMProvider
      from typing import List, Dict, Any, AsyncGenerator
      import httpx

      class CustomLLMProvider(ILLMProvider):
          
          def __init__(self, name: str, config: Dict[str, Any]):
              super().__init__(name, config)
              self.api_key = config["api_key"]
              self.base_url = config.get("base_url", "https://api.custom.com")
              self.client = httpx.Client(
                  headers={"Authorization": f"Bearer {self.api_key}"}
              )
          
          @classmethod
          def create(cls, provider_name: str, config: Dict[str, Any]) -> "CustomLLMProvider":
              return cls(provider_name, config)
          
          def complete(self, messages: List[Dict[str, str]], 
                      tools: Optional[List[Dict[str, Any]]] = None, 
                      **kwargs) -> Dict[str, Any]:
              # Prepare request
              payload = {
                  "messages": messages,
                  "model": self.model,
                  "temperature": kwargs.get("temperature", 0.7)
              }
              
              # Make API call
              response = self.client.post(f"{self.base_url}/completions", json=payload)
              response.raise_for_status()
              
              # Parse response
              data = response.json()
              return {
                  "role": "assistant",
                  "content": data["choices"][0]["message"]["content"]
              }
          
          async def stream(self, messages: List[Dict[str, str]], 
                          tools: Optional[List[Dict[str, Any]]] = None,
                          **kwargs) -> AsyncGenerator[str, None]:
              # Implement streaming
              async with httpx.AsyncClient() as client:
                  async with client.stream("POST", f"{self.base_url}/stream", 
                                         json={"messages": messages}) as response:
                      async for line in response.aiter_lines():
                          if line.startswith("data: "):
                              yield line[6:]
          
          def is_available(self) -> bool:
              try:
                  response = self.client.get(f"{self.base_url}/health")
                  return response.status_code == 200
              except:
                  return False
          
          def get_token_count(self, text: str) -> int:
              # Implement token counting for your model
              return len(text.split()) * 1.3  # Rough estimate
          
          def get_max_tokens(self) -> int:
              return 4096  # Your model's limit

2. **Register the provider:**

   .. code-block:: python

      # gathering/llm/__init__.py or registry
      from gathering.llm.custom_provider import CustomLLMProvider

      PROVIDERS = {
          "openai": OpenAIProvider,
          "anthropic": AnthropicProvider,
          "custom": CustomLLMProvider  # Add your provider
      }

3. **Write comprehensive tests:**

   .. code-block:: python

      # tests/unit/test_custom_provider.py
      import pytest
      from gathering.llm.custom_provider import CustomLLMProvider

      class TestCustomProvider:
          
          @pytest.fixture
          def provider(self):
              return CustomLLMProvider.create("custom", {
                  "api_key": "test_key",
                  "model": "custom-model-1"
              })
          
          def test_provider_creation(self, provider):
              assert provider.name == "custom"
              assert provider.model == "custom-model-1"
          
          def test_completion(self, provider, mocker):
              # Mock API response
              mock_response = mocker.Mock()
              mock_response.json.return_value = {
                  "choices": [{
                      "message": {"content": "Hello!"}
                  }]
              }
              mocker.patch.object(provider.client, 'post', return_value=mock_response)
              
              # Test completion
              response = provider.complete([{"role": "user", "content": "Hi"}])
              assert response["content"] == "Hello!"
          
          @pytest.mark.asyncio
          async def test_streaming(self, provider):
              chunks = []
              async for chunk in provider.stream([{"role": "user", "content": "Hi"}]):
                  chunks.append(chunk)
              assert len(chunks) > 0

Creating a New Tool
~~~~~~~~~~~~~~~~~~~

1. **Define the tool interface:**

   .. code-block:: python

      # gathering/tools/database_tool.py
      from gathering.core.interfaces import ITool, ToolResult, ToolPermission
      import psycopg2
      from typing import Any, Dict

      class DatabaseTool(ITool):
          """Tool for database operations."""
          
          def __init__(self, name: str, tool_type: str, config: Dict[str, Any]):
              super().__init__(name, tool_type, config)
              self.connection_string = config["connection_string"]
              self.allowed_tables = config.get("allowed_tables", [])
              
          @classmethod
          def from_config(cls, config: Dict[str, Any]) -> "DatabaseTool":
              return cls(config["name"], "database", config)
          
          def execute(self, input_data: Any) -> ToolResult:
              if not self.validate_input(input_data):
                  return ToolResult(
                      success=False,
                      error="Invalid input format"
                  )
              
              action = input_data["action"]
              
              if action == "query" and self.has_permission(ToolPermission.READ):
                  return self._execute_query(input_data["sql"])
              elif action == "insert" and self.has_permission(ToolPermission.WRITE):
                  return self._execute_insert(input_data["table"], input_data["data"])
              else:
                  return ToolResult(
                      success=False,
                      error=f"Action '{action}' not permitted"
                  )
          
          def _execute_query(self, sql: str) -> ToolResult:
              try:
                  with psycopg2.connect(self.connection_string) as conn:
                      with conn.cursor() as cur:
                          cur.execute(sql)
                          results = cur.fetchall()
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
              # Implement async version using asyncpg
              return self.execute(input_data)
          
          def validate_input(self, input_data: Any) -> bool:
              if not isinstance(input_data, dict):
                  return False
              return "action" in input_data
          
          def is_available(self) -> bool:
              try:
                  conn = psycopg2.connect(self.connection_string)
                  conn.close()
                  return True
              except:
                  return False
          
          def get_description(self) -> str:
              return "Execute database queries and operations"
          
          def get_parameters_schema(self) -> Dict[str, Any]:
              return {
                  "type": "object",
                  "properties": {
                      "action": {
                          "type": "string",
                          "enum": ["query", "insert", "update", "delete"]
                      },
                      "sql": {"type": "string"},
                      "table": {"type": "string"},
                      "data": {"type": "object"}
                  },
                  "required": ["action"]
              }

2. **Add to tool factory:**

   .. code-block:: python

      # gathering/core/implementations.py
      def create_tool_from_string(tool_name: str) -> Optional[ITool]:
          tool_map = {
              "calculator": lambda: CalculatorTool.from_config({"name": "calculator"}),
              "filesystem": lambda: FileSystemTool.from_config({...}),
              "database": lambda: DatabaseTool.from_config({
                  "name": "database",
                  "connection_string": os.getenv("DATABASE_URL"),
                  "permissions": ["read", "write"]
              })
          }
          return tool_map.get(tool_name, lambda: None)()