# Phase 2: Pipeline Execution Engine - Research

**Researched:** 2026-02-10
**Domain:** DAG-based pipeline execution, topological traversal, retry/backoff, circuit breakers, async cancellation/timeout (Python/asyncio/PostgreSQL)
**Confidence:** HIGH

## Summary

Phase 2 replaces the stubbed pipeline execution with a real DAG-based execution engine. The current codebase already has pipeline CRUD (API router at `gathering/api/routers/pipelines.py`, skill at `gathering/skills/gathering/pipelines.py`) with database tables (`circle.pipelines`, `circle.pipeline_runs`) storing nodes and edges as JSONB, but the actual execution is a no-op -- the API endpoint at line 419 in `pipelines.py` contains `# TODO: Actually execute the pipeline nodes (async task)` and simply marks each node as "executed" without doing anything. The node types already defined in the schema are: `trigger`, `agent`, `condition`, `action`, `parallel`, and `delay`.

The key insight from codebase analysis is that this phase is a **build** phase, not a swap phase. Unlike Phase 1 (which replaced in-memory stores with DB), Phase 2 must create new modules: a DAG validator, a pipeline executor, per-node retry/circuit-breaker logic, and cancellation/timeout infrastructure. However, the project already has substantial patterns to build on: `BackgroundTaskRunner` in `gathering/orchestration/background.py` provides a step-based execution loop with timeout, cancellation (`request_stop()`), and event emission; the `EventBus` in `gathering/orchestration/events.py` supports task lifecycle events; and the `AgentHandle`/`AgentWrapper` pattern provides the agent execution interface. The DB layer (`DatabaseService` via pycopg) and the `safe_update_builder` pattern from Phase 1 are ready for use.

Python's stdlib `graphlib.TopologicalSorter` (Python 3.9+, project requires 3.11+) provides DAG traversal with automatic cycle detection via `CycleError`, eliminating the need for any external graph library. For retry with exponential backoff, `tenacity` is declared in `pyproject.toml` (^8.2) but not yet installed -- it must be installed and is the standard Python solution. Circuit breaker functionality has no standard Python library with broad adoption, but is simple enough (~50 lines) to implement as a small class that tracks failure counts and open/half-open/closed state transitions.

**Primary recommendation:** Build in three sequential plans: (1) DAG validation + pipeline executor core (topological traversal, node dispatch, output passing), (2) retry/backoff + circuit breaker per node, (3) cancellation + timeout enforcement + comprehensive tests.

## Standard Stack

### Core (Already Available)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| graphlib | stdlib (Python 3.11+) | `TopologicalSorter` for DAG traversal + `CycleError` for cycle detection | Zero dependencies, built into Python, exact match for requirements FEAT-01 and FEAT-02 |
| asyncio | stdlib | Task creation, cancellation (`Task.cancel()`), timeout (`asyncio.wait_for()`, `asyncio.timeout()`) | Native Python async, already used throughout the codebase |
| pydantic | ^2.0 | Node/edge schema validation | Already used for all API schemas in the project |

### New Dependencies (To Install)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tenacity | ^8.2 | Retry with exponential backoff per node | Already declared in pyproject.toml but not installed. Use for per-node retry logic with configurable max attempts, exponential wait, and custom retry conditions. |

### Build Internally (Do Not Import External)
| Component | Why Internal | Complexity |
|-----------|-------------|------------|
| Circuit breaker | No mature, lightweight Python circuit breaker library with broad adoption. `pybreaker` exists but is unmaintained (last release 2021). The pattern is ~50 lines: track failure count, transition between CLOSED/OPEN/HALF_OPEN states, time-based recovery. | LOW |
| Pipeline executor | Project-specific: must integrate with existing `EventBus`, `DatabaseService`, node type dispatch, and JSONB storage format. | MEDIUM |
| Node type dispatchers | Each node type (agent, condition, action, etc.) requires project-specific logic tied to `AgentHandle`/`AgentWrapper` and skill execution. | MEDIUM |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| graphlib.TopologicalSorter | networkx | networkx is overkill -- massive library for a single topological sort. graphlib is stdlib and purpose-built. |
| tenacity | Custom retry loop | tenacity handles edge cases (jitter, retry conditions, callback hooks) that would take 200+ lines to replicate. Already a declared dependency. |
| Internal circuit breaker | pybreaker | pybreaker is unmaintained (last commit 2021), adds external dependency for ~50 lines of code. Internal is simpler and testable. |
| asyncio.TaskGroup (3.11+) | asyncio.gather | TaskGroup provides structured concurrency with proper cancellation propagation. Available since Python 3.11 which is the project minimum. Prefer for parallel node execution. |

