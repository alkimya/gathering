# Phase 5: Multi-Instance + Production Hardening - Research

**Researched:** 2026-02-11
**Domain:** PostgreSQL advisory locks for distributed task coordination, FastAPI/uvicorn graceful shutdown with request draining
**Confidence:** HIGH

## Summary

Phase 5 addresses two distinct production requirements: (1) preventing duplicate task execution when multiple server instances process the same scheduler queue, and (2) ensuring zero-downtime rolling deploys by draining in-flight requests before process exit. Both requirements are well-served by the existing stack -- no new dependencies are needed.

The codebase already has a fully functional `AsyncPooledDatabase` (pycopg wrapper around `psycopg_pool.AsyncConnectionPool`) used by route handlers since Phase 4. PostgreSQL advisory locks (`pg_try_advisory_xact_lock`) are the standard mechanism for coordinating distributed task execution without external infrastructure. They work through regular SQL calls over existing database connections -- no Redis, ZooKeeper, or external coordination service required. The scheduler (`gathering/orchestration/scheduler.py`) currently uses an in-memory `asyncio.Lock` and `_running_actions` set to prevent concurrent execution, but this only protects a single process. Multiple uvicorn workers or separate pods will each have their own scheduler instance checking the same `circle.scheduled_actions` table.

For graceful shutdown, uvicorn 0.38.0 already handles SIGTERM natively: it stops accepting new connections and waits for in-flight requests to complete. However, the current application lifespan in `gathering/api/main.py` does not coordinate request draining with its internal subsystems (scheduler, background executor, async DB pool). The shutdown sequence needs to be ordered: stop the scheduler first (prevent new task creation), wait for in-flight HTTP requests to finish, pause background tasks, then close the async connection pool.

**Primary recommendation:** Add `pg_try_advisory_xact_lock(scheduled_action_id)` to the scheduler's `_execute_action` method so only one instance wins the lock per action execution cycle. For graceful shutdown, introduce a shutdown state flag that the `/health/ready` endpoint can reflect (returning 503 when shutting down), and ensure the lifespan shutdown sequence drains in-flight requests before closing subsystems.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| psycopg | 3.3.2 | PostgreSQL async driver | Already installed; advisory lock SQL runs over existing connections |
| psycopg_pool | 3.3.0 | Async connection pool | Already installed; provides `AsyncConnectionPool` with `connection()` context manager |
| pycopg (local) | 0.1.0 | High-level wrapper | Project's own lib; `AsyncPooledDatabase.connection()` yields raw `AsyncConnection` for lock queries |
| uvicorn | 0.38.0 | ASGI server | Already installed; native SIGTERM handling with graceful shutdown |
| FastAPI | 0.126.0 | Web framework | Already installed; `lifespan` context manager controls startup/shutdown |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-asyncio | >=0.21 | Async test runner | Already installed; needed for multi-instance coordination tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PG advisory locks | Redis distributed locks (redlock) | Adds external dependency; PG advisory locks work with existing infra and are ACID-compliant |
| PG advisory locks | `SELECT ... FOR UPDATE SKIP LOCKED` | Requires schema changes to treat the action table as a queue; advisory locks are orthogonal to data |
| uvicorn native shutdown | Custom signal handler with asyncio shutdown | Overcomplicates; uvicorn already sends lifespan shutdown event; just respond to it properly |
| In-process readiness flag | Kubernetes preStop hook sleep | PreStop is complementary but the app itself must also report not-ready via `/health/ready` |

**Installation:**
```bash
# No new dependencies required
```

## Architecture Patterns

### Current Scheduler Architecture (SINGLE-INSTANCE ONLY)
```
Instance A: Scheduler._run_loop()
  -> _check_and_execute_due_actions()
    -> asyncio.Lock (in-memory, process-local)
    -> _running_actions set (in-memory, process-local)
    -> Creates asyncio.Task for each due action
    -> PROBLEM: Instance B runs the same loop simultaneously
```

### Target Scheduler Architecture (MULTI-INSTANCE SAFE)
```
Instance A: Scheduler._run_loop()
  -> _check_and_execute_due_actions()
    -> For each due action:
      -> BEGIN TRANSACTION
      -> pg_try_advisory_xact_lock(action.id) -- non-blocking
      -> Returns TRUE: this instance wins, execute action
      -> Returns FALSE: another instance already has it, skip
      -> COMMIT (auto-releases xact lock)

Instance B: (runs same code simultaneously)
  -> pg_try_advisory_xact_lock(action.id) -- returns FALSE
  -> Skip -- no duplicate execution
```

