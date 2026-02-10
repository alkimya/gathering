# Coding Conventions

**Analysis Date:** 2026-02-10

## Naming Patterns

**Files:**
- Lowercase with underscores: `file_manager.py`, `event_bus.py`
- Test files follow pattern: `test_*.py` (e.g., `test_auth.py`, `test_code_executor.py`)
- Exception files use plural when defining multiple classes: `exceptions.py`
- Class modules match class names in lowercase: `goals.py` contains `GoalManager`, `Goal`, etc.

**Functions:**
- Lowercase with underscores: `get_password_hash()`, `create_access_token()`, `verify_password()`
- Private/internal functions prefixed with underscore: `_row_to_goal()`, `_get_git_status()`, `_parse_decomposition_response()`
- Async functions use `async def` and maintain same naming: `async def get_goal()`, `async def build_context()`
- Public methods exposed in APIs documented and type-hinted

**Variables:**
- Lowercase with underscores for local variables: `goal_id`, `agent_id`, `user_message`
- Constants in UPPERCASE: `ALGORITHM = "HS256"`, `ACCESS_TOKEN_EXPIRE_HOURS = 24`, `EXCLUDED_PATTERNS = [...]`
- Type hints required for function parameters and returns
- Protected attributes prefixed with underscore: `_memories`, `_next_id`, `_persona_cache`

**Types:**
- Dataclasses with clear field documentation: `@dataclass class Goal: ...`
- Enum classes for finite sets: `class GoalStatus(Enum):`, `class EventType(Enum):`
- Pydantic models for API schemas: `class TokenData(BaseModel):`, `class UserCreate(BaseModel):`
- Protocol classes for interfaces: `class MemoryStore(Protocol):`

## Code Style

**Formatting:**
- Tool: `black` (line length 100)
- Target versions: Python 3.11, 3.12
- Exclude: `.git`, `.venv`, `build`, `dist`

**Linting:**
- Primary tool: `ruff` with multiple rule sets
- Rules enabled: E (pycodestyle errors), W (warnings), F (Pyflakes), I (isort), B (bugbear), C4 (comprehensions), UP (pyupgrade), S (security/bandit)
- Ignored: E501 (line too long - handled by black), S101 (assert in tests)
- Configuration: `pyproject.toml` [tool.ruff]

**Type Checking:**
- Tool: `mypy` (strict mode)
- Settings: `disallow_untyped_defs = true`, `disallow_incomplete_defs = true`, `check_untyped_defs = true`
- Exceptions: Tests excluded from mypy checks
- Python version: 3.11

## Import Organization

**Order:**
1. Standard library imports (`datetime`, `asyncio`, `logging`, `json`, etc.)
2. Third-party imports (`fastapi`, `pydantic`, `sqlalchemy`, etc.)
3. Local application imports (`from gathering.agents`, `from gathering.api`, etc.)
4. Blank line between groups

**Path Aliases:**
- Absolute imports preferred over relative imports
- Full module paths: `from gathering.agents.goals import Goal`
- Commonly organized by feature/module: `from gathering.agents`, `from gathering.workspace`, `from gathering.core`

**Example from `gathering/agents/goals.py`:**
```python
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from gathering.orchestration.events import EventBus, EventType
```

## Error Handling

**Patterns:**
- Custom exception hierarchy rooted in `GatheringError` (see `gathering/core/exceptions.py`)
- Context-specific exceptions: `ConfigurationError`, `AgentError`, `LLMProviderError`, `ToolExecutionError`, `SecurityError`, `MemoryOperationError`
- Exceptions capture details dict with metadata: `details: Optional[Dict[str, Any]]`
- `.to_dict()` method for serialization to logs
- Specific error types with properties (e.g., `is_retryable`, `is_auth_error` in `LLMProviderError`)

**Concrete Examples from `gathering/agents/goals.py`:**
```python
async def create_goal(self, goal: Goal) -> int:
    """Create a new goal."""
    if not self.db_service:
        raise ValueError("Database service not configured")
    # ... implementation

try:
    self.db_service.execute(...)
    return True
except Exception as e:
    logger.error(f"Failed to add dependency: {e}")
    return False
```

**Exception Classes Pattern:**
- All custom exceptions have clear docstrings
- Constructor accepts context parameters and builds `details` dict
- Example from `gathering/core/exceptions.py`:
```python
class ConfigurationError(GatheringError):
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
        expected: Optional[str] = None,
    ):
        details = {}
        if field:
            details["field"] = field
        super().__init__(message, details)
```

