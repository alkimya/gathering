---
phase: 04-performance-optimization
plan: 04
subsystem: api, database
tags: [async, asyncio, fastapi, pycopg, async-db, concurrency, non-blocking]

# Dependency graph
requires:
  - phase: 04-01
    provides: "AsyncDatabaseService with pool lifecycle wired into FastAPI lifespan"
provides:
  - "5 route handlers using AsyncDatabaseService via Depends(get_async_db)"
  - "Integration test proving concurrent async DB requests execute in parallel"
  - "Proven pattern for migrating sync-to-async DB access in FastAPI routes"
affects: [05-polish, future-full-migration]

# Tech tracking
tech-stack:
  added: [httpx-async-testing]
  patterns: [async-db-dependency-injection, concurrent-request-testing]

key-files:
  created:
    - tests/test_async_db_routes.py
  modified:
    - gathering/api/routers/agents.py
    - gathering/api/routers/health.py
    - gathering/api/routers/models.py
    - gathering/api/routers/dashboard.py
    - gathering/api/routers/memories.py

key-decisions:
  - "Migrate 5 representative handlers across 3 routers (not all ~100+ endpoints) to prove pattern"
  - "Use direct SQL in async models.py handlers since AsyncDatabaseService has no convenience methods"
  - "Mock async DB with asyncio.sleep delay to prove parallel execution in concurrency test"

patterns-established:
  - "Async DB migration: import get_async_db, change Depends, add await on all DB calls"
  - "Concurrency test pattern: asyncio.gather() + wall-clock timing to prove non-blocking"

# Metrics
duration: 7min
completed: 2026-02-11
---

# Phase 04 Plan 04: Async DB Route Migration Summary

**5 route handlers migrated from sync to async DB access with integration test proving concurrent requests execute in parallel, not serially**

## Performance

- **Duration:** 7 min
- **Started:** 2026-02-11T00:00:53Z
- **Completed:** 2026-02-11T00:08:05Z
- **Tasks:** 2
- **Files modified:** 7 (3 routers migrated + 2 bug fixes + 1 test created)

## Accomplishments
- Migrated 5 route handlers across agents.py (GET history, POST chat), health.py (GET checks), and models.py (GET providers, GET provider) from sync DatabaseService to AsyncDatabaseService
- Created integration test suite with 4 tests: smoke test, concurrency proof, dependency type check, and providers endpoint test
- Concurrency test fires 10 simultaneous requests that complete in parallel (~10-50ms), not serially (~100ms+), proving the event loop is unblocked
- Fixed 3 blocking bugs in rate-limit decorator wiring (dashboard.py missing request param, memories.py duplicate param names)

## Task Commits

Each task was committed atomically:

1. **Task 1: Migrate representative route handlers to AsyncDatabaseService** - `c845573` (feat)
2. **Task 2: Add integration test proving async DB concurrency** - `ff1309e` (test)
3. **Chore: Wire rate limit decorators to remaining router endpoints** - `5a31d9a` (chore)

## Files Created/Modified
- `gathering/api/routers/agents.py` - get_agent_history and chat_with_agent use AsyncDatabaseService
- `gathering/api/routers/health.py` - get_health_checks uses AsyncDatabaseService for non-blocking probe
- `gathering/api/routers/models.py` - list_providers and get_provider use AsyncDatabaseService with direct SQL
- `gathering/api/routers/dashboard.py` - Fixed missing request param on get_dashboard_config
- `gathering/api/routers/memories.py` - Fixed duplicate request param names in recall and search_knowledge
- `tests/test_async_db_routes.py` - 4 integration tests proving async DB works end-to-end

## Decisions Made
- Migrated 5 representative handlers (not all ~100+ endpoints) to prove the pattern works at scale without scope creep
- Used direct SQL in async models.py handlers because AsyncDatabaseService exposes execute/fetch_one/fetch_all but not the convenience methods (get_providers, get_provider) that sync DatabaseService has
- Mock async DB uses asyncio.sleep(0.01) to simulate real async I/O -- if serialized, 10 concurrent requests would take ~100ms; if parallel, ~10-50ms

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed dashboard.py missing request parameter**
- **Found during:** Task 2 (test execution blocked by import error)
- **Issue:** Linter added `@limiter.limit(TIER_READ)` to `get_dashboard_config` but didn't add `request: Request` parameter, causing slowapi to raise Exception at import time
- **Fix:** Added `request: Request` parameter to function signature
- **Files modified:** gathering/api/routers/dashboard.py
- **Verification:** App creates without errors
- **Committed in:** ff1309e (Task 2 commit)

**2. [Rule 1 - Bug] Fixed memories.py duplicate request parameter names**
- **Found during:** Task 2 (test execution blocked by SyntaxError)
- **Issue:** Linter added `request: Request` to `recall()` and `search_knowledge()` which already had parameters named `request` (RecallRequest and KnowledgeSearchRequest), causing SyntaxError: duplicate argument
- **Fix:** Renamed RecallRequest param to `recall_request` and KnowledgeSearchRequest to `search_request`, updated all body references
- **Files modified:** gathering/api/routers/memories.py
- **Verification:** Module imports successfully
- **Committed in:** ff1309e (Task 2 commit)

**3. [Rule 3 - Blocking] Committed pre-existing rate-limit decorator wiring**
- **Found during:** Task 2 (linter auto-applied changes to 14+ router files)
- **Issue:** Rate limit decorators from 04-02 were auto-applied by linter to all router endpoints but never committed
- **Fix:** Committed the rate-limit wiring changes as a separate chore commit
- **Files modified:** 14 router files (background_tasks, circles, conversations, goals, lsp, pipelines, plugins, projects, scheduled_actions, settings, tools, workspace, agents, models)
- **Verification:** All imports succeed, app creates without errors
- **Committed in:** 5a31d9a (separate chore commit)

---

**Total deviations:** 3 auto-fixed (2 bugs from incomplete linter edits, 1 blocking uncommitted changes)
**Impact on plan:** Bug fixes were essential for test execution. Rate-limit wiring completes 04-02 work. No scope creep.

## Issues Encountered
- pytest-asyncio 1.3.0 is old but compatible with `@pytest.mark.asyncio` decorator style
- Coverage threshold (80%) fails for test file in isolation due to project-wide coverage config -- tests themselves pass cleanly

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Async DB migration pattern proven end-to-end for 5 handlers across 3 routers
- Full migration of remaining ~100+ endpoints is future work (not in scope for gap closure)
- Rate limit decorators now wired to all router endpoints
- Ready for phase 05 or additional gap closure plans

---
*Phase: 04-performance-optimization*
*Completed: 2026-02-11*
