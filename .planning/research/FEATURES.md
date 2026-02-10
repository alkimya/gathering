# Feature Research: Production-Readiness for Multi-Agent AI Framework

**Domain:** Production consolidation of Python/FastAPI multi-agent AI framework
**Researched:** 2026-02-10
**Confidence:** HIGH (codebase analysis) / MEDIUM (industry patterns from training data -- WebSearch/WebFetch unavailable)

**Note on sources:** WebSearch and WebFetch were unavailable during this research. Findings are based on direct codebase analysis (HIGH confidence) cross-referenced with well-established production engineering patterns (MEDIUM confidence -- these patterns are stable/mature, not subject to rapid change, but could not be verified against current docs).

---

## Feature Landscape

### Table Stakes (Must Have for Production Deployment)

Features that are non-negotiable for production. Missing any of these means the system cannot be safely deployed.

#### TS-1: Persistent User Authentication

| Attribute | Detail |
|-----------|--------|
| **Feature** | Database-backed user storage replacing in-memory `_users_store` |
| **Why Expected** | Users are lost on every server restart. Registration is functionally useless. Multi-instance deployments share no user state. |
| **Complexity** | LOW |
| **Current State** | `gathering/api/auth.py` lines 342-387: `_users_store: dict[str, dict] = {}` -- pure in-memory dict with TODO comments |
| **Implementation Notes** | Create `users` table in PostgreSQL. Replace `get_user_by_email`, `get_user_by_id`, `create_user` with `DatabaseService` queries. Add unique constraint on email. Migrate `UserCreate`/`UserResponse` to proper ORM models. |
| **Priority** | P1 -- blocks all authenticated usage across restarts |

#### TS-2: Persistent Token Blacklist

| Attribute | Detail |
|-----------|--------|
| **Feature** | Database or Redis-backed token revocation list replacing in-memory `_token_blacklist` |
| **Why Expected** | Logout tokens are restored on server restart, meaning "revoked" tokens become valid again. Security violation. |
| **Complexity** | LOW |
| **Current State** | `gathering/api/auth.py` lines 177-269: `_token_blacklist: dict[str, float] = {}` with SHA-256 truncated hashes |
| **Implementation Notes** | Option A: PostgreSQL table `token_blacklist(token_hash, expires_at)` with index on `token_hash`. Option B: Redis SET with TTL matching token expiry (preferred if Redis available, since it auto-expires). Keep in-memory as L1 cache with DB/Redis as source of truth. |
| **Priority** | P1 -- security vulnerability: revoked tokens work after restart |

#### TS-3: SQL Injection Elimination

| Attribute | Detail |
|-----------|--------|
| **Feature** | All SQL queries use parameterized statements; no f-string SQL construction |
| **Why Expected** | SQL injection is OWASP Top 10 #3. Any production security audit will flag this immediately. |
| **Complexity** | MEDIUM |
| **Current State** | `gathering/api/routers/pipelines.py` line 311: `f"UPDATE circle.pipelines SET {', '.join(updates)} WHERE id = %(id)s RETURNING *"` -- column names from user input interpolated. `gathering/skills/gathering/schedules.py` line 390: similar f-string SQL. Also `gathering/db/database.py` lines 264-275 and 303-310: f-string with schema names in health_check/get_stats. |
| **Implementation Notes** | Audit every `.py` file for f-string SQL. The pipelines UPDATE is the most dangerous -- the column names in `updates` list come from `PipelineUpdate` model field names (not raw user input), but the pattern is still unsafe. Replace with SQLAlchemy ORM operations or pre-validated column allowlists. The database.py health check f-strings use the hardcoded `self.SCHEMA` constant, which is lower risk but should still use parameterized queries. |
| **Priority** | P1 -- active security vulnerability |

#### TS-4: Pipeline Execution Engine

| Attribute | Detail |
|-----------|--------|
| **Feature** | Pipeline nodes actually execute (agent tasks, conditions, actions) instead of faking completion |
| **Why Expected** | The pipeline feature is a core product capability. Currently it lies -- it reports "completed" with fake logs for every node without executing anything. |
| **Complexity** | HIGH |
| **Current State** | `gathering/api/routers/pipelines.py` lines 413-446: TODO comment at line 413 says "Actually execute the pipeline nodes (async task)". Code loops through nodes, creates fake log entries like "Executed node: {name}", marks run as completed. Nothing runs. |
| **Implementation Notes** | Build a `PipelineExecutor` service that: (1) validates DAG structure, (2) topologically sorts nodes, (3) dispatches to appropriate handlers by node type (trigger, agent, condition, action, parallel, delay), (4) propagates results between nodes, (5) handles failures with configurable retry. Use background task execution (existing `BackgroundExecutor`). |
| **Priority** | P1 -- core feature is non-functional |

