# Phase 4: Performance Optimization - Research

**Researched:** 2026-02-11
**Domain:** Database async access, query optimization, rate limiting, event bus throughput, in-memory cache bounding
**Confidence:** HIGH

## Summary

Phase 4 optimizes six distinct performance domains across the existing GatheRing codebase. The critical finding is that the project already ships with `pycopg` -- a local wrapper around `psycopg` 3.3.2 -- which includes a fully functional `AsyncDatabase` and `AsyncPooledDatabase` class that are **not currently used by any API route handler**. All database access in `api/dependencies.py` (the `DatabaseService` singleton) goes through the **sync** `Database` class, meaning every SQL call inside an `async def` FastAPI handler blocks the event loop. This is the single highest-impact optimization target.

The existing rate limiter is a hand-rolled `RateLimitMiddleware` using an unbounded `defaultdict(list)` with no per-endpoint tiers, no distributed backend, no `Retry-After` header on the response model (though it does add the header). The requirement calls for `slowapi`, which is the standard FastAPI rate-limiting library with per-endpoint decorators and Redis storage support. It is **not currently installed**.

The event bus (`gathering/events/event_bus.py`) uses `asyncio.gather` for concurrent handler dispatch, which is correct, but has **no batching, no deduplication, and spawns unbounded concurrent tasks** under rapid-fire emission. The in-memory caches (token blacklist, file tree, event history, LLM response cache, activity tracker, embedding cache) each have ad-hoc bounding -- some use `OrderedDict` with manual eviction, some use `deque(maxlen=...)`, some have **no bounds at all** (e.g., `ActivityTracker._activities`, `MemoryService._persona_cache`).

**Primary recommendation:** Migrate `DatabaseService` to use `AsyncPooledDatabase` from pycopg, replace the hand-rolled rate limiter with slowapi, add batching/dedup to the event bus, and unify all in-memory caches to a single bounded LRU pattern.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| psycopg | 3.3.2 | PostgreSQL async driver | Already installed; native async/await, connection pooling, COPY protocol |
| psycopg_pool | 3.3.0 | Async connection pool | Already installed; manages connection lifecycle for concurrent access |
| pycopg (local) | 0.1.0 | High-level wrapper | Project's own library; provides `AsyncDatabase` and `AsyncPooledDatabase` |
| slowapi | >=0.1.9 | Per-endpoint rate limiting | Standard FastAPI rate limiter; decorator-based, Redis backend support |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| redis | >=5.0 | Distributed rate-limit storage | Already in optional deps; needed for distributed slowapi backend |
| pytest-asyncio | >=0.21 | Async test runner | Already installed; needed for event bus concurrency tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| slowapi | Hand-rolled middleware (current) | Current implementation lacks per-endpoint tiers, Redis support, and proper 429 response format |
| psycopg async | asyncpg | asyncpg is already in requirements.txt but the codebase standardized on psycopg via pycopg wrapper; switching would require rewriting all SQL to use asyncpg's `$1` parameter style instead of `%(name)s` |
| OrderedDict LRU | `functools.lru_cache` | `lru_cache` works for function-level caching but not for dict-based stores like TokenBlacklist or EventBus history |
| OrderedDict LRU | `cachetools.LRUCache` | External dependency; `OrderedDict` with manual eviction is sufficient and already the pattern used in `TokenBlacklist` and `LRUCache` |

**Installation:**
```bash
pip install slowapi
```

## Architecture Patterns

### Current Database Architecture (SYNC -- blocks event loop)
```
FastAPI async handler
  -> DatabaseService (sync singleton)
    -> pycopg.Database (sync)
      -> psycopg.Connection (sync, blocks event loop!)
```

### Target Database Architecture (ASYNC -- non-blocking)
```
FastAPI async handler
  -> AsyncDatabaseService (async singleton)
    -> pycopg.AsyncPooledDatabase (async, pooled)
      -> psycopg.AsyncConnection (async, non-blocking)
```