**Installation:**
```bash
pip install "tenacity>=8.2,<9.0"
```

## Architecture Patterns

### Recommended Project Structure

```
gathering/
  orchestration/
    pipeline/                  # NEW: Pipeline execution package
      __init__.py              # Exports: PipelineExecutor, PipelineValidator, etc.
      validator.py             # DAG validation, cycle detection, node schema checks
      executor.py              # Core execution engine: topological traversal, node dispatch
      nodes.py                 # Node type dispatchers: agent, condition, action, etc.
      circuit_breaker.py       # CircuitBreaker class (CLOSED/OPEN/HALF_OPEN)
      models.py                # Pydantic models: PipelineDefinition, NodeConfig, etc.
    events.py                  # EXTEND: Add pipeline-specific EventTypes
    background.py              # EXISTING: Reference pattern for execution loop
  api/routers/
    pipelines.py               # MODIFY: Wire run endpoint to real executor
tests/
  test_pipeline_execution.py   # NEW: Comprehensive pipeline execution tests
  test_pipeline_validation.py  # NEW: Cycle detection, schema validation tests
```

### Pattern 1: DAG Validation with graphlib

**What:** Validate pipeline graph structure before execution -- reject cycles, validate node types, verify edge connectivity.
**When to use:** Before any pipeline execution starts (FEAT-02).

```python
# Source: Python stdlib graphlib + codebase analysis of pipeline JSONB structure

import graphlib
from typing import Any

def validate_pipeline_dag(nodes: list[dict], edges: list[dict]) -> list[str]:
    """Validate pipeline is a valid DAG. Returns list of errors (empty = valid).

    Validates:
    1. No cycles (graphlib.CycleError)
    2. All edge endpoints reference existing nodes
    3. At least one node exists
    4. Node types are valid
    5. All nodes are reachable from a root (no orphans)
    """
    errors = []

    if not nodes:
        errors.append("Pipeline must have at least one node")
        return errors

    node_ids = {n["id"] for n in nodes}
    valid_types = {"trigger", "agent", "condition", "action", "parallel", "delay"}

    # Validate node types
    for node in nodes:
        if node.get("type") not in valid_types:
            errors.append(f"Node '{node['id']}' has invalid type: {node.get('type')}")

    # Validate edge endpoints
    for edge in edges:
        if edge.get("from") not in node_ids:
            errors.append(f"Edge '{edge['id']}' references unknown source: {edge['from']}")
        if edge.get("to") not in node_ids:
            errors.append(f"Edge '{edge['id']}' references unknown target: {edge['to']}")

    if errors:
        return errors

    # Build dependency graph: node -> set of predecessors
    graph: dict[str, set[str]] = {n["id"]: set() for n in nodes}
    for edge in edges:
        graph[edge["to"]].add(edge["from"])

    # Check for cycles using TopologicalSorter
    try:
        ts = graphlib.TopologicalSorter(graph)
        list(ts.static_order())  # Forces full traversal, raises CycleError
    except graphlib.CycleError as e:
        cycle_nodes = e.args[1] if len(e.args) > 1 else "unknown"
        errors.append(f"Pipeline contains a cycle: {cycle_nodes}")

    return errors
```

### Pattern 2: Topological Execution with Output Passing

**What:** Execute nodes in topological order, passing outputs from predecessors to successors.
**When to use:** Core pipeline execution loop (FEAT-01).