#### TS-5: Schedule Action Execution

| Attribute | Detail |
|-----------|--------|
| **Feature** | Scheduled actions dispatch real work (run tasks, call APIs, trigger pipelines) instead of only logging |
| **Why Expected** | The scheduling feature is useless if it only logs "would run action" without doing anything. |
| **Complexity** | MEDIUM |
| **Current State** | `gathering/skills/gathering/schedules.py` line 477: TODO comment. Scheduler framework (`gathering/orchestration/scheduler.py`) exists with action tracking, but `run_now` only creates log entries. |
| **Implementation Notes** | Implement action dispatcher that maps `action_type` to handlers: `run_task` -> create background task for agent, `execute_pipeline` -> trigger pipeline run, `send_notification` -> call notification service, `call_api` -> HTTP request. Wire into existing scheduler's `_execute_action` method. |
| **Priority** | P1 -- core feature is non-functional |

#### TS-6: Async Database Access

| Attribute | Detail |
|-----------|--------|
| **Feature** | Async database operations in async FastAPI handlers (eliminate sync-in-async blocking) |
| **Why Expected** | Calling synchronous `db.execute()` inside `async def` route handlers blocks the event loop, destroying concurrent request handling. Under load, the API becomes single-threaded. |
| **Complexity** | HIGH |
| **Current State** | `gathering/db/database.py` uses synchronous SQLAlchemy engine. `DatabaseService` in `gathering/api/dependencies.py` wraps it synchronously. All routers (`pipelines.py`, `scheduled_actions.py`, etc.) are `async def` but call sync DB. The project already has `asyncpg` in requirements. |
| **Implementation Notes** | Two approaches: (A) Use `run_in_executor` to wrap sync calls (quick fix, lower performance gain), or (B) Create async SQLAlchemy engine with `create_async_engine` + `AsyncSession` (proper fix). Given `asyncpg` is already a dependency, approach B is correct. Create `AsyncDatabase` class alongside existing `Database`. Migrate routers incrementally. |
| **Priority** | P1 -- blocks production performance under any concurrent load |

#### TS-7: Audit Logging for Authentication Events

| Attribute | Detail |
|-----------|--------|
| **Feature** | Log all auth events: login attempts (success/failure), registration, token generation, logout, privilege escalation |
| **Why Expected** | Required for security compliance. Without audit logs, there is no way to investigate breaches, detect brute force attacks, or maintain accountability. |
| **Complexity** | LOW |
| **Current State** | Auth router has no logging at all. Login failures return 401 with no record. No way to detect credential stuffing or compromised accounts. |
| **Implementation Notes** | Add structured log entries at each auth endpoint. Use existing `structlog` dependency. Log: timestamp, email (not password), IP address, user-agent, success/failure, failure reason. Store in dedicated `auth_audit_log` table for queryability. Emit events on EventBus for real-time alerting. |
| **Priority** | P1 -- security compliance requirement |

#### TS-8: Path Traversal Fix

| Attribute | Detail |
|-----------|--------|
| **Feature** | File serving endpoints validate paths cannot escape workspace root |
| **Why Expected** | Path traversal allows reading arbitrary server files (e.g., `/etc/passwd`, `.env`). Critical security vulnerability. |
| **Complexity** | LOW |
| **Current State** | `gathering/api/routers/workspace.py` lines 175-188: Nested try-except obscures error handling. Path validation exists but is fragile. |
| **Implementation Notes** | Use `pathlib.Path.resolve()` and verify the resolved path starts with the allowed workspace root. Reject symbolic links that escape the root. Deny encoded path separators (`%2F`, `%5C`). Add integration tests with malicious paths. |
| **Priority** | P1 -- active security vulnerability |

#### TS-9: N+1 Query Elimination

| Attribute | Detail |
|-----------|--------|
| **Feature** | Circle member retrieval uses JOINs instead of per-member queries |
| **Why Expected** | N+1 queries cause exponential slowdown. A circle with 10 agents makes 30+ queries instead of 1. Unacceptable for production response times. |
| **Complexity** | MEDIUM |
| **Current State** | `gathering/api/dependencies.py` lines 310-320: Each circle member triggers separate agent, model, and provider queries. |
| **Implementation Notes** | Replace with single JOIN query: `SELECT m.*, a.name, a.model, p.name FROM circle_members m JOIN agents a ON ... JOIN providers p ON ...`. Use SQLAlchemy `joinedload` or `selectinload` for ORM approach. |
| **Priority** | P1 -- blocks acceptable response times |

#### TS-10: Comprehensive Error Handling

