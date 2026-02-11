---
phase: 05-multi-instance-production-hardening
plan: 01
subsystem: orchestration
tags: [postgresql, advisory-lock, scheduler, concurrency, multi-instance]

# Dependency graph
requires:
  - phase: 04-performance-optimization
    provides: AsyncDatabaseService with connection pool for async DB access
provides:
  - Scheduler._try_acquire_action_lock() method using pg_try_advisory_xact_lock
  - Multi-instance coordination via PostgreSQL advisory locks
  - SCHEDULER_LOCK_NAMESPACE constant for lock namespacing
  - async_db parameter wiring in Scheduler and get_scheduler()
affects: [05-02-graceful-shutdown, lifespan-wiring, multi-instance-deployment]

# Tech tracking
tech-stack:
  added: []
  patterns: [pg_try_advisory_xact_lock two-integer form, fail-closed lock pattern, optional async_db for backward compat]

key-files:
  created:
    - tests/test_advisory_lock_scheduler.py
  modified:
    - gathering/orchestration/scheduler.py

key-decisions:
  - "Advisory lock uses two-integer form pg_try_advisory_xact_lock(namespace, action_id) to avoid collision with other lock users"
  - "Fail-closed on DB error: returns False (skip execution) rather than risk duplicate"
  - "async_db is optional -- single-instance mode (None) always returns True for backward compatibility"
  - "Lock check is first gate in _execute_action, before existing concurrency check"

patterns-established:
  - "Advisory lock gate pattern: check lock before any execution logic, discard from _running_actions on skip"
  - "Fail-closed pattern: DB errors in coordination paths result in safe skip, not risky proceed"

# Metrics
duration: 3min
completed: 2026-02-11
---

# Phase 5 Plan 1: Advisory Lock Coordination Summary

**PostgreSQL advisory lock coordination in Scheduler using pg_try_advisory_xact_lock for exactly-once execution across multiple instances**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-11T00:50:12Z
- **Completed:** 2026-02-11T00:53:19Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added _try_acquire_action_lock() method using pg_try_advisory_xact_lock with two-integer form (namespace, action_id)
- Integrated advisory lock check at the start of _execute_action as the first gate before any execution logic
- Maintained full backward compatibility: async_db=None means single-instance mode where all locks return True
- 5 new tests proving single-instance bypass, fail-closed on DB error, exactly-once under concurrency, cleanup on skip, and normal execution with lock

## Task Commits

Each task was committed atomically:

1. **Task 1: Add advisory lock coordination to Scheduler** - `21e19ee` (feat)
2. **Task 2: Add advisory lock coordination tests** - `3da54c7` (test)

## Files Created/Modified
- `gathering/orchestration/scheduler.py` - Added SCHEDULER_LOCK_NAMESPACE, async_db parameter, _try_acquire_action_lock method, lock gate in _execute_action
- `tests/test_advisory_lock_scheduler.py` - 5 tests covering advisory lock behavior

## Decisions Made
- Used two-integer form pg_try_advisory_xact_lock(namespace, action_id) with SCHEDULER_LOCK_NAMESPACE=1 to prevent collision with other advisory lock users
- Fail-closed on DB error: any exception during lock acquisition returns False (skip) rather than True (risk duplicate)
- Lock check placed before existing async with self._lock block so advisory lock is the first gate in _execute_action
- async_db parameter is Optional[Any] to avoid circular imports with AsyncDatabaseService

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Advisory lock coordination ready for multi-instance deployments
- Plan 02 (graceful shutdown) will wire async_db into get_scheduler() via lifespan changes
- Existing scheduler behavior unchanged when running single-instance

## Self-Check: PASSED

All files exist, all commits verified, all content markers confirmed.

---
*Phase: 05-multi-instance-production-hardening*
*Completed: 2026-02-11*
