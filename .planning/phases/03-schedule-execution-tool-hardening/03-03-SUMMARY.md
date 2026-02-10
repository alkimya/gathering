---
phase: 03-schedule-execution-tool-hardening
plan: 03
subsystem: testing
tags: [pytest, scheduler, crash-recovery, jsonschema, validation, async, tool-registry, skill-registry, workspace]

# Dependency graph
requires:
  - phase: 03-schedule-execution-tool-hardening
    plan: 01
    provides: "ACTION_DISPATCHERS dispatch table, _recover_missed_runs, race condition fix, ScheduledAction.action_type/action_config"
  - phase: 03-schedule-execution-tool-hardening
    plan: 02
    provides: "JSON Schema validation on ToolRegistry/SkillRegistry, execute_async(), workspace path resolution"
provides:
  - "13 scheduler dispatch and crash recovery tests proving all 4 action types dispatch correctly"
  - "15 tool validation, async execution, and workspace path tests proving FEAT-07, FEAT-08, RLBL-04"
  - "28 total passing tests covering all Phase 3 success criteria"
affects: [04-observability-polish-deploy]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "MockDBService pattern for scheduler tests (execute/execute_one with configurable returns)"
    - "Lazy import patching: patch at source module path, not consumer module, for deferred imports"
    - "MockSkill concrete subclass for SkillRegistry validation testing"
    - "monkeypatch + _project_path_cache.clear() for workspace path test isolation"

key-files:
  created:
    - "tests/test_scheduler_recovery.py"
    - "tests/test_tool_validation.py"
  modified: []

key-decisions:
  - "Lazy import patching required: dispatchers import PipelineExecutor, NotificationsSkill, HTTPSkill inside functions, so patches target source modules not scheduler module"
  - "MockSkill concrete subclass with configurable tools_def and execute_fn for SkillRegistry testing without loading real skill modules"
  - "Workspace path cache cleared in setup_method for test isolation since get_project_path uses module-level TTL cache"

patterns-established:
  - "Lazy import mocking: patch at gathering.skills.notifications.sender.NotificationsSkill (not scheduler module) for deferred imports"
  - "Race condition structural test: capture _running_actions state inside patched create_task to verify ordering"
  - "SkillRegistry test isolation: reset() in setup/teardown + patch get() to inject mock instances"

# Metrics
duration: 6min
completed: 2026-02-10
---

# Phase 03 Plan 03: Scheduler Recovery and Tool Validation Tests Summary

**28 tests covering scheduler dispatch for all 4 action types, crash recovery deduplication, race condition fix, JSON Schema validation, async tool execution, and workspace path resolution**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-10T21:40:00Z
- **Completed:** 2026-02-10T21:46:00Z
- **Tasks:** 2
- **Files created:** 2

## Accomplishments
- 13 scheduler tests proving all 4 ACTION_DISPATCHERS work, crash recovery executes missed runs and deduplicates completed/running ones, race condition fix verified structurally, and ScheduledAction supports action_type/action_config
- 15 tool validation tests proving JSON Schema validation rejects invalid params with descriptive errors, async tools are properly awaited, sync tools run in executor, concurrent async is parallel, SkillRegistry validates input_schema, and workspace path resolves from DB/env/cwd
- Full test suite passes with no regressions (1100 passed, 2 pre-existing failures unrelated to this plan)

## Task Commits

Each task was committed atomically:

1. **Task 1: Scheduler dispatch and crash recovery tests** - `d0f66a0` (test)
2. **Task 2: Tool validation, async execution, and workspace path tests** - `7aa45de` (test)

## Files Created/Modified
- `tests/test_scheduler_recovery.py` - 427 lines: 13 tests covering ACTION_DISPATCHERS (4 types), crash recovery (missed/completed/running/future), race condition fix, unknown type handling, and ScheduledAction dataclass fields
- `tests/test_tool_validation.py` - 395 lines: 15 tests covering JSON Schema validation (valid/invalid/missing/extra/nested), async/sync execution paths, concurrent parallelism, SkillRegistry input validation, and workspace path resolution (DB/env/cwd)

## Decisions Made
- Lazy import patching strategy: dispatcher functions use deferred imports (e.g. `from gathering.skills.notifications.sender import NotificationsSkill` inside the function body), so unittest.mock.patch must target the source module path, not `gathering.orchestration.scheduler.NotificationsSkill`
- MockSkill with injectable tools_def and execute_fn avoids loading real skill modules (which have heavy dependencies) while testing SkillRegistry validation behavior
- Workspace path cache (`_project_path_cache`) cleared in test setup_method since the module-level TTL dict would otherwise persist stale values between tests

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed mock patch targets for lazy imports**
- **Found during:** Task 1
- **Issue:** Plan specified `unittest.mock.patch` for `PipelineExecutor`, `NotificationsSkill`, `HTTPSkill` at the scheduler module level, but these are imported lazily inside dispatcher function bodies, causing `AttributeError: module does not have attribute`
- **Fix:** Patched at source module paths (`gathering.orchestration.pipeline.executor.PipelineExecutor`, `gathering.skills.notifications.sender.NotificationsSkill`, `gathering.skills.http.client.HTTPSkill`)
- **Files modified:** tests/test_scheduler_recovery.py
- **Committed in:** d0f66a0 (Task 1 commit)

**2. [Rule 1 - Bug] Fixed workspace path mock targets for lazy imports**
- **Found during:** Task 2
- **Issue:** Plan implied patching `get_database_service` on the workspace module, but it is imported lazily inside `_resolve_project_path` via `from gathering.api.dependencies import get_database_service`
- **Fix:** Patched at `gathering.api.dependencies.get_database_service` instead of `gathering.api.routers.workspace.get_database_service`
- **Files modified:** tests/test_tool_validation.py
- **Committed in:** 7aa45de (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs -- incorrect mock patch targets)
**Impact on plan:** Essential for test correctness. The lazy import pattern used throughout the codebase requires patching at source module, not consumer module.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All Phase 3 success criteria are now covered by passing tests
- Phase 3 (Schedule Execution & Tool Hardening) is complete: 3/3 plans done
- Ready to proceed to Phase 4 (Observability, Polish & Deploy)
- Full test suite at 1100+ passing tests with no regressions

## Self-Check: PASSED

- tests/test_scheduler_recovery.py exists on disk (427 lines)
- tests/test_tool_validation.py exists on disk (395 lines)
- Task 1 commit d0f66a0 found in git history
- Task 2 commit 7aa45de found in git history
- All 28 new tests pass
- No regressions in existing test suite

---
*Phase: 03-schedule-execution-tool-hardening*
*Completed: 2026-02-10*