| Attribute | Detail |
|-----------|--------|
| **Feature** | Replace bare `except Exception` with specific error types and proper error context |
| **Why Expected** | 90+ bare exception handlers hide bugs, swallow context, make debugging impossible. Production systems need clear error propagation. |
| **Complexity** | MEDIUM |
| **Current State** | Codebase-wide issue. Many handlers catch `Exception` and either re-raise as generic HTTP 500 or silently continue. `scheduled_actions.py` exposes raw exception messages to clients via `detail=str(e)`. |
| **Implementation Notes** | Audit all exception handlers. Categorize: (1) expected errors -> specific exceptions with user-safe messages, (2) unexpected errors -> log full traceback, return generic 500. Create custom exception hierarchy: `GatheringError`, `AuthError`, `PipelineError`, `ScheduleError`, `DatabaseError`. Never expose internal error messages to clients. |
| **Priority** | P1 -- blocks debugging and leaks implementation details |

#### TS-11: Timing-Safe Auth Comparison

| Attribute | Detail |
|-----------|--------|
| **Feature** | All authentication comparisons use constant-time operations |
| **Why Expected** | Timing attacks can extract password hashes character by character. Standard security requirement. |
| **Complexity** | LOW |
| **Current State** | `gathering/api/auth.py` lines 296-334: `verify_admin_credentials` correctly uses `secrets.compare_digest` for email and `passlib.verify` for password. But `authenticate_user` (line 472) calls `verify_password` which uses passlib (timing-safe), and email lookup is a dict lookup (not timing-safe -- reveals whether email exists based on response time). |
| **Implementation Notes** | Ensure `authenticate_user` always performs password verification even when user not found (already done for admin path, not for DB user path at line 492-496). Add dummy verification when user doesn't exist in DB lookup. Verify all auth paths have consistent timing. |
| **Priority** | P1 -- security vulnerability |

#### TS-12: Database Persistence Tests

| Attribute | Detail |
|-----------|--------|
| **Feature** | Integration tests proving data survives server restart: users, conversations, tasks, pipelines |
| **Why Expected** | Without these tests, there's no proof that persistence actually works. Deploying to production with untested persistence is reckless. |
| **Complexity** | MEDIUM |
| **Current State** | 1071 tests exist, but CONCERNS.md identifies no tests for: user creation persistence, conversation history, task tracking, pipeline execution flow. Tests mock the database layer. |
| **Implementation Notes** | Add integration test suite using a real test database (PostgreSQL in CI). Test: create user -> restart -> verify user exists. Create pipeline run -> verify persisted. Create scheduled action -> verify runs table populated. Use pytest fixtures for database setup/teardown. |
| **Priority** | P1 -- cannot verify production correctness without these |

#### TS-13: Auth Token Lifecycle Tests

| Attribute | Detail |
|-----------|--------|
| **Feature** | Tests for token expiry, blacklist cleanup, concurrent token use, refresh flow |
| **Why Expected** | Auth is the security perimeter. Untested auth = unknown security posture. |
| **Complexity** | LOW |
| **Current State** | No tests for: token expiry edge cases, blacklist cleanup timing, what happens with expired blacklist entries, timing attack resistance. |
| **Implementation Notes** | Test: expired token rejected, blacklisted token rejected, blacklist entry cleaned after token expiry, near-expiry tokens handled correctly, concurrent blacklist operations safe. Use `freezegun` or `time_machine` to manipulate time in tests. |
| **Priority** | P1 -- security cannot be verified without these |

#### TS-14: Pipeline Execution Tests

| Attribute | Detail |
|-----------|--------|
| **Feature** | Tests for pipeline node traversal, error propagation, task routing, DAG validation |
| **Why Expected** | Pipeline execution is being built (TS-4). It needs tests to prove correctness. |
| **Complexity** | MEDIUM |
| **Current State** | No tests exist for pipeline execution because execution itself is stubbed. Tests will be built alongside the implementation. |
| **Implementation Notes** | Test: linear pipeline executes nodes in order, parallel nodes execute concurrently, condition nodes route correctly, failed node triggers error handling, invalid DAG rejected, pipeline cancellation stops execution. |
| **Priority** | P1 -- required alongside TS-4 implementation |

#### TS-15: Tool Registry Parameter Validation

| Attribute | Detail |
|-----------|--------|
| **Feature** | Tool execution validates input parameters against declared JSON schema before running |
| **Why Expected** | Without validation, tools receive garbage input and fail with cryptic errors deep in execution. Defense in depth. |
| **Complexity** | LOW |
| **Current State** | `gathering/core/tool_registry.py` lines 354-355: TODO comments noting validation is skipped. |
| **Implementation Notes** | Use `jsonschema` library (or Pydantic model validation) to validate kwargs against `tool.parameters` schema. Raise `ValueError` with clear message listing which parameters failed. Add async function support check at same time (tool.async_function flag). |
| **Priority** | P1 -- tools are a core capability; invalid input causes runtime failures |

