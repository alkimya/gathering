# Testing

GatheRing uses pytest for testing with a focus on test-driven development (TDD).

## Test Structure

```text
tests/
├── unit/                          # Unit tests
│   ├── test_agents.py
│   ├── test_circles.py
│   ├── test_memory.py
│   └── test_tools.py
├── integration/                   # Integration tests
│   ├── test_api.py
│   ├── test_database.py
│   └── test_websocket.py
├── e2e/                           # End-to-end tests
│   └── test_workflows.py
├── test_auth_persistence.py       # Auth lifecycle (v1.0)
├── test_sql_security.py           # SQL injection prevention (v1.0)
├── test_path_traversal.py         # Path traversal defense (v1.0)
├── test_pipeline_validation.py    # DAG validation, cycle rejection (v1.0)
├── test_pipeline_execution.py     # Node execution, retry, circuit breaker (v1.0)
├── test_pipeline_cancellation.py  # Cancellation, timeout (v1.0)
├── test_scheduler_recovery.py     # Crash recovery, deduplication (v1.0)
├── test_tool_validation.py        # JSON Schema validation (v1.0)
├── test_event_bus_concurrency.py  # Parallel handling, dedup, ordering (v1.0)
├── test_async_database.py         # Async DB concurrency (v1.0)
├── test_rate_limit_tiers.py       # Per-endpoint rate limiting (v1.0)
├── test_advisory_locks.py         # Multi-instance coordination (v1.0)
├── test_graceful_shutdown.py      # Shutdown draining (v1.0)
├── conftest.py                    # Shared fixtures
└── fixtures/                      # Test data
    ├── agents.json
    └── conversations.json
```

### v1.0 Test Categories

| Category | Tests | What They Prove |
|----------|-------|----------------|
| Auth lifecycle | ~50 | Token creation, expiry, blacklist persistence, constant-time auth |
| Pipeline execution | ~41 | DAG traversal, node dispatch, retry, circuit breaker, cancellation, timeout |
| Scheduler recovery | ~28 | Action dispatch, crash recovery, dedup, race conditions |
| Tool validation | ~15 | JSON Schema validation, async execution, workspace paths |
| Event concurrency | ~7 | Parallel handling, dedup, ordering, backpressure |
| Rate limiting | ~5 | Per-endpoint tiers, 429 response, Retry-After headers |
| Advisory locks | ~5 | Multi-instance coordination, fail-closed behavior |
| Graceful shutdown | ~5 | Ordered teardown, readiness probe, request draining |

## Running Tests

### All Tests

```bash
pytest
```

### With Coverage

```bash
pytest --cov=gathering --cov-report=html
```

### Specific Tests

```bash
# Single file
pytest tests/unit/test_agents.py

# Single test
pytest tests/unit/test_agents.py::test_create_agent

# By marker
pytest -m "not slow"

# By keyword
pytest -k "memory"
```

### Verbose Output

```bash
pytest -v --tb=short
```

## Writing Tests

### Basic Test

```python
# tests/unit/test_agents.py
import pytest
from gathering.agents import Agent


def test_create_agent():
    """Test basic agent creation."""
    # Arrange
    config = {"name": "TestAgent", "provider": "openai", "model": "gpt-4o"}

    # Act
    agent = Agent.from_config(config)

    # Assert
    assert agent.name == "TestAgent"
    assert agent.provider == "openai"
    assert agent.model == "gpt-4o"
```

### Async Tests

```python
import pytest


@pytest.mark.asyncio
async def test_agent_process_message():
    """Test async message processing."""
    agent = Agent(name="Test", provider="anthropic", model="claude-sonnet-4-20250514")

    response = await agent.process_message("Hello")

    assert response is not None
    assert len(response) > 0
```

### Parametrized Tests

```python
import pytest


@pytest.mark.parametrize("provider,model,expected_class", [
    ("openai", "gpt-4o", "OpenAIProvider"),
    ("anthropic", "claude-sonnet-4-20250514", "AnthropicProvider"),
    ("ollama", "llama3.2", "OllamaProvider"),
])
def test_provider_initialization(provider, model, expected_class):
    """Test provider initialization."""
    agent = Agent(name="Test", provider=provider, model=model)
    assert agent.llm_provider.__class__.__name__ == expected_class
```

### Test Classes

```python
class TestAgentMemory:
    """Tests for agent memory functionality."""

    def test_memory_stores_messages(self, agent):
        """Test that messages are stored."""
        agent.process_message("Hello")
        history = agent.memory.get_history()
        assert len(history) >= 1

    def test_memory_clears(self, agent):
        """Test memory clearing."""
        agent.process_message("Hello")
        agent.memory.clear()
        assert len(agent.memory.get_history()) == 0
```

## Fixtures

### Basic Fixtures

```python
# tests/conftest.py
import pytest
from gathering.agents import Agent
from gathering.db import Database


@pytest.fixture
def agent():
    """Create a test agent."""
    return Agent(name="TestAgent", provider="ollama", model="llama3.2")


@pytest.fixture
async def db():
    """Create a test database connection."""
    database = Database(test=True)
    await database.connect()
    yield database
    await database.disconnect()
```

### Scoped Fixtures

```python
@pytest.fixture(scope="session")
def app():
    """Create app once per test session."""
    from gathering.api.app import create_app
    return create_app(testing=True)


@pytest.fixture(scope="function")
async def clean_db(db):
    """Clean database before each test."""
    await db.execute("TRUNCATE agent.agents CASCADE")
    yield db
```

### Factory Fixtures

