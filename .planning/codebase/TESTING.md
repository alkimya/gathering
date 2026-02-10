# Testing Patterns

**Analysis Date:** 2026-02-10

## Test Framework

**Runner:**
- pytest 7.4+
- pytest-asyncio 0.21+ for async test support
- Config: `pytest.ini` and `pyproject.toml [tool.pytest.ini_options]`

**Assertion Library:**
- pytest's built-in assertions (no additional library needed)
- unittest.mock.AsyncMock, MagicMock for mocking

**Run Commands:**
```bash
pytest tests                          # Run all tests
pytest tests -v                       # Run with verbose output
pytest tests -k test_name             # Run specific test by name
pytest tests --tb=short               # Short traceback format
pytest tests -m unit                  # Run only unit tests
pytest tests --cov=gathering          # Run with coverage report
pytest tests --cov-report=html        # Generate HTML coverage report
pytest tests --asyncio-mode=auto      # Auto asyncio mode for async tests
```

## Test File Organization

**Location:**
- Tests separate from source code in `/tests` directory
- Test file structure mirrors source structure where applicable
- Each major feature has dedicated test file

**Directory Structure:**
```
tests/
├── conftest.py                       # Fixtures and configuration
├── test_auth.py                      # Authentication tests
├── test_agents_goals.py              # Goal management tests
├── test_event_bus.py                 # Event system tests
├── test_code_executor.py             # Code execution tests
├── test_api.py                       # API endpoint tests
├── integration/                      # Integration tests
└── e2e/                              # End-to-end tests
```

**Naming:**
- Test files: `test_*.py` or `*_test.py`
- Test classes: `Test*` (e.g., `TestPasswordHashing`, `TestEventBus`)
- Test functions: `test_*` (e.g., `test_hash_password`, `test_create_access_token`)

## Test Structure

**Suite Organization:**
```python
"""
Tests for authentication module.
Tests JWT token creation/validation, password hashing, and auth endpoints.
"""

import pytest
from unittest.mock import patch

from gathering.api.auth import (
    create_access_token,
    verify_password,
)


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_hash_password(self):
        """Test password hashing produces a bcrypt hash."""
        password = "secure_password_123"
        hashed = get_password_hash(password)

        assert hashed is not None
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_correct_password(self):
        """Test verifying correct password returns True."""
        password = "test_password"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True
```

**Patterns:**
- Tests grouped in classes by feature/functionality
- Clear, descriptive docstrings on every test
- Module-level docstring explaining test scope
- One assertion focus per test function (generally)
- Setup/teardown via fixtures, not setUp methods

## Test Structure Patterns

**Arrange-Act-Assert (AAA) Pattern:**
```python
def test_eval_simple_math(self, executor):
    """Test evaluating simple math expressions."""
    # Arrange
    expression = "2 + 3 * 4"

    # Act
    result = executor._eval_python(expression)

    # Assert
    assert result["success"] is True
    assert result["result"] == 14
```

**Test Organization by Class:**
Each test class groups related tests. Section headers separate concerns:
```python
# =============================================================================
# Password Hashing Tests
# =============================================================================

class TestPasswordHashing:
    """Tests for password hashing functions."""
    # ... password-specific tests

# =============================================================================
# JWT Token Tests
# =============================================================================

class TestJWTTokens:
    """Tests for JWT token creation and validation."""
    # ... token-specific tests
```

## Mocking

**Framework:** `unittest.mock` (AsyncMock, MagicMock, patch)

**Patterns:**

AsyncMock for async functions:
```python
async def test_api_call(self):
    """Test API response handling."""
    mock_response = AsyncMock()
    mock_response.json.return_value = {"status": "ok"}

    with patch("module.function", new=mock_response):
        result = await function()
        assert result["status"] == "ok"
```

MagicMock for synchronous mocking:
```python
def test_with_mock(self):
    """Test with mocked dependency."""
    mock_service = MagicMock()
    mock_service.get_data.return_value = [1, 2, 3]

    # Use mock_service in test
    result = process(mock_service)
    assert result == [1, 2, 3]
```

**What to Mock:**
- External services (APIs, databases) - use mocks to avoid network calls
- Long-running operations - replace with instant responses
- Random behavior - control via mocks for deterministic tests
- File I/O - use fixtures with temp directories instead

**What NOT to Mock:**
- Core business logic you're testing
- In-memory data structures
- Internal helper functions within the module under test
- For integration tests, real objects/services

## Fixtures and Factories

**Test Data Pattern:**
```python
@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def basic_agent_config():
    """Basic agent configuration for testing."""
    return {
        "name": "TestAgent",
        "llm_provider": "openai",
        "model": "gpt-4",
        "api_key": "test_key"
    }


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    return MockLLMProvider.create("openai", {
        "api_key": "test_key",
        "model": "gpt-4"
    })
```

**Location:**
- Fixtures in `tests/conftest.py` for shared use across test files
- Module-specific fixtures in test files where local to that module
- Factory methods for complex object creation

**Fixture Scopes:**
- `function` (default): New instance per test
- `module`: Shared across all tests in module
- `session`: Shared across entire test session

## Coverage