#### TS-16: Rate Limiting Hardening

| Attribute | Detail |
|-----------|--------|
| **Feature** | Production-grade rate limiting with per-endpoint configuration and auth endpoint protection |
| **Why Expected** | The existing `RateLimitMiddleware` is in-memory only, uses a single global limit, and grows unbounded (no cleanup of old IPs). Auth endpoints need stricter limits to prevent brute force. |
| **Complexity** | MEDIUM |
| **Current State** | `gathering/api/middleware.py` lines 130-205: In-memory rate limiter exists with sliding window. No per-endpoint differentiation. `self.requests` dict grows unbounded (no IP cleanup). Auth endpoints get same limit as regular endpoints. |
| **Implementation Notes** | Add IP cleanup (evict entries not seen for 10 minutes). Add per-endpoint tiers: auth endpoints (10/min), write endpoints (30/min), read endpoints (120/min). For multi-instance: use Redis-backed rate limiting (INCR + EXPIRE pattern). Add `X-Forwarded-For` validation to prevent header spoofing. |
| **Priority** | P1 -- existing rate limiter has memory leak and insufficient auth protection |

---

### Differentiators (Competitive Advantage for Production Quality)

Features that go beyond "doesn't crash" into "runs well in production." Not strictly required for deployment but significantly reduce operational burden and risk.

#### D-1: Distributed Task Coordination

| Attribute | Detail |
|-----------|--------|
| **Feature** | Multi-instance task locking so parallel deployments don't execute the same scheduled action twice |
| **Value Proposition** | Enables horizontal scaling. Without this, running 2+ instances means duplicate task execution, data corruption, wasted LLM API costs. |
| **Complexity** | HIGH |
| **Current State** | `gathering/orchestration/scheduler.py` lines 218-241: `_running_actions` tracked in-memory dict. No cross-instance awareness. |
| **Implementation Notes** | Use PostgreSQL advisory locks (`pg_try_advisory_lock`) or Redis distributed locks (SETNX + TTL). Advisory locks are preferred since PostgreSQL is already required. Create a `task_locks` table or use advisory lock IDs derived from action IDs. Add lease renewal for long-running tasks. |

#### D-2: Pipeline Error Recovery

| Attribute | Detail |
|-----------|--------|
| **Feature** | Retry logic, circuit breakers, dead letter queues for failed pipeline nodes |
| **Value Proposition** | LLM API calls fail regularly (rate limits, timeouts, transient errors). Without retry, every transient failure kills the entire pipeline. |
| **Complexity** | MEDIUM |
| **Current State** | Pipeline execution is stubbed (TS-4). No error handling infrastructure exists. |
| **Implementation Notes** | Use `tenacity` library (already in requirements) for retry logic. Implement per-node retry config: max_retries, backoff strategy, timeout. Add circuit breaker pattern for external services (LLM providers). Store failed node state for manual retry/resume. |

#### D-3: Event Bus Batching and Deduplication

| Attribute | Detail |
|-----------|--------|
| **Feature** | High-frequency events batched and deduplicated to prevent task saturation |
| **Value Proposition** | Under active agent workloads, the event bus creates unbounded async tasks. Batching reduces overhead by 10-50x for burst events. |
| **Complexity** | MEDIUM |
| **Current State** | `gathering/orchestration/circle.py` lines 256-260: `create_task()` for every emit. No batching. No deduplication. |
| **Implementation Notes** | Implement event queue with configurable flush interval (e.g., 100ms). Deduplicate events by type+key within flush window. Use asyncio.Queue for buffering. Add backpressure handling when queue is full. |

#### D-4: Structured Logging with Request Correlation

| Attribute | Detail |
|-----------|--------|
| **Feature** | JSON structured logs with request IDs propagated through all layers including background tasks |
| **Value Proposition** | Enables log aggregation (ELK, Datadog). Makes production debugging possible. Correlates auth events with API calls with background task execution. |
| **Complexity** | LOW |
| **Current State** | `structlog` is a dependency but logging uses stdlib `logging` throughout. Request logging middleware generates request IDs but doesn't propagate to service layer. Background tasks have no correlation IDs. |
| **Implementation Notes** | Configure structlog as the logging backend with JSON output. Use contextvars for request ID propagation. Pass correlation IDs to background tasks and pipeline execution. Add trace IDs from OpenTelemetry when available. |

#### D-5: Graceful Shutdown with In-Flight Request Draining