### Key Design Decision: Transaction-Level vs Session-Level Locks

**Use `pg_try_advisory_xact_lock` (transaction-level), NOT `pg_try_advisory_lock` (session-level).**

Rationale:
- Transaction-level locks auto-release on COMMIT/ROLLBACK -- no risk of leaked locks
- Session-level locks persist until explicit unlock or session close -- dangerous with connection pooling because the connection returns to the pool with the lock still held
- The scheduler check-and-execute cycle is naturally transactional: acquire lock, mark action as executing, release lock

### Graceful Shutdown Sequence

```
SIGTERM received by uvicorn
  |
  v
uvicorn stops accepting new connections
  |
  v
FastAPI lifespan.__aexit__ called (the "yield" in lifespan finishes)
  |
  v
1. Set app-wide shutdown flag (AtomicBool or asyncio.Event)
2. /health/ready starts returning 503 (load balancer stops routing)
3. Stop scheduler (prevent new task creation)
     scheduler.stop(timeout=10)
4. Wait brief period for in-flight requests to drain (2-5s)
5. Pause background task executor
     executor.shutdown(timeout=30)
6. Close async database pool
     async_db.shutdown()
7. Process exits cleanly
```

### Pattern: Advisory Lock Wrapper for AsyncDatabaseService

```python
# In gathering/api/async_db.py or a new module
async def try_advisory_lock(pool: AsyncPooledDatabase, lock_id: int) -> bool:
    """Attempt to acquire a transaction-scoped advisory lock.

    Returns True if lock acquired, False if another session holds it.
    The lock auto-releases when the connection's transaction ends.
    """
    async with pool.connection() as conn:
        async with conn.transaction():
            cur = await conn.execute(
                "SELECT pg_try_advisory_xact_lock(%(lock_id)s) AS acquired",
                {"lock_id": lock_id},
            )
            row = await cur.fetchone()
            return row["acquired"] if row else False
```

### Pattern: Scheduler with Advisory Lock Guard

```python
# In Scheduler._execute_action()
async def _execute_action(self, action, triggered_by="scheduler"):
    # Attempt to acquire advisory lock for this action
    lock_acquired = await self._try_acquire_lock(action.id)
    if not lock_acquired:
        logger.debug("Action %s locked by another instance, skipping", action.id)
        return

    # Proceed with execution (only one instance reaches here)
    ...existing execution logic...
```

### Pattern: Readiness Probe Reflecting Shutdown State

```python
# In gathering/api/routers/health.py
_shutting_down = False

def set_shutting_down():
    global _shutting_down
    _shutting_down = True

@router.get("/ready")
async def readiness_check(request: Request):
    if _shutting_down:
        return JSONResponse(
            status_code=503,
            content={"ready": False, "reason": "shutting_down"},
        )
    return {"ready": True}
```

### Anti-Patterns to Avoid
- **Session-level advisory locks with connection pooling:** The connection returns to the pool with the lock still held. Next request gets the same connection and inherits the lock. Use transaction-level locks exclusively.
- **Blocking advisory locks (`pg_advisory_lock` without `try`):** If two instances both call `pg_advisory_lock` for the same key, one blocks until the other releases. Use `pg_try_advisory_lock` (non-blocking) so the losing instance skips immediately.
- **Relying on `asyncio.Lock` for cross-process coordination:** `asyncio.Lock` is per-event-loop, per-process. It cannot coordinate across uvicorn workers or pods.
- **Killing background tasks on shutdown:** Tasks should be paused with checkpoint, not cancelled. The current `executor.shutdown()` already does this correctly.
- **No shutdown timeout:** Always set a maximum wait time for shutdown. If background tasks hang, the process must eventually exit.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Distributed locking | Redis-based lock, file-based lock, custom DB row locking | `pg_try_advisory_xact_lock()` | Zero infrastructure; ACID; auto-releases on transaction end; no deadlock risk with `try` variant |
| Connection draining | Custom SIGTERM handler with request counter | uvicorn's native graceful shutdown + lifespan cleanup | uvicorn already tracks in-flight requests; lifespan gives you the shutdown hook |
| Leader election (scheduler) | Raft, external service discovery | Advisory lock on a well-known key (e.g., `hashlib.md5(b'scheduler').digest()[:8]`) | Only one instance should run the scheduler loop; advisory lock is sufficient for leader election |
| Health check during shutdown | Custom middleware checking process state | Readiness probe returning 503 + Kubernetes preStop hook | Standard K8s pattern; load balancer respects `/health/ready` returning 503 |

