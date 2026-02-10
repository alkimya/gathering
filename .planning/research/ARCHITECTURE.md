# Architecture Research

**Domain:** Production-hardening of existing multi-agent AI framework
**Researched:** 2026-02-10
**Confidence:** HIGH (based on direct codebase analysis of all relevant source files)

## Current Architecture (As-Is)

### System Overview

```
+-----------------------------------------------------------------------+
|                       React 19 Dashboard                              |
|   (pages: Agents, Circles, Tasks, Schedules, Goals, Settings, IDE)   |
+----------------------------+------------------------------------------+
                             |  HTTP/REST + WebSocket
+----------------------------v------------------------------------------+
|                         API Layer (FastAPI)                            |
|  +-------------+  +----------+  +-------------+  +-----------+        |
|  | 18+ Routers |  | Auth/JWT |  | Middleware   |  | WebSocket |        |
|  | (agents,    |  | (in-mem  |  | (rate limit, |  | Manager   |        |
|  |  circles,   |  |  users,  |  |  CORS, sec   |  | (event    |        |
|  |  pipelines  |  |  in-mem  |  |  headers,    |  |  bridge)  |        |
|  |  scheduled  |  |  token   |  |  logging)    |  |           |        |
|  |  actions..) |  |  blackl) |  |              |  |           |        |
|  +------+------+  +----+-----+  +------+------+  +-----+-----+        |
|         |              |               |                |              |
+---------+--------------+---------------+----------------+--------------+
          |              |               |                |
+---------v--------------v---------------v----------------v--------------+
|                    Orchestration Layer                                  |
|  +----------------+  +------------+  +------------+  +-------------+   |
|  | GatheringCircle|  | Facilitator|  | Background |  | Scheduler   |   |
|  | (multi-agent   |  | (task      |  | Executor   |  | (cron, int, |   |
|  |  coordination) |  |  routing)  |  | (async     |  |  once, evt) |   |
|  +-------+--------+  +-----+------+  |  tasks)    |  +------+------+   |
|          |                  |         +------+-----+         |         |
|          +------------------+-----------+----+---------------+         |
|                             |                                          |
|  +--------------------------v--------------------------------------+   |
|  |              EventBus (pub/sub, in-memory singleton)            |   |
|  |   events: agent.*, task.*, circle.*, memory.*, conversation.*   |   |
|  +---+-----+-----+-----+-----+-----+-----+-----+-----+-----------+   |
+------+-----+-----+-----+-----+-----+-----+-----+-----+---------------+
       |     |     |     |     |     |     |     |
+------v-----v-----v-----v-----v-----v-----v-----v-----v----------------+
|                        Agent Layer                                     |
|  +-------------+  +---------------+  +-------------+  +--------+       |
|  | AgentWrapper|  | MemoryService |  | Persona     |  | Project|       |
|  | (chat, tool |  | (recall, add, |  | (identity,  |  | Context|       |
|  |  execution) |  |  scoped)      |  |  prompts)   |  |        |       |
|  +------+------+  +-------+-------+  +------+------+  +---+----+       |
|         |                 |                  |             |            |
+---------+-----------------+------------------+-------------+------------+
          |                 |                  |
+---------v-----------------v------------------v-------------------------+
|                     Skill System (18+ skills)                          |
|  +------+ +-----+ +------+ +------+ +------+ +-------+ +------+       |
|  | code | | git | |shell | |  db  | | http | |deploy | | RAG  | ...   |
|  +------+ +-----+ +------+ +------+ +------+ +-------+ +------+       |
+------------------------------------------------------------------------+
          |                 |
+---------v-----------------v--------------------------------------------+
|                    Data Layer                                           |
|  +--------------------+  +------------------+  +------------------+    |
|  | DatabaseService     |  | SQLAlchemy ORM   |  | pgvector         |    |
|  | (pycopg, sync)      |  | (8 schemas)      |  | (embeddings)     |    |
|  +----------+----------+  +--------+---------+  +--------+---------+    |
|             |                      |                     |             |
|  +----------v----------------------v---------------------v----------+  |
|  |                    PostgreSQL 16                                  |  |
|  |  Schemas: agent | circle | project | communication |             |  |
|  |           memory | review | audit | public                       |  |
|  +--------------------------------------------------------------+   |  |
+------------------------------------------------------------------------+
|                    LLM Providers                                       |
|  +----------+  +--------+  +----------+  +-------+  +--------+        |
|  | Anthropic|  | OpenAI |  | DeepSeek |  | Ollama|  | Mistral|        |
|  +----------+  +--------+  +----------+  +-------+  +--------+        |
+------------------------------------------------------------------------+
```