```python
# Source: graphlib.TopologicalSorter + BackgroundTaskRunner pattern from orchestration/background.py

import graphlib
import asyncio
from datetime import datetime, timezone

class PipelineExecutor:
    """Execute a validated pipeline DAG."""

    def __init__(self, pipeline_id: int, nodes: list, edges: list,
                 db: DatabaseService, event_bus: EventBus):
        self.pipeline_id = pipeline_id
        self.nodes = {n["id"]: n for n in nodes}
        self.edges = edges
        self.db = db
        self.event_bus = event_bus
        self._cancel_requested = False
        self._node_outputs: dict[str, Any] = {}  # node_id -> output

    def request_cancel(self):
        self._cancel_requested = True

    async def execute(self, run_id: int, trigger_data: dict = None) -> dict:
        """Execute the pipeline, returning execution result."""
        # Build dependency graph
        graph = {nid: set() for nid in self.nodes}
        successors = {nid: [] for nid in self.nodes}
        for edge in self.edges:
            graph[edge["to"]].add(edge["from"])
            successors[edge["from"]].append(edge["to"])

        ts = graphlib.TopologicalSorter(graph)
        ts.prepare()

        # Inject trigger data as output of trigger nodes
        for nid, node in self.nodes.items():
            if node["type"] == "trigger":
                self._node_outputs[nid] = trigger_data or {}

        while ts.is_active():
            if self._cancel_requested:
                return {"status": "cancelled"}

            # Get ready nodes (all predecessors complete)
            ready = ts.get_ready()

            # Execute ready nodes (potentially in parallel for independent nodes)
            for node_id in ready:
                if self._cancel_requested:
                    return {"status": "cancelled"}

                node = self.nodes[node_id]
                # Gather inputs from predecessor outputs
                predecessors = graph[node_id]
                inputs = {pid: self._node_outputs.get(pid) for pid in predecessors}

                # Execute node based on type
                output = await self._execute_node(node, inputs, run_id)
                self._node_outputs[node_id] = output

                # For condition nodes, evaluate and skip branches if needed
                if node["type"] == "condition" and not output.get("result", True):
                    # Skip downstream nodes in the false branch
                    pass

                ts.done(node_id)

        return {"status": "completed", "outputs": self._node_outputs}
```

### Pattern 3: Per-Node Retry with Exponential Backoff (tenacity)

**What:** Wrap individual node execution with configurable retry using tenacity.
**When to use:** FEAT-03 -- per-node retry with backoff.

```python
# Source: tenacity docs + pyproject.toml dependency declaration

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryCallState,
)

async def execute_node_with_retry(
    node: dict,
    inputs: dict,
    max_retries: int = 3,
    backoff_base: float = 1.0,
    backoff_max: float = 60.0,
) -> dict:
    """Execute a node with exponential backoff retry."""

    @retry(
        stop=stop_after_attempt(max_retries),
        wait=wait_exponential(multiplier=backoff_base, max=backoff_max),
        retry=retry_if_exception_type(NodeExecutionError),
        reraise=True,
    )
    async def _execute():
        return await dispatch_node(node, inputs)

    return await _execute()
```

### Pattern 4: Circuit Breaker

**What:** Track node failures and fail-fast when a node exceeds its failure threshold.
**When to use:** FEAT-03 -- circuit breaker after retry exhaustion.

```python
# Source: standard circuit breaker pattern (Nygard, "Release It!")

import time
from enum import Enum
from dataclasses import dataclass, field

class CircuitState(Enum):
    CLOSED = "closed"        # Normal operation
    OPEN = "open"            # Failing, reject immediately
    HALF_OPEN = "half_open"  # Testing if recovery happened

@dataclass
class CircuitBreaker:
    """Per-node circuit breaker.

    - CLOSED: requests pass through. Failures increment counter.
    - OPEN: requests fail immediately. After recovery_timeout, transition to HALF_OPEN.
    - HALF_OPEN: one test request allowed. Success -> CLOSED, Failure -> OPEN.
    """
    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: float = 0.0
    success_count: int = 0

    def can_execute(self) -> bool:
        """Check if execution should proceed."""
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.monotonic() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        if self.state == CircuitState.HALF_OPEN:
            return True
        return False

    def record_success(self) -> None:
        """Record a successful execution."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Record a failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.monotonic()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN
```

### Pattern 5: Cancellation and Timeout with asyncio

**What:** Enforce per-pipeline timeout and support mid-execution cancellation.
**When to use:** FEAT-04 -- pipeline cancellation and timeout.

