# Roadmap: GatheRing Consolidation

## Overview

GatheRing has a sound architecture with 1071 tests but critical production gaps: in-memory auth, stubbed pipelines, stubbed schedules, SQL injection, sync DB in async handlers, and no distributed coordination. This roadmap fixes everything in strict dependency order -- auth and security first (everything authenticates through it), pipeline execution second (schedules dispatch to it), schedule and tool completion third, performance fourth (don't optimize broken code), and multi-instance hardening last (distributed bugs on top of local bugs are impossible to debug). Tests accompany each phase rather than living in a separate phase.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Auth + Security Foundation** - Persistent auth, SQL injection elimination, security hardening, DB layer consolidation
- [ ] **Phase 2: Pipeline Execution Engine** - DAG traversal, node execution, validation, error recovery, cancellation
- [ ] **Phase 3: Schedule Execution + Tool Hardening** - Action dispatch, crash recovery, tool validation, async tools, workspace paths
- [ ] **Phase 4: Performance Optimization** - Async DB, N+1 elimination, rate limiting, event batching, cache bounds
- [ ] **Phase 5: Multi-Instance + Production Hardening** - Distributed coordination, graceful shutdown

## Phase Details

### Phase 1: Auth + Security Foundation
**Goal**: Users and tokens persist across restarts, all security vulnerabilities are closed, and the database layer is consolidated on pycopg
**Depends on**: Nothing (first phase)
**Requirements**: DBLR-01, DBLR-02, SEC-01, SEC-02, SEC-03, SEC-04, SEC-05, SEC-06, RLBL-01, RLBL-02, TEST-01, TEST-03
**Success Criteria** (what must be TRUE):
  1. A user created via the API exists in PostgreSQL and survives a server restart -- logging in after restart succeeds with the same credentials
  2. A revoked token remains rejected after server restart -- logout is permanent, not just until the next deploy
  3. No SQL query in the codebase constructs WHERE/SET clauses using f-strings with user-supplied values -- all user input flows through parameterized statements
  4. Auth endpoints respond in constant time regardless of whether the email exists -- timing attacks cannot enumerate accounts
  5. File-serving endpoints reject encoded path traversal attempts (../, %2e%2e/, symlink escape) and return 403, not file contents
**Plans:** 3 plans

Plans:
- [ ] 01-01-PLAN.md -- Foundation: library swaps (PyJWT, bcrypt), exception classes, structlog config, auth migration SQL
- [ ] 01-02-PLAN.md -- Auth persistence: DB-backed users and token blacklist, constant-time auth, audit event logging
- [ ] 01-03-PLAN.md -- Security hardening: safe_update_builder, path traversal defense, bare exception fixes, comprehensive tests

### Phase 2: Pipeline Execution Engine
**Goal**: Pipelines execute real work -- DAG traversal runs agent tasks, conditions gate execution, errors recover or fail cleanly, and runs are cancellable
**Depends on**: Phase 1 (auth working, SQL safe, DB layer consolidated)
**Requirements**: FEAT-01, FEAT-02, FEAT-03, FEAT-04, TEST-02
**Success Criteria** (what must be TRUE):
  1. A pipeline with multiple connected nodes executes in topological order -- each node runs its agent task, condition, or action for real and passes output to downstream nodes
  2. A pipeline containing a cycle is rejected at validation time with a clear error before any node executes
  3. A failing node retries with exponential backoff up to a configured limit, then trips its circuit breaker -- subsequent calls to a broken node fail fast without retrying
  4. A running pipeline can be cancelled mid-execution and a pipeline exceeding its timeout is terminated -- neither leaves zombie tasks or locked resources
**Plans**: TBD

Plans:
- [ ] 02-01: TBD
- [ ] 02-02: TBD
- [ ] 02-03: TBD

### Phase 3: Schedule Execution + Tool Hardening
**Goal**: Schedules dispatch real actions on their cron triggers, tools validate input before execution, and the scheduler survives crashes without running duplicates
**Depends on**: Phase 2 (pipeline execution works -- execute_pipeline is a schedule action type)
**Requirements**: FEAT-05, FEAT-06, FEAT-07, FEAT-08, RLBL-04, TEST-05
**Success Criteria** (what must be TRUE):
  1. A schedule with action_type "execute_pipeline" triggers a real pipeline run at the configured cron time -- the pipeline appears in execution history with actual results
  2. After a server crash and restart, the scheduler detects missed runs and does not re-execute actions that already completed -- no duplicate pipeline runs or duplicate notifications
  3. A tool invoked with parameters that violate its JSON schema is rejected before execution with a validation error describing which parameters are invalid
  4. Async tools (marked with async_function flag) execute without blocking the event loop -- concurrent tool invocations run in parallel, not sequentially
  5. Workspace API resolves file paths relative to the project directory, not the server's working directory -- accessing "src/main.py" returns the project file, not the server's src/main.py
**Plans**: TBD

Plans:
- [ ] 03-01: TBD
- [ ] 03-02: TBD
- [ ] 03-03: TBD

### Phase 4: Performance Optimization
**Goal**: Database access is non-blocking, query patterns are efficient, API endpoints enforce rate limits, and in-memory stores are bounded
**Depends on**: Phases 1-3 (correct behavior established -- optimize working code, not broken code)
**Requirements**: PERF-01, PERF-02, PERF-03, PERF-04, PERF-05, TEST-04
**Success Criteria** (what must be TRUE):
  1. Database queries in async route handlers use the pycopg async driver -- no sync calls block the FastAPI event loop under concurrent load
  2. Retrieving a circle with 20 members executes a bounded number of queries (1-2 JOINs), not 20+ individual member lookups
  3. API endpoints enforce per-endpoint rate limits -- exceeding the limit returns 429 Too Many Requests with a Retry-After header
  4. Rapid-fire event emissions (100+ events/second) are batched and deduplicated -- the event bus processes them without spawning unbounded tasks or exhausting memory
  5. In-memory caches (token blacklist, file tree, event history) have configurable size bounds and evict least-recently-used entries when full
**Plans**: TBD

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD
- [ ] 04-03: TBD

### Phase 5: Multi-Instance + Production Hardening
**Goal**: Multiple server instances coordinate without duplicate task execution, and the server shuts down gracefully without dropping in-flight requests
**Depends on**: Phases 1-4 (single-instance correctness and performance established)
**Requirements**: RLBL-03, SEC-07
**Success Criteria** (what must be TRUE):
  1. Two server instances processing the same task queue never execute the same task simultaneously -- PostgreSQL advisory locks prevent duplicate execution
  2. During shutdown, the server stops accepting new requests, waits for in-flight requests to complete (up to a timeout), and then exits cleanly -- no 502s during rolling deploys
**Plans**: TBD

Plans:
- [ ] 05-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Auth + Security Foundation | 0/3 | Planned | - |
| 2. Pipeline Execution Engine | 0/3 | Not started | - |
| 3. Schedule Execution + Tool Hardening | 0/3 | Not started | - |
| 4. Performance Optimization | 0/3 | Not started | - |
| 5. Multi-Instance + Production Hardening | 0/1 | Not started | - |