| Attribute | Detail |
|-----------|--------|
| **Feature** | Server shutdown waits for in-flight requests and background tasks to complete |
| **Value Proposition** | Prevents data corruption during deployments. Zero-downtime deploys require draining. |
| **Complexity** | LOW |
| **Current State** | `gathering/api/main.py` lifespan handler stops scheduler (10s timeout) and background executor (30s timeout). But no HTTP request draining. Uvicorn's default graceful shutdown is 0 seconds. |
| **Implementation Notes** | Configure uvicorn `--timeout-graceful-shutdown 30`. Add signal handlers (SIGTERM) that set a "shutting down" flag. Health endpoint returns 503 when shutting down (load balancer stops routing). Existing scheduler/executor shutdown logic is adequate. |

#### D-6: Cache Bounds and Eviction

| Attribute | Detail |
|-----------|--------|
| **Feature** | Bounded caches with LRU eviction and size limits |
| **Value Proposition** | Prevents unbounded memory growth. Current in-memory caches (token blacklist, rate limiter IP tracking, event bus) grow without limit. |
| **Complexity** | LOW |
| **Current State** | `_token_blacklist` grows until cleanup (hourly). `RateLimitMiddleware.requests` dict never evicts old IPs. `lru_cache()` on `get_db_cached` has no maxsize. |
| **Implementation Notes** | Add `maxsize` to all `lru_cache` decorators. Implement periodic cleanup for rate limiter IP entries (every 5 minutes, evict IPs not seen in 10 minutes). Token blacklist cleanup is already periodic but needs size cap (reject blacklist additions if > 100K entries, rely on short token TTL). |

#### D-7: Event Bus Concurrency Testing

| Attribute | Detail |
|-----------|--------|
| **Feature** | Tests proving event handlers work correctly under concurrent load |
| **Value Proposition** | Without these tests, race conditions in task assignment, circle membership, and event ordering are undetectable. |
| **Complexity** | MEDIUM |
| **Current State** | No concurrency tests for event bus. CONCERNS.md flags "Task state corruption under concurrent activity; deadlocks possible." |
| **Implementation Notes** | Use `asyncio.gather` to fire concurrent events. Test: parallel task assignments don't double-assign, event ordering preserved within topics, handler exceptions don't break other handlers. Use `pytest-asyncio` with explicit concurrency. |

#### D-8: Scheduler Recovery Testing

| Attribute | Detail |
|-----------|--------|
| **Feature** | Tests proving missed scheduled runs are detected and recovered after crash/restart |
| **Value Proposition** | Without recovery testing, the scheduler silently drops actions when the server restarts. Users don't know their scheduled tasks stopped running. |
| **Complexity** | MEDIUM |
| **Current State** | `gathering/api/main.py` lifespan handler calls `executor.recover_tasks()` for background tasks, but scheduled actions recovery is untested. |
| **Implementation Notes** | Test: create scheduled action with next_run in the past, start scheduler, verify catch-up execution fires. Test: action in "running" state on startup gets reset to "pending". Test: maxed-out execution count actions are properly completed, not retried. |

#### D-9: Workspace Path Resolution

| Attribute | Detail |
|-----------|--------|
| **Feature** | Workspace API resolves project-specific paths instead of using hardcoded `os.getcwd()` |
| **Value Proposition** | Multi-project support is broken without this. All agents access the same directory regardless of which project they belong to. |
| **Complexity** | LOW |
| **Current State** | `gathering/api/routers/workspace.py` lines 44-48: TODO comment. Returns cwd for all projects. |
| **Implementation Notes** | Query projects table for path. Validate path exists. Add per-project path isolation. This is also security-relevant (TS-8) since incorrect path resolution could enable cross-project access. |

#### D-10: Async Tool Execution

| Attribute | Detail |
|-----------|--------|
| **Feature** | Tool registry supports async tool functions alongside sync ones |
| **Value Proposition** | Many tools (HTTP calls, database queries, LLM calls) are naturally async. Forcing sync execution blocks the event loop. |
| **Complexity** | LOW |
| **Current State** | `gathering/core/tool_registry.py` line 355: TODO comment. `ToolDefinition` has `async_function` flag but `execute()` always calls synchronously. |
| **Implementation Notes** | In `execute()`, check `tool.async_function`. If true, `await` the function. If false, call directly (or use `run_in_executor` if in async context). Simple conditional in one method. |

---

### Anti-Features (Do NOT Build During Consolidation)

Features that seem valuable but would derail the consolidation effort or introduce complexity without proportional benefit.