### Pattern 1: AsyncPooledDatabase Lifecycle in FastAPI
**What:** Create the async connection pool during app lifespan, share via dependency injection
**When to use:** All async route handlers that access the database

```python
# Source: pycopg/pool.py (already in project)
from pycopg import AsyncPooledDatabase

# Global pool instance
_async_db: AsyncPooledDatabase | None = None

async def get_async_db() -> AsyncPooledDatabase:
    """FastAPI dependency for async database access."""
    if _async_db is None:
        raise RuntimeError("Database pool not initialized")
    return _async_db

# In lifespan:
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _async_db
    _async_db = AsyncPooledDatabase.from_env(min_size=4, max_size=20)
    await _async_db.open()
    yield
    await _async_db.close()
    _async_db = None
```

### Pattern 2: slowapi Per-Endpoint Rate Limiting
**What:** Decorator-based rate limits on individual endpoints with tiered limits
**When to use:** All API endpoints, with different limits per sensitivity level

```python
# Source: slowapi docs / GitHub
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Different tiers per endpoint
@router.post("/auth/login")
@limiter.limit("5/minute")  # Strict: auth endpoints
async def login(request: Request): ...

@router.get("/agents")
@limiter.limit("60/minute")  # Standard: read endpoints
async def list_agents(request: Request): ...

@router.post("/circles/{name}/tasks")
@limiter.limit("30/minute")  # Moderate: write endpoints
async def create_task(request: Request): ...
```

### Pattern 3: Event Bus Batching with asyncio.Queue
**What:** Buffer rapid events in a queue, process in batches with configurable window
**When to use:** When event emission rate exceeds 100 events/second

```python
import asyncio
from collections import defaultdict

class BatchingEventBus:
    def __init__(self, batch_window_ms: int = 50, max_batch_size: int = 100):
        self._queue: asyncio.Queue[Event] = asyncio.Queue()
        self._batch_window = batch_window_ms / 1000.0
        self._max_batch_size = max_batch_size
        self._seen: dict[str, float] = {}  # dedup: event_key -> timestamp
        self._dedup_window = 1.0  # seconds

    async def publish(self, event: Event) -> None:
        # Deduplication: skip if same event type+data seen within window
        dedup_key = f"{event.type.value}:{hash(frozenset(event.data.items()))}"
        now = event.timestamp.timestamp()
        if dedup_key in self._seen and (now - self._seen[dedup_key]) < self._dedup_window:
            return  # Duplicate, skip
        self._seen[dedup_key] = now
        await self._queue.put(event)

    async def _process_loop(self):
        """Background task: drain queue in batches."""
        while True:
            batch = []
            try:
                # Wait for first event
                event = await self._queue.get()
                batch.append(event)
                # Collect more within window
                deadline = asyncio.get_event_loop().time() + self._batch_window
                while len(batch) < self._max_batch_size:
                    timeout = deadline - asyncio.get_event_loop().time()
                    if timeout <= 0:
                        break
                    event = await asyncio.wait_for(self._queue.get(), timeout=timeout)
                    batch.append(event)
            except asyncio.TimeoutError:
                pass
            if batch:
                await self._dispatch_batch(batch)
```

### Pattern 4: Bounded LRU Cache with OrderedDict
**What:** Consistent pattern for all in-memory caches with configurable max size and LRU eviction
**When to use:** TokenBlacklist, event history, file tree cache, activity tracker, embedding cache

```python
from collections import OrderedDict
from typing import Optional, TypeVar

V = TypeVar("V")

class BoundedLRUDict(OrderedDict[str, V]):
    """OrderedDict with max size and LRU eviction."""
    def __init__(self, max_size: int = 1000, *args, **kwargs):
        self._max_size = max_size
        super().__init__(*args, **kwargs)

    def __setitem__(self, key: str, value: V) -> None:
        if key in self:
            self.move_to_end(key)
        super().__setitem__(key, value)
        while len(self) > self._max_size:
            self.popitem(last=False)  # Evict LRU

    def __getitem__(self, key: str) -> V:
        self.move_to_end(key)  # Mark as recently used
        return super().__getitem__(key)

    @property
    def max_size(self) -> int:
        return self._max_size
```

