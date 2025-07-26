Core API Reference
==================

This section covers the core interfaces and implementations of the GatheRing framework.

.. contents:: Table of Contents
   :local:
   :depth: 2

Interfaces
----------

IAgent
~~~~~~

.. autoclass:: gathering.core.interfaces.IAgent
   :members:
   :undoc-members:
   :show-inheritance:

The main interface for AI agents in the GatheRing framework.

**Example Usage:**

.. code-block:: python

   from gathering.core import BasicAgent
   
   # Create an agent from configuration
   agent = BasicAgent.from_config({
       "name": "Assistant",
       "llm_provider": "openai",
       "model": "gpt-4",
       "age": 30,
       "history": "10 years of experience as a helpful assistant"
   })
   
   # Process a message
   response = agent.process_message("Hello, how are you?")
   print(response)

**Configuration Parameters:**

.. list-table::
   :widths: 20 20 60
   :header-rows: 1

   * - Parameter
     - Type
     - Description
   * - name
     - str (required)
     - Agent name
   * - llm_provider
     - str (required)
     - LLM provider ("openai", "anthropic", "ollama")
   * - model
     - str
     - Model name (default: "gpt-4")
   * - age
     - int
     - Agent age (optional)
   * - history
     - str
     - Agent background/history (optional)
   * - personality_blocks
     - list[str]
     - List of personality trait names
   * - competencies
     - list[str]
     - List of competency names
   * - tools
     - list[str]
     - List of tool names to enable

ILLMProvider
~~~~~~~~~~~~

.. autoclass:: gathering.core.interfaces.ILLMProvider
   :members:
   :undoc-members:
   :show-inheritance:

Interface for Language Model providers.

**Supported Providers:**

- ``openai``: OpenAI GPT models
- ``anthropic``: Anthropic Claude models  
- ``ollama``: Local Ollama models

**Example Usage:**

.. code-block:: python

   from gathering.core import MockLLMProvider
   
   # Create a provider
   provider = MockLLMProvider.create("openai", {
       "api_key": "your-api-key",
       "model": "gpt-4"
   })
   
   # Get completion
   messages = [{"role": "user", "content": "Hello!"}]
   response = provider.complete(messages)
   print(response["content"])

**Streaming Example:**

.. code-block:: python

   import asyncio
   
   async def stream_response():
       async for chunk in provider.stream(messages):
           print(chunk, end="")
   
   asyncio.run(stream_response())

ITool
~~~~~

.. autoclass:: gathering.core.interfaces.ITool
   :members:
   :undoc-members:
   :show-inheritance:

Interface for external tools that agents can use.

**Tool Result:**

.. autoclass:: gathering.core.interfaces.ToolResult
   :members:
   :undoc-members:

**Example Tool Implementation:**

.. code-block:: python

   from gathering.core import ITool, ToolResult
   
   class CustomTool(ITool):
       @classmethod
       def from_config(cls, config):
           return cls(config["name"], "custom", config)
       
       def execute(self, input_data):
           # Tool logic here
           return ToolResult(
               success=True,
               output="Tool executed successfully"
           )

IPersonalityBlock
~~~~~~~~~~~~~~~~~

.. autoclass:: gathering.core.interfaces.IPersonalityBlock
   :members:
   :undoc-members:
   :show-inheritance:

Modular personality components for agents.

**Available Personality Traits:**

.. list-table::
   :widths: 20 80
   :header-rows: 1

   * - Trait
     - Description
   * - curious
     - Asks questions to understand better
   * - analytical
     - Analyzes information step by step
   * - empathetic
     - Shows understanding and empathy
   * - formal
     - Maintains professional tone
   * - creative
     - Thinks creatively and innovatively
   * - logical
     - Applies logical reasoning
   * - cheerful
     - Positive and cheerful demeanor
   * - patient
     - Patient in explanations
   * - knowledgeable
     - Demonstrates expertise
   * - eager
     - Shows enthusiasm

**Example Usage:**

.. code-block:: python

   from gathering.core import BasicPersonalityBlock
   
   # Create personality block
   curious = BasicPersonalityBlock.from_config({
       "type": "trait",
       "name": "curious",
       "intensity": 0.8  # 0.0 to 1.0
   })
   
   # Add to agent
   agent.add_personality_block(curious)

IMemory
~~~~~~~

.. autoclass:: gathering.core.interfaces.IMemory
   :members:
   :undoc-members:
   :show-inheritance:

Interface for agent memory systems.