#### AF-1: Custom Authentication Provider (OAuth2/OIDC)

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|--------------|---------------|-----------------|-------------|
| Full OAuth2/OIDC provider with social login (Google, GitHub) | "Production auth needs OAuth" | Massive scope increase. The current JWT auth is functionally sound -- the problem is persistence, not protocol. Adding OAuth2 flows, token exchanges, callback handling would be a multi-week project that doesn't fix any of the actual bugs. | Fix persistence (TS-1, TS-2), fix timing attacks (TS-11), add audit logging (TS-7). OAuth2 integration is a post-consolidation feature. |

#### AF-2: Kubernetes/Docker Infrastructure

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|--------------|---------------|-----------------|-------------|
| Helm charts, K8s manifests, Docker Compose production configs | "Need containerization for production" | Infrastructure is a separate concern from application correctness. The existing `PRODUCTION_READINESS.md` already has Docker/K8s templates. Building infrastructure before the application works correctly is putting the cart before the horse. | Fix application bugs first. Infrastructure configs already exist in docs. Container orchestration is a post-consolidation concern. |

#### AF-3: New Feature Development

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|--------------|---------------|-----------------|-------------|
| New skills, new LLM providers, new dashboard pages, plugin marketplace | "While we're in there, let's add..." | Scope creep is the primary risk to consolidation. Every new feature adds new untested code, new potential bugs, new integration points. The goal is to make existing features work, not add more broken ones. | Complete consolidation. Then add features on a solid foundation. |

#### AF-4: Full Database Migration to Async-Only

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|--------------|---------------|-----------------|-------------|
| Rip out all synchronous SQLAlchemy code and replace with async-only | "If we're fixing async, do it right" | The codebase has 1694 lines in dependencies.py alone, plus all routers. A wholesale migration is a rewrite that will break everything simultaneously. Incremental is safer. | Create `AsyncDatabase` alongside `Database`. Migrate hot paths (routers) first. Keep sync for CLI tools, migrations, background tasks that don't need async. |

#### AF-5: Distributed Event Bus (Kafka/RabbitMQ)

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|--------------|---------------|-----------------|-------------|
| Replace in-memory EventBus with Kafka or RabbitMQ | "Need distributed events for scaling" | Adds a major infrastructure dependency. The current event bus works for single-instance deployment. Distributed events are needed only when running multiple instances -- which requires distributed task coordination (D-1) first anyway. | Fix event bus batching (D-3). Use PostgreSQL LISTEN/NOTIFY for cross-instance events if needed. Kafka is a v2+ consideration. |

#### AF-6: Real-Time Collaboration / Multi-User Dashboard

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|--------------|---------------|-----------------|-------------|
| Multiple users editing pipelines simultaneously, shared cursors, conflict resolution | "Collaborative AI framework should be collaborative" | CRDT or OT algorithms for real-time collaboration are extremely complex. The dashboard currently works for single-user. Multi-user is a v2+ feature. | Support multiple user accounts (TS-1). Basic RBAC is sufficient for now. Real-time collaboration is post-consolidation. |

#### AF-7: Comprehensive Frontend Refactoring

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|--------------|---------------|-----------------|-------------|
| Rewrite React dashboard with new component library, state management, design system | "Dashboard looks outdated" | The dashboard works. It's not broken. Consolidation scope explicitly excludes frontend changes. Backend API contract compatibility means the dashboard continues working without changes. | Leave dashboard as-is. Focus on API correctness. Dashboard improvements are a separate project. |

---

## Feature Dependencies

```
[TS-1: Persistent Users]
    +--requires--> PostgreSQL users table
    +--enables---> [TS-7: Audit Logging] (needs user IDs to log against)
    +--enables---> [TS-12: Persistence Tests] (needs real users to test)

[TS-2: Persistent Token Blacklist]
    +--requires--> [TS-1: Persistent Users] (blacklist references user sessions)
    +--requires--> PostgreSQL table or Redis
    +--enables---> [TS-13: Auth Token Tests]

[TS-3: SQL Injection Fix]
    +--independent-- (can be done anytime, should be done first)

[TS-4: Pipeline Execution]
    +--requires--> [TS-6: Async DB] (pipeline runs async, needs async DB)
    +--requires--> [TS-15: Tool Validation] (pipeline nodes use tools)
    +--enables---> [TS-14: Pipeline Tests]
    +--enables---> [D-2: Pipeline Error Recovery]

[TS-5: Schedule Execution]
    +--requires--> [TS-4: Pipeline Execution] (execute_pipeline action type)
    +--benefits--> [D-1: Distributed Coordination] (prevent duplicate execution)

[TS-6: Async DB]
    +--independent-- (can start early, migrate incrementally)
    +--enables---> [TS-9: N+1 Fix] (better with async joins)

[TS-7: Audit Logging]
    +--requires--> [TS-1: Persistent Users] (log user IDs)
    +--requires--> [D-4: Structured Logging] (log format consistency)

[TS-8: Path Traversal Fix]
    +--independent-- (quick security fix)

[TS-9: N+1 Query Fix]
    +--independent-- (can be done with either sync or async DB)

[TS-10: Error Handling]
    +--independent-- (can be done incrementally across codebase)

[TS-11: Timing-Safe Auth]
    +--requires--> [TS-1: Persistent Users] (need DB user lookup path)

[D-1: Distributed Coordination]
    +--requires--> [TS-5: Schedule Execution] (coordinate what?)
    +--benefits--> [TS-4: Pipeline Execution] (prevent duplicate pipeline runs)

[D-4: Structured Logging]
    +--enhances--> [TS-7: Audit Logging]
    +--enhances--> [TS-10: Error Handling]
```

