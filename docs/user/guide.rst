User Guide
==========

Welcome to the GatheRing User Guide. This guide will help you get started with creating and managing AI agents.

.. contents:: Table of Contents
   :local:
   :depth: 3

Getting Started
---------------

Installation
~~~~~~~~~~~~

1. **Clone the repository:**

   .. code-block:: bash

      git clone https://github.com/alkimya/gathering.git
      cd gathering

2. **Create a virtual environment:**

   .. code-block:: bash

      python -m venv venv
      source venv/bin/activate  # On Windows: venv\Scripts\activate

3. **Install dependencies:**

   .. code-block:: bash

      pip install -r requirements.txt

4. **Verify installation:**

   .. code-block:: bash

      python quick_start.py

Quick Start Example
~~~~~~~~~~~~~~~~~~~

Here's the simplest way to create and use an agent:

.. code-block:: python

   from gathering.core import BasicAgent

   # Create a simple agent
   assistant = BasicAgent.from_config({
       "name": "Helper",
       "llm_provider": "openai",
       "model": "gpt-4"
   })

   # Have a conversation
   response = assistant.process_message("Hello! How can you help me?")
   print(response)

Creating Agents
---------------

Basic Agent Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~

Every agent requires at minimum a name and an LLM provider:

.. code-block:: python

   config = {
       "name": "Assistant",
       "llm_provider": "openai",  # or "anthropic", "ollama"
       "model": "gpt-4"           # model depends on provider
   }

   agent = BasicAgent.from_config(config)

Adding Background and History
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Make your agents more interesting with personal details:

.. code-block:: python

   config = {
       "name": "Dr. Sarah Chen",
       "age": 42,
       "history": "15 years as a marine biologist, PhD from MIT, "
                  "specialized in coral reef ecosystems",
       "llm_provider": "anthropic",
       "model": "claude-3"
   }

   marine_expert = BasicAgent.from_config(config)

Complete Agent Example
~~~~~~~~~~~~~~~~~~~~~~

Here's a fully configured agent with all features:

.. code-block:: python

   teacher_config = {
       "name": "Professor Williams",
       "age": 55,
       "history": "30 years teaching mathematics at university level, "
                  "author of several textbooks on calculus",
       "llm_provider": "openai",
       "model": "gpt-4",
       "personality_blocks": ["patient", "knowledgeable", "analytical"],
       "competencies": ["mathematics", "teaching", "curriculum_design"],
       "tools": ["calculator", "filesystem"]
   }

   math_teacher = BasicAgent.from_config(teacher_config)

Agent Personalities
-------------------

Understanding Personality Blocks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Personality blocks are modular traits that influence how agents communicate:

.. code-block:: python

   from gathering.core import BasicPersonalityBlock

   # Create individual personality traits
   curious = BasicPersonalityBlock.from_config({
       "type": "trait",
       "name": "curious",
       "intensity": 0.8  # 0.0 to 1.0
   })

   agent.add_personality_block(curious)

Available Personality Traits
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: Personality Traits
   :widths: 20 40 40
   :header-rows: 1

   * - Trait
     - Description
     - Example Behavior
   * - curious
     - Asks questions to learn more
     - "That's interesting! Can you tell me more about..."
   * - analytical
     - Breaks down problems systematically
     - "Let's analyze this step by step..."
   * - empathetic
     - Shows understanding and care
     - "I understand how you feel..."
   * - formal
     - Professional communication style
     - "I would be pleased to assist you with..."
   * - creative
     - Thinks outside the box
     - "Here's an innovative approach..."
   * - cheerful
     - Positive and upbeat
     - "Great question! I'm happy to help!"
   * - patient
     - Takes time to explain thoroughly
     - "Let me explain this in detail..."

Combining Personalities
~~~~~~~~~~~~~~~~~~~~~~~

Agents can have multiple personality traits:

.. code-block:: python

   # Create a friendly teacher
   teacher = BasicAgent.from_config({
       "name": "Ms. Johnson",
       "llm_provider": "openai",
       "personality_blocks": ["patient", "cheerful", "knowledgeable"]
   })

   # Create a serious researcher
   researcher = BasicAgent.from_config({
       "name": "Dr. Smith",
       "llm_provider": "anthropic",
       "personality_blocks": ["analytical", "formal", "logical"]
   })

Personality Intensity
~~~~~~~~~~~~~~~~~~~~~

Control how strongly traits influence behavior:

.. code-block:: python

   # Subtle curiosity (occasionally asks questions)
   subtle = BasicPersonalityBlock.from_config({
       "name": "curious",
       "intensity": 0.3
   })

   # Strong curiosity (frequently asks follow-up questions)
   strong = BasicPersonalityBlock.from_config({
       "name": "curious", 
       "intensity": 0.9
   })

Using Tools
-----------

Available Tools
~~~~~~~~~~~~~~~

Calculator Tool
^^^^^^^^^^^^^^^

For mathematical operations:

.. code-block:: python

   agent = BasicAgent.from_config({
       "name": "MathBot",
       "llm_provider": "openai",
       "tools": ["calculator"]
   })

   response = agent.process_message("What's 15% of 2500?")
   # Agent will use calculator to compute: 375

FileSystem Tool
^^^^^^^^^^^^^^^

For reading and writing files:

.. code-block:: python

   agent = BasicAgent.from_config({
       "name": "FileManager",
       "llm_provider": "openai",
       "tools": ["filesystem"]
   })

   # Agent can now read/write files when needed
   response = agent.process_message(
       "Save this shopping list to a file: milk, eggs, bread"
   )

