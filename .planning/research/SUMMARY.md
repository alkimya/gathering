# Project Research Summary

**Project:** GatheRing Production-Readiness Consolidation
**Domain:** Multi-agent AI framework production hardening (Python/FastAPI/PostgreSQL)
**Researched:** 2026-02-10
**Confidence:** HIGH (direct codebase analysis + established production patterns)

## Executive Summary

GatheRing is a multi-agent AI framework with a FastAPI backend, React dashboard, and PostgreSQL database. It has 18+ routers, 18+ skills, and 1071 tests. The core architecture is sound, but production deployment is blocked by critical gaps: in-memory auth that loses state on restart, stubbed pipeline execution that fakes completion, synchronous database calls that block the event loop, and active security vulnerabilities (SQL injection, path traversal). The consolidation scope is NOT a rewrite—it's completing half-finished features and replacing dangerous shortcuts with production-grade implementations.

The recommended approach follows a strict dependency order: **Auth first** (everything authenticates through it), **pipeline execution second** (schedules depend on it), **performance third** (don't optimize broken code), **distributed coordination last** (single-instance must work before multi-instance). The stack requires targeted additions (PyJWT, slowapi, structured logging activation) and replacements (psycopg3 async, bcrypt direct) rather than wholesale changes. Security fixes (SQL injection, timing attacks) must ship in Phase 1 because later phases depend on a non-corrupted database.

Key risk: the 262 bare exception catches mean bugs are currently masked. Fixing them gradually (Tier 1 security paths first, Tier 2 features second, Tier 3 polish last) prevents catastrophic test suite destabilization while systematically revealing the actual error states. Success criteria: users survive restart, pipelines execute real work, auth endpoints resist brute force, and performance scales linearly with load.

## Key Findings

### Recommended Stack

**Core insight:** The stack doesn't need replacement—it needs consolidation. psycopg3, structlog, and tenacity are already declared dependencies but unused. The actual problems are unmaintained libraries (python-jose, passlib) and missing production infrastructure (rate limiting, audit logging, async database).

**Core technology changes:**
- **psycopg3 (already installed)**: Replace psycopg2-binary + asyncpg with single async-capable driver. SQLAlchemy 2.0.45 officially supports `postgresql+psycopg://` dialect. Eliminates dual-driver maintenance burden.
- **PyJWT**: Replace python-jose (unmaintained, pulls 3 extra deps). FastAPI security docs now reference PyJWT. Already a transitive dependency via redis.
- **bcrypt direct**: Remove passlib wrapper (no release since 2020, no Python 3.12+ support). PyCA's bcrypt 4.3.0 is actively maintained. Direct usage is simpler than passlib's abstraction.
- **slowapi**: Production-grade rate limiting with Redis backend support. Replaces 75-line custom middleware that has memory leak (unbounded IP tracking).
- **structlog (activate)**: Already declared, never used. JSON structured logging with request ID propagation. Foundation for audit trail.
- **PostgreSQL advisory locks**: Zero-infrastructure distributed coordination. Use `pg_try_advisory_lock()` for multi-instance task deduplication.

**Version confidence:** HIGH. All packages verified installed or in pyproject.toml. Compatibility matrix confirmed via METADATA inspection.

### Expected Features

**Table Stakes (16 features—all P1 blocking):**
The codebase has 16 must-fix issues where missing any one means production deployment is unsafe or non-functional:

1. **Persistent users** — registration currently writes to in-memory dict, lost on restart
2. **Persistent token blacklist** — logout tokens become valid again after restart (security violation)
3. **SQL injection elimination** — f-string SQL in pipelines.py, schedules.py (OWASP Top 10 #3)
4. **Pipeline execution engine** — currently fakes completion with fake logs, nothing executes
5. **Schedule action execution** — scheduler framework exists but only logs, never dispatches
6. **Async database access** — sync DB calls in async handlers block event loop (destroys concurrency)
7. **Audit logging** — no auth event logging (can't detect breaches or brute force)
8. **Path traversal fix** — workspace file serving needs path validation strengthening
9. **N+1 query fix** — circle member retrieval makes 30+ queries for 10 agents instead of 1 JOIN
10. **Error handling** — 262 bare exception catches hide bugs and leak implementation details
11. **Timing-safe auth** — email lookup timing reveals account existence
12. **Persistence tests** — no integration tests proving data survives restart
13. **Token lifecycle tests** — no tests for expiry, blacklist cleanup, concurrent use
14. **Pipeline execution tests** — will accompany implementation
15. **Tool parameter validation** — tools receive garbage input, fail deep in execution (TODO in tool_registry.py)
16. **Rate limiting hardening** — current implementation has memory leak, no per-endpoint tiers

**Differentiators (10 features—P2 production quality):**
Features that enable scaling and reduce operational burden but aren't strictly required for launch:

- Distributed task coordination (PostgreSQL advisory locks for multi-instance)
- Pipeline error recovery (tenacity-based retry, circuit breakers, dead letter queues)
- Event bus batching (prevents task saturation under high event volume)
- Structured logging with correlation (enables log aggregation, production debugging)
- Graceful shutdown (zero-downtime deploys via request draining)
- Cache bounds (LRU eviction for unbounded in-memory stores)
- Event bus concurrency tests, scheduler recovery tests, workspace path resolution, async tool execution

**Anti-features (7 items explicitly deferred):**
OAuth2/OIDC, Kubernetes manifests, new feature development, full async-only DB rewrite, distributed event bus (Kafka), real-time collaboration, frontend refactoring—all explicitly out of scope. These are v2+ considerations.

### Architecture Approach

**Current state:** Working foundation with critical gaps. FastAPI + 18 routers + PostgreSQL + 8 schemas + background executor + scheduler framework + 18 skills. The orchestration layer (GatheringCircle, Facilitator, EventBus) is functional for single-agent flows but pipeline execution is stubbed.

**Critical finding:** Two separate EventBus implementations exist (events/event_bus.py for WebSocket bridge, orchestration/events.py for circle coordination). These are NOT interchangeable—different EventType enums, different scopes. Production hardening must preserve this boundary.

**Major components and state:**
1. **Auth module** — in-memory users dict, in-memory token blacklist (STUBBED—loses state on restart)
2. **Pipeline router** — CRUD works, execution is fake (creates completion logs without running anything)
3. **Scheduler** — tracks schedules, dispatch is stub (only logs "would run action")
4. **DatabaseService** — synchronous psycopg wrapper (blocks event loop in async handlers)
5. **AgentWrapper + Skills** — working for basic flows, no input validation
6. **EventBus** — working but no persistence, no batching, unbounded task creation

**Build order (dependency-driven):**
1. **Phase 1: Auth + Security** — persistent users/tokens, SQL injection fixes, timing-safe auth, audit logging. Everything authenticates through auth; corrupt data invalidates all later work.
2. **Phase 2: Pipeline Execution** — build PipelineEngine, node handlers, DAG validation, error recovery. Schedules dispatch to pipelines.
3. **Phase 3: Schedule Execution + Tools** — action dispatcher, retry logic, distributed locking, tool validation. Depends on working pipelines.
4. **Phase 4: Performance + Async DB** — run_in_executor wrapper (immediate fix), N+1 elimination, event batching. Don't optimize broken code.
5. **Phase 5: Distributed Coordination** — only after single-instance works. Multi-instance bugs on top of local bugs are impossible to debug.

### Critical Pitfalls

**1. Auth migration breaks existing sessions (P1 blocker)**
In-memory store uses `str(uuid.uuid4())` for user IDs. Database migration likely uses auto-incrementing integers or different UUID format. Existing JWT tokens decode to user IDs that don't exist in the database, causing 401 cascades. **Prevention:** Freeze UserResponse schema contract before touching storage. Keep user ID format as `str` in API regardless of DB type. Write migration script. Contract tests as acceptance gate.

**2. Sync-to-async DB migration blocks event loop (P2 critical)**
Every async router calls synchronous `db.execute()`. In FastAPI, `async def` + sync I/O = event loop starvation. Worse than using `def` (which FastAPI runs in threadpool). Common FastAPI mistake. **Prevention:** Strategy A (recommended): Replace DatabaseService with async implementation using psycopg3. Strategy B (interim): Change `async def` to `def` in routers (FastAPI handles via threadpool). Test with concurrent load—single-user tests never catch this.

**3. Pipeline execution without timeouts enables infinite loops (P3 blocker)**
Pipeline validation is currently absent (accepts arbitrary node configs, no cycle detection). When execution is implemented, cyclic pipelines run forever. LLM calls in loops burn API credits unboundedly. No resource limits. **Prevention:** Implement validation BEFORE execution (topological sort for cycle detection). Hard timeout per pipeline run (30min default). Per-node timeout (5min for LLM, 60s for actions). Track execution depth, abort after max iterations. Make runs cancellable.

**4. 262 bare exception catches create silent failure cascades (P4 pervasive)**
Most catch `Exception`, log, return default value (False, None, empty list) or silently continue. Real bugs get caught 6 layers deep. User sees "no results" instead of "service unavailable". **Prevention:** Do NOT fix all 262 at once (will break test suite catastrophically). Categorize into tiers: Tier 1 (auth, DB, security—fix in Phase 1), Tier 2 (features—fix during implementation), Tier 3 (skills, UI—fix in polish). Add linting rule to prevent new bare catches.

**5. SQL injection fix breaks dynamic UPDATE builders (P5 subtle)**
Several f-string SQL queries exist in dynamic UPDATE patterns. Naively replacing with parameterized queries breaks because you can't parameterize column names—only values. The f-string SET clause construction from hardcoded column names is actually safe. Real risk is if user input reaches column name position. **Prevention:** Audit each f-string SQL individually. For dynamic UPDATEs, validate column names against explicit allowlist. Parameterize values only. Consider migrating to SQLAlchemy Core `update().values()`.

**6. Schedule execution runs duplicate actions after recovery (P6 data corruption)**
Scheduler tracks running actions in-memory set. After restart, set is empty. Actions mid-execution appear "due" and execute again. For non-idempotent actions (notifications, pipelines), this causes duplicates. **Prevention:** Persist execution state to scheduled_actions table (last_execution_id, execution_status, execution_started_at). Use "claim" pattern: write execution_log row with status=claimed before executing. If already claimed, skip.

**7. Test suite becomes unreliable during consolidation (P7 meta-risk)**
With 1071 tests, many test stub behavior as if it were real. Fixing implementations breaks tests that were testing wrong behavior. Can't distinguish "failed because I fixed a bug" from "failed because I broke something". **Prevention:** Tag all tests BEFORE code changes: @pytest.mark.stub (will break), @pytest.mark.contract (must never break), @pytest.mark.unit (should not break). CI runs `pytest -m "not stub"` as gate. Write new tests FIRST (TDD) defining correct behavior.

## Implications for Roadmap

Based on research, the dependency chain dictates this phase structure:

### Phase 1: Foundation—Auth Persistence + Security Hardening
**Rationale:** Auth is the trust foundation. Every feature authenticates through it. If auth loses state on restart, no identity-dependent feature works reliably. SQL injection fixes go here because corrupt data invalidates all subsequent work. Security fixes must ship before features that depend on data integrity.

**Delivers:** Database-backed user storage, persistent token blacklist, parameterized SQL queries, timing-safe auth comparisons, path traversal fixes, audit logging for auth events, comprehensive error handling in critical paths.

**Addresses features:** TS-1 (persistent users), TS-2 (token blacklist), TS-3 (SQL injection), TS-7 (audit logging), TS-8 (path traversal), TS-10 (error handling Tier 1), TS-11 (timing-safe auth), TS-12 (persistence tests), TS-13 (token tests).

**Stack elements:** PyJWT (replace python-jose), bcrypt direct (replace passlib), structlog activation, PostgreSQL auth schema.

**Avoids pitfalls:** P1 (auth migration), P4 (bare exceptions in security paths), P5 (SQL injection fix correctness), P7 (test tagging done in Phase 0 pre-work).

**Dependencies:** None. This is the starting point.

**Test coverage:** Contract tests for UserResponse schema, integration tests for token lifecycle, negative security tests for SQL injection payloads, timing attack resistance tests.

### Phase 2: Core Feature—Pipeline Execution Engine
**Rationale:** Pipelines are the primary workflow feature. Currently 100% stubbed (fake completion logs). Schedules dispatch to pipeline execution, so this must work before schedule implementation. Depends on working auth (agents authenticate) and secure database (from Phase 1).

**Delivers:** PipelineEngine class with DAG traversal, node type handlers (trigger, agent, condition, action, parallel, delay), validation (cycle detection, schema checks), error recovery (per-node retry, circuit breakers), event emission for progress tracking, background task integration.

**Addresses features:** TS-4 (pipeline execution), TS-14 (pipeline tests), TS-15 (tool validation), portions of TS-10 (error handling Tier 2).

**Stack elements:** tenacity (retry logic), psycopg3 async (start async migration here), BackgroundExecutor integration.

**Architecture components:** PipelineEngine, NodeHandler strategy pattern, integration with AgentWrapper and skill system.

**Avoids pitfalls:** P3 (validation before execution, timeouts, resource limits), P4 (specific exception types for pipeline errors).

**Dependencies:** Requires Phase 1 complete (auth working, SQL safe).

**Test coverage:** DAG traversal correctness, node execution, error propagation, cycle detection rejection, timeout enforcement, cancellation support.

### Phase 3: Scheduler Completion + Tool Hardening
**Rationale:** Schedules dispatch to pipelines (Phase 2) and background tasks (already working). Action execution is currently stubbed. Distributed coordination prevents duplicate execution in multi-instance deployments. Tool validation prevents garbage input crashes.

**Delivers:** Action type dispatcher (run_task, execute_pipeline, send_notification, call_api), retry logic with exponential backoff, distributed locking via PostgreSQL advisory locks, scheduler state persistence, tool parameter validation against JSON schema, async tool support, workspace path resolution.

**Addresses features:** TS-5 (schedule execution), TS-15 (tool validation), D-1 (distributed coordination), D-9 (workspace paths), D-10 (async tools), portions of TS-10 (error handling Tier 2).

**Stack elements:** PostgreSQL advisory locks, tenacity, jsonschema validation, asyncio concurrent execution.

**Avoids pitfalls:** P6 (duplicate execution recovery), P4 (specific exception types for scheduler errors).

**Dependencies:** Requires Phase 2 complete (pipeline execution works).

**Test coverage:** Schedule dispatch correctness, retry behavior, concurrent execution prevention, tool validation, recovery after restart.

### Phase 4: Performance Optimization
**Rationale:** Performance fixes don't change behavior—they make existing correct behavior faster. Doing this before correctness wastes effort on code that will change. Phase 1-3 establish correct behavior; Phase 4 makes it fast.

**Delivers:** Async database migration (run_in_executor wrapper first, full async driver later), N+1 query elimination (JOIN optimization for circle members), event bus batching and deduplication, rate limiting hardening (slowapi integration, per-endpoint tiers, Redis backend), cache bounds (LRU eviction), module splitting (dependencies.py is 1694 lines).

**Addresses features:** TS-6 (async DB), TS-9 (N+1 fix), TS-16 (rate limiting), D-3 (event batching), D-6 (cache bounds), portions of D-4 (structured logging with correlation).

**Stack elements:** psycopg3 full async migration, slowapi, Redis (optional), OpenTelemetry instrumentation.

**Avoids pitfalls:** P2 (event loop blocking), P4 (error handling Tier 3).

**Dependencies:** Requires Phase 1-3 complete (correct behavior established).

**Test coverage:** Async behavior verification, query count assertions, cache consistency, rate limit correctness, concurrent load testing.

### Phase 5: Multi-Instance Hardening (Optional—v1.1+)
**Rationale:** Distributed coordination only matters for multi-instance deployment. Single-instance must work correctly first. Distributed bugs on top of local bugs are impossible to debug. This phase is optional for v1.0 (single-instance production launch).

**Delivers:** Cross-instance distributed locks (advisory locks for task assignment), scheduler coordination across instances, event bus persistence for crash recovery, cross-instance token blacklist verification, graceful shutdown with request draining.

**Addresses features:** D-1 (distributed coordination completion), D-5 (graceful shutdown), D-7 (event concurrency tests), D-8 (scheduler recovery tests).

**Avoids pitfalls:** Distributed bugs (by ensuring single-instance correctness first).

**Dependencies:** Requires Phase 1-4 complete. Single-instance passes all tests.

**Test coverage:** Multi-instance simulation, lock contention, split-brain scenarios, cross-instance consistency.

### Phase Ordering Rationale

1. **Auth + Security MUST come first** because every feature depends on authentication state and data integrity. A pipeline authenticating against in-memory users breaks on restart. SQL injection in any query corrupts data that all later phases depend on.

2. **Pipeline execution MUST come before schedule execution** because `execute_pipeline` is a schedule action type. Building scheduler dispatch before the pipeline engine exists means nothing to dispatch to.

3. **Performance MUST come after correctness** because async migration changes calling conventions. Wrapping a buggy sync call in run_in_executor still has the bug—now harder to debug on a thread pool.

4. **Distributed coordination MUST come last** because it multiplies complexity. Adding distributed locks to a scheduler that doesn't execute actions is premature complexity.

5. **Tests accompany each phase** (not a separate testing phase) because deferred testing makes later phases unable to verify they haven't broken earlier fixes.

### Research Flags

**Phases needing research-phase during planning:**
- **Phase 2 (Pipeline Execution):** Complex DAG traversal, error recovery patterns, circuit breaker implementation. Will benefit from `/gsd:research-phase` on pipeline execution patterns, especially for async DAG execution and partial failure handling.
- **Phase 3 (Distributed Coordination):** PostgreSQL advisory locks usage patterns, distributed lock pitfalls. Research phase for distributed locking patterns recommended.

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (Auth + Security):** Well-documented patterns. JWT auth, password hashing, SQL parameterization are established practices. OWASP guidance is comprehensive.
- **Phase 4 (Performance):** N+1 query fixes, async DB migration, rate limiting are standard FastAPI production patterns. Extensive documentation available.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All recommended packages verified installed or in pyproject.toml. Version compatibility confirmed via METADATA inspection. No version conflicts detected. |
| Features | HIGH | Based on direct codebase analysis + CONCERNS.md audit. Every feature mapped to specific file/line numbers. Prioritization grounded in actual missing functionality vs. nice-to-haves. |
| Architecture | HIGH | Full codebase traversal completed. Component boundaries identified. Dual EventBus discovered and documented. Build order derived from actual dependency chains, not theory. |
| Pitfalls | HIGH | Grounded in actual code patterns (262 bare exceptions counted, f-string SQL locations identified). Pitfall severity based on impact analysis, not speculation. Recovery strategies tested against codebase structure. |

**Overall confidence:** HIGH

This is NOT theoretical research—it's a forensic analysis of an existing codebase with concrete findings mapped to specific files and line numbers. The recommended approach comes from observed gaps, not domain assumptions.

### Gaps to Address

1. **APScheduler 4.x availability:** Stack research recommends APScheduler 4.x (major rewrite with async support). Need to verify version stability at install time. If not stable, fall back to existing croniter-based scheduler with advisory lock coordination.

2. **slowapi version and Starlette compatibility:** slowapi needs verification at install time for compatibility with Starlette 0.50.0 (installed). If incompatible, custom rate limiting middleware can be hardened (add cleanup, per-endpoint config) as interim solution.

3. **Pipeline node type handlers:** Research identifies node types (trigger, agent, condition, action, parallel, delay) but implementation details need discovery during Phase 2. Specifically: how conditions evaluate, what "parallel" means for execution context, whether delays block or schedule.

4. **Token migration strategy:** If user ID format changes during auth migration, existing JWT tokens become invalid. Need decision: force re-login (simplest) or implement token migration (transparent to users). Research recommends keeping user ID format as `str` to avoid this entirely.

5. **Multi-instance event bus:** Phase 5 mentions "event bus persistence" but two separate EventBus implementations exist. Need clarification: does multi-instance coordination apply to both buses, or only orchestration/events.py?

These gaps are "discover during implementation" items, not blockers to roadmap creation. The roadmap phases are sound; these are refinement details.

## Sources

### Primary (HIGH confidence)
- `.planning/codebase/CONCERNS.md` — comprehensive codebase audit (2026-02-10)
- `.planning/codebase/ARCHITECTURE.md` — architecture analysis
- `.planning/PROJECT.md` — project requirements and constraints
- Direct source inspection: `gathering/api/auth.py`, `gathering/api/routers/pipelines.py`, `gathering/skills/gathering/schedules.py`, `gathering/orchestration/scheduler.py`, `gathering/db/database.py`, `gathering/core/tool_registry.py`, `gathering/api/middleware.py`
- Installed package METADATA: psycopg 3.3.2, psycopg-pool 3.3.0, SQLAlchemy 2.0.45, bcrypt 4.3.0, python-jose 3.5.0, passlib 1.7.4, redis 7.1.0, asyncpg 0.31.0
- `pyproject.toml` dependency declarations: structlog, tenacity, opentelemetry-*
- Grep analysis: 262 `except Exception` across 74 files, f-string SQL locations

### Secondary (MEDIUM confidence)
- FastAPI async vs. sync behavior patterns (well-established, documented in FastAPI official docs)
- SQLAlchemy async engine usage (official SQLAlchemy 2.0 documentation)
- OWASP Top 10 security patterns (stable, mature guidance)
- PostgreSQL advisory locks documentation (PostgreSQL core feature, stable API)
- Python datetime.utcnow() deprecation (PEP 495, Python official docs)
- JWT authentication patterns (RFC 7519, industry standard)
- bcrypt password hashing (well-established cryptographic standard)

### Tertiary (LOW confidence—training data patterns)
- slowapi usage patterns (not currently installed, based on training data knowledge of FastAPI rate limiting libraries)
- APScheduler 4.x async support (major rewrite mentioned in training data, version availability needs verification)
- Pipeline DAG execution patterns (general async workflow patterns, not GatheRing-specific)

---
*Research completed: 2026-02-10*
*Ready for roadmap: yes*
*Next step: Requirements definition using this research as foundation*
