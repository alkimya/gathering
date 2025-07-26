# Contributing to GatheRing

First off, thank you for considering contributing to GatheRing! It's people like you that make GatheRing such a great tool. We welcome contributions from everyone and are grateful for even the smallest of fixes!

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How Can I Contribute?](#how-can-i-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Enhancements](#suggesting-enhancements)
  - [Your First Code Contribution](#your-first-code-contribution)
  - [Pull Requests](#pull-requests)
- [Development Process](#development-process)
  - [Setting Up Your Development Environment](#setting-up-your-development-environment)
  - [Test-Driven Development](#test-driven-development)
  - [Code Style](#code-style)
  - [Commit Messages](#commit-messages)
- [Project Structure](#project-structure)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Community](#community)

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to [gathering-conduct@example.com].

### Our Pledge

We pledge to make participation in our project and our community a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity and expression, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:

   ```bash
   git clone https://github.com/your-username/gathering.git
   cd gathering
   ```

3. **Add the upstream repository**:

   ```bash
   git remote add upstream https://github.com/original/gathering.git
   ```

4. **Create a new branch** for your feature or fix:

   ```bash
   git checkout -b feature/your-feature-name
   ```

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

**Bug Report Template:**

```markdown
**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Create agent with config '...'
2. Call method '....'
3. See error

**Expected behavior**
What you expected to happen.

**Actual behavior**
What actually happened. Include error messages.

**Environment:**
 - OS: [e.g. Ubuntu 22.04]
 - Python version: [e.g. 3.11.2]
 - GatheRing version: [e.g. 0.1.0]

**Additional context**
Add any other context about the problem here.
```

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

- **Use a clear and descriptive title**
- **Provide a step-by-step description** of the suggested enhancement
- **Provide specific examples** to demonstrate the steps
- **Describe the current behavior** and **explain which behavior you expected to see instead**
- **Explain why this enhancement would be useful**

### Your First Code Contribution

Unsure where to begin contributing? You can start by looking through these issues:

- Issues labeled `good first issue` - these should only require a few lines of code
- Issues labeled `help wanted` - these tend to be a bit more involved

### Pull Requests

Please follow these steps for your contribution:

1. **Follow the style guide** - Run `black` and `flake8` before committing
2. **Write tests** - We practice TDD; write tests first
3. **Update documentation** - Keep docs in sync with code changes
4. **Write clear commit messages** - Follow our commit convention
5. **Keep PRs focused** - One feature or fix per PR

## Development Process

### Setting Up Your Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Install package in development mode
pip install -e .
```

### Test-Driven Development

We follow TDD principles. Here's the workflow:

1. **Write a failing test** (Red)

   ```python
   def test_new_feature():
       result = my_new_feature("input")
       assert result == "expected output"
   ```

2. **Run the test** - it should fail

   ```bash
   pytest tests/unit/test_new_feature.py::test_new_feature -v
   ```

3. **Write minimal code** to make it pass (Green)

   ```python
   def my_new_feature(input):
       return "expected output"
   ```

4. **Refactor** while keeping tests green

5. **Run all tests** to ensure nothing broke

   ```bash
   pytest
   ```

### Code Style

We use several tools to maintain code quality:

- **Black** for code formatting (line length: 100)
- **Flake8** for linting
- **MyPy** for type checking
- **isort** for import sorting

Run all checks:

```bash
make lint  # Runs all linters
make format  # Formats code with black
```

#### Style Guidelines

```python
# Good example
from typing import List, Optional

from gathering.core import IAgent
from gathering.tools import CalculatorTool


class ExampleAgent(IAgent):
    """
    Brief description of the agent.
    
    This agent demonstrates our coding style with proper
    docstrings, type hints, and clear naming.
    
    Attributes:
        name: The agent's name
        tools: List of available tools
    """
    
    def __init__(self, name: str, tools: Optional[List[str]] = None):
        """Initialize the agent.
        
        Args:
            name: Agent name
            tools: Optional list of tool names
        """
        self.name = name
        self.tools = tools or []
    
    def process_message(self, message: str) -> str:
        """Process a message and return response.
        
        Args:
            message: The input message
            
        Returns:
            The agent's response
            
        Raises:
            ValueError: If message is empty
        """
        if not message:
            raise ValueError("Message cannot be empty")
        
        # Process the message
        response = self._generate_response(message)
        return response
    
    def _generate_response(self, message: str) -> str:
        """Private method for response generation."""
        return f"Received: {message}"
```

### Commit Messages

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```html
<type>(<scope>): <subject>

<body>

<footer>
```

#### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `perf`: Performance improvements

#### Examples

```bash
# Feature
git commit -m "feat(agents): add emotional state tracking

- Implement EmotionalState class
- Add emotion transitions based on conversation
- Update agent interface
- Add comprehensive tests

Closes #123"

# Bug fix
git commit -m "fix(memory): prevent memory overflow in long conversations

The context window was not properly truncated, causing
memory issues in conversations over 1000 messages.

Fixes #456"

# Documentation
git commit -m "docs(api): update agent configuration examples

- Add examples for personality blocks
- Clarify tool permissions
- Fix typos in docstrings"
```

## Project Structure

```bash
GatheRing/
├── gathering/                    # Source code
│   ├── core/              # Core interfaces and implementations
│   ├── agents/            # Agent implementations
│   ├── llm/               # LLM provider implementations
│   ├── tools/             # Tool implementations
│   └── web/               # Web interface (future)
├── tests/                  # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── e2e/               # End-to-end tests
├── docs/                   # Documentation
│   ├── api/               # API reference
│   ├── user/              # User guide
│   └── developer/         # Developer guide
├── examples/               # Example code
├── scripts/                # Utility scripts
└── benchmarks/             # Performance benchmarks
```

## Testing Guidelines

### Test Structure

```python
class TestAgentMemory:
    """Test agent memory functionality."""
    
    def test_memory_stores_messages(self):
        """Test that messages are stored correctly."""
        # Arrange
        agent = BasicAgent.from_config({"name": "Test", "llm_provider": "openai"})
        message = "Hello, world!"
        
        # Act
        agent.process_message(message)
        
        # Assert
        history = agent.memory.get_conversation_history()
        assert len(history) == 2  # User message + agent response
        assert history[0].content == message
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=gathering --cov-report=html

# Run specific test file
pytest tests/unit/test_agents.py

# Run tests matching pattern
pytest -k "memory"

# Run with verbose output
pytest -v
```

### Writing Good Tests

1. **Test one thing** - Each test should verify one behavior
2. **Use descriptive names** - Test names should explain what they test
3. **Follow AAA pattern** - Arrange, Act, Assert
4. **Use fixtures** - Don't repeat setup code
5. **Mock external dependencies** - Tests should be fast and reliable

## Documentation

### Docstring Format

We use Google-style docstrings:

```python
def complex_function(param1: str, param2: Optional[int] = None) -> dict:
    """
    Brief description of function.
    
    Longer description providing context and details about
    the function's behavior and usage.
    
    Args:
        param1: Description of param1
        param2: Description of param2 (default: None)
        
    Returns:
        Dictionary containing:
            - 'result': The main result
            - 'metadata': Additional information
            
    Raises:
        ValueError: If param1 is empty
        TypeError: If param2 is not an integer
        
    Example:
        >>> result = complex_function("test", 42)
        >>> print(result['result'])
        'Processed: test'
    """
```

### Building Documentation

```bash
cd docs
make html  # Build HTML docs
make livehtml  # Serve with auto-reload
```

## Community

### Getting Help

- **GitHub Issues**: For bugs and features
- **Discussions**: For questions and ideas
- **Discord**: [Join our server](https://discord.gg/gathering) (coming soon)
- **Email**: <gathering-dev@example.com>

### Recognition

Contributors will be recognized in:

- The AUTHORS file
- Release notes
- Project website

### Decision Making

- **Minor changes**: Can be approved by one maintainer
- **Major changes**: Require discussion and consensus
- **Architecture changes**: Require RFC (Request for Comments)

## Thank You

Your contributions make GatheRing better for everyone. We appreciate your time and effort in improving this project!

Happy coding! 🚀
