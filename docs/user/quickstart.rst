Quick Start Guide
=================

This guide will get you up and running with GatheRing in 5 minutes.

Your First Agent
----------------

.. code-block:: python

   from gathering.core import BasicAgent

   # Create a simple agent
   agent = BasicAgent.from_config({
       "name": "Assistant",
       "llm_provider": "openai",
       "model": "gpt-4"
   })

   # Ask a question
   response = agent.process_message("What can you help me with?")
   print(response)

Adding Personality
------------------

.. code-block:: python

   # Create a friendly agent
   friendly_agent = BasicAgent.from_config({
       "name": "Buddy",
       "llm_provider": "openai",
       "personality_blocks": ["cheerful", "helpful", "casual"]
   })

   response = friendly_agent.process_message("How's your day going?")

Using Tools
-----------

.. code-block:: python

   # Create agent with calculator
   math_agent = BasicAgent.from_config({
       "name": "Calculator",
       "llm_provider": "openai",
       "tools": ["calculator"]
   })

   response = math_agent.process_message("What's 15% tip on $85.50?")

Multi-Agent Conversation
------------------------

.. code-block:: python

   from gathering.core import BasicConversation

   # Create two agents
   alice = BasicAgent.from_config({"name": "Alice", "llm_provider": "openai"})
   bob = BasicAgent.from_config({"name": "Bob", "llm_provider": "anthropic"})

   # Start conversation
   chat = BasicConversation.create([alice, bob])
   chat.add_message(alice, "Hi Bob, what do you think about AI?")
   
   # Bob responds
   responses = chat.process_turn()
   print(f"{responses[0]['agent'].name}: {responses[0]['content']}")

Next Steps
----------

- Read the full :doc:`guide`
- Explore :doc:`examples`
- Check the :doc:`/api/core`