Adding Tools to Existing Agents
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from gathering.core import CalculatorTool

   # Create agent without tools
   agent = BasicAgent.from_config({
       "name": "Assistant",
       "llm_provider": "openai"
   })

   # Add calculator later
   calculator = CalculatorTool.from_config({"name": "calculator"})
   agent.add_tool(calculator)

Tool Permissions
~~~~~~~~~~~~~~~~

Control what tools can do:

.. code-block:: python

   from gathering.core import FileSystemTool

   # Read-only file access
   readonly_fs = FileSystemTool.from_config({
       "name": "filesystem",
       "permissions": ["read"],  # No write permission
       "base_path": "/data"
   })

   # Full access
   full_fs = FileSystemTool.from_config({
       "name": "filesystem",
       "permissions": ["read", "write", "delete"],
       "base_path": "/workspace"
   })

Multi-Agent Conversations
-------------------------

Creating Conversations
~~~~~~~~~~~~~~~~~~~~~~

Have multiple agents interact:

.. code-block:: python

   from gathering.core import BasicConversation

   # Create agents
   interviewer = BasicAgent.from_config({
       "name": "Jane",
       "llm_provider": "openai",
       "personality_blocks": ["curious", "formal"]
   })

   expert = BasicAgent.from_config({
       "name": "Dr. Expert",
       "llm_provider": "anthropic",
       "personality_blocks": ["knowledgeable", "patient"]
   })

   # Start conversation
   interview = BasicConversation.create([interviewer, expert])

Managing Conversation Flow
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Interviewer asks first question
   interview.add_message(
       interviewer, 
       "Dr. Expert, can you explain quantum computing?"
   )

   # Get expert's response
   responses = interview.process_turn()
   print(f"{responses[0]['agent'].name}: {responses[0]['content']}")

   # Continue the conversation
   interview.add_message(
       interviewer,
       "How does that differ from classical computing?"
   )
   responses = interview.process_turn()

Saving and Loading Conversations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Save conversation to file
   interview.save("conversations/quantum_interview.json")

   # Load it later
   interview.load("conversations/quantum_interview.json")
   history = interview.get_history()

Best Practices
--------------

Choosing Appropriate Personalities
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Match personality to purpose:

- **Customer Service**: ``empathetic``, ``patient``, ``cheerful``
- **Technical Support**: ``analytical``, ``logical``, ``patient``
- **Teaching**: ``knowledgeable``, ``patient``, ``encouraging``
- **Research**: ``analytical``, ``curious``, ``thorough``

Providing Rich Backgrounds
~~~~~~~~~~~~~~~~~~~~~~~~~~

Detailed histories make agents more believable:

.. code-block:: python

   # Good: Specific and relevant
   history = """20 years as a chef in French restaurants, trained at 
                Le Cordon Bleu, specialized in pastry and desserts"""

   # Less effective: Too vague
   history = "Experienced cook"

Using Tools Wisely
~~~~~~~~~~~~~~~~~~

Only add tools the agent actually needs:

.. code-block:: python

   # Financial advisor needs calculator
   financial_advisor = BasicAgent.from_config({
       "name": "MoneyWise",
       "tools": ["calculator"],
       "competencies": ["finance", "investment"]
   })

   # Therapist probably doesn't
   therapist = BasicAgent.from_config({
       "name": "Dr. Care",
       "personality_blocks": ["empathetic", "patient"],
       "competencies": ["psychology", "counseling"]
   })

Memory Management
~~~~~~~~~~~~~~~~~

Agents remember conversation history:

.. code-block:: python

   # First interaction
   agent.process_message("My name is Alice")

   # Later in conversation
   response = agent.process_message("What's my name?")
   # Agent responds: "Your name is Alice"

Error Handling
~~~~~~~~~~~~~~

Always handle potential errors:

.. code-block:: python

   from gathering.core.exceptions import ConfigurationError, LLMProviderError

   try:
       agent = BasicAgent.from_config(config)
       response = agent.process_message("Hello")
   except ConfigurationError as e:
       print(f"Invalid configuration: {e.message}")
   except LLMProviderError as e:
       print(f"LLM error: {e.message}")

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**"Agent name is required"**

.. code-block:: python

   # Wrong
   config = {"llm_provider": "openai"}

   # Correct
   config = {"name": "Assistant", "llm_provider": "openai"}

**"Invalid LLM provider"**

.. code-block:: python

   # Wrong
   config = {"name": "Bot", "llm_provider": "gpt"}

   # Correct - use exact provider names
   config = {"name": "Bot", "llm_provider": "openai"}

**"Write permission denied"**

.. code-block:: python

   # Add write permission to filesystem tool
   fs_tool = FileSystemTool.from_config({
       "name": "filesystem",
       "permissions": ["read", "write"]  # Include write
   })

Performance Tips
~~~~~~~~~~~~~~~~

1. **Reuse agents** instead of creating new ones:

   .. code-block:: python

      # Create once
      agent = BasicAgent.from_config(config)
      
      # Use many times
      for question in questions:
          response = agent.process_message(question)

2. **Clear memory** for long conversations:

   .. code-block:: python

      # After many messages
      if len(agent.memory.get_conversation_history()) > 100:
          agent.memory.clear()

3. **Use appropriate models**:

   - Fast responses: Use smaller models
   - Complex tasks: Use larger models

Getting Help
~~~~~~~~~~~~

1. Check the :doc:`/api/core`
2. Review example code in ``examples/``
3. Run tests to verify setup: ``pytest``
4. Check logs for detailed error messages

Next Steps
----------

Now that you understand the basics:

1. Explore advanced personality combinations
2. Create custom tools for your use case
3. Build multi-agent systems for complex tasks
4. Integrate with your applications

.. tip::
   For advanced usage and extending the framework, see the :doc:`/developer/extending`

Happy agent building! 🤖✨