Frequently Asked Questions
==========================

General Questions
-----------------

**Q: What is GatheRing?**
   GatheRing is a collaborative multi-agent AI framework that allows you to create intelligent agents with unique personalities, skills, and tools. Agents can work independently or collaborate to solve complex problems.

**Q: Which LLM providers are supported?**
   Currently supported providers:
   
   - OpenAI (GPT models)
   - Anthropic (Claude models)
   - Ollama (local models)
   - More providers coming soon

**Q: Do I need API keys?**
   Yes, for cloud providers like OpenAI and Anthropic. For local models with Ollama, no API key is needed.

**Q: Can agents work offline?**
   Yes, if you use Ollama with local models. Cloud-based providers require internet connection.

Technical Questions
-------------------

**Q: How do I handle rate limits?**
   Implement rate limiting in your application:

   .. code-block:: python

      import time
      from typing import List

      class RateLimitedAgent:
          def __init__(self, agent, requests_per_minute=10):
              self.agent = agent
              self.rpm = requests_per_minute
              self.requests = []
          
          def process_message(self, message: str) -> str:
              # Check rate limit
              now = time.time()
              self.requests = [r for r in self.requests if now - r < 60]
              
              if len(self.requests) >= self.rpm:
                  wait_time = 60 - (now - self.requests[0])
                  time.sleep(wait_time)
              
              self.requests.append(now)
              return self.agent.process_message(message)

**Q: Can I use multiple LLM providers in one agent?**
   Not directly, but you can create a custom provider that routes to different providers:

   .. code-block:: python

      class MultiProvider(ILLMProvider):
          def __init__(self, providers: Dict[str, ILLMProvider]):
              self.providers = providers
              self.current = "openai"
          
          def complete(self, messages, **kwargs):
              provider = kwargs.pop("provider", self.current)
              return self.providers[provider].complete(messages, **kwargs)

**Q: How do I save agent state?**
   Use serialization:

   .. code-block:: python

      import pickle

      # Save agent state
      with open("agent_state.pkl", "wb") as f:
          pickle.dump({
              "config": agent.config,
              "memory": agent.memory.get_conversation_history(),
              "tool_history": agent.get_tool_usage_history()
          }, f)

      # Restore agent
      with open("agent_state.pkl", "rb") as f:
          state = pickle.load(f)
          agent = BasicAgent.from_config(state["config"])
          # Restore memory
          for msg in state["memory"]:
              agent.memory.add_message(msg)

Troubleshooting
---------------

**Q: "Module not found" errors**
   Ensure you're in the correct directory and virtual environment:

   .. code-block:: bash

      cd gathering
      source venv/bin/activate
      pip install -e .

**Q: Agent responses are generic**
   - Add more specific personality blocks
   - Provide detailed history/background
   - Use more specific prompts

**Q: Tools aren't being used**
   - Check tool permissions
   - Ensure tool is added to agent
   - Verify tool is available: ``tool.is_available()``

**Q: Memory seems limited**
   Default memory has token limits. For longer conversations:

   .. code-block:: python

      # Increase context window
      agent.memory.get_context_window(max_tokens=8000)

Best Practices
--------------

**Q: How many personality traits should an agent have?**
   3-5 traits work best. Too many can dilute the personality.

**Q: Should I create new agents or reuse them?**
   Reuse agents when possible. Creating agents has overhead.

**Q: How do I make agents more consistent?**
   - Use lower temperature settings
   - Provide detailed system prompts
   - Maintain conversation context

**Q: What's the best way to test agents?**
   Write unit tests for agent behaviors:

   .. code-block:: python

      def test_agent_personality():
          agent = BasicAgent.from_config({
              "name": "Tester",
              "personality_blocks": ["analytical"]
          })
          
          response = agent.process_message("Explain this: 2+2=4")
          assert "analyze" in response.lower() or "examine" in response.lower()
          