**Example Usage:**

.. code-block:: python

   # Access agent's memory
   memory = agent.memory
   
   # Get conversation history
   history = memory.get_conversation_history(limit=10)
   
   # Search memory
   relevant = memory.search("previous topic", limit=5)
   
   # Clear memory
   memory.clear()

IConversation
~~~~~~~~~~~~~

.. autoclass:: gathering.core.interfaces.IConversation
   :members:
   :undoc-members:
   :show-inheritance:

Manages conversations between multiple agents.

**Example Multi-Agent Conversation:**

.. code-block:: python

   from gathering.core import BasicConversation
   
   # Create conversation
   conversation = BasicConversation.create([agent1, agent2])
   
   # Agent1 speaks
   conversation.add_message(agent1, "What do you think about AI?")
   
   # Get responses from other agents
   responses = conversation.process_turn()
   for resp in responses:
       print(f"{resp['agent'].name}: {resp['content']}")

Data Classes
------------

Message
~~~~~~~

.. autoclass:: gathering.core.interfaces.Message
   :members:
   :undoc-members:

Represents a message in a conversation.

**Attributes:**

- ``role`` (str): Message role ("user", "assistant", "system", "tool")
- ``content`` (str): Message content
- ``timestamp`` (datetime): When the message was created
- ``metadata`` (dict): Additional metadata

ToolPermission
~~~~~~~~~~~~~~

.. autoclass:: gathering.core.interfaces.ToolPermission
   :members:
   :undoc-members:
   :show-inheritance:

Enumeration of tool permissions.

**Values:**

- ``READ``: Read permission
- ``WRITE``: Write permission  
- ``EXECUTE``: Execute permission
- ``DELETE``: Delete permission

Implementations
---------------

BasicAgent
~~~~~~~~~~

.. autoclass:: gathering.core.implementations.BasicAgent
   :members:
   :undoc-members:
   :show-inheritance:

Basic implementation of IAgent interface.

**Complete Example:**

.. code-block:: python

   from gathering.core import BasicAgent, CalculatorTool
   
   # Create a research assistant
   researcher = BasicAgent.from_config({
       "name": "Dr. Research",
       "age": 35,
       "history": "PhD in Data Science, 10 years experience",
       "llm_provider": "openai",
       "model": "gpt-4",
       "personality_blocks": ["analytical", "curious", "patient"],
       "tools": ["calculator", "filesystem"]
   })
   
   # Process research request
   response = researcher.process_message(
       "Calculate the statistical significance of a 15% improvement"
   )
   
   # Check tool usage
   for usage in researcher.get_tool_usage_history():
       print(f"Used {usage['tool']} at {usage['timestamp']}")

BasicMemory
~~~~~~~~~~~

.. autoclass:: gathering.core.implementations.BasicMemory
   :members:
   :undoc-members:
   :show-inheritance:

Simple in-memory implementation of IMemory.

MockLLMProvider
~~~~~~~~~~~~~~~

.. autoclass:: gathering.core.implementations.MockLLMProvider
   :members:
   :undoc-members:
   :show-inheritance:

Mock LLM provider for testing purposes.

Available Tools
---------------

CalculatorTool
~~~~~~~~~~~~~~

.. autoclass:: gathering.core.implementations.CalculatorTool
   :members:
   :undoc-members:
   :show-inheritance:

Tool for mathematical calculations.

**Supported Operations:**

- Basic arithmetic: ``+``, ``-``, ``*``, ``/``
- Parentheses: ``()``
- Percentage calculations: ``15% of 2500``

**Example:**

.. code-block:: python

   from gathering.core import CalculatorTool
   
   calculator = CalculatorTool.from_config({"name": "calc"})
   result = calculator.execute("15% of 2500")
   print(result.output)  # 375.0

FileSystemTool
~~~~~~~~~~~~~~

.. autoclass:: gathering.core.implementations.FileSystemTool
   :members:
   :undoc-members:
   :show-inheritance:

Tool for file system operations with permission control.

**Example:**

.. code-block:: python

   from gathering.core import FileSystemTool
   
   fs_tool = FileSystemTool.from_config({
       "name": "filesystem",
       "permissions": ["read", "write"],
       "base_path": "/tmp/data"
   })
   
   # Read file
   result = fs_tool.execute({
       "action": "read",
       "path": "config.json"
   })
   
   # Write file
   result = fs_tool.execute({
       "action": "write",
       "path": "output.txt",
       "content": "Hello, world!"
   })