```python
# Source: Python asyncio stdlib + BackgroundTaskRunner pattern

import asyncio

class PipelineRunManager:
    """Manages running pipeline executions with cancellation and timeout."""

    def __init__(self):
        self._running: dict[int, asyncio.Task] = {}  # run_id -> asyncio.Task
        self._executors: dict[int, PipelineExecutor] = {}  # run_id -> executor

    async def start_run(
        self,
        run_id: int,
        executor: PipelineExecutor,
        timeout_seconds: int = 3600,
    ) -> None:
        """Start a pipeline run with timeout."""
        self._executors[run_id] = executor

        async def _run_with_timeout():
            try:
                async with asyncio.timeout(timeout_seconds):
                    return await executor.execute(run_id)
            except TimeoutError:
                # Update run status to timeout
                return {"status": "timeout", "error": f"Pipeline exceeded {timeout_seconds}s timeout"}
            finally:
                self._running.pop(run_id, None)
                self._executors.pop(run_id, None)

        task = asyncio.create_task(_run_with_timeout())
        self._running[run_id] = task

    async def cancel_run(self, run_id: int) -> bool:
        """Cancel a running pipeline."""
        executor = self._executors.get(run_id)
        if executor:
            executor.request_cancel()  # Cooperative cancellation

        task = self._running.get(run_id)
        if task and not task.done():
            task.cancel()  # Force cancellation
            return True
        return False
```

### Pattern 6: Node Type Dispatching

**What:** Execute different logic based on node type (agent, condition, action, etc.).
**When to use:** Inside the executor, for each node.

```python
# Source: codebase analysis of PipelineNode types + AgentHandle/AgentWrapper patterns

async def dispatch_node(node: dict, inputs: dict) -> dict:
    """Dispatch execution to the appropriate node handler."""
    node_type = node["type"]
    config = node.get("config", {})

    if node_type == "trigger":
        # Trigger nodes just pass through their data
        return inputs

    elif node_type == "agent":
        # Run an agent task
        agent_id = config.get("agent_id")
        task = config.get("task", "")
        # Use AgentRegistry to get the agent, execute task
        agent = get_agent_registry().get(int(agent_id))
        if not agent:
            raise NodeExecutionError(f"Agent {agent_id} not found")
        # Format inputs as context for the agent
        context = format_inputs_for_agent(inputs)
        result = await agent.process_message_async(f"{task}\n\nContext:\n{context}")
        return {"result": result, "agent_id": agent_id}

    elif node_type == "condition":
        # Evaluate a condition
        condition_expr = config.get("condition", "true")
        result = evaluate_condition(condition_expr, inputs)
        return {"result": result}

    elif node_type == "action":
        # Execute a specific action (notify, call API, etc.)
        action_type = config.get("action")
        return await execute_action(action_type, config, inputs)

    elif node_type == "parallel":
        # Fan out to downstream nodes (handled by executor)
        return inputs

    elif node_type == "delay":
        # Wait for configured duration
        delay_seconds = config.get("seconds", 0)
        await asyncio.sleep(delay_seconds)
        return inputs

    else:
        raise NodeExecutionError(f"Unknown node type: {node_type}")
```

### Existing Database Schema (Already Exists)

The pipeline tables already exist via `_ensure_table_exists()` in `gathering/api/routers/pipelines.py`:

```sql
-- circle.pipelines (exists)
CREATE TABLE IF NOT EXISTS circle.pipelines (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('active', 'paused', 'draft')),
    nodes JSONB DEFAULT '[]'::jsonb,      -- Array of node objects
    edges JSONB DEFAULT '[]'::jsonb,      -- Array of edge objects
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_run TIMESTAMP WITH TIME ZONE,
    run_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0
);

-- circle.pipeline_runs (exists)
CREATE TABLE IF NOT EXISTS circle.pipeline_runs (
    id SERIAL PRIMARY KEY,
    pipeline_id INTEGER NOT NULL REFERENCES circle.pipelines(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    current_node VARCHAR(100),
    logs JSONB DEFAULT '[]'::jsonb,
    trigger_data JSONB DEFAULT '{}'::jsonb,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### Schema Extensions Needed

The existing schema needs additions for per-node execution tracking, retry/circuit-breaker state, and timeout configuration:

```sql
-- New migration: 007_pipeline_execution.sql

-- Add execution config to pipelines
ALTER TABLE circle.pipelines
    ADD COLUMN IF NOT EXISTS timeout_seconds INTEGER DEFAULT 3600,
    ADD COLUMN IF NOT EXISTS max_retries_per_node INTEGER DEFAULT 3,
    ADD COLUMN IF NOT EXISTS retry_backoff_base FLOAT DEFAULT 1.0,
    ADD COLUMN IF NOT EXISTS retry_backoff_max FLOAT DEFAULT 60.0;

