---
phase: 03-schedule-execution-tool-hardening
plan: 01
subsystem: orchestration
tags: [scheduler, dispatcher, pipeline, crash-recovery, asyncio, notifications, http]

# Dependency graph
requires:
  - phase: 02-pipeline-execution-engine
    provides: "PipelineExecutor, PipelineRunManager, node dispatch system, tenacity retry"
provides:
  - "ACTION_DISPATCHERS dispatch table for all 4 scheduler action types"
  - "_recover_missed_runs crash recovery with deduplication"
  - "Race condition fix in _check_and_execute_due_actions"
  - "Real action dispatch in pipeline action nodes via skills"
  - "ScheduledAction.action_type and action_config fields"
affects: [03-02, 03-03, pipeline-execution, schedule-management]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module-level dispatch table (ACTION_DISPATCHERS) for extensible action routing"
    - "Dispatcher function signature: async (action, context) -> dict"
    - "Crash recovery with deduplication via DB window query"
    - "Pre-task running_actions registration to prevent race conditions"

key-files:
  created: []
  modified:
    - "gathering/orchestration/scheduler.py"
    - "gathering/orchestration/pipeline/nodes.py"

key-decisions:
  - "Dispatcher functions are module-level async functions, not Scheduler methods, keeping dispatch table clean and testable"
  - "Lightweight local dispatch in pipeline action nodes instead of importing scheduler dispatchers to avoid tight coupling and block nested pipeline execution"
  - "action_config JSONB stores skill_config, tool_name, and tool_input for notification and API dispatchers"
  - "_insert_action SQL reconciled with actual DB schema columns (removed nonexistent goal, event_trigger, allow_concurrent, etc.)"
  - "goal field made optional with empty string default for backward compatibility with action_config-based actions"

patterns-established:
  - "Action type dispatch: ACTION_DISPATCHERS[action_type](action, context) pattern for extensible action routing"
  - "Crash recovery: query scheduled_action_runs for window deduplication before re-executing missed actions"
  - "Pipeline action nodes: direct skill instantiation for send_notification and call_api, NodeConfigError for unsupported types"

# Metrics
duration: 4min
completed: 2026-02-10
---

# Phase 03 Plan 01: Action Type Dispatchers and Crash Recovery Summary

**Scheduler dispatches all 4 action types via ACTION_DISPATCHERS table with crash recovery deduplication and pipeline action nodes executing real skills**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-10T21:13:30Z
- **Completed:** 2026-02-10T21:17:33Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- ACTION_DISPATCHERS dispatch table routing run_task, execute_pipeline, send_notification, and call_api to dedicated async handler functions
- Crash recovery via _recover_missed_runs that queries scheduled_action_runs for deduplication before re-executing missed actions
- Race condition fix: _running_actions.add() called synchronously before asyncio.create_task() in _check_and_execute_due_actions
- Pipeline action nodes now dispatch real work via NotificationsSkill and HTTPSkill instead of returning stub metadata
- ScheduledAction dataclass reconciled with DB schema: added action_type and action_config fields

## Task Commits

Each task was committed atomically:

1. **Task 1: Add action type dispatchers and reconcile ScheduledAction dataclass** - `0072e0e` (feat)
2. **Task 2: Upgrade pipeline action node to dispatch real actions** - `c01a2ed` (feat)

## Files Created/Modified
- `gathering/orchestration/scheduler.py` - Added ACTION_DISPATCHERS, 4 dispatcher functions, _recover_missed_runs, action_type/action_config fields, race condition fix, reconciled _insert_action SQL
- `gathering/orchestration/pipeline/nodes.py` - Replaced Phase 2 stub _handle_action with real skill dispatch via NotificationsSkill and HTTPSkill

## Decisions Made
- Dispatcher functions are module-level async functions (not Scheduler methods) to keep the dispatch table clean and independently testable
- Pipeline action nodes use lightweight local dispatch instead of importing scheduler's ACTION_DISPATCHERS, avoiding tight coupling and explicitly blocking nested pipeline execution
- action_config JSONB stores skill_config, tool_name, and tool_input keys for notification and API dispatchers
- _insert_action SQL reconciled with actual DB schema -- removed nonexistent columns (goal, event_trigger, allow_concurrent, max_steps, timeout_seconds, start_date, end_date, tags, metadata) that existed only in the old code
- goal field defaulted to empty string for backward compatibility since new action types use action_config instead

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Reconciled _insert_action SQL with actual DB schema**
- **Found during:** Task 1
- **Issue:** _insert_action referenced columns (goal, event_trigger, allow_concurrent, max_steps, timeout_seconds, start_date, end_date, tags, metadata) that do not exist in the actual DB schema (001_complete_schema.sql). Only action_type, action_config, and the standard columns exist.
- **Fix:** Rewrote _insert_action to only reference columns that exist in the DB schema
- **Files modified:** gathering/orchestration/scheduler.py
- **Verification:** Python import succeeds, SQL matches DB schema columns
- **Committed in:** 0072e0e (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential for correctness -- old SQL would fail at runtime against real DB.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Scheduler can now dispatch all 4 action types and recover from crashes
- Pipeline action nodes execute real skills instead of stubs
- Ready for Phase 03 Plan 02 (schedule management hardening / additional testing)
- All 41 existing pipeline tests pass with no regressions

## Self-Check: PASSED

- All modified files exist on disk
- Both task commits (0072e0e, c01a2ed) found in git history
- ACTION_DISPATCHERS contains 4 entries
- _recover_missed_runs method present (2 references)
- _running_actions.add race condition fix present (2 references)
- 41 existing pipeline tests pass with no regressions

---
*Phase: 03-schedule-execution-tool-hardening*
*Completed: 2026-02-10*