**Key insight:** PostgreSQL advisory locks are the single most important primitive for this phase. They replace Redis, ZooKeeper, and custom distributed locking -- all with zero additional infrastructure because the application already has PostgreSQL.

## Common Pitfalls

### Pitfall 1: Advisory Lock Key Collision
**What goes wrong:** Two unrelated features use the same advisory lock key space, causing unexpected blocking.
**Why it happens:** Advisory lock keys are global across the database. If the scheduler uses raw action IDs (1, 2, 3...) and some other feature also uses small integers as lock keys, they collide.
**How to avoid:** Namespace lock keys. Use the two-integer form: `pg_try_advisory_xact_lock(namespace, resource_id)` where `namespace` is a constant per feature (e.g., `1` for scheduler, `2` for background tasks). Or use a hash: `pg_try_advisory_xact_lock(hashint('scheduler:' || action_id))`.
**Warning signs:** Unexplained lock contention or stalls on unrelated features.

### Pitfall 2: Scheduler Running on All Instances
**What goes wrong:** Each server instance starts its own `Scheduler._run_loop()`, all checking the same `scheduled_actions` table. Even with advisory locks preventing duplicate execution, N instances doing N queries every 60 seconds is wasteful.
**Why it happens:** The scheduler starts unconditionally in `lifespan()`.
**How to avoid:** Either (a) use advisory lock-based leader election so only one instance runs the scheduler loop, or (b) keep all instances running the loop but rely on advisory locks per-action to prevent duplicates (simpler, slightly more DB load, but correct).
**Warning signs:** N times the expected number of scheduler check queries in pg_stat_statements.

### Pitfall 3: Connection Pool Exhaustion During Shutdown
**What goes wrong:** During shutdown, the async pool is closed before in-flight requests finish their database queries, causing connection errors.
**Why it happens:** Shutdown sequence closes the pool too early.
**How to avoid:** Close the async pool LAST in the shutdown sequence, after in-flight requests have drained.
**Warning signs:** "pool closed" errors in logs during deploys.

### Pitfall 4: Readiness Probe Not Reflecting Shutdown
**What goes wrong:** Load balancer keeps sending traffic to a pod that is shutting down, causing 502 errors.
**Why it happens:** `/health/ready` returns 200 even during shutdown.
**How to avoid:** Set a shutdown flag at the start of lifespan cleanup, have `/health/ready` check it, and use a Kubernetes preStop hook with a short sleep to give the load balancer time to notice.
**Warning signs:** 502/503 errors during rolling deploys.

### Pitfall 5: Lock Scope Too Broad
**What goes wrong:** An advisory lock is held during the entire task execution (which could take minutes/hours), blocking other instances from even checking if the task is done.
**Why it happens:** Using session-level lock acquired before execution starts.
**How to avoid:** Use transaction-level lock only for the "claim" phase. Once the action is claimed (status updated to 'running' in DB), release the lock. Other instances see 'running' status and skip.
**Warning signs:** Lock held for entire task duration; other instances permanently blocked on that action.

## Code Examples

### Advisory Lock Integration in Scheduler

```python
# Source: PostgreSQL docs + psycopg 3.3 async API
# In gathering/orchestration/scheduler.py

async def _try_acquire_action_lock(self, action_id: int) -> bool:
    """Try to acquire advisory lock for a scheduled action.

    Uses transaction-level lock that auto-releases on commit.
    Uses two-integer form: (NAMESPACE_SCHEDULER, action_id).
    """
    NAMESPACE_SCHEDULER = 1  # Namespace constant for scheduler locks

    if not self._async_db:
        return True  # No DB = single instance, always proceed

    try:
        async with self._async_db._pool.connection() as conn:
            async with conn.transaction():
                cur = await conn.execute(
                    "SELECT pg_try_advisory_xact_lock(%s, %s) AS acquired",
                    [NAMESPACE_SCHEDULER, action_id],
                )
                row = await cur.fetchone()
                return row["acquired"] if row else False
    except Exception as e:
        logger.warning("Advisory lock check failed for action %s: %s", action_id, e)
        return False  # Fail-safe: don't execute if lock check fails
```