### Component Responsibilities

| Component | Responsibility | Current State |
|-----------|----------------|---------------|
| **FastAPI Routers (18+)** | HTTP endpoint handling, request validation, response serialization | Working; routes to DatabaseService directly |
| **Auth Module** | JWT create/decode, user auth, token blacklist | **STUBBED**: in-memory user store, in-memory blacklist |
| **Middleware Stack** | Auth enforcement, rate limiting, CORS, security headers, logging | Working; rate limiter is per-instance in-memory |
| **WebSocket Manager** | Real-time event broadcast to dashboard | Working; bridges EventBus to WebSocket clients |
| **GatheringCircle** | Multi-agent task routing, review workflow, conflict detection | Working for basic flows; no distributed coordination |
| **Facilitator** | Task-to-agent matching, competency scoring | Working |
| **Background Executor** | Long-running async task execution with checkpointing | Working; recovery on restart implemented |
| **Scheduler** | Cron/interval/event-triggered action dispatch | **STUBBED**: tracks schedules but execution only logs |
| **EventBus (events/)** | Singleton pub/sub, async handlers, event history | Working; no persistence, no batching |
| **EventBus (orchestration/)** | Circle-scoped event coordination | Working; separate implementation from events/ |
| **AgentWrapper** | LLM + persona + memory + tools composition | Working |
| **MemoryService** | Scoped memory with RAG semantic search | Working |
| **Skill System** | 18+ pluggable tool modules for agent capabilities | Working |
| **DatabaseService** | SQL query execution via pycopg | Working; **SYNC-ONLY** (blocks event loop) |
| **SQLAlchemy Models** | ORM definitions for 8 schemas | Defined; not fully used (raw SQL dominates) |
| **Pipeline Router** | Pipeline CRUD and execution | **STUBBED**: creates fake completion logs |

### Critical Architectural Finding: Two EventBus Implementations

The codebase has **two separate EventBus systems** that serve different purposes:

1. **`gathering/events/event_bus.py`** -- Singleton, simpler, used by WebSocket integration and general system events. Uses `EventType(str, Enum)`.
2. **`gathering/orchestration/events.py`** -- Instance-based, richer (correlation IDs, event filters), used by GatheringCircle and orchestration. Uses `EventType(Enum)` (not str-based).

These are **not interchangeable** -- different EventType enums, different Event dataclass shapes. The WebSocket bridge subscribes to the `events/` bus, while circle task coordination uses the `orchestration/` bus. Production-hardening must preserve this boundary or explicitly merge them.

## Component Boundaries and Communication Paths

### Internal Boundaries

| Boundary | Communication Pattern | State Shared | Production Fix Needed |
|----------|----------------------|-------------|----------------------|
| API Router <-> DatabaseService | Direct function call (sync) | SQL queries | Make async |
| API Router <-> Orchestration | Direct function call | Task/action objects | No change needed |
| Orchestration <-> EventBus | Pub/sub (async) | Event payloads | Add persistence |
| EventBus <-> WebSocket | Event subscription -> broadcast | Event data serialized to JSON | No change needed |
| AgentWrapper <-> LLM Provider | Direct async call | Messages, tool definitions | No change needed |
| AgentWrapper <-> Skills | Direct function call | Tool input/output | Add parameter validation |
| Auth Middleware <-> Auth Module | Direct function call | JWT tokens, user data | Move to DB persistence |
| Scheduler <-> Background Executor | Direct async call | Task objects | Implement actual execution |
| Pipeline Router <-> Agent System | **NOT CONNECTED** | Nothing flows | Build execution engine |

