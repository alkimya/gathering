Contributing Guide
==================

Thank you for your interest in contributing to GatheRing! This guide will help you get started.

.. contents:: Table of Contents
   :local:
   :depth: 2

Code of Conduct
---------------

Please read and follow our Code of Conduct to ensure a welcoming environment for all contributors.

Getting Started
---------------

1. **Fork the repository** on GitHub
2. **Clone your fork**:

   .. code-block:: bash

      git clone https://github.com/yourusername/gathering.git
      cd gathering

3. **Add upstream remote**:

   .. code-block:: bash

      git remote add upstream https://github.com/original/gathering.git

4. **Create a branch**:

   .. code-block:: bash

      git checkout develop
      git pull upstream develop
      git checkout -b feature/your-feature-name

Development Workflow
--------------------

Test-Driven Development (TDD)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We follow TDD principles. Always write tests first:

1. **Write a failing test** (Red)

   .. code-block:: python

      # tests/unit/test_new_feature.py
      def test_new_feature_does_something():
          result = new_feature("input")
          assert result == "expected output"

2. **Run the test** - it should fail:

   .. code-block:: bash

      pytest tests/unit/test_new_feature.py -v

3. **Write minimal code** to make it pass (Green)

   .. code-block:: python

      # gathering/module/new_feature.py
      def new_feature(input):
          return "expected output"

4. **Refactor** while keeping tests green (Refactor)

5. **Run all tests**:

   .. code-block:: bash

      pytest

Code Style
----------

Python Style Guide
~~~~~~~~~~~~~~~~~~

We follow PEP 8 with these additions:

- Line length: 100 characters
- Use type hints for all public functions
- Write docstrings for all public classes and methods

.. code-block:: python

   from typing import Optional, List, Dict
   
   
   class ExampleClass:
       """
       Brief description of the class.
       
       Longer description explaining purpose and usage.
       
       Attributes:
           name: The name of the example
           value: The current value
       
       Example:
           >>> example = ExampleClass("test", 42)
           >>> example.process()
           "Processed: test with value 42"
       """
       
       def __init__(self, name: str, value: int = 0):
           """Initialize ExampleClass.
           
           Args:
               name: The name to use
               value: Initial value (default: 0)
           """
           self.name = name
           self.value = value
       
       def process(self, modifier: Optional[float] = None) -> str:
           """
           Process the example with optional modifier.
           
           Args:
               modifier: Optional multiplier for value
               
           Returns:
               Processed string representation
               
           Raises:
               ValueError: If modifier is negative
           """
           if modifier is not None and modifier < 0:
               raise ValueError("Modifier must be non-negative")
           
           final_value = self.value * (modifier or 1)
           return f"Processed: {self.name} with value {final_value}"

Import Organization
~~~~~~~~~~~~~~~~~~~

Organize imports in this order:

.. code-block:: python

   # Standard library imports
   import os
   import sys
   from datetime import datetime
   from typing import List, Dict, Optional
   
   # Third-party imports
   import pytest
   import numpy as np
   from langchain import LLMChain
   
   # Local imports
   from gathering.core import IAgent
   from gathering.tools import CalculatorTool
   from gathering.utils.helpers import format_output

Naming Conventions
~~~~~~~~~~~~~~~~~~

.. list-table:: Naming Conventions
   :widths: 30 70
   :header-rows: 1

   * - Type
     - Convention
   * - Classes
     - ``PascalCase`` (e.g., ``AgentManager``)
   * - Functions/Variables
     - ``snake_case`` (e.g., ``process_message``)
   * - Constants
     - ``UPPER_SNAKE_CASE`` (e.g., ``MAX_RETRIES``)
   * - Private methods
     - ``_leading_underscore`` (e.g., ``_internal_method``)
   * - Module files
     - ``snake_case.py`` (e.g., ``llm_provider.py``)

Testing Guidelines
------------------

Test Structure
~~~~~~~~~~~~~~

Follow the Arrange-Act-Assert pattern:

.. code-block:: python

   def test_agent_remembers_conversation():
       # Arrange
       agent = BasicAgent.from_config({
           "name": "TestBot",
           "llm_provider": "openai"
       })
       first_message = "My name is Alice"
       second_message = "What's my name?"
       
       # Act
       agent.process_message(first_message)
       response = agent.process_message(second_message)
       
       # Assert
       assert "Alice" in response
       assert len(agent.memory.get_conversation_history()) == 4

Test Organization
~~~~~~~~~~~~~~~~~

- ``tests/unit/``: Fast, isolated unit tests
- ``tests/integration/``: Component interaction tests
- ``tests/e2e/``: End-to-end scenario tests

Use Fixtures
~~~~~~~~~~~~

Create reusable test components:

.. code-block:: python

   # tests/conftest.py
   import pytest
   from gathering.core import BasicAgent
   
   @pytest.fixture
   def basic_agent():
       """Provide a basic agent for testing."""
       return BasicAgent.from_config({
           "name": "TestAgent",
           "llm_provider": "openai",
           "model": "gpt-4"
       })
   
   @pytest.fixture
   def agent_with_tools():
       """Provide an agent with tools configured."""
       return BasicAgent.from_config({
           "name": "ToolAgent",
           "llm_provider": "openai",
           "tools": ["calculator", "filesystem"]
       })