### Graceful Shutdown Lifespan

```python
# Source: FastAPI lifespan docs + uvicorn SIGTERM behavior
# In gathering/api/main.py

import asyncio
from gathering.api.routers.health import set_shutting_down

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    # ... existing startup code ...

    yield

    # --- SHUTDOWN ---
    print("GatheRing API shutting down...")

    # 1. Signal health probes that we're shutting down
    set_shutting_down()

    # 2. Brief pause to let load balancer detect unhealthy state
    await asyncio.sleep(3)

    # 3. Stop the scheduler (no new tasks)
    try:
        scheduler = get_scheduler()
        await scheduler.stop(timeout=10)
        print("Scheduler stopped")
    except Exception as e:
        print(f"Warning: Error during scheduler shutdown: {e}")

    # 4. Gracefully shutdown background task executor (pause tasks)
    try:
        executor = get_background_executor()
        await executor.shutdown(timeout=30)
        print("Background task executor shutdown complete")
    except Exception as e:
        print(f"Warning: Error during background executor shutdown: {e}")

    # 5. Close async database pool LAST
    try:
        from gathering.api.async_db import AsyncDatabaseService
        if AsyncDatabaseService._instance is not None:
            await AsyncDatabaseService.get_instance().shutdown()
            print("Async database pool closed")
    except Exception as e:
        print(f"Warning: Error during async database pool shutdown: {e}")
```

### Multi-Instance Test Pattern