### External Integration Points

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| PostgreSQL | pycopg (sync), SQLAlchemy (ORM, not fully used) | Primary data store; sync driver is a bottleneck |
| LLM APIs (Anthropic, OpenAI, etc.) | httpx async client | Already async; rate limited |
| Redis (optional) | redis-py | Cache layer; not required for core function |
| Frontend (React) | REST + WebSocket | Contract must not break |

## Data Flow for Production-Hardening Targets

### Flow 1: Auth Persistence (Currently Broken)

```
Current (broken):
  Login request -> verify_admin_credentials() OR _users_store dict lookup
  Register -> _users_store[email] = user dict (IN MEMORY, LOST ON RESTART)
  Token blacklist -> _token_blacklist dict (IN MEMORY, LOST ON RESTART)

Target:
  Login request -> verify_admin_credentials() OR SELECT FROM auth.users WHERE email=...
  Register -> INSERT INTO auth.users (...) RETURNING *
  Token blacklist -> INSERT INTO auth.token_blacklist (token_hash, expires_at)
  Token check -> SELECT 1 FROM auth.token_blacklist WHERE token_hash=... AND expires_at > NOW()
```

**Dependency**: None. Auth is the foundation. Everything else authenticates through it.

### Flow 2: SQL Injection Elimination

```
Current (vulnerable):
  pipelines.py line 311: f"... WHERE status = '{status}' ..."
  schedules.py line 390: f"... WHERE agent_id = {agent_id} ..."

Target:
  All queries use %(param)s parameterization or SQLAlchemy ORM.
```

**Dependency**: None. Can be fixed independently in any file.

### Flow 3: Pipeline Execution (Currently Stubbed)

```
Current (stub):
  POST /pipelines/{id}/run
    -> Create pipeline_run record (status=running)
    -> Iterate nodes, create fake log entries
    -> Mark run completed (nothing actually executed)

Target:
  POST /pipelines/{id}/run
    -> Create pipeline_run record (status=running)
    -> Launch async task via BackgroundExecutor
    -> PipelineEngine traverses DAG:
       - trigger node: validate trigger data
       - agent node: AgentWrapper.chat() with task goal
       - condition node: evaluate condition against context
       - action node: execute action (notify, API call)
       - parallel node: fan-out concurrent branches
       - delay node: asyncio.sleep
    -> Each node: update logs, check for failure
    -> On failure: retry logic, circuit breaker, or fail pipeline
    -> On complete: mark run completed, emit events
```

**Dependencies**: Requires working auth (to authenticate agent calls), working agent system (AgentWrapper.chat()), working EventBus (to emit progress events).

### Flow 4: Schedule Execution (Currently Stubbed)

```
Current (stub):
  Scheduler._run_action() -> creates background task record
  -> emits SCHEDULED_ACTION_TRIGGERED event
  -> Never actually executes the agent goal

Target:
  Scheduler._run_action()
    -> Dispatch based on action_type:
       - "run_task": BackgroundExecutor.enqueue() with agent_id + goal
       - "execute_pipeline": POST /pipelines/{id}/run internally
       - "send_notification": notification skill execution
       - "call_api": HTTP skill execution
    -> Track execution via ScheduledActionRun
    -> Handle retries on failure
```

**Dependencies**: Requires working pipeline execution (for execute_pipeline action type), working background executor (already functional), working auth (agent must be valid).

### Flow 5: Sync-to-Async Database Migration