### Anti-Patterns to Avoid
- **Sync DB in async handlers:** The current `DatabaseService` calls sync `psycopg` inside async FastAPI handlers. This blocks the event loop and serializes all DB-bound requests. Every `db.execute()` call in an `async def` handler is a blocking call.
- **Unbounded `defaultdict(list)` for rate limiting:** The current `RateLimitMiddleware.requests` grows without bound across all IPs. A long-running server will accumulate stale entries. Use slowapi which handles cleanup internally.
- **`asyncio.gather(*tasks)` without concurrency limit:** The event bus creates one task per handler per event. Under 100+ events/sec with 10 handlers, that is 1000+ concurrent tasks per second with no backpressure.
- **`functools.lru_cache()` for singletons:** Already used in `api/dependencies.py`. These are unbounded and cannot be inspected or configured. The current usage is acceptable for singletons but should not be extended to data caches.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Per-endpoint rate limiting | `RateLimitMiddleware` (current) | slowapi `@limiter.limit()` | Handles cleanup, Redis backend, Retry-After headers, per-endpoint tiers, shared/exempt limits |
| Async DB access | Wrapping sync calls in `asyncio.to_thread` | `AsyncPooledDatabase` (already in pycopg) | Thread pool is limited and adds overhead; native async is zero-copy |
| Connection pooling | SQLAlchemy `QueuePool` (current in `database.py`) | `psycopg_pool.AsyncConnectionPool` (via pycopg) | Native async pool with health checks, idle management, max lifetime |
| Distributed rate limiting | Redis-based sliding window | slowapi with `RedisStorage` | Proven algorithm, handles distributed coordination |
| LRU eviction | Manual `popitem(last=False)` | Consistent `BoundedLRUDict` wrapper | Single pattern reduces bugs; `__getitem__` override ensures access-order tracking |

**Key insight:** The project already has the async database infrastructure (pycopg `AsyncDatabase` + `AsyncPooledDatabase`) fully implemented and tested -- it just is not wired into the API layer. The migration is about plumbing, not building from scratch.

## Common Pitfalls

### Pitfall 1: Mixing sync and async database calls
**What goes wrong:** Adding async DB methods while leaving sync fallbacks causes subtle bugs. Some paths go async, others still block the event loop.
**Why it happens:** Incremental migration leaves sync paths alive "just in case."
**How to avoid:** Migrate `DatabaseService` wholesale. Create `AsyncDatabaseService` as the new singleton. Keep the old `DatabaseService` only for non-async contexts (CLI, migrations, scripts) -- never call it from an `async def` route.
**Warning signs:** Import of both `DatabaseService` and `AsyncDatabaseService` in the same router module.

### Pitfall 2: slowapi decorator order
**What goes wrong:** Rate limit not applied because decorator is in wrong position relative to router decorator.
**Why it happens:** slowapi needs `request: Request` in the handler signature, and the decorator must be placed *after* the route decorator.
**How to avoid:** Always use pattern: `@router.get(...)` then `@limiter.limit(...)` then `async def handler(request: Request, ...)`.
**Warning signs:** 429 responses never returned even under heavy load.

### Pitfall 3: Event deduplication key collision
**What goes wrong:** Two semantically different events get the same dedup key, causing one to be silently dropped.
**Why it happens:** Dedup key based only on event type, not including discriminating data fields.
**How to avoid:** Include `event.type`, `event.source_agent_id`, `event.circle_id`, and a hash of key data fields in the dedup key.
**Warning signs:** Missing events in subscribers despite confirmed publish calls.

### Pitfall 4: Forgetting to await pool.open() before use
**What goes wrong:** `AsyncPooledDatabase` created with `open=False` (the default), but `await pool.open()` never called. All queries fail with "pool not open" errors.
**Why it happens:** Pool creation is sync, opening is async. Easy to forget the second step.
**How to avoid:** Always open in the FastAPI lifespan `yield` block. Add a runtime check in the dependency function.
**Warning signs:** `PoolTimeout` or `PoolClosed` exceptions on first request.

