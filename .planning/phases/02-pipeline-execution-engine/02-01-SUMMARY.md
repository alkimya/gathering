---
phase: 02-pipeline-execution-engine
plan: 01
subsystem: orchestration
tags: [pydantic, graphlib, dag-validation, pipeline, topological-sort, postgresql]

# Dependency graph
requires:
  - phase: 01-auth-security-foundation
    provides: "DatabaseService, safe_update_builder, pycopg DB layer"
provides:
  - "PipelineDefinition, PipelineNode, PipelineEdge Pydantic models"
  - "validate_pipeline_dag() with cycle detection via graphlib.TopologicalSorter"
  - "get_execution_order() returning topological node ordering"
  - "parse_pipeline_definition() for raw JSONB-to-model conversion"
  - "10 pipeline EventType entries (5 run-level, 5 node-level)"
  - "pipeline_node_runs DB table for per-node execution tracking"
  - "Execution config columns on pipelines table (timeout, retry settings)"
affects: [02-02-PLAN, 02-03-PLAN]

# Tech tracking
tech-stack:
  added: [graphlib (stdlib)]
  patterns: [DAG validation before execution, TopologicalSorter for cycle detection, Pydantic model aliases for JSON reserved words]

key-files:
  created:
    - gathering/orchestration/pipeline/__init__.py
    - gathering/orchestration/pipeline/models.py
    - gathering/orchestration/pipeline/validator.py
    - gathering/db/migrations/007_pipeline_execution.sql
  modified:
    - gathering/orchestration/events.py

key-decisions:
  - "graphlib.TopologicalSorter (stdlib) for cycle detection -- zero-dependency, CycleError provides cycle path info"
  - "PipelineEdge uses Field(alias='from') with populate_by_name=True to handle JSON 'from'/'to' reserved words"
  - "Node config stored as generic dict on PipelineNode; type-specific config models available for targeted validation"
  - "Orphan nodes logged as warnings, not validation errors -- allows standalone trigger nodes"

patterns-established:
  - "Pipeline validation before execution: always call validate_pipeline_dag() before any pipeline runs"
  - "Pydantic alias pattern: use Field(alias=...) + ConfigDict(populate_by_name=True) when JSON keys are Python reserved words"

# Metrics
duration: 4min
completed: 2026-02-10
---

# Phase 2 Plan 1: Pipeline Validation + Data Models Summary

**Pipeline DAG validation with graphlib.TopologicalSorter, Pydantic models for pipeline/node/edge definition, 10 pipeline EventTypes, and pipeline_node_runs DB migration**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-10T20:15:11Z
- **Completed:** 2026-02-10T20:19:01Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Pipeline Pydantic models (PipelineDefinition, PipelineNode, PipelineEdge, NodeExecutionResult) parse existing JSONB node/edge format
- DAG validator rejects cycles (graphlib.CycleError), dangling edges, invalid node types, and missing required config
- get_execution_order returns topological sort for pipeline executor consumption
- parse_pipeline_definition bridges raw JSONB dicts to validated Pydantic models
- 10 pipeline EventType entries added (5 run-level: started/completed/failed/cancelled/timeout; 5 node-level: started/completed/failed/skipped/retrying)
- Migration 007 creates pipeline_node_runs table and adds execution config columns to pipelines table

## Task Commits

Each task was committed atomically:

1. **Task 1: Create pipeline package with Pydantic models and DAG validator** - `44a4828` (feat)
2. **Task 2: Add pipeline EventTypes and create DB migration** - `49b046d` (feat)

## Files Created/Modified
- `gathering/orchestration/pipeline/__init__.py` - Package exports for all pipeline models and validators
- `gathering/orchestration/pipeline/models.py` - Pydantic models: PipelineDefinition, PipelineNode, PipelineEdge, NodeExecutionResult, typed config models
- `gathering/orchestration/pipeline/validator.py` - validate_pipeline_dag, get_execution_order, parse_pipeline_definition using graphlib.TopologicalSorter
- `gathering/orchestration/events.py` - Added 10 pipeline-specific EventType enum entries
- `gathering/db/migrations/007_pipeline_execution.sql` - Execution config columns, timeout status, pipeline_node_runs table

## Decisions Made
- graphlib.TopologicalSorter (stdlib) chosen for cycle detection -- zero external dependencies, CycleError reports full cycle path
- PipelineEdge uses Field(alias="from") with ConfigDict(populate_by_name=True) to handle JSON "from"/"to" reserved words in Python
- Node config stored as generic dict on PipelineNode rather than discriminated union -- type-specific config models (AgentNodeConfig, etc.) available separately for targeted validation in validator
- Orphan nodes (no edges, not trigger type) generate log warnings, not validation errors -- allows standalone trigger nodes without false positives

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Pipeline models and validator ready for executor (Plan 02-02) to import
- EventTypes ready for executor to emit pipeline run/node lifecycle events
- Migration 007 ready to run against database for node-level tracking
- get_execution_order provides topological ordering the executor will use for node traversal

## Self-Check: PASSED

- All 5 created/modified files verified on disk
- Commit 44a4828 (Task 1) verified in git log
- Commit 49b046d (Task 2) verified in git log
- 118 existing tests pass (1 pre-existing DB connection failure unrelated to changes)

---
*Phase: 02-pipeline-execution-engine*
*Completed: 2026-02-10*