```
Current:
  FastAPI async handler -> db.execute(sql, params)  [BLOCKS EVENT LOOP]
  DatabaseService uses pycopg (synchronous wrapper)

Target:
  FastAPI async handler -> await db.execute_async(sql, params)
  OR: run_in_executor(None, db.execute, sql, params)  [interim fix]
  Long-term: asyncpg or psycopg3 async driver
```

**Dependencies**: This is a cross-cutting concern. Every router is affected. Should be done after core features work but before performance optimization. The interim fix (run_in_executor) is safe to apply incrementally.

## Recommended Build Order

The build order is determined by the **dependency DAG** between fixes. A fix cannot be safely built if its dependencies have not been addressed.

### Dependency Graph

```
Auth Persistence --------+
                         |
SQL Injection Fixes -----+---> Pipeline Execution ----> Schedule Execution
                         |           |
Security Fixes ----------+           |
(timing attacks,                     |
 path traversal,                     v
 LSP validation)         Distributed Coordination
                                     |
                                     v
Sync-to-Async DB ------> Performance Optimization
(run_in_executor)         (N+1 queries, event batching,
                           file cache, module splitting)

Tests: Accompany each fix (not a separate phase)
```

### Phase-by-Phase Build Order

**Phase 1: Auth Persistence + Security Hardening**

Why first: Auth is the trust foundation. Every other feature authenticates through it. If auth loses state on restart, no feature depending on user identity works reliably. SQL injection fixes go here because they prevent data corruption that would invalidate all subsequent work.

- Replace `_users_store` dict with database queries (auth.users table)
- Persist token blacklist to database (auth.token_blacklist table)
- Parameterize all SQL queries (eliminate f-string SQL)
- Apply timing-safe comparison to all auth code paths
- Fix path traversal edge cases in workspace file serving
- Add LSP input validation (path sanitization, content size limits)
- Replace bare exception catches in critical paths
- Add audit logging for auth events
- Tests: token lifecycle, user persistence, SQL injection regression, timing attack resistance

**Phase 2: Pipeline Execution Engine**

Why second: Pipelines are the primary workflow feature. They depend on working auth (agents must be authenticated) and secure data layer (from Phase 1). Schedule execution depends on pipeline execution.

- Build PipelineEngine class that traverses node DAG
- Implement node type handlers (trigger, agent, condition, action, parallel, delay)
- Integrate with BackgroundExecutor for async execution
- Add pipeline validation (cycle detection, required fields, node type checking)
- Implement error recovery (per-node retry, circuit breaker, failure handler nodes)
- Emit events via EventBus for pipeline progress
- Tests: DAG traversal, node execution, error propagation, task routing

**Phase 3: Schedule Execution + Tool Registry Fixes**

Why third: Schedules dispatch to pipeline execution and background tasks, both of which must work first. Tool registry fixes ensure agents actually validate inputs before executing skills.

- Implement action type dispatcher in Scheduler._run_action()
- Handle retry logic with exponential backoff
- Persist scheduler running state to database (survive restarts)
- Add distributed locking for concurrent execution prevention
- Implement tool registry parameter validation against JSON schema
- Add async function support in tool registry
- Fix workspace API project path resolution
- Tests: schedule execution, retry behavior, tool validation, concurrent scheduling

**Phase 4: Performance + Async Database**

Why fourth: Performance fixes don't change behavior -- they make existing correct behavior faster. Doing this before correctness is fixed wastes effort on code that will change.

- Wrap synchronous DB calls with run_in_executor (immediate fix)
- Eliminate N+1 queries in circle member retrieval (JOIN optimization)
- Implement event bus batching and deduplication
- Fix file tree cache invalidation (git status consistency)
- Split dependencies.py (1694 lines) into domain modules
- Tests: async behavior verification, query count assertions, cache consistency

**Phase 5: Distributed Coordination**

Why last: Distributed coordination only matters for multi-instance deployment. Single-instance must work correctly first (Phases 1-4). Distributed bugs on top of local bugs are impossible to debug.

