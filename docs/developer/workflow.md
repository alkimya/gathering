# GatheRing Development Workflow 🔄

## TDD/BDD Development Process

### 1. Write Tests First (Red Phase) 🔴

```bash
# Create a new test file
touch tests/unit/test_new_feature.py

# Write failing tests
pytest tests/unit/test_new_feature.py -v
```

### 2. Implement Minimal Code (Green Phase) 🟢

```bash
# Implement just enough to pass tests
# Run tests continuously
pytest tests/unit/test_new_feature.py -v --tb=short
```

### 3. Refactor (Refactor Phase) 🔵

```bash
# Improve code while keeping tests green
# Run all tests to ensure nothing breaks
pytest

# Check code quality
make lint
make format
```

## Daily Development Workflow

### Morning Setup

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Pull latest changes
git pull origin main

# Install any new dependencies
pip install -r requirements.txt

# Run all tests to ensure clean state
pytest
```

### During Development

```bash
# Run tests in watch mode (requires pytest-watch)
pip install pytest-watch
ptw tests/unit/test_current_feature.py

# Check coverage for specific module
pytest tests/unit/test_agents.py --cov=gathering.agents --cov-report=term-missing

# Run only marked tests
pytest -m "not slow"  # Skip slow tests
pytest -m unit        # Only unit tests
```

### Before Committing

```bash
# Format code
black gathering tests

# Lint code
flake8 gathering tests
mypy gathering

# Run all tests with coverage
pytest

# Check coverage report
open htmlcov/index.html  # Mac
# or
xdg-open htmlcov/index.html  # Linux
# or
start htmlcov/index.html  # Windows

# Update documentation if needed
```

### Commit Guidelines

```bash
# Stage changes
git add -p  # Review changes piece by piece

# Commit with descriptive message
git commit -m "feat(agents): Add emotional state tracking

- Implement EmotionalState class
- Add tests for mood transitions
- Update agent interface
- 100% test coverage maintained"

# Push to feature branch
git push origin feature/emotional-states
```

## BDD Scenario Writing

### Example Feature File

```gherkin
# features/agent_conversation.feature
Feature: Agent Conversation
  As a user
  I want agents to have natural conversations
  So that they can collaborate effectively

  Scenario: Agent remembers user name
    Given an agent named "Assistant"
    When I tell the agent "My name is Alice"
    And I ask "What is my name?"
    Then the agent should respond with "Alice"

  Scenario: Two agents collaborate
    Given an agent named "Teacher" with competency "mathematics"
    And an agent named "Student" with personality "curious"
    When the student asks the teacher about "calculus"
    Then the teacher should provide an explanation
    And the student should ask follow-up questions
```

### Implementing BDD Tests

```python
# tests/bdd/test_agent_conversation.py
import pytest
from pytest_bdd import scenarios, given, when, then

from gathering.core import BasicAgent

scenarios('../features/agent_conversation.feature')

@given('an agent named "<name>"')
def agent_with_name(name):
    return BasicAgent.from_config({
        "name": name,
        "llm_provider": "openai",
        "model": "gpt-4"
    })

@when('I tell the agent "<message>"')
def tell_agent(agent_with_name, message):
    return agent_with_name.process_message(message)

@then('the agent should respond with "<expected>"')
def check_response(tell_agent, expected):
    assert expected in tell_agent
```

## Testing Best Practices

### 1. Test Organization

```bash
tests/
├── unit/           # Fast, isolated tests
├── integration/    # Component interaction tests
├── e2e/           # Full system tests
├── fixtures/      # Shared test data
└── bdd/           # Behavior-driven tests
```

### 2. Test Naming Convention

```python
def test_should_create_agent_when_config_is_valid():
    """Test names should clearly describe the scenario."""
    pass

def test_should_raise_error_when_llm_provider_is_invalid():
    """Include both action and expected outcome."""
    pass
```

### 3. Fixture Usage

```python
@pytest.fixture
def configured_agent():
    """Reusable test setup."""
    return BasicAgent.from_config({...})

def test_agent_memory(configured_agent):
    """Use fixtures for DRY tests."""
    assert configured_agent.memory is not None
```

### 4. Mocking External Services

```python
@patch('gathering.llm.openai_provider.OpenAI')
def test_agent_without_api_calls(mock_openai):
    """Mock external services for unit tests."""
    mock_openai.return_value.complete.return_value = {...}
```

## Performance Testing

### Benchmarking

```bash
# Install pytest-benchmark
pip install pytest-benchmark

# Run benchmarks
pytest tests/benchmarks/ --benchmark-only

# Compare results
pytest-benchmark compare
```

### Example Benchmark Test

```python
def test_agent_response_time(benchmark, configured_agent):
    """Benchmark agent response time."""
    result = benchmark(
        configured_agent.process_message,
        "Hello, how are you?"
    )
    assert result is not None
```

## Documentation During Development

### 1. Update docstrings immediately

```python
def process_message(self, message: str) -> str:
    """
    Process user message and generate response.
    
    Args:
        message: The user's input message
        
    Returns:
        The agent's response
        
    Raises:
        AgentError: If processing fails
        
    Example:
        >>> agent = BasicAgent.from_config({...})
        >>> response = agent.process_message("Hello")
        >>> print(response)
        "Hello! How can I help you?"
    """
```

### 2. Keep BLUEPRINT.md updated

- Mark completed tasks
- Add new discoveries
- Update architecture diagrams

### 3. Write user documentation

- Add examples for new features
- Update API documentation
- Create tutorials

## Continuous Integration

### GitHub Actions Workflow

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests
        run: |
          pytest --cov=gathering --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Debugging Tips

### 1. Use pytest debugging

```bash
# Drop into debugger on failure
pytest --pdb

# Show local variables on failure
pytest -l

# Verbose output
pytest -vv
```

### 2. Print debugging in tests

```python
def test_complex_scenario(capsys):
    """Use capsys to capture prints."""
    print("Debug info")
    result = some_function()
    
    captured = capsys.readouterr()
    assert "Debug info" in captured.out
```

### 3. Use logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_with_logging(caplog):
    """Capture log output in tests."""
    with caplog.at_level(logging.DEBUG):
        result = function_that_logs()
    
    assert "Expected message" in caplog.text
```

## Remember: TDD Cycle 🔄

1. **Red**: Write a failing test
2. **Green**: Write minimal code to pass
3. **Refactor**: Improve code quality
4. **Repeat**: For each new feature

Keep tests fast, isolated, and readable!