### Pitfall 5: N+1 queries hidden by sync-to-async migration
**What goes wrong:** Migrating sync N+1 code to async makes each query non-blocking but the *count* of queries remains the same. Performance improves per-query but total latency is still proportional to N.
**Why it happens:** Async migration fixes event loop blocking but not query patterns.
**How to avoid:** Fix N+1 patterns (PERF-02) *before* or *during* async migration, not after.
**Warning signs:** Circle member retrieval still executes 20+ queries visible in SQL logs, even though they are async.

### Pitfall 6: Unbounded `_seen` dict in event deduplication
**What goes wrong:** The dedup dict for event batching grows without bound if events have unique keys.
**Why it happens:** Old entries are never cleaned up.
**How to avoid:** Periodically prune entries older than the dedup window. Use a TTL-aware dict or clean up in the batch processing loop.
**Warning signs:** Gradual memory growth on long-running servers.

## Code Examples

### Circle Member Retrieval: N+1 vs JOIN (PERF-02)

Current pattern (N+1 hidden in `_load_from_db`):
```python
# gathering/api/dependencies.py lines 850-863
# For each circle, calls get_circle_members_with_info which is already a JOIN
# BUT: _load_from_db calls self._db.get_agent(agent_id_local) INSIDE the member loop
# That's an extra query per member.

for member in members:
    # ...
    agent_data = self._db.get_agent(agent_id_local)  # N+1 QUERY per member
    system_prompt = agent_data.get('system_prompt')
    skill_row = self._db.execute_one(                 # ANOTHER N+1 per member
        "SELECT skill_names FROM agent.agents WHERE id = %(id)s",
        {'id': agent_id_local}
    )
```

Target pattern (single JOIN query):
```python
# Single query that gets circle + all members + agent details
members_with_details = await db.execute("""
    SELECT
        m.*,
        a.name as agent_name,
        a.system_prompt,
        a.base_prompt,
        a.skill_names,
        p.name as provider_name,
        mod.model_name,
        mod.model_alias
    FROM circle.members m
    JOIN agent.agents a ON a.id = m.agent_id
    LEFT JOIN agent.models mod ON a.model_id = mod.id
    LEFT JOIN agent.providers p ON mod.provider_id = p.id
    WHERE m.circle_id = %s AND m.is_active = true
""", [circle_id])
# One query instead of 2N+1
```

### AsyncDatabaseService Migration (PERF-01)

```python
# New async service using pycopg's AsyncPooledDatabase
from pycopg import AsyncPooledDatabase, Config

class AsyncDatabaseService:
    """Async database service for API using pycopg AsyncPooledDatabase."""

    _instance: Optional['AsyncDatabaseService'] = None

    def __init__(self):
        config = Config.from_env()
        self._pool = AsyncPooledDatabase(config, min_size=4, max_size=20)

    async def startup(self):
        """Call during FastAPI lifespan startup."""
        await self._pool.open()

    async def shutdown(self):
        """Call during FastAPI lifespan shutdown."""
        await self._pool.close()

    async def execute(self, sql: str, params=None) -> list[dict]:
        """Execute query and return list of dicts (non-blocking)."""
        return await self._pool.execute(sql, params or [])

    async def execute_one(self, sql: str, params=None) -> Optional[dict]:
        """Execute query and return first row (non-blocking)."""
        return await self._pool.fetch_one(sql, params or [])
```

### slowapi Integration (PERF-03)

```python
# gathering/api/rate_limit.py (new file)
from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limit tiers
TIER_AUTH = "5/minute"       # Authentication endpoints
TIER_WRITE = "30/minute"     # Write/mutation endpoints
TIER_READ = "120/minute"     # Read endpoints
TIER_HEALTH = "300/minute"   # Health/status endpoints

def get_limiter() -> Limiter:
    """Create limiter with optional Redis backend."""
    from gathering.core.config import get_settings
    settings = get_settings()

    # Use Redis if available for distributed support
    storage_uri = None
    if hasattr(settings, 'redis_url') and settings.redis_url:
        storage_uri = settings.redis_url

    return Limiter(
        key_func=get_remote_address,
        storage_uri=storage_uri,  # None = in-memory, "redis://..." = distributed
        default_limits=["120/minute"],
    )
```