- Implement distributed lock for task assignment (PostgreSQL advisory locks)
- Add cross-instance scheduler coordination
- Implement event bus persistence for crash recovery (optional event store)
- Add cross-instance token blacklist verification
- Tests: multi-instance simulation, lock contention, split-brain scenarios

## Architectural Patterns for Fixes

### Pattern 1: Repository Pattern for Auth Persistence

**What:** Extract data access behind a repository interface, swap in-memory for database.
**When:** Replacing `_users_store` and `_token_blacklist` in auth.py.
**Trade-offs:** Adds indirection but enables testing with in-memory store while running database in production.

```python
class UserRepository:
    """Abstract user data access."""

    async def get_by_email(self, email: str) -> Optional[dict]:
        raise NotImplementedError

    async def get_by_id(self, user_id: str) -> Optional[dict]:
        raise NotImplementedError

    async def create(self, user_data: UserCreate) -> dict:
        raise NotImplementedError


class DatabaseUserRepository(UserRepository):
    """PostgreSQL implementation."""

    def __init__(self, db: DatabaseService):
        self._db = db

    async def get_by_email(self, email: str) -> Optional[dict]:
        return self._db.execute_one(
            "SELECT * FROM auth.users WHERE email = %(email)s",
            {"email": email.lower()}
        )
```

### Pattern 2: Strategy Pattern for Pipeline Node Execution

**What:** Each node type has a handler strategy. PipelineEngine dispatches to the correct handler.
**When:** Building pipeline execution engine (Phase 2).
**Trade-offs:** More classes but each handler is testable in isolation.

```python
class NodeHandler(ABC):
    @abstractmethod
    async def execute(self, node: PipelineNode, context: PipelineContext) -> NodeResult:
        pass

class AgentNodeHandler(NodeHandler):
    async def execute(self, node: PipelineNode, context: PipelineContext) -> NodeResult:
        agent = await AgentWrapper.from_db(node.config.agent_id, self.db)
        result = await agent.chat(node.config.task, context=context.data)
        return NodeResult(success=True, output=result)

class PipelineEngine:
    _handlers: Dict[str, NodeHandler] = {
        "trigger": TriggerNodeHandler(),
        "agent": AgentNodeHandler(),
        "condition": ConditionNodeHandler(),
        "action": ActionNodeHandler(),
    }

    async def execute(self, pipeline: Pipeline, trigger_data: dict) -> PipelineRun:
        # Topological sort of DAG, then execute in order
        ...
```

### Pattern 3: Async Wrapper for Sync Database (Interim)

**What:** Wrap synchronous database calls in `run_in_executor` to unblock the event loop.
**When:** Phase 4, as a bridge before full async driver migration.
**Trade-offs:** Thread pool overhead but immediate unblocking; not a permanent solution.