### Dependency Notes

- **TS-1 is the foundation**: Nearly everything depends on having real users in a real database. Do this first.
- **TS-3 (SQL injection) and TS-8 (path traversal) are independent security fixes**: They can be done immediately and in parallel with anything else. Quick wins that remove active vulnerabilities.
- **TS-4 (pipeline execution) is the largest single item**: It has the most dependencies and enables the most downstream work. It should be the centerpiece of the implementation phase.
- **TS-6 (async DB) is a cross-cutting concern**: It touches every router. Best done incrementally: create async database class first, migrate routers one at a time.
- **D-1 (distributed coordination) is a v1.x feature**: Not needed for single-instance production deployment. Required before scaling to multiple instances.

---

## MVP Definition

### Launch With (v1 -- Production-Deployable)

Minimum set for a single-instance production deployment that doesn't lose data, isn't exploitable, and actually runs its features.

- [x] **TS-1: Persistent Users** -- without this, registration is broken
- [x] **TS-2: Persistent Token Blacklist** -- without this, logout is broken
- [x] **TS-3: SQL Injection Fix** -- without this, database is exploitable
- [x] **TS-4: Pipeline Execution** -- without this, core feature is fake
- [x] **TS-5: Schedule Execution** -- without this, core feature is fake
- [x] **TS-6: Async DB Access** -- without this, performance is unusable under load
- [x] **TS-7: Audit Logging** -- without this, security events are invisible
- [x] **TS-8: Path Traversal Fix** -- without this, filesystem is exposed
- [x] **TS-9: N+1 Query Fix** -- without this, API is slow
- [x] **TS-10: Error Handling** -- without this, debugging is impossible and secrets leak
- [x] **TS-11: Timing-Safe Auth** -- without this, passwords are extractable
- [x] **TS-12: Persistence Tests** -- without this, there's no proof anything works
- [x] **TS-13: Auth Token Tests** -- without this, auth correctness is unverified
- [x] **TS-14: Pipeline Tests** -- without this, new pipeline code is untested
- [x] **TS-15: Tool Validation** -- without this, tools crash on bad input
- [x] **TS-16: Rate Limiting Hardening** -- without this, brute force is easy and memory leaks

### Add After Validation (v1.x -- Production-Hardened)

Features to add once core is deployed and running.

- [ ] **D-1: Distributed Coordination** -- trigger: need to scale to 2+ instances
- [ ] **D-2: Pipeline Error Recovery** -- trigger: pipeline failures in production
- [ ] **D-3: Event Bus Batching** -- trigger: performance issues under heavy agent workloads
- [ ] **D-4: Structured Logging** -- trigger: first production debugging session
- [ ] **D-5: Graceful Shutdown** -- trigger: first zero-downtime deployment
- [ ] **D-6: Cache Bounds** -- trigger: memory usage monitoring shows growth
- [ ] **D-7: Event Bus Concurrency Tests** -- trigger: unexplained duplicate tasks
- [ ] **D-8: Scheduler Recovery Tests** -- trigger: missed scheduled runs
- [ ] **D-9: Workspace Path Resolution** -- trigger: multi-project usage
- [ ] **D-10: Async Tool Execution** -- trigger: tool performance under load

### Future Consideration (v2+)