## Logging

**Framework:** Python's standard `logging` module via `structlog`

**Patterns:**
- Module-level logger: `logger = logging.getLogger(__name__)`
- Log at appropriate levels: debug, info, warning, error
- Include context in messages: `logger.info(f"Created goal {goal_id}: {goal.title}")`
- Error logging includes exception: `logger.error(f"Failed to add dependency: {e}")`
- Telemetry decorators add tracing: `@trace_method()`, `@trace_async_method()`

**Example from `gathering/agents/goals.py`:**
```python
logger = logging.getLogger(__name__)

# Usage
logger.info(f"Created goal {goal_id}: {goal.title}")
logger.error(f"Failed to add dependency: {e}")
```

## Comments

**When to Comment:**
- Complex algorithms that aren't immediately obvious
- Non-obvious business logic or domain decisions
- Workarounds and temporary solutions with explanation
- Section headers using equals/dashes: `# =============================================================================`

**JSDoc/TSDoc:**
- Docstrings on all public classes and functions
- Triple quotes for module docstrings at top of file
- Triple quotes for class/function docstrings with description, Args, Returns format

**Docstring Pattern from `gathering/api/auth.py`:**
```python
def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload data (should include 'sub' for user identification)
        expires_delta: Token expiration time (default: 24 hours)

    Returns:
        Encoded JWT token string
    """
```

## Function Design

**Size:** Prefer focused functions under 50 lines; break down larger operations into helper methods

**Parameters:**
- Explicit type hints required: `async def create_goal(self, goal: Goal) -> int:`
- Optional parameters use `Optional[T]` from typing
- Use type unions where appropriate: `Union[str, int]`
- Default values for optional parameters

**Return Values:**
- Explicit return type hints: `-> bool`, `-> Optional[Goal]`, `-> List[int]`
- Return `None` explicitly for optional returns
- Async functions return coroutines: `async def` followed by type hint
- Return dictionaries for complex multi-value returns: `-> Dict[str, Any]`

**Example from `gathering/agents/memory.py`:**
```python
async def build_context(
    self,
    agent_id: int,
    user_message: str,
    project_id: Optional[int] = None,
    include_memories: bool = True,
    memory_limit: int = 5,
) -> InjectedContext:
    """Build complete context for an LLM call."""
    context = InjectedContext()
    # ... implementation
    return context
```

## Module Design

**Exports:**
- Public interfaces at module level are clear
- Private implementation details prefixed with underscore
- Singleton patterns use module-level functions: `get_goal_manager()` returns cached `_goal_manager`

**Barrel Files:**
- `__init__.py` files export main classes/functions for clean imports
- Example: `from gathering.agents import GoalManager` (via `gathering/agents/__init__.py`)
- Avoid `from gathering.agents import *` - be explicit

**Example from `gathering/agents/goals.py`:**
```python
# Singleton instance
_goal_manager: Optional[GoalManager] = None

def get_goal_manager(
    db_service: Any = None,
    event_bus: Optional[EventBus] = None,
) -> GoalManager:
    """Get the global goal manager instance."""
    global _goal_manager
    if _goal_manager is None:
        _goal_manager = GoalManager(
            db_service=db_service,
            event_bus=event_bus,
        )
    return _goal_manager
```

## Dataclass Conventions

**Patterns:**
- Use `@dataclass` decorator for data models
- Field defaults: `field(default_factory=dict)` for mutable defaults
- Type hint all fields
- Include docstrings on the class
- Methods for computed properties: `@property` decorator for derived values

**Example from `gathering/agents/goals.py`:**
```python
@dataclass
class Goal:
    """Represents an agent goal."""
    id: int
    agent_id: int
    title: str
    description: str
    status: GoalStatus = GoalStatus.PENDING
    priority: GoalPriority = GoalPriority.MEDIUM
    progress_percent: int = 0

    # Mutable defaults with factory
    context: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    # Computed property
    def is_blocked(self) -> bool:
        """Check if goal is blocked by dependencies."""
        return self.blocking_count > 0
```

## Async/Await Patterns

- Async methods clearly marked: `async def method_name() -> Type:`
- Await all coroutines: `result = await self.store.search_memories(...)`
- Async context managers supported: `async with` for resource management
- pytest-asyncio for async test execution

---

*Convention analysis: 2026-02-10*