```python
import asyncio
from functools import partial

class AsyncDatabaseService:
    """Async wrapper around synchronous DatabaseService."""

    def __init__(self, sync_db: DatabaseService):
        self._sync = sync_db

    async def execute(self, sql: str, params: Optional[dict] = None) -> List[dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, partial(self._sync.execute, sql, params)
        )
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Big-Bang Async Migration

**What people do:** Convert all database calls to async in one massive PR.
**Why it's wrong:** Breaks everything at once; impossible to bisect regressions; merge conflicts with concurrent work.
**Do this instead:** Phase the migration. First wrap sync calls in `run_in_executor` (works immediately, no API change). Then migrate hot paths to async driver. Test at each step.

### Anti-Pattern 2: Merging the Two EventBus Implementations

**What people do:** "Simplify" by combining `events/event_bus.py` and `orchestration/events.py` into one system.
**Why it's wrong:** They serve different scopes. The events/ bus is a system-wide singleton for WebSocket broadcasting. The orchestration/ bus is per-circle with correlation tracking. Merging conflates lifecycle management and creates coupling between unrelated subscribers.
**Do this instead:** Keep them separate. If inter-bus communication is needed, create an explicit bridge (like the existing WebSocket integration pattern).

### Anti-Pattern 3: Adding Distributed Coordination Before Local Correctness

**What people do:** Add Redis locks and distributed state before verifying single-instance behavior works.
**Why it's wrong:** Distributed bugs are orders of magnitude harder to debug. If local execution is broken, distributed coordination just distributes the bugs.
**Do this instead:** Phase 1-4 first (local correctness). Phase 5 adds distributed coordination only after single-instance passes all tests.

### Anti-Pattern 4: Testing Persistence After All Fixes

**What people do:** Defer test writing to a "testing phase" at the end.
**Why it's wrong:** You lose the ability to verify each fix independently. Bugs compound. Integration failures are blamed on the wrong phase.
**Do this instead:** Every fix ships with its tests. Auth persistence tests prove users survive restart. Pipeline tests prove nodes execute. Schedule tests prove actions dispatch.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1 instance, <100 agents | Current architecture works once stubs are replaced. No distributed coordination needed. In-memory rate limiter is sufficient. |
| 2-5 instances, 100-1000 agents | Need persistent token blacklist (database). Need distributed scheduler locks (PostgreSQL advisory locks). Need shared rate limiting (Redis or DB). EventBus stays in-memory per instance but events of interest persisted to DB. |
| 5+ instances, 1000+ agents | Need external message broker (Redis Pub/Sub or RabbitMQ) for cross-instance EventBus. Need connection pooler (PgBouncer). Need pipeline execution queue. Consider read replicas for query load. |

### Scaling Priorities

1. **First bottleneck (now):** Synchronous database calls block the event loop. Fix: `run_in_executor` wrapper (Phase 4).
2. **Second bottleneck (~10 concurrent users):** N+1 queries in circle member retrieval. Fix: JOIN optimization (Phase 4).
3. **Third bottleneck (~5 instances):** In-memory token blacklist not shared. Fix: Database persistence (Phase 1).
4. **Fourth bottleneck (~50 concurrent pipelines):** Event bus task saturation. Fix: Batching and deduplication (Phase 4).

## Build Order Implications for Roadmap

The architecture analysis reveals a clear **dependency chain** that dictates phase ordering:

1. **Auth + Security MUST come first** because every feature depends on authentication state. A pipeline that authenticates against an in-memory user store will break on restart. SQL injection in any query path corrupts data that all subsequent phases depend on.

2. **Pipeline execution MUST come before schedule execution** because `execute_pipeline` is a schedule action type. The scheduler dispatches to the pipeline engine. Building the scheduler's dispatch logic before the pipeline engine exists means the scheduler has nothing to dispatch to.

3. **Performance MUST come after correctness** because async migration changes calling conventions. If you wrap a buggy sync call in `run_in_executor`, you still have a bug -- now it's just harder to debug because it runs on a thread pool.

4. **Distributed coordination MUST come last** because it multiplies the complexity of every component. Adding distributed locks to a scheduler that doesn't execute actions is premature complexity.

5. **Tests accompany each phase** (not a separate phase) because deferred testing makes later phases unable to verify they haven't broken earlier fixes.

## Sources

- Direct codebase analysis of all files referenced above (HIGH confidence -- primary source)
- `gathering/api/auth.py` lines 342-387: in-memory user store confirmed
- `gathering/api/auth.py` lines 177-269: in-memory token blacklist confirmed
- `gathering/api/routers/pipelines.py` line 413: "TODO: Actually execute the pipeline nodes" confirmed
- `gathering/orchestration/scheduler.py`: execution dispatch implemented but action execution is stub
- `gathering/api/dependencies.py`: synchronous DatabaseService confirmed
- `gathering/events/event_bus.py` vs `gathering/orchestration/events.py`: dual EventBus confirmed
- `.planning/codebase/CONCERNS.md`: full concern audit referenced for completeness
- `.planning/codebase/ARCHITECTURE.md`: existing architecture analysis referenced

---
*Architecture research for: GatheRing production-readiness consolidation*
*Researched: 2026-02-10*
