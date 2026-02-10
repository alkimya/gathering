---
phase: 04-performance-optimization
plan: 01
subsystem: database
tags: [async, psycopg, connection-pool, n-plus-one, query-optimization, fastapi-lifespan]

# Dependency graph
requires:
  - phase: 01-auth-security-foundation
    provides: DatabaseService singleton pattern, pycopg wrapper integration
provides:
  - AsyncDatabaseService singleton with async connection pool lifecycle
  - get_async_db() FastAPI dependency for async route handlers
  - get_circle_members_full() JOIN query eliminating N+1 in circle loading
affects: [04-02, 04-03, future async route migration]

# Tech tracking
tech-stack:
  added: [pycopg.AsyncPooledDatabase (already in project, now wired)]
  patterns: [async db singleton with lifespan lifecycle, JOIN-based batch loading]

key-files:
  created:
    - gathering/api/async_db.py
  modified:
    - gathering/api/main.py
    - gathering/api/dependencies.py

key-decisions:
  - "AsyncDatabaseService uses Config.from_env() pattern (same as existing DatabaseService) for env var parsing"
  - "Pool sized at min_size=4, max_size=20 for web workload concurrency"
  - "Async pool startup/shutdown added to lifespan after scheduler (startup) and before scheduler (shutdown)"
  - "get_circle_members_full() uses single JOIN instead of 2N+1 per-member queries"
  - "Existing get_agent() and get_circle_members_with_info() preserved for backward compatibility"

patterns-established:
  - "Async DB lifecycle: singleton.get_instance() in lifespan startup, singleton.shutdown() in lifespan shutdown"
  - "JOIN-based batch loading: fetch all related data in one query instead of per-row lookups"

# Metrics
duration: 9min
completed: 2026-02-11
---

# Phase 4 Plan 1: Async Database Service and N+1 Query Elimination Summary

**AsyncDatabaseService with pycopg AsyncPooledDatabase wired into FastAPI lifespan, plus single-JOIN circle member loading replacing 2N+1 per-member queries**

## Performance

- **Duration:** 9 min
- **Started:** 2026-02-10T23:32:43Z
- **Completed:** 2026-02-10T23:41:44Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- AsyncDatabaseService singleton using pycopg AsyncPooledDatabase with async startup/shutdown lifecycle
- FastAPI lifespan wires pool open on startup and close on shutdown (non-blocking DB access ready for route migration)
- get_async_db() dependency function available for any route handler to Depends() inject
- Circle member retrieval reduced from 2N+1 queries to 1 JOIN query per circle via get_circle_members_full()
- Backward compatibility preserved: existing get_agent(), get_circle_members_with_info() unchanged

## Task Commits

Each task was committed atomically:

1. **Task 1: Create AsyncDatabaseService and wire into FastAPI lifespan** - `7c4ce51` (feat)
2. **Task 2: Eliminate N+1 queries in circle member retrieval** - `bc0efef` (feat)

## Files Created/Modified
- `gathering/api/async_db.py` - AsyncDatabaseService singleton with pool lifecycle, execute/fetch methods, get_async_db dependency
- `gathering/api/main.py` - Lifespan startup/shutdown blocks for async database pool
- `gathering/api/dependencies.py` - get_circle_members_full() JOIN method, CircleRegistry._load_from_db() updated to use it

## Decisions Made
- AsyncDatabaseService mirrors DatabaseService env var parsing (DATABASE_URL or DB_* vars) for consistency
- Pool sized min_size=4, max_size=20 -- suitable for web app concurrency without over-allocating connections
- Lifespan ordering: async pool starts after scheduler (both need DB), shuts down before scheduler (pool should outlive scheduler)
- N+1 fix is sync (uses DatabaseService, not AsyncDatabaseService) -- query count reduction is independent of sync/async
- ConversationRegistry._load_from_db() checked for N+1 but does not call get_agent() in loop, so no change needed

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing test failure in test_create_circle (DB auth error in test env) -- not caused by these changes, confirmed identical failure count before/after (12 failed, 1164 passed)
- Stash pop during verification reverted dependencies.py changes, requiring re-application -- no impact on final result

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- AsyncDatabaseService is infrastructure-ready; route handlers can be migrated incrementally via Depends(get_async_db)
- N+1 elimination in circle loading is complete; similar pattern in AgentRegistry._load_from_db() could be optimized in future work
- Plans 04-02 (rate limiting) and 04-03 (event bus) can proceed independently

## Self-Check: PASSED

- All 4 files exist (async_db.py, main.py, dependencies.py, SUMMARY.md)
- Both commits found (7c4ce51, bc0efef)
- AsyncDatabaseService importable with get_async_db
- get_circle_members_full method exists on DatabaseService

---
*Phase: 04-performance-optimization*
*Completed: 2026-02-11*