```python
# Test: Two concurrent scheduler instances don't execute the same action
import asyncio
import pytest

@pytest.mark.asyncio
async def test_advisory_lock_prevents_duplicate_execution(async_db):
    """Simulate two scheduler instances competing for the same action."""
    action_id = 42
    NAMESPACE = 1

    results = []

    async def try_lock_and_record(instance_name: str):
        async with async_db._pool.connection() as conn:
            async with conn.transaction():
                cur = await conn.execute(
                    "SELECT pg_try_advisory_xact_lock(%s, %s) AS acquired",
                    [NAMESPACE, action_id],
                )
                row = await cur.fetchone()
                acquired = row["acquired"]
                results.append((instance_name, acquired))
                if acquired:
                    # Simulate execution time
                    await asyncio.sleep(0.1)

    # Run two "instances" concurrently
    await asyncio.gather(
        try_lock_and_record("instance_a"),
        try_lock_and_record("instance_b"),
    )

    # Exactly one should have acquired the lock
    acquired_count = sum(1 for _, acquired in results if acquired)
    assert acquired_count == 1, f"Expected 1 lock acquisition, got {acquired_count}: {results}"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Redis/ZooKeeper for distributed locks | PG advisory locks for DB-backed apps | Always available, gaining adoption 2023-2025 | Zero additional infrastructure needed |
| Custom SIGTERM handler | uvicorn native graceful shutdown | uvicorn >= 0.17 (2022) | No custom signal handling code needed |
| Hard stop (kill -9) | Graceful drain with preStop hook | K8s standard since 1.15 (2019) | Zero-downtime deploys |
| `gunicorn --preload` with worker management | `uvicorn` with `--workers` flag | uvicorn 0.30+ (2024) | Simpler deployment; single process manager |

**Deprecated/outdated:**
- `gunicorn` as process manager for uvicorn: While still common, uvicorn 0.30+ supports `--workers` natively. For simple deployments, `uvicorn --workers N` is sufficient. For production K8s, single-worker containers with horizontal pod autoscaling is preferred.

## Open Questions

1. **Leader election vs per-action locking for scheduler**
   - What we know: Both approaches work. Per-action locking is simpler (no leader election), leader election reduces DB queries.
   - What's unclear: Project's scale requirements -- is the extra DB load from N instances each running scheduler checks acceptable?
   - Recommendation: Start with per-action advisory locking (simpler). Add leader election later only if DB query load becomes a concern. The scheduler checks every 60 seconds, so even with 4 instances, that's only 4 queries/minute.

2. **uvicorn `--workers` vs Kubernetes horizontal scaling**
   - What we know: The app uses singletons (`get_scheduler()`, `get_background_executor()`) which are process-local. Multiple uvicorn workers each get their own singleton.
   - What's unclear: Whether the deployment target is multi-worker uvicorn or multi-pod K8s.
   - Recommendation: Design for both. Advisory locks work regardless of whether "multiple instances" means uvicorn workers or K8s pods. The `workers: int = 4` setting in `Settings` suggests multi-worker uvicorn is planned.

3. **Scheduler check_interval tuning for multi-instance**
   - What we know: Current `check_interval=60` seconds. With N instances, the effective check frequency is N/60 per second.
   - What's unclear: Whether actions can tolerate up to 60s delay between scheduled time and execution.
   - Recommendation: Keep 60s for now. If lower latency is needed, reduce interval but add jitter (`check_interval + random(0, 10)`) to avoid thundering herd.

## Sources

### Primary (HIGH confidence)
- PostgreSQL 18 official docs - [Advisory Locks / Explicit Locking](https://www.postgresql.org/docs/current/explicit-locking.html) - session vs transaction level, auto-release semantics
- PostgreSQL 18 official docs - [Advisory Lock Functions](https://www.postgresql.org/docs/current/functions-admin.html) - function signatures for `pg_try_advisory_xact_lock(bigint)` and `pg_try_advisory_xact_lock(int, int)`
- psycopg 3.3 docs - [Connection pool API](https://www.psycopg.org/psycopg3/docs/api/pool.html) - `AsyncConnectionPool` with `connection()` context manager
- Codebase: `gathering/api/async_db.py` - existing `AsyncDatabaseService` with `_pool: AsyncPooledDatabase`
- Codebase: `gathering/orchestration/scheduler.py` - current scheduler with in-memory `_running_actions` set
- Codebase: `gathering/orchestration/background.py` - current `BackgroundTaskExecutor.shutdown()` with timeout
- Codebase: `gathering/api/main.py` - current lifespan with startup/shutdown sequence

### Secondary (MEDIUM confidence)
- [OneUpTime: How to Use Advisory Locks in PostgreSQL (2026)](https://oneuptime.com/blog/post/2026-01-25-use-advisory-locks-postgresql/view) - practical patterns for task queue coordination
- [Leapcell: Orchestrating Distributed Tasks with PG Advisory Locks](https://leapcell.io/blog/orchestrating-distributed-tasks-with-postgresql-advisory-locks) - multi-instance coordination patterns
- [Flavio Del Grosso: PostgreSQL Advisory Locks Explained](https://flaviodelgrosso.com/blog/postgresql-advisory-locks) - session vs transaction level deep-dive
- [FastAPI Discussion #6912: How to gracefully stop FastAPI app](https://github.com/fastapi/fastapi/discussions/6912) - lifespan shutdown patterns
- [Uvicorn Discussion #2257: Graceful Shutdown within Kubernetes](https://github.com/Kludex/uvicorn/discussions/2257) - uvicorn SIGTERM behavior
- [OneUpTime: Graceful Shutdown Handlers for Kubernetes (2026)](https://oneuptime.com/blog/post/2026-02-09-graceful-shutdown-handlers/view) - preStop hook + readiness probe pattern

### Tertiary (LOW confidence)
- [Codegenes: Understanding pg_try_advisory_lock behavior](https://www.codegenes.net/blog/acquiring-advisory-locks-in-postgres/) - edge cases with advisory locks and LIMIT clauses

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already installed, no new dependencies
- Architecture (advisory locks): HIGH - PostgreSQL docs are authoritative, psycopg async API verified in codebase
- Architecture (graceful shutdown): HIGH - uvicorn behavior verified, FastAPI lifespan pattern already in use
- Pitfalls: HIGH - well-documented in PostgreSQL docs and community sources
- Code examples: MEDIUM - patterns verified against codebase structure but untested

**Research date:** 2026-02-11
**Valid until:** 2026-04-11 (stable domain -- PostgreSQL advisory locks and uvicorn shutdown semantics change rarely)
