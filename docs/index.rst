.. GatheRing documentation master file

Welcome to GatheRing's Documentation
====================================

.. image:: https://img.shields.io/badge/version-0.1.0-blue.svg
   :target: https://github.com/alkimya/gathering
   :alt: Version

.. image:: https://img.shields.io/badge/python-3.11+-blue.svg
   :target: https://www.python.org/downloads/
   :alt: Python Version

.. image:: https://img.shields.io/badge/license-MIT-green.svg
   :target: https://opensource.org/licenses/MIT
   :alt: License

**GatheRing** is a collaborative multi-agent AI framework that enables the creation of intelligent agents with unique personalities, diverse competencies, and professional expertise.

.. warning::
   This is version 0.1.0 - an initial release with core functionality. 
   Some features are still under development.

Key Features
------------

* 🤖 **Multi-Agent System** - Create and manage multiple AI agents
* 🎭 **Personality System** - Modular personality blocks for unique agent behaviors  
* 🔧 **Tool Integration** - Extensible tool system for agent capabilities
* 🌐 **Multi-LLM Support** - OpenAI, Anthropic, Ollama, and more
* 🤝 **Agent Collaboration** - Agents can work together on complex tasks
* 🧪 **Test-Driven** - Built with TDD/BDD principles

Quick Start
-----------

.. code-block:: python

   from gathering.core import BasicAgent

   # Create an agent
   agent = BasicAgent.from_config({
       "name": "Assistant",
       "llm_provider": "openai",
       "model": "gpt-4"
   })

   # Have a conversation
   response = agent.process_message("Hello!")
   print(response)

.. toctree::
   :maxdepth: 2
   :caption: User Documentation
   :hidden:

   user/installation
   user/quickstart
   user/guide
   user/examples
   user/faq

.. toctree::
   :maxdepth: 2
   :caption: API Reference
   :hidden:

   api/core
   api/agents
   api/tools
   api/llm
   api/exceptions

.. toctree::
   :maxdepth: 2
   :caption: Developer Guide
   :hidden:

   developer/architecture
   developer/contributing
   developer/extending
   developer/testing
   developer/plugins

.. toctree::
   :maxdepth: 1
   :caption: Additional Resources
   :hidden:

   changelog
   roadmap
   license

Getting Help
------------

* 📖 Read the :doc:`user/guide`
* 🔍 Check the :doc:`api/core`
* 💬 Join our community discussions
* 🐛 Report issues on GitHub

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`