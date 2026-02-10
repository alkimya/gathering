---
phase: 03-schedule-execution-tool-hardening
plan: 02
subsystem: api, core
tags: [jsonschema, validation, async, tool-registry, skill-registry, workspace]

# Dependency graph
requires:
  - phase: 01-auth-security-foundation
    provides: "validate_file_path, safe_update_builder, auth middleware"
provides:
  - "JSON Schema validation on ToolRegistry.execute() and SkillRegistry.execute_tool()"
  - "Async execution path via ToolRegistry.execute_async() and SkillRegistry.execute_tool_async()"
  - "BaseSkill.execute_async() default runs sync in executor (non-blocking)"
  - "Workspace path resolution from DB (repository_path) or WORKSPACE_ROOT env var"
affects: [04-observability-polish-deploy, agents, pipelines]

# Tech tracking
tech-stack:
  added: [jsonschema]
  patterns: [guarded-import-with-graceful-degradation, layered-resolution-with-cache, async-sync-dispatch]

key-files:
  created: []
  modified:
    - gathering/core/tool_registry.py
    - gathering/skills/registry.py
    - gathering/skills/base.py
    - gathering/api/routers/workspace.py
    - requirements.txt

key-decisions:
  - "jsonschema import guarded with try/except ImportError so modules load even without it installed"
  - "ToolRegistry.execute() raises RuntimeError for async tools instead of silently blocking"
  - "Workspace path uses project.projects.repository_path (actual DB column) not a new workspace_path column"
  - "Workspace cache uses monotonic clock TTL dict (5min) instead of functools.lru_cache"

patterns-established:
  - "Guarded import: try/import jsonschema + _HAS_JSONSCHEMA flag for optional validation"
  - "Layered resolution: DB -> env var -> fallback with warning for configuration lookup"
  - "Async/sync dispatch: async tools awaited, sync tools wrapped in run_in_executor"

# Metrics
duration: 4min
completed: 2026-02-10
---

# Phase 3 Plan 2: Tool Registry Hardening Summary

**JSON Schema validation on both ToolRegistry and SkillRegistry with async execution paths and workspace path resolution from DB/WORKSPACE_ROOT**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-10T21:13:26Z
- **Completed:** 2026-02-10T21:17:22Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- ToolRegistry.execute() validates kwargs against tool.parameters JSON Schema before calling tool function; rejects with descriptive ValueError including parameter path
- ToolRegistry.execute_async() awaits async tools directly, wraps sync tools in run_in_executor; sync execute() rejects async tools with RuntimeError
- SkillRegistry.execute_tool() validates tool_input against skill's input_schema before execution; returns SkillResponse with validation_error on failure
- SkillRegistry.execute_tool_async() added for async skill execution with same validation
- BaseSkill.execute_async() default now runs sync execute() in thread executor instead of blocking event loop
- Workspace get_project_path() resolves from DB (repository_path) or WORKSPACE_ROOT, with cwd only as last-resort fallback with deprecation warning

## Task Commits

Each task was committed atomically:

1. **Task 1: Add JSON Schema validation and async execution to ToolRegistry and SkillRegistry** - `d0670cf` (feat)
2. **Task 2: Fix workspace path resolution** - `86cc477` (feat)

## Files Created/Modified
- `gathering/core/tool_registry.py` - Added _validate_params(), execute_async(), jsonschema validation in execute()
- `gathering/skills/registry.py` - Added _validate_tool_input(), _find_skill_for_tool(), execute_tool_async(), validation in execute_tool()
- `gathering/skills/base.py` - Updated execute_async() to use run_in_executor instead of direct sync call
- `gathering/api/routers/workspace.py` - Replaced get_project_path() with layered DB/env/cwd resolution with TTL cache
- `requirements.txt` - Added jsonschema>=4.20,<5.0

## Decisions Made
- jsonschema import guarded with try/except ImportError so modules load even without it installed -- graceful degradation over hard dependency
- ToolRegistry.execute() raises RuntimeError for async tools rather than silently blocking the event loop
- Workspace path uses existing `project.projects.repository_path` column (actual schema) instead of adding a new column -- no migration needed
- Workspace cache uses simple dict with monotonic clock TTL (5min) since functools.lru_cache does not support TTL expiry

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Tool registries now validate parameters before execution, ready for pipeline integration
- Async execution paths available for event-loop-aware callers
- Workspace API ready for multi-project deployment with WORKSPACE_ROOT configuration

## Self-Check: PASSED

All files verified present on disk. Both task commits (d0670cf, 86cc477) verified in git log.

---
*Phase: 03-schedule-execution-tool-hardening*
*Completed: 2026-02-10*
