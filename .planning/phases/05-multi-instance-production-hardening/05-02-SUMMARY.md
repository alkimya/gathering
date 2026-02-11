---
phase: 05-multi-instance-production-hardening
plan: 02
subsystem: api
tags: [graceful-shutdown, readiness-probe, health-check, lifespan, fastapi]

# Dependency graph
requires:
  - phase: 04-performance-optimization
    provides: AsyncDatabaseService pool, rate-limited health endpoints
  - phase: 05-multi-instance-production-hardening plan 01
    provides: Advisory lock coordination in Scheduler (async_db parameter)
provides:
  - Shutdown-aware /health/ready readiness probe (503 during shutdown)
  - Ordered lifespan shutdown (scheduler -> executor -> async DB pool)
  - Startup reordering (async DB pool before scheduler for advisory lock wiring)
  - 5 graceful shutdown tests
affects: [deployment, rolling-updates, load-balancer-integration]

# Tech tracking
tech-stack:
  added: []
  patterns: [shutdown-aware-readiness-probe, ordered-subsystem-teardown, lb-drain-pause]

key-files:
  created:
    - tests/test_graceful_shutdown.py
  modified:
    - gathering/api/routers/health.py
    - gathering/api/main.py

key-decisions:
  - "Startup reorder: async DB pool init moved before scheduler start so advisory lock wiring is available"
  - "Shutdown order: set_shutting_down -> sleep(3) LB drain -> scheduler stop -> sleep(2) task drain -> executor shutdown -> async DB pool close LAST"
  - "sleep(2) drain after scheduler.stop() for in-flight _execute_action tasks holding advisory lock queries"

patterns-established:
  - "Shutdown flag pattern: module-level _shutting_down bool with set/reset functions for probe coordination"
  - "Ordered teardown: subsystems close in reverse dependency order -- scheduler (creates work) before executor (runs work) before DB pool (provides data)"

# Metrics
duration: 4min
completed: 2026-02-11
---

# Phase 5 Plan 2: Graceful Shutdown Summary

**Shutdown-aware /health/ready readiness probe with ordered lifespan teardown: scheduler first, async DB pool last, with LB drain pauses**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-11T00:50:17Z
- **Completed:** 2026-02-11T00:55:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- /health/ready returns 503 with `{"ready": false, "reason": "shutting_down"}` during shutdown, 200 during normal operation
- Startup reordered: async DB pool initializes before scheduler, passing `async_db` for advisory lock coordination
- Shutdown sequence: set_shutting_down -> sleep(3) LB drain -> scheduler.stop() -> sleep(2) in-flight task drain -> executor.shutdown() -> async_db.shutdown() (LAST)
- 5 tests proving readiness probe behavior, shutdown order, idempotent flag, and flag reset

## Task Commits

Each task was committed atomically:

1. **Task 1: Add shutdown-aware readiness probe and reorder lifespan shutdown** - `45c8691` (feat)
2. **Task 2: Add graceful shutdown tests** - `e6b4995` (test)

## Files Created/Modified
- `gathering/api/routers/health.py` - Added _shutting_down flag, set_shutting_down(), reset_shutting_down(); readiness_check returns 503 during shutdown
- `gathering/api/main.py` - Reordered startup (async DB before scheduler), reordered shutdown (scheduler first, DB last), added asyncio import, LB drain pauses
- `tests/test_graceful_shutdown.py` - 5 tests: readiness 200, readiness 503, shutdown sequence order, idempotent flag, reset restores readiness

## Decisions Made
- Startup reorder: async DB pool init moved before scheduler start so advisory lock wiring (from Plan 01) is available at scheduler construction time
- Shutdown order: set_shutting_down -> sleep(3) LB drain -> scheduler stop -> sleep(2) task drain -> executor shutdown -> async DB pool close LAST -- ensures in-flight advisory lock queries from _execute_action tasks complete before pool closes
- sleep(2) added after scheduler.stop() because fire-and-forget asyncio.create_task(_execute_action(...)) tasks may still hold advisory lock queries

## Deviations from Plan

None - plan executed exactly as written. The `async_db` parameter on `get_scheduler()` already existed from Plan 01 execution (commit `21e19ee`), so no additional wiring was needed in the scheduler module.

## Issues Encountered
- Test `test_shutdown_sequence_order` initially hit RecursionError: the mock's `side_effect` for `set_shutting_down` tried to re-import the patched function, causing infinite recursion. Fixed by saving a reference to the real function before patching.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Graceful shutdown with ordered teardown complete -- rolling deploys can proceed with zero 502/503 errors
- Load balancer integration ready: /health/ready returns 503 during shutdown, giving LBs 3 seconds to detect and stop routing
- Phase 5 complete: advisory lock coordination (Plan 01) + graceful shutdown (Plan 02) provide multi-instance production hardening

## Self-Check: PASSED

- FOUND: gathering/api/routers/health.py
- FOUND: gathering/api/main.py
- FOUND: tests/test_graceful_shutdown.py
- FOUND: 05-02-SUMMARY.md
- FOUND: commit 45c8691 (Task 1)
- FOUND: commit e6b4995 (Task 2)

---
*Phase: 05-multi-instance-production-hardening*
*Completed: 2026-02-11*