```python
@pytest.fixture
def agent_factory():
    """Factory for creating test agents."""
    created = []

    def _create(name="Test", provider="ollama", model="llama3.2", **kwargs):
        agent = Agent(name=name, provider=provider, model=model, **kwargs)
        created.append(agent)
        return agent

    yield _create

    # Cleanup
    for agent in created:
        agent.cleanup()


def test_with_factory(agent_factory):
    agent1 = agent_factory(name="Agent1")
    agent2 = agent_factory(name="Agent2", provider="openai", model="gpt-4o")
    # ...
```

## Mocking

### Basic Mocking

```python
from unittest.mock import Mock, patch


def test_with_mock():
    mock_llm = Mock()
    mock_llm.generate.return_value = "Mocked response"

    agent = Agent(name="Test", provider="openai", model="gpt-4o", llm=mock_llm)
    response = agent.process_message("Hello")

    assert response == "Mocked response"
    mock_llm.generate.assert_called_once()
```

### Patching

```python
from unittest.mock import patch


@patch("gathering.agents.llm_client")
def test_with_patch(mock_client):
    mock_client.generate.return_value = Mock(
        content=[Mock(text="Response")]
    )

    agent = Agent(name="Test", provider="anthropic", model="claude-sonnet-4-20250514")
    response = agent.process_message("Hello")

    assert response == "Response"
```

### Async Mocking

```python
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_async_mock():
    mock_db = AsyncMock()
    mock_db.fetch_one.return_value = {"id": 1, "name": "Test"}

    result = await mock_db.fetch_one("SELECT * FROM agents WHERE id = 1")

    assert result["name"] == "Test"
```

## API Testing

### Testing Endpoints

```python
import pytest
from httpx import AsyncClient
from gathering.api.app import app


@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_list_agents(client):
    response = await client.get("/agents")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_agent(client):
    response = await client.post(
        "/agents",
        json={
            "name": "NewAgent",
            "provider": "anthropic",
            "model": "claude-sonnet-4-20250514"
        },
    )

    assert response.status_code == 201
    assert response.json()["name"] == "NewAgent"
```

### Testing WebSocket

```python
from starlette.testclient import TestClient


def test_websocket_connection():
    client = TestClient(app)

    with client.websocket_connect("/ws/circles/test") as ws:
        ws.send_json({"type": "ping"})
        response = ws.receive_json()
        assert response["type"] == "pong"
```

## Database Testing

### Test Database

```python
# tests/conftest.py
import pytest
from gathering.db import Database


@pytest.fixture(scope="session")
async def test_db():
    """Create test database."""
    db = Database(url="postgresql://localhost/gathering_test")
    await db.connect()
    await db.run_migrations()
    yield db
    await db.disconnect()


@pytest.fixture(autouse=True)
async def clean_tables(test_db):
    """Clean tables before each test."""
    await test_db.execute("TRUNCATE agent.agents CASCADE")
    yield
```

### Testing Queries

```python
@pytest.mark.asyncio
async def test_insert_agent(test_db):
    result = await test_db.execute(
        """
        INSERT INTO agent.agents (name, provider, model)
        VALUES ($1, $2, $3)
        RETURNING id
        """,
        "TestAgent",
        "openai",
        "gpt-4o",
    )

    assert result["id"] is not None

    agent = await test_db.fetch_one(
        "SELECT * FROM agent.agents WHERE id = $1",
        result["id"],
    )
    assert agent["name"] == "TestAgent"
    assert agent["provider"] == "openai"
```

## Test Markers

```python
# pytest.ini
[pytest]
markers =
    slow: marks tests as slow
    integration: marks integration tests
    e2e: marks end-to-end tests
```

Usage:

```python
@pytest.mark.slow
def test_large_dataset():
    # ...


@pytest.mark.integration
async def test_database_integration():
    # ...
```

Running:

```bash
# Skip slow tests
pytest -m "not slow"

# Only integration tests
pytest -m integration
```

## Test Coverage

### Configuration

```ini
# .coveragerc
[run]
source = gathering
omit =
    */tests/*
    */__init__.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise NotImplementedError
```

### Running Coverage

```bash
# Generate coverage report
pytest --cov=gathering --cov-report=html

# Check minimum coverage
pytest --cov=gathering --cov-fail-under=80
```

## Best Practices

### 1. Follow AAA Pattern

```python
def test_something():
    # Arrange - Set up test data
    data = create_test_data()

    # Act - Perform the action
    result = do_something(data)

    # Assert - Verify the result
    assert result == expected
```

### 2. One Assertion Per Test (When Possible)

```python
# Good - focused tests
def test_agent_has_name():
    agent = Agent(name="Test")
    assert agent.name == "Test"


def test_agent_has_default_provider():
    agent = Agent(name="Test")
    assert agent.provider == "anthropic"  # default provider
```

### 3. Use Descriptive Names

```python
# Good
def test_agent_raises_error_when_name_is_empty():
    with pytest.raises(ValueError):
        Agent(name="")


# Bad
def test_agent_error():
    # ...
```

### 4. Isolate Tests

Tests should not depend on each other or external state.

### 5. Mock External Services

```python
@patch("gathering.llm.anthropic_client")
def test_without_real_api(mock_client):
    # Test without calling real API
    pass
```

## Continuous Integration

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: gathering_test
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt

      - name: Run tests
        run: |
          pytest --cov=gathering --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Related Topics

- [Contributing](contributing.md) - Contribution guidelines
- [API](api.md) - API testing
- [Database](database.md) - Database testing