**Requirements:**
- Target: 80% minimum (enforced via `pytest.ini` `cov-fail-under=80`)
- Report formats: HTML, term-missing, term:skip-covered
- Exclude: Tests themselves, test utilities

**View Coverage:**
```bash
pytest --cov=gathering --cov-report=html
open htmlcov/index.html  # View HTML report

pytest --cov=gathering --cov-report=term-missing  # Terminal report
```

**Configuration in `pytest.ini`:**
```ini
addopts =
    --cov=gathering
    --cov-report=html
    --cov-report=term-missing
    --cov-report=term:skip-covered
    --cov-fail-under=80
```

## Test Types

**Unit Tests:**
- Scope: Single function or method
- Focus: Logic, edge cases, error handling
- Isolation: Mock external dependencies
- Speed: Should run in milliseconds
- Marker: `@pytest.mark.unit` (optional)
- Location: `tests/test_*.py`

Example from `tests/test_code_executor.py`:
```python
class TestCodeExecutorSafety:
    """Tests for code execution safety features."""

    @pytest.fixture
    def executor(self):
        """Create a code executor instance."""
        return CodeExecutionSkill()

    def test_eval_simple_math(self, executor):
        """Test evaluating simple math expressions."""
        result = executor._eval_python("2 + 3 * 4")
        assert result["success"] is True
        assert result["result"] == 14

    def test_eval_blocks_import(self, executor):
        """Test that import statements are blocked."""
        result = executor._eval_python("__import__('os')")
        assert result["success"] is False
        assert "not allowed" in result["error"].lower()
```

**Integration Tests:**
- Scope: Multiple components working together
- Focus: Component interaction, data flow
- Minimal mocking - test real integrations
- Slower than unit tests (seconds)
- Marker: `@pytest.mark.integration`
- Location: `tests/integration/`

**E2E Tests:**
- Scope: Full application workflows
- Focus: User workflows, system behavior
- No mocking of application code
- External dependencies may be mocked
- Slowest category of tests (minutes)
- Marker: `@pytest.mark.e2e`
- Location: `tests/e2e/`

## Common Patterns

**Async Testing Pattern:**
```python
@pytest.mark.asyncio
async def test_async_operation(self):
    """Test asynchronous function."""
    result = await async_function()
    assert result is not None
```

Async with pytest-asyncio auto mode (configured in pytest.ini):
```python
# asyncio_mode = "auto" in pytest.ini means no need for @pytest.mark.asyncio
async def test_something(self):
    """Async test runs automatically."""
    await some_async_call()
```

**Error Testing Pattern:**
```python
def test_invalid_input_raises(self):
    """Test that invalid input raises appropriate exception."""
    with pytest.raises(ValueError) as exc_info:
        process_invalid_input()

    assert "expected message" in str(exc_info.value)
```

**Fixture with Setup/Teardown:**
```python
@pytest.fixture
def bus():
    """Fresh event bus for each test."""
    bus = EventBus()
    bus.reset()  # Setup
    yield bus
    bus.reset()  # Teardown
```

## Test Markers

**Available Markers** (defined in `pytest.ini`):
```ini
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow running tests
    llm: Tests requiring LLM calls
    asyncio: Async tests
    security: Security-related tests
```

**Usage:**
```python
@pytest.mark.slow
def test_long_running_operation():
    """This test takes a long time."""
    pass

@pytest.mark.llm
def test_with_llm_call():
    """Requires actual LLM API calls."""
    pass

@pytest.mark.security
def test_authorization():
    """Security-critical test."""
    pass
```

**Run by Marker:**
```bash
pytest -m unit              # Only unit tests
pytest -m "not slow"        # Skip slow tests
pytest -m "security"        # Security tests only
```

## Conftest Fixtures

**Location:** `/home/loc/workspace/gathering/tests/conftest.py`

**Key Fixtures:**
- `temp_dir`: Temporary directory with cleanup
- `basic_agent_config`: Standard agent configuration
- `agent_with_tools_config`: Agent with tools enabled
- `mock_llm_provider`: Mock LLM provider
- `calculator_tool`: Calculator tool instance
- `filesystem_tool`: Filesystem tool with temp directory

Example usage in tests:
```python
def test_file_operations(self, temp_dir):
    """Test with temporary directory fixture."""
    file_path = temp_dir / "test.txt"
    file_path.write_text("content")
    assert file_path.read_text() == "content"
```

## Test Naming Convention

**Test Class Names:**
- `Test` prefix followed by what's being tested
- Examples: `TestPasswordHashing`, `TestJWTTokens`, `TestEventBus`

**Test Function Names:**
- `test_` prefix describing specific behavior
- Pattern: `test_[what]_[condition]_[expected_result]`
- Examples:
  - `test_hash_password` - describes action
  - `test_verify_correct_password` - verb + context
  - `test_eval_blocks_import` - tests security constraint
  - `test_event_creation` - tests object creation

## Logging in Tests

**Configuration:**
- `log_cli = true` in pytest.ini
- `log_cli_level = INFO`
- Logs captured during test runs for debugging

**Usage:**
```python
import logging

logger = logging.getLogger(__name__)

def test_something():
    logger.info("Starting test")
    result = do_something()
    logger.info(f"Result: {result}")
```

---

*Testing analysis: 2026-02-10*