-- Add timeout status to runs
ALTER TABLE circle.pipeline_runs
    DROP CONSTRAINT IF EXISTS pipeline_runs_status_check;
ALTER TABLE circle.pipeline_runs
    ADD CONSTRAINT pipeline_runs_status_check
    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled', 'timeout'));

-- Add duration_seconds to runs
ALTER TABLE circle.pipeline_runs
    ADD COLUMN IF NOT EXISTS duration_seconds INTEGER DEFAULT 0;

-- Per-node execution log (new table)
CREATE TABLE IF NOT EXISTS circle.pipeline_node_runs (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES circle.pipeline_runs(id) ON DELETE CASCADE,
    node_id VARCHAR(100) NOT NULL,
    node_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'skipped', 'cancelled')),
    input_data JSONB DEFAULT '{}'::jsonb,
    output_data JSONB DEFAULT '{}'::jsonb,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_ms INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_pipeline_node_runs_run_id
    ON circle.pipeline_node_runs(run_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_node_runs_node_id
    ON circle.pipeline_node_runs(run_id, node_id);
```

### Anti-Patterns to Avoid

- **Recursive DAG traversal:** Do NOT write a recursive DFS for execution order. Use `graphlib.TopologicalSorter` which handles the algorithm correctly, including parallel-ready node detection via `get_ready()`/`done()`.
- **Global circuit breaker state:** Circuit breakers must be PER-NODE within a run, not global. A failure in node A should not trip the breaker for node B. Store breakers in a dict keyed by node_id.
- **Cancellation via task.cancel() only:** `asyncio.Task.cancel()` is not cooperative -- it raises `CancelledError` at the next await. Always combine with a cooperative `_cancel_requested` flag checked between node executions, so cleanup can happen before the task is killed.
- **Blocking the event loop in node execution:** Agent node execution may involve LLM API calls. These MUST be async. The existing `AgentHandle.process_message` callback is already async. Never use synchronous LLM calls inside the pipeline executor.
- **Storing full node outputs in the runs table:** JSONB columns can grow large. Store summaries/metadata in `pipeline_node_runs`, not the full agent response text. Use truncation for logging.
- **Executing nodes without validation first:** Always validate the DAG (cycle check + schema validation) BEFORE starting execution. Never attempt to execute a pipeline that hasn't passed validation.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Topological sort | Custom DFS/BFS graph traversal | `graphlib.TopologicalSorter` (stdlib) | Handles cycles (CycleError), parallel-ready nodes (get_ready/done), edge cases |
| Cycle detection | Custom visited/recursion-stack algorithm | `graphlib.TopologicalSorter` + catch `CycleError` | Stdlib, battle-tested, reports the cycle path |
| Exponential backoff retry | Custom sleep loop with `2**n` | `tenacity` library | Handles jitter, retry conditions, callbacks, async, max time, composition |
| Async timeout | Manual `time.monotonic()` tracking | `asyncio.timeout()` (Python 3.11+) or `asyncio.wait_for()` | Context manager, proper cancellation propagation, exception handling |
| Schema validation for nodes | Custom type-checking code | Pydantic models with discriminated unions | Already the project pattern, handles validation errors with clear messages |

**Key insight:** The only custom component needed is the circuit breaker (~50 lines) and the execution engine itself (which must integrate with the project's specific node types, event bus, and database). Everything else has a stdlib or existing-dependency solution.

## Common Pitfalls

### Pitfall 1: graphlib.TopologicalSorter Static vs Iterative API
**What goes wrong:** Using `static_order()` returns nodes in topological order but prevents parallel execution. Using `prepare()/get_ready()/done()` enables parallelism but requires careful lifecycle management.
**Why it happens:** The two APIs serve different use cases. `static_order()` is simple but sequential. The iterative API allows executing independent nodes in parallel.
**How to avoid:** For Phase 2, start with `static_order()` (sequential execution) to get correctness first. Optimize to `prepare()/get_ready()/done()` only if parallel execution is needed (the `parallel` node type suggests it might be). Document the choice.
**Warning signs:** Tests pass with 3 nodes but fail with 10+ nodes due to ordering assumptions.

### Pitfall 2: Condition Nodes Don't Skip Downstream Branches
**What goes wrong:** A condition node evaluates to `false` but its downstream nodes still execute, because the topological sort includes ALL nodes regardless of runtime conditions.
**Why it happens:** `graphlib.TopologicalSorter` computes the full traversal statically. It doesn't know about runtime branch decisions.
**How to avoid:** After a condition evaluates to `false`, track "skipped" nodes. When a node is ready to execute, check if ALL its predecessors were either completed or skipped-false. If any predecessor was on a false branch and was the ONLY path to this node, skip it too. Alternatively, use `ts.done(node_id)` to mark skipped nodes as done without executing them.
**Warning signs:** Nodes after a false condition still run. Downstream nodes after a false branch produce errors because their expected inputs are missing.

### Pitfall 3: Circuit Breaker State Leaks Between Runs
**What goes wrong:** A circuit breaker tripped in run #1 causes nodes to fail-fast in run #2 without retrying.
**Why it happens:** Circuit breakers are stored at the executor level and reused across runs.
**How to avoid:** Create fresh circuit breakers for each pipeline run. Do NOT persist circuit breaker state across runs. The breaker's purpose is to prevent cascading failures WITHIN a single run, not across runs.
**Warning signs:** A previously-failed pipeline always fails immediately on re-run without any retry attempts.

### Pitfall 4: Cancellation Leaves Orphan Tasks
**What goes wrong:** Cancelling a pipeline run leaves agent tasks or background processes running.
**Why it happens:** `asyncio.Task.cancel()` only cancels the task itself, not any sub-tasks or external processes it spawned.
**How to avoid:** Track all spawned sub-tasks in the executor. On cancellation, cancel each sub-task individually. Use `asyncio.TaskGroup` (Python 3.11+) which automatically cancels all child tasks when any task raises an exception.
**Warning signs:** After cancellation, the server still shows CPU usage from LLM calls. Agent conversations continue after the pipeline run is cancelled.

### Pitfall 5: Timeout Doesn't Update Database Status
**What goes wrong:** A pipeline times out at the asyncio level but the database still shows `status='running'`.
**Why it happens:** The timeout exception is caught but the database update in the `finally` block fails or is skipped.
**How to avoid:** Always wrap the execution in a try/finally that updates the database. Use a `finally` block that checks the actual outcome and writes the appropriate status. The existing `BackgroundTaskRunner._persist_task()` pattern does this correctly -- follow it.
**Warning signs:** `SELECT * FROM circle.pipeline_runs WHERE status = 'running'` returns runs that ended minutes ago.

### Pitfall 6: Two EventBus Implementations Confused
**What goes wrong:** Pipeline events go to the wrong EventBus instance.
**Why it happens:** The project has two EventBus implementations: `gathering/events/event_bus.py` (singleton, system-wide) and `gathering/orchestration/events.py` (instance-based, circle-scoped). They have the SAME class name `EventBus` but DIFFERENT APIs (the first uses `subscribe/publish`, the second uses `subscribe/emit`).
**How to avoid:** Pipeline execution should use `gathering/orchestration/events.py` (the circle-scoped one with `emit()`), consistent with how `BackgroundTaskRunner` and `Facilitator` emit events. Import explicitly: `from gathering.orchestration.events import EventBus, EventType`.
**Warning signs:** Events emitted by the pipeline executor never reach subscribers. Import errors or attribute errors (`publish` vs `emit`).

## Code Examples

Verified patterns from codebase analysis and stdlib documentation:

### graphlib.TopologicalSorter Usage
```python
# Source: Python 3.11 stdlib, verified locally

import graphlib

# Build graph: node -> set of predecessors
graph = {
    "D": {"B", "C"},
    "C": {"A"},
    "B": {"A"},
    "A": set(),
}

# Static order (sequential)
ts = graphlib.TopologicalSorter(graph)
order = list(ts.static_order())
# order = ['A', 'C', 'B', 'D'] or ['A', 'B', 'C', 'D'] (both valid)

# Cycle detection
try:
    cyclic_graph = {"A": {"B"}, "B": {"A"}}
    ts2 = graphlib.TopologicalSorter(cyclic_graph)
    list(ts2.static_order())
except graphlib.CycleError as e:
    # e.args[1] contains the cycle path: ['A', 'B', 'A']
    cycle_path = e.args[1]
```

### asyncio.timeout (Python 3.11+) for Pipeline Timeout
```python
# Source: Python 3.11 stdlib

import asyncio

async def run_with_timeout(coro, timeout_seconds: int):
    """Run coroutine with timeout, returning result or timeout status."""
    try:
        async with asyncio.timeout(timeout_seconds):
            return await coro
    except TimeoutError:
        return {"status": "timeout", "error": f"Exceeded {timeout_seconds}s"}
```

### Existing BackgroundTaskRunner Cancellation Pattern
```python
# Source: gathering/orchestration/background.py lines 183-209

# The existing pattern uses cooperative cancellation:
class BackgroundTaskRunner:
    def __init__(self, ...):
        self._stop_requested = False

    def request_stop(self):
        self._stop_requested = True

    async def run(self):
        while ...:
            if self._stop_requested:
                self.task.status = BackgroundTaskStatus.CANCELLED
                break
            # ... execute step ...
```

### Existing Event Emission Pattern
```python
# Source: gathering/orchestration/background.py lines 538-546

# Pipeline executor should emit events using this exact pattern:
async def _emit_event(self, event_type: EventType, data: dict) -> None:
    if self.event_bus:
        await self.event_bus.emit(
            event_type=event_type,
            data=data,
            source_agent_id=None,  # Pipeline-level, not agent-specific
        )
```

### Existing Pipeline Node JSONB Structure
```python
# Source: gathering/api/routers/pipelines.py PipelineNode model

# Nodes stored in circle.pipelines.nodes JSONB column:
{
    "id": "node-1",
    "type": "agent",  # trigger | agent | condition | action | parallel | delay
    "name": "Analyze Data",
    "config": {
        "agent_id": "1",
        "task": "Analyze the provided dataset and summarize findings"
    },
    "position": {"x": 100, "y": 200},
    "next": ["node-2"]
}

# Edges stored in circle.pipelines.edges JSONB column:
{
    "id": "edge-1",
    "from": "node-1",
    "to": "node-2",
    "condition": null  # Optional condition expression
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom DFS topological sort | `graphlib.TopologicalSorter` | Python 3.9 (stdlib) | Zero-dependency, cycle detection built-in |
| Manual sleep loops for retry | `tenacity` library | tenacity stable since 2020+ | Composable retry strategies, async support |
| Thread-based cancellation | `asyncio.Task.cancel()` + cooperative flags | Python 3.11+ with `asyncio.TaskGroup` | Structured concurrency, automatic child cancellation |
| `asyncio.wait_for()` for timeout | `asyncio.timeout()` context manager | Python 3.11 | Cleaner API, context manager pattern |

**Deprecated/outdated:**
- `asyncio.wait_for()`: Still works but `asyncio.timeout()` (Python 3.11+) is preferred for its context manager pattern.
- Manual retry loops: tenacity handles all the edge cases (jitter, max time, callback hooks).

## Open Questions

1. **Should parallel nodes execute concurrently?**
   - What we know: The pipeline schema supports a "parallel" node type. `graphlib.TopologicalSorter.get_ready()` returns all nodes whose predecessors are complete, enabling parallel execution.
   - What's unclear: Whether concurrent agent execution is safe given the current LLM provider implementations. Rate limits on LLM APIs could cause parallel nodes to fail.
   - Recommendation: Start with sequential execution (`static_order()`). Add parallel execution as a follow-up if needed. The architecture should support both -- use the iterative `prepare()/get_ready()/done()` API but process ready nodes one at a time initially.

2. **How should condition nodes control branching?**
   - What we know: Edges have an optional `condition` field. Condition nodes have a `config.condition` field.
   - What's unclear: The expression language for conditions. Is it a simple Python expression? A DSL? JSON path matching?
   - Recommendation: Start with simple truthiness checks on the condition node's output (`output.get("result", True)`). The condition expression in `config.condition` can be evaluated as a simple boolean expression against the inputs. Do NOT implement a full expression language -- keep it to basic comparisons initially.

3. **Should circuit breaker state be persisted to the database?**
   - What we know: Circuit breakers are per-node, per-run. Their purpose is to prevent cascading failures within a single execution.
   - What's unclear: Whether there's value in persisting breaker trip events for observability.
   - Recommendation: Keep circuit breaker state in-memory only (per executor instance). Log trip events to `pipeline_node_runs` as error entries. Do not create a separate persistence layer for breakers.

4. **How does the existing `_ensure_table_exists()` pattern interact with migrations?**
   - What we know: The pipeline router creates tables lazily with `CREATE TABLE IF NOT EXISTS`. The migration system uses numbered SQL files.
   - What's unclear: Whether the lazy creation conflicts with migrations.
   - Recommendation: Create a proper migration (`007_pipeline_execution.sql`) for the schema extensions. The existing `CREATE TABLE IF NOT EXISTS` is fine for backward compatibility, but new columns/constraints should go through migrations.

## Codebase Integration Points

### Files to Create
| File | Purpose |
|------|---------|
| `gathering/orchestration/pipeline/__init__.py` | Package exports |
| `gathering/orchestration/pipeline/validator.py` | DAG validation, cycle detection, schema checks |
| `gathering/orchestration/pipeline/executor.py` | Core execution engine |
| `gathering/orchestration/pipeline/nodes.py` | Node type dispatchers |
| `gathering/orchestration/pipeline/circuit_breaker.py` | Circuit breaker implementation |
| `gathering/orchestration/pipeline/models.py` | Pydantic models for pipeline config |
| `gathering/db/migrations/007_pipeline_execution.sql` | Schema extensions |
| `tests/test_pipeline_validation.py` | Validation tests |
| `tests/test_pipeline_execution.py` | Execution tests |

### Files to Modify
| File | Change |
|------|--------|
| `gathering/api/routers/pipelines.py` | Replace stubbed `run_pipeline()` with real executor call; add validation endpoint |
| `gathering/orchestration/events.py` | Add pipeline-specific EventTypes (PIPELINE_RUN_STARTED, NODE_STARTED, NODE_COMPLETED, etc.) |
| `gathering/orchestration/__init__.py` | Export new pipeline classes |

### Files NOT to Modify
| File | Reason |
|------|--------|
| `gathering/events/event_bus.py` | System-wide singleton EventBus -- DO NOT TOUCH (prior decision) |
| `gathering/orchestration/background.py` | Reference pattern only -- pipeline executor is a separate concern |
| `gathering/skills/gathering/pipelines.py` | Skill-level CRUD -- execution happens at orchestration level |

## Sources

### Primary (HIGH confidence)
- `gathering/api/routers/pipelines.py` -- Direct analysis of pipeline CRUD API, database schema, stubbed execution (TODO at line 419)
- `gathering/skills/gathering/pipelines.py` -- Direct analysis of pipeline skill with node type schema
- `gathering/orchestration/background.py` -- Direct analysis of BackgroundTaskRunner execution loop, cancellation, timeout patterns
- `gathering/orchestration/events.py` -- Direct analysis of EventBus and EventType definitions
- `gathering/orchestration/circle.py` -- Direct analysis of AgentHandle, task execution callbacks
- `gathering/api/dependencies.py` -- Direct analysis of DatabaseService, AgentRegistry patterns
- `gathering/db/models.py` -- Direct analysis of SQLAlchemy models and schema architecture
- `graphlib` (Python 3.11 stdlib) -- Verified locally: `TopologicalSorter`, `CycleError`, `static_order()`, `prepare()/get_ready()/done()`
- `pyproject.toml` -- Dependency declarations: tenacity ^8.2, Python ^3.11, pydantic ^2.0

### Secondary (MEDIUM confidence)
- Python asyncio documentation -- `asyncio.timeout()` (3.11+), `Task.cancel()`, `TaskGroup`
- tenacity PyPI/docs -- retry decorator API, exponential backoff, async support
- Phase 1 research (`01-RESEARCH.md`) -- Database patterns, safe_update_builder, exception handling policy

### Tertiary (LOW confidence)
- tenacity is declared in pyproject.toml but NOT currently installed -- needs `pip install` before use
- Parallel node execution safety with LLM rate limits -- needs validation during implementation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- graphlib verified locally with actual code execution. tenacity is a declared dependency. All patterns verified against codebase.
- Architecture: HIGH -- Based on direct analysis of every relevant file. Pipeline schema, execution stub, and integration points identified precisely.
- Pitfalls: HIGH -- Grounded in actual codebase analysis (two EventBus implementations, BackgroundTaskRunner patterns, JSONB structure). Dual EventBus warning from prior decisions.
- Circuit breaker: MEDIUM -- Pattern is well-known but implementation is internal (no external library verification). Kept simple intentionally.

**Research date:** 2026-02-10
**Valid until:** 2026-03-12 (30 days -- stable domain, stdlib-based approach)