- [ ] OAuth2/OIDC integration -- after auth consolidation proves stable
- [ ] Kafka/RabbitMQ event bus -- after multi-instance deployment proven
- [ ] Real-time collaboration -- after multi-user support validated
- [ ] Plugin marketplace -- after plugin system stabilized
- [ ] API versioning -- after first external consumer integration

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority | Category |
|---------|------------|---------------------|----------|----------|
| TS-1: Persistent Users | HIGH | LOW | P1 | Security/Data |
| TS-2: Persistent Token Blacklist | HIGH | LOW | P1 | Security |
| TS-3: SQL Injection Fix | HIGH | MEDIUM | P1 | Security |
| TS-4: Pipeline Execution | HIGH | HIGH | P1 | Core Feature |
| TS-5: Schedule Execution | HIGH | MEDIUM | P1 | Core Feature |
| TS-6: Async DB | HIGH | HIGH | P1 | Performance |
| TS-7: Audit Logging | MEDIUM | LOW | P1 | Security |
| TS-8: Path Traversal Fix | HIGH | LOW | P1 | Security |
| TS-9: N+1 Query Fix | MEDIUM | MEDIUM | P1 | Performance |
| TS-10: Error Handling | MEDIUM | MEDIUM | P1 | Reliability |
| TS-11: Timing-Safe Auth | HIGH | LOW | P1 | Security |
| TS-12: Persistence Tests | HIGH | MEDIUM | P1 | Testing |
| TS-13: Auth Token Tests | HIGH | LOW | P1 | Testing |
| TS-14: Pipeline Tests | HIGH | MEDIUM | P1 | Testing |
| TS-15: Tool Validation | MEDIUM | LOW | P1 | Reliability |
| TS-16: Rate Limiting Hardening | MEDIUM | MEDIUM | P1 | Security |
| D-1: Distributed Coordination | MEDIUM | HIGH | P2 | Scalability |
| D-2: Pipeline Error Recovery | HIGH | MEDIUM | P2 | Reliability |
| D-3: Event Bus Batching | LOW | MEDIUM | P2 | Performance |
| D-4: Structured Logging | MEDIUM | LOW | P2 | Observability |
| D-5: Graceful Shutdown | MEDIUM | LOW | P2 | Operations |
| D-6: Cache Bounds | LOW | LOW | P2 | Performance |
| D-7: Event Concurrency Tests | MEDIUM | MEDIUM | P2 | Testing |
| D-8: Scheduler Recovery Tests | MEDIUM | MEDIUM | P2 | Testing |
| D-9: Workspace Path Resolution | LOW | LOW | P2 | Feature Fix |
| D-10: Async Tool Execution | LOW | LOW | P2 | Performance |

**Priority key:**
- P1: Must have for launch (all Table Stakes)
- P2: Should have, add when possible (all Differentiators)
- P3: Nice to have, future consideration (none in scope -- post-consolidation features)

---

## Competitor Feature Analysis

| Feature Area | LangGraph/LangChain | CrewAI | AutoGen | GatheRing Current | GatheRing Target |
|--------------|---------------------|--------|---------|-------------------|------------------|
| Auth/Users | External (bring your own) | None (library) | None (library) | In-memory (broken) | Persistent DB auth |
| Pipeline Execution | Graph-based, working | Sequential/hierarchical | Conversation-based | Stubbed (fake) | DAG-based, async |
| Scheduling | External (Celery/APScheduler) | None | None | Framework exists, no execution | Full cron/interval execution |
| Error Recovery | Built-in retry in graphs | Basic retry | Agent-level retry | None | Tenacity-based per-node retry |
| Observability | LangSmith integration | CrewAI observability | None | OpenTelemetry scaffolding | Full OTel + structured logging |
| Security | N/A (library, not service) | N/A | N/A | Multiple active vulnerabilities | Hardened (parameterized SQL, path validation, timing-safe) |
| Testing | Community tests | Moderate | Moderate | 1071 tests (gaps in critical paths) | Full coverage of critical paths |

**Key insight:** Most competitor frameworks are libraries, not deployed services. They push auth, security, and persistence concerns to the consumer. GatheRing is a deployed service with a REST API and dashboard, so it must handle these concerns itself. This makes the security and persistence fixes more critical -- there's no external auth gateway to fall back on.

---

## Sources

- Direct codebase analysis of `/home/loc/workspace/gathering/` (HIGH confidence)
- `.planning/codebase/CONCERNS.md` -- codebase audit from 2026-02-10 (HIGH confidence)
- `.planning/PROJECT.md` -- project requirements definition (HIGH confidence)
- `docs/archive/PRODUCTION_READINESS.md` -- existing production readiness documentation (HIGH confidence for infrastructure patterns)
- OWASP Top 10 security patterns (MEDIUM confidence -- training data, well-established stable practices)
- FastAPI production deployment patterns (MEDIUM confidence -- training data, well-documented stable patterns)
- SQLAlchemy async support patterns (MEDIUM confidence -- training data, asyncpg already in project dependencies confirming async DB is the expected path)
- Python production application patterns (MEDIUM confidence -- training data, industry standard practices)

---
*Feature research for: GatheRing production-readiness consolidation*
*Researched: 2026-02-10*