### Event Bus Concurrency Test (TEST-04)

```python
# tests/test_event_bus_concurrency.py
import asyncio
import pytest
from gathering.events import EventBus, Event, EventType

@pytest.mark.asyncio
async def test_parallel_handlers_no_race_condition():
    """Verify handlers run concurrently without data corruption."""
    bus = EventBus()
    bus.reset()
    counter = {"value": 0}
    lock = asyncio.Lock()

    async def safe_increment(event: Event):
        async with lock:
            current = counter["value"]
            await asyncio.sleep(0.001)  # Simulate work
            counter["value"] = current + 1

    for _ in range(10):
        bus.subscribe(EventType.TASK_COMPLETED, safe_increment)

    await bus.publish(Event(type=EventType.TASK_COMPLETED))
    assert counter["value"] == 10  # All 10 handlers ran

@pytest.mark.asyncio
async def test_rapid_fire_does_not_exhaust_memory():
    """100+ events/second should not create unbounded tasks."""
    bus = EventBus()
    bus.reset()
    received = []

    async def handler(event: Event):
        received.append(event.id)

    bus.subscribe(EventType.TASK_CREATED, handler)

    # Fire 200 events rapidly
    for i in range(200):
        await bus.publish(Event(
            type=EventType.TASK_CREATED,
            data={"id": i},
        ))

    assert len(received) == 200

@pytest.mark.asyncio
async def test_event_ordering_preserved():
    """Events should be delivered to each handler in publish order."""
    bus = EventBus()
    bus.reset()
    order = []

    async def handler(event: Event):
        order.append(event.data["seq"])

    bus.subscribe(EventType.TASK_CREATED, handler)

    for i in range(50):
        await bus.publish(Event(
            type=EventType.TASK_CREATED,
            data={"seq": i},
        ))

    assert order == list(range(50))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| asyncpg for async PostgreSQL | psycopg 3 async | psycopg 3.0 (2021), mature by 3.1 (2023) | Unified sync/async API, native Python types, COPY protocol |
| flask-limiter | slowapi (adapted from flask-limiter for Starlette/FastAPI) | 2020+ | Drop-in FastAPI support with per-endpoint decorators |
| SQLAlchemy async + asyncpg | psycopg 3 + psycopg_pool directly | 2023+ trend | Simpler stack, fewer layers, better pool management |
| Manual OrderedDict LRU | Still manual (no stdlib bounded dict) | N/A | Python stdlib has no built-in bounded LRU dict; OrderedDict pattern remains standard |

**Deprecated/outdated:**
- `asyncpg` in requirements.txt: Still listed but not used by any import in the `gathering/` package. Can be removed once async migration to psycopg is complete.
- `psycopg2-binary` in requirements.txt: Legacy sync driver. Only needed for Alembic migrations. Not needed for runtime async.
- `python-jose[cryptography]` in requirements.txt: Already replaced by `PyJWT[crypto]` in Phase 1, but the old dependency line is still in `requirements.txt`.

## Open Questions

1. **Parameter style compatibility**
   - What we know: pycopg's `AsyncDatabase.execute()` uses `%s` positional parameters (psycopg native style). The current `DatabaseService` uses `%(name)s` named parameters throughout.
   - What's unclear: Whether `AsyncPooledDatabase.execute()` supports named parameters or only positional.
   - Recommendation: Test with named parameters. psycopg 3 supports both `%s` and `%(name)s` in its cursor. If the pool wrapper passes through to psycopg cursors, named params should work. Verify with a quick test before committing to a migration approach.

2. **slowapi interaction with existing AuthenticationMiddleware**
   - What we know: slowapi works via `app.state.limiter` and an exception handler. The existing `AuthenticationMiddleware` and `RateLimitMiddleware` both run as Starlette middleware.
   - What's unclear: Whether slowapi decorators can coexist with the existing middleware stack or if `RateLimitMiddleware` must be fully removed first.
   - Recommendation: Remove `RateLimitMiddleware` entirely and replace with slowapi. They serve the same purpose; running both would cause double-limiting.

3. **Event bus batching backward compatibility**
   - What we know: Current `publish()` is fire-and-forget with immediate handler dispatch. Batching introduces a delay window.
   - What's unclear: Whether any subscriber depends on synchronous delivery semantics (event delivered before `publish()` returns).
   - Recommendation: Make batching opt-in via a `batch=True` parameter on `publish()` for new high-frequency paths. Keep the default synchronous delivery for backward compatibility. Add the batch processing loop as an optional background task.

4. **Redis availability for slowapi**
   - What we know: Redis is listed as an optional dependency (`extras = ["redis"]`). Not all deployment environments will have Redis.
   - What's unclear: Whether production deployments currently run Redis.
   - Recommendation: Configure slowapi to use in-memory storage by default, with Redis as an opt-in via `REDIS_URL` environment variable. This matches the existing pattern in `cache/redis_cache.py` which gracefully falls back when Redis is unavailable.

## Sources

### Primary (HIGH confidence)
- pycopg source code: `/home/loc/workspace/gathering/venv/lib/python3.13/site-packages/pycopg/` -- AsyncDatabase, AsyncPooledDatabase, Config, pool.py (verified locally, version 0.1.0)
- psycopg 3.3.2 installed locally -- `psycopg.AsyncConnection`, `psycopg_pool.AsyncConnectionPool`
- Existing codebase: `gathering/api/dependencies.py`, `gathering/api/middleware.py`, `gathering/events/event_bus.py`, `gathering/api/auth.py`, `gathering/cache/redis_cache.py` -- current implementations analyzed

### Secondary (MEDIUM confidence)
- [psycopg 3 Connection Pool documentation](https://www.psycopg.org/psycopg3/docs/advanced/pool.html) -- Pool lifecycle, FastAPI integration patterns
- [psycopg_pool API reference](https://www.psycopg.org/psycopg3/docs/api/pool.html) -- AsyncConnectionPool parameters and methods
- [slowapi GitHub](https://github.com/laurentS/slowapi) -- Per-endpoint decorators, Redis storage, exception handler setup
- [slowapi PyPI](https://pypi.org/project/slowapi/) -- Version info, compatibility
- [slowapi Documentation](https://slowapi.readthedocs.io/) -- Configuration options, rate string format
- [Asynchronous Postgres with Python, FastAPI, and Psycopg 3](https://medium.com/@benshearlaw/asynchronous-postgres-with-python-fastapi-and-psycopg-3-fafa5faa2c08) -- Lifespan pattern
- [FastAPI, Pydantic, Psycopg3: The Ultimate Trio](https://spwoodcock.dev/blog/2024-10-fastapi-pydantic-psycopg/) -- Dependency injection pattern

### Tertiary (LOW confidence)
- [Mastering Event-Driven Architecture in Python with AsyncIO](https://medium.com/data-science-collective/mastering-event-driven-architecture-in-python-with-asyncio-and-pub-sub-patterns-2b26db3f11c9) -- AsyncIO pub/sub patterns
- [3 Essential Async Patterns for Python Services (Elastic Blog)](https://www.elastic.co/blog/async-patterns-building-python-service) -- Batching and queue patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- psycopg/psycopg_pool already installed and verified; slowapi is the established FastAPI rate limiter
- Architecture: HIGH -- pycopg `AsyncPooledDatabase` already exists with full API; migration path is clear
- Pitfalls: HIGH -- Derived from direct analysis of existing codebase patterns and known asyncio gotchas
- Event bus batching: MEDIUM -- Pattern is well-understood but specific dedup key design needs validation
- N+1 queries: HIGH -- Identified specific lines in `dependencies.py` where N+1 occurs

**Research date:** 2026-02-11
**Valid until:** 2026-03-11 (stable domain; libraries are mature)