Mock External Services
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from unittest.mock import patch, Mock
   
   @patch('gathering.llm.openai_provider.openai.Completion.create')
   def test_agent_without_api_calls(mock_openai):
       # Setup mock
       mock_openai.return_value = Mock(
           choices=[Mock(text="Mocked response")]
       )
       
       # Test agent
       agent = BasicAgent.from_config({...})
       response = agent.process_message("Hello")
       
       # Verify
       assert response == "Mocked response"
       mock_openai.assert_called_once()

Documentation
-------------

Docstring Format
~~~~~~~~~~~~~~~~

Use Google-style docstrings:

.. code-block:: python

   def complex_function(
       param1: str,
       param2: Optional[int] = None,
       **kwargs
   ) -> Dict[str, Any]:
       """
       Brief description of what the function does.
       
       Longer description providing more context, explaining the
       algorithm or approach used, and any important details.
       
       Args:
           param1: Description of param1
           param2: Description of param2 (default: None)
           **kwargs: Additional keyword arguments:
               - option1 (bool): Description of option1
               - option2 (str): Description of option2
       
       Returns:
           Dictionary containing:
               - 'result': The main result
               - 'metadata': Additional information
       
       Raises:
           ValueError: If param1 is empty
           TypeError: If param2 is not an integer
       
       Example:
           >>> result = complex_function("test", param2=42)
           >>> print(result['result'])
           'Processed: test with 42'
       
       Note:
           This function has side effects on the global state.
       
       See Also:
           simple_function: A simpler version
           related_function: Related functionality
       """

Commit Messages
---------------

Follow Conventional Commits format:

.. code-block:: text

   <type>(<scope>): <subject>
   
   <body>
   
   <footer>

Types
~~~~~

- ``feat``: New feature
- ``fix``: Bug fix
- ``docs``: Documentation only
- ``style``: Code style changes (formatting, etc)
- ``refactor``: Code refactoring
- ``test``: Adding or updating tests
- ``chore``: Maintenance tasks
- ``perf``: Performance improvements

Examples
~~~~~~~~

.. code-block:: text

   feat(agents): add emotion tracking to personality system
   
   - Implement EmotionalState class
   - Add emotion transitions based on conversation
   - Update agent interface to expose emotional state
   - Add comprehensive tests
   
   Closes #123

.. code-block:: text

   fix(tools): handle permission errors in filesystem tool
   
   The filesystem tool was crashing when accessing protected
   directories. Now it properly catches permission errors
   and returns a helpful error message.
   
   Fixes #456

Pull Request Process
--------------------

1. **Update your branch**:

   .. code-block:: bash

      git checkout develop
      git pull upstream develop
      git checkout feature/your-feature
      git rebase develop

2. **Run quality checks**:

   .. code-block:: bash

      # Format code
      black gathering tests
      
      # Lint
      flake8 gathering tests
      
      # Type check
      mypy gathering
      
      # Run tests
      pytest
      
      # Check coverage
      pytest --cov=gathering --cov-report=term-missing

3. **Create Pull Request**:

   - Title: Use conventional commit format
   - Description: Use the PR template
   - Target branch: ``develop`` (not ``main``)

PR Template
~~~~~~~~~~~

.. code-block:: markdown

   ## Description
   Brief description of what this PR does.
   
   ## Type of Change
   - [ ] Bug fix (non-breaking change that fixes an issue)
   - [ ] New feature (non-breaking change that adds functionality)
   - [ ] Breaking change (fix or feature that breaks existing functionality)
   - [ ] Documentation update
   
   ## Testing
   - [ ] Unit tests pass
   - [ ] Integration tests pass
   - [ ] Manual testing completed
   
   ## Checklist
   - [ ] My code follows the project style guidelines
   - [ ] I have performed a self-review
   - [ ] I have added tests that prove my fix/feature works
   - [ ] New and existing unit tests pass locally
   - [ ] I have added necessary documentation
   - [ ] My changes generate no new warnings
   
   ## Related Issues
   Closes #(issue number)

Review Process
--------------

Code Review Checklist
~~~~~~~~~~~~~~~~~~~~~

When reviewing PRs, check for:

- **Correctness**: Does the code do what it claims?
- **Tests**: Are there adequate tests?
- **Documentation**: Is it well documented?
- **Style**: Does it follow our conventions?
- **Performance**: Are there any performance concerns?
- **Security**: Are there any security issues?

Providing Feedback
~~~~~~~~~~~~~~~~~~

- Be constructive and specific
- Suggest improvements, don't just criticize
- Acknowledge good work
- Ask questions if something is unclear

Release Process
---------------

Version Numbering
~~~~~~~~~~~~~~~~~

We follow Semantic Versioning (SemVer):

- **MAJOR.MINOR.PATCH** (e.g., 1.2.3)
- **MAJOR**: Breaking API changes
- **MINOR**: New functionality, backwards compatible
- **PATCH**: Bug fixes, backwards compatible

Release Checklist
~~~~~~~~~~~~~~~~~

1. Update version in ``pyproject.toml``, ``__init__.py``
2. Update ``CHANGELOG.md``
3. Run full test suite
4. Create release PR to ``main``
5. Tag release: ``git tag -a v1.2.3 -m "Release version 1.2.3"``
6. Push tag: ``git push origin v1.2.3``
7. Create GitHub release

Getting Help
------------

- **Discord**: Join our community server
- **GitHub Issues**: Report bugs or request features
- **Email**: core-team@gathering.ai

Thank you for contributing to GatheRing! 🎉
