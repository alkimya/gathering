---
phase: 02-pipeline-execution-engine
plan: 02
subsystem: orchestration
tags: [pipeline, executor, dag-traversal, circuit-breaker, tenacity, retry, exponential-backoff, node-dispatch]

# Dependency graph
requires:
  - phase: 02-pipeline-execution-engine
    plan: 01
    provides: "PipelineDefinition, PipelineNode, PipelineEdge models; validate_pipeline_dag; get_execution_order; parse_pipeline_definition; 10 pipeline EventTypes"
  - phase: 01-auth-security-foundation
    provides: "DatabaseService, safe_update_builder"
provides:
  - "PipelineExecutor class with topological DAG execution, output passing, event emission"
  - "dispatch_node() with handlers for trigger, agent, condition, action, parallel, delay"
  - "CircuitBreaker class with CLOSED/OPEN/HALF_OPEN state machine"
  - "NodeExecutionError and NodeConfigError exception types"
  - "run_pipeline endpoint wired to real PipelineExecutor (replaces stub)"
  - "validate_pipeline endpoint for DAG validation without execution"
affects: [02-03-PLAN]

# Tech tracking
tech-stack:
  added: [tenacity]
  patterns: [retry with exponential backoff via tenacity, circuit breaker per node, condition false-branch skip propagation, handler dispatch table]

key-files:
  created:
    - gathering/orchestration/pipeline/executor.py
    - gathering/orchestration/pipeline/nodes.py
    - gathering/orchestration/pipeline/circuit_breaker.py
  modified:
    - gathering/orchestration/pipeline/__init__.py
    - gathering/api/routers/pipelines.py

key-decisions:
  - "tenacity retry wraps node execution with configurable exponential backoff and max retries"
  - "CircuitBreaker is per-node, threshold configurable via node config or pipeline defaults"
  - "Agent nodes degrade gracefully when no agent_registry -- return simulated result instead of failing"
  - "Condition evaluation avoids eval() -- supports 'true'/'false' literals and 'input.<key>' safe lookups"
  - "Event emission and node run persistence wrapped in try/except to never block pipeline execution"
  - "Condition false-branch propagation uses skip_sources set including the condition node itself"

patterns-established:
  - "Handler dispatch table: _NODE_HANDLERS dict maps node type string to async handler function"
  - "Circuit breaker per resource: create CircuitBreaker instance per node, check before execution, record success/failure after"
  - "Graceful degradation pattern: agent nodes return simulated results when registry unavailable"
  - "Skip propagation: condition false marks downstream-only successors via BFS with skip_sources"

# Metrics
duration: 7min
completed: 2026-02-10
---

# Phase 2 Plan 2: Pipeline Execution Engine Summary

**DAG executor with topological traversal, 6 node-type dispatchers, tenacity retry with exponential backoff, per-node circuit breakers, and real API execution replacing the stub**

## Performance

- **Duration:** 7 min
- **Started:** 2026-02-10T20:21:21Z
- **Completed:** 2026-02-10T20:28:49Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- PipelineExecutor traverses DAG in topological order, dispatching each node and passing outputs to downstream nodes
- 6 node-type handlers: trigger (passthrough), agent (LLM dispatch with graceful degradation), condition (safe eval), action (log + return), parallel (topology fan-out), delay (asyncio.sleep)
- CircuitBreaker per node with CLOSED/OPEN/HALF_OPEN state machine and configurable failure threshold
- tenacity retry wraps node execution with exponential backoff, retrying only NodeExecutionError (not config errors)
- Condition false-branch correctly skips all downstream-only successors via BFS propagation
- API run_pipeline endpoint replaced: parses definition, creates executor, runs with timeout, records real results
- New /validate endpoint checks DAG structure without executing

## Task Commits

Each task was committed atomically:

1. **Task 1: Create pipeline executor, node dispatchers, and circuit breaker** - `317fa9a` (feat)
2. **Task 2: Wire pipeline executor into API router** - `dd4c9e2` (feat)
3. **Fix: Condition false-branch skip propagation** - `4e6f59f` (fix)

## Files Created/Modified
- `gathering/orchestration/pipeline/executor.py` - PipelineExecutor: DAG traversal, retry, circuit breaker, event emission, node run persistence
- `gathering/orchestration/pipeline/nodes.py` - dispatch_node() with 6 type handlers, NodeExecutionError, NodeConfigError
- `gathering/orchestration/pipeline/circuit_breaker.py` - CircuitBreaker: CLOSED/OPEN/HALF_OPEN state machine
- `gathering/orchestration/pipeline/__init__.py` - Updated exports: PipelineExecutor, CircuitBreaker, CircuitState, dispatch_node, error types
- `gathering/api/routers/pipelines.py` - run_pipeline uses real executor, new /validate endpoint, cleaned up inline imports

## Decisions Made
- tenacity retry wraps node execution with configurable exponential backoff (multiplier=1.0, max=60s by default) -- only retries NodeExecutionError, not NodeConfigError
- CircuitBreaker failure_threshold is per-node, configurable via node config dict or defaults to 5
- Agent nodes return simulated results when no agent_registry is available -- graceful degradation over hard failure
- Condition evaluation does NOT use eval() -- supports "true"/"false" literals and "input.<key>" safe lookups against predecessor outputs
- Event emission and node run persistence are wrapped in try/except so they never block pipeline execution
- Pipeline timeout uses asyncio.wait_for with configurable timeout_seconds from pipeline config

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed condition false-branch skip propagation**
- **Found during:** Task 2 verification testing
- **Issue:** Nodes downstream of a false condition were not being skipped because the skip check only verified if ALL predecessors were in `skipped_nodes`, but the condition node itself was not in `skipped_nodes` (it executed successfully). `_mark_downstream_skipped` correctly added downstream nodes to `skipped_nodes`, but the main loop check did not account for nodes already marked by downstream propagation.
- **Fix:** Added `node_id in skipped_nodes` check at step 7b so nodes marked by `_mark_downstream_skipped` are recognized. Also updated `_mark_downstream_skipped` to use a `skip_sources` set that includes the false condition node when evaluating successor eligibility.
- **Files modified:** gathering/orchestration/pipeline/executor.py
- **Verification:** Condition false-branch test passes -- downstream action node correctly skipped. True-branch still executes normally.
- **Committed in:** `4e6f59f`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential for correctness -- condition branching is a core feature of the execution engine.

## Issues Encountered

None beyond the deviation documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- PipelineExecutor ready for Plan 02-03 (testing and integration) to exercise
- All 6 node types implemented and verified
- Circuit breaker state machine complete and tested
- API endpoints wired: /validate and /run use real executor
- 118 existing tests continue to pass (1 pre-existing DB connection failure unrelated to changes)

## Self-Check: PASSED

- All 5 created/modified files verified on disk
- Commit 317fa9a (Task 1) verified in git log
- Commit dd4c9e2 (Task 2) verified in git log
- Commit 4e6f59f (Fix) verified in git log
- 118 existing tests pass (1 pre-existing DB connection failure unrelated to changes)

---
*Phase: 02-pipeline-execution-engine*
*Completed: 2026-02-10*
