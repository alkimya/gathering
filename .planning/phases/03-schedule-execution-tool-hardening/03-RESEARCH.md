# Phase 3: Schedule Execution + Tool Hardening - Research

**Researched:** 2026-02-10
**Domain:** Async scheduler crash recovery, JSON Schema validation, tool registry hardening, workspace path resolution
**Confidence:** HIGH

## Summary

Phase 3 bridges two separate subsystems -- the scheduler (which dispatches actions on cron triggers) and the tool registry (which validates and executes tool functions). Both subsystems exist in the codebase as working scaffolds with explicit TODO markers for the missing functionality. The scheduler (`gathering/orchestration/scheduler.py`) has a complete `_execute_action` method that only dispatches `run_task` via the background executor -- it does not handle `execute_pipeline`, `send_notification`, or `call_api` action types. The `SchedulesSkill._run_now()` has a literal `# TODO: Actually execute the action based on action_type` comment. The core tool registry (`gathering/core/tool_registry.py`) has TODOs for "parameter validation against JSON schema" and "handle async functions" in its `execute()` method.

The crash recovery requirement (FEAT-06) is the most architecturally significant item. The existing scheduler loads actions from the database on startup (`_load_actions`) and tracks `next_run_at` in PostgreSQL, but does NOT check for missed runs between the last shutdown and current startup. After a crash, any scheduled action whose `next_run_at` is in the past will simply be recalculated to the next future time, silently skipping the missed execution window. The database already stores `scheduled_action_runs` with status tracking, which provides the foundation for deduplication -- we need to check whether a run record exists for the missed window before executing.

The workspace path issue (RLBL-04) is a simple but important fix: `get_project_path()` in `gathering/api/routers/workspace.py` line 50 returns `os.getcwd()`, meaning all file operations resolve against the server's working directory rather than the project's configured path.

**Primary recommendation:** Implement action type dispatchers using the existing pipeline executor and skill registry, add startup recovery logic to the scheduler that checks `scheduled_action_runs` for already-completed missed windows, use `jsonschema.validate()` for tool parameter validation (Pydantic is not designed for validating arbitrary JSON against arbitrary schemas), and fix workspace path resolution to use a project path lookup from the database.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| croniter | 2.0.7 | Cron expression parsing and next-run calculation | Already in use by scheduler, well-maintained |
| pydantic | 2.12.5 | Request validation, model definitions | Already in use throughout codebase |
| tenacity | 8.5.0 | Retry with exponential backoff | Already in use by pipeline executor |
| asyncio | stdlib | Async scheduling, timeout, task management | Python 3.11+ asyncio.timeout already used in Phase 2 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| jsonschema | 4.x (install needed) | Validate tool parameters against JSON Schema | FEAT-07: tool parameter validation before execution |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| jsonschema | pydantic model_validate | Pydantic validates against Pydantic models, not arbitrary JSON Schema dicts. Tool definitions use raw JSON Schema dicts in `input_schema` -- jsonschema is the direct validator for that format |
| jsonschema | fastjsonschema | Faster but less maintained; not worth the risk for correctness-focused phase |

**Installation:**
```bash
pip install jsonschema
```

## Architecture Patterns

### Relevant File Locations
```
gathering/
├── orchestration/
│   ├── scheduler.py           # Main scheduler -- needs action dispatchers, crash recovery
│   ├── background.py          # BackgroundTaskExecutor -- run_task action uses this
│   ├── events.py              # EventBus + EventType enum
│   └── pipeline/
│       ├── executor.py        # PipelineExecutor + PipelineRunManager
│       ├── models.py          # PipelineDefinition, PipelineNode, etc.
│       ├── nodes.py           # Node type dispatchers (action handler is Phase 2 stub)
│       └── validator.py       # DAG validation
├── core/
│   └── tool_registry.py       # ToolRegistry + ToolDefinition -- needs validation + async
├── skills/
│   ├── base.py                # BaseSkill, SkillResponse, execute_async()
│   ├── registry.py            # SkillRegistry -- lazy-loading skill instances
│   ├── notifications/
│   │   └── sender.py          # NotificationsSkill -- send_notification uses this
│   ├── http/
│   │   └── client.py          # HTTPSkill -- call_api uses this
│   └── gathering/
│       └── schedules.py       # SchedulesSkill -- has TODO for action execution
├── workspace/
│   ├── __init__.py            # WorkspaceManager, FileManager, GitManager exports
│   ├── manager.py             # WorkspaceManager class
│   └── file_manager.py        # FileManager class
├── api/
│   └── routers/
│       ├── workspace.py       # get_project_path() returns os.getcwd() -- THE BUG
│       └── scheduled_actions.py  # API endpoints for schedules
└── db/
    └── migrations/
        └── archive/
            └── 013_scheduled_actions.sql  # Schema for scheduled_actions and runs
```

### Pattern 1: Action Type Dispatcher
**What:** Map each `action_type` string to a handler function that performs the actual work, replacing the current approach where `_execute_action` only creates background tasks via `AgentWrapper`.
**When to use:** When the scheduler fires a due action.
**Example:**
```python
# Source: Derived from existing codebase patterns (nodes.py dispatch table)
ACTION_DISPATCHERS = {
    "run_task": _dispatch_run_task,
    "execute_pipeline": _dispatch_execute_pipeline,
    "send_notification": _dispatch_send_notification,
    "call_api": _dispatch_call_api,
}

async def _dispatch_execute_pipeline(action: ScheduledAction, context: dict) -> dict:
    """Execute a pipeline run from a scheduled action."""
    pipeline_id = action.metadata.get("pipeline_id")
    if not pipeline_id:
        raise ValueError("execute_pipeline requires 'pipeline_id' in metadata")

    # Load pipeline definition from DB
    db = context["db"]
    row = db.execute_one(
        "SELECT nodes, edges FROM circle.pipelines WHERE id = %(id)s",
        {"id": pipeline_id},
    )
    if not row:
        raise ValueError(f"Pipeline {pipeline_id} not found")

    definition = PipelineDefinition(
        nodes=row["nodes"],
        edges=row["edges"],
    )

    # Create a pipeline run record
    run_row = db.execute_one(
        """INSERT INTO circle.pipeline_runs (pipeline_id, status, triggered_by)
           VALUES (%(pipeline_id)s, 'running', 'scheduler')
           RETURNING id""",
        {"pipeline_id": pipeline_id},
    )
    run_id = run_row["id"]

    executor = PipelineExecutor(
        pipeline_id=pipeline_id,
        definition=definition,
        db=db,
        event_bus=context.get("event_bus"),
    )

    result = await executor.execute(run_id=run_id, trigger_data=action.metadata)
    return result
```

### Pattern 2: Crash Recovery with Deduplication
**What:** On scheduler startup, query for scheduled actions whose `next_run_at` is in the past and check whether a `scheduled_action_runs` entry exists for that time window. Only execute if no completed run exists.
**When to use:** In `Scheduler.start()` after `_load_actions()`.
**Example:**
```python
# Source: Derived from existing schema (013_scheduled_actions.sql)
async def _recover_missed_runs(self):
    """Detect and handle missed runs after crash/restart."""
    now = datetime.now(timezone.utc)

    for action in self._actions.values():
        if action.status != ScheduledActionStatus.ACTIVE:
            continue
        if not action.next_run_at or action.next_run_at >= now:
            continue

        # Check if a run already exists for this missed window
        existing_run = self.db_service.execute_one("""
            SELECT id, status FROM circle.scheduled_action_runs
            WHERE scheduled_action_id = %(action_id)s
              AND triggered_at >= %(window_start)s
              AND status IN ('completed', 'running', 'pending')
            ORDER BY triggered_at DESC LIMIT 1
        """, {
            "action_id": action.id,
            "window_start": action.next_run_at - timedelta(seconds=60),
        })

        if existing_run:
            # Already ran or running -- just advance next_run_at
            logger.info(f"Action {action.id} already has run for missed window, skipping")
            action.next_run_at = action.calculate_next_run()
            await self._persist_action(action)
        else:
            # Missed and never ran -- execute now
            logger.info(f"Action {action.id} missed, executing recovery run")
            await self._execute_action(action, triggered_by="recovery")
```

### Pattern 3: Tool Parameter Validation via JSON Schema
**What:** Before executing any tool, validate `tool_input` against the tool's `input_schema` JSON Schema definition using the `jsonschema` library.
**When to use:** In `ToolRegistry.execute()` and `SkillRegistry.execute_tool()`.
**Example:**
```python
# Source: jsonschema library standard usage
import jsonschema

def execute(self, tool_name: str, **kwargs) -> Any:
    tool = self.get(tool_name)
    if not tool:
        raise ValueError(f"Tool '{tool_name}' not found in registry")

    # Validate parameters against schema
    if tool.parameters:
        try:
            jsonschema.validate(instance=kwargs, schema=tool.parameters)
        except jsonschema.ValidationError as e:
            raise ValueError(
                f"Invalid parameters for tool '{tool_name}': {e.message}"
            ) from e

    # Execute (sync or async based on async_function flag)
    if tool.async_function:
        import asyncio
        return asyncio.get_event_loop().run_until_complete(tool.function(**kwargs))
    return tool.function(**kwargs)
```

### Pattern 4: Async Tool Execution
**What:** When `ToolDefinition.async_function` is `True`, await the function rather than calling it synchronously. Provide both sync and async execution paths.
**When to use:** For tools that perform I/O (HTTP requests, DB queries, file operations).
**Example:**
```python
# Source: Existing BaseSkill.execute_async() pattern
async def execute_async(self, tool_name: str, **kwargs) -> Any:
    tool = self.get(tool_name)
    if not tool:
        raise ValueError(f"Tool '{tool_name}' not found")

    # Validate parameters
    if tool.parameters:
        jsonschema.validate(instance=kwargs, schema=tool.parameters)

    if tool.async_function:
        return await tool.function(**kwargs)
    else:
        # Run sync function in executor to avoid blocking event loop
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: tool.function(**kwargs))
```

### Anti-Patterns to Avoid
- **Skipping missed runs silently:** The current behavior of just recalculating `next_run_at` to the future means scheduled pipeline runs silently disappear after a crash. Always check and log.
- **Using eval() for condition evaluation:** Already avoided in Phase 2, maintain this discipline.
- **Blocking event loop with sync tool execution:** When `async_function=True`, never call the function synchronously. When `async_function=False` but called from async context, use `run_in_executor`.
- **Validating tool params with Pydantic model_validate:** The tool schemas are raw JSON Schema dicts, not Pydantic models. Use `jsonschema.validate()` which is purpose-built for this.
- **Executing duplicate actions after crash recovery:** Always check `scheduled_action_runs` before re-executing a missed action.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cron expression parsing | Custom cron parser | `croniter` (already installed) | Edge cases: day-of-week + day-of-month interaction, leap seconds, timezone handling |
| JSON Schema validation | Custom validator against `input_schema` dicts | `jsonschema` library | Full JSON Schema Draft 4-7 compliance, format validators, detailed error messages with path info |
| Retry with backoff | Custom retry loop | `tenacity` (already installed) | Composable stop/wait/retry strategies, async support, before/after hooks |
| Pipeline execution | New pipeline runner | `PipelineExecutor` from Phase 2 | Already handles DAG traversal, retry, circuit breakers, cancellation |

**Key insight:** The scheduled action types map directly to existing subsystems -- `execute_pipeline` uses `PipelineExecutor`, `send_notification` uses `NotificationsSkill`, `call_api` uses `HTTPSkill`, `run_task` uses `BackgroundTaskExecutor`. The dispatcher just needs to bridge the scheduler to these existing systems.

## Common Pitfalls

### Pitfall 1: Race Condition in Concurrent Schedule Check
**What goes wrong:** Two scheduler loop iterations both see `should_run() == True` for the same action before either marks it as running, causing duplicate execution.
**Why it happens:** `_check_and_execute_due_actions` uses `asyncio.create_task` to fire off execution, but `_running_actions` is only updated inside `_execute_action` after an async context switch.
**How to avoid:** Add the action to `_running_actions` inside the lock in `_check_and_execute_due_actions` BEFORE creating the task, not inside `_execute_action`.
**Warning signs:** Duplicate entries in `scheduled_action_runs` with same `triggered_at` timestamp for the same action.

### Pitfall 2: Crash Recovery Executing Already-Completed Actions
**What goes wrong:** After a crash, the scheduler sees `next_run_at < now` and re-executes an action that already completed before the crash.
**Why it happens:** The action's `next_run_at` was not advanced before the crash, and no run completion check is performed.
**How to avoid:** Query `scheduled_action_runs` for a completed/running run in the missed time window before executing.
**Warning signs:** Duplicate pipeline runs or duplicate notifications after server restart.

### Pitfall 3: Workspace Path Always Using os.getcwd()
**What goes wrong:** The `get_project_path()` function in `workspace.py` always returns `os.getcwd()`, meaning file operations resolve against the server's working directory regardless of which project is being accessed.
**Why it happens:** The function has a TODO comment acknowledging this: `"# TODO: Integrate with project database when available"`.
**How to avoid:** Look up the project path from the database using the `project_id` parameter, with a fallback to a configured workspace root + project directory.
**Warning signs:** Accessing `src/main.py` via the workspace API returns the server's `src/main.py` instead of the project's.

### Pitfall 4: Tool Schema Validation Not Returning Useful Errors
**What goes wrong:** Validation rejects input but only says "invalid parameters" without explaining which parameter failed and why.
**Why it happens:** Catching `jsonschema.ValidationError` and only returning `e.message` without `e.path` or `e.schema_path`.
**How to avoid:** Include `e.path` (which parameter failed), `e.message` (what's wrong), and `e.validator` (which validation rule failed) in the error response.
**Warning signs:** Users can't figure out how to fix their tool invocations from the error message alone.

### Pitfall 5: Async Tools Blocking the Event Loop
**What goes wrong:** A tool marked `async_function=True` actually blocks the event loop because the underlying implementation does synchronous I/O.
**Why it happens:** The `async_function` flag is just a marker; nothing enforces that the function is actually non-blocking.
**How to avoid:** For the core tool registry, when `async_function=True`, always `await` the function. When `async_function=False` but called from an async context, wrap in `run_in_executor`. Test concurrent tool invocations to verify parallelism.
**Warning signs:** Multiple async tool invocations running sequentially instead of concurrently.

### Pitfall 6: Two Separate Registry Systems
**What goes wrong:** Confusion about which registry to modify -- `gathering/core/tool_registry.py` (ToolRegistry with ToolDefinition) vs `gathering/skills/registry.py` (SkillRegistry with BaseSkill).
**Why it happens:** They serve different purposes. ToolRegistry is for standalone functions with JSON Schema parameters. SkillRegistry is for skill modules that provide tool sets.
**How to avoid:** FEAT-07 (JSON Schema validation) applies to BOTH registries. The ToolRegistry validates against `ToolDefinition.parameters`, and the SkillRegistry validates against `input_schema` from `get_tools_definition()`. Implement validation in both paths.
**Warning signs:** Tools registered via one registry bypass validation implemented in the other.

## Code Examples

Verified patterns from existing codebase:

### Existing Scheduler Action Execution (current -- needs extension)
```python
# Source: gathering/orchestration/scheduler.py:380-442
# Currently only dispatches run_task via BackgroundTaskExecutor
async def _execute_action(self, action: ScheduledAction, triggered_by: str = "scheduler"):
    # ... creates ScheduledActionRun record ...
    executor = get_background_executor(db_service=self.db_service)
    agent = AgentWrapper(agent_id=action.agent_id, name=f"scheduled-{action_id}")
    task_id = await executor.start_task(goal=action.goal, agent=agent, ...)
```

### Existing Pipeline Executor (Phase 2 -- what execute_pipeline will call)
```python
# Source: gathering/orchestration/pipeline/executor.py:79-421
executor = PipelineExecutor(
    pipeline_id=pipeline_id,
    definition=definition,
    db=db,
    event_bus=event_bus,
    agent_registry=agent_registry,
)
result = await executor.execute(run_id=run_id, trigger_data=trigger_data)
```

### Existing Tool Definition with async_function Flag
```python
# Source: gathering/core/tool_registry.py:83-131
@dataclass
class ToolDefinition:
    name: str
    description: str
    category: ToolCategory
    function: Callable
    required_competencies: List[str]
    parameters: Dict[str, Any]       # JSON Schema
    returns: Dict[str, Any]          # JSON Schema
    async_function: bool = False     # <-- currently ignored in execute()
```

### Existing Skill Tools Definition with input_schema
```python
# Source: gathering/skills/base.py:101-120
# Skills return tool definitions with input_schema in JSON Schema format
def get_tools_definition(self) -> List[Dict[str, Any]]:
    return [
        {
            "name": "tool_name",
            "description": "What this tool does",
            "input_schema": {
                "type": "object",
                "properties": {...},
                "required": [...]
            }
        }
    ]
```

### Existing SchedulesSkill TODO
```python
# Source: gathering/skills/gathering/schedules.py:477
# Inside _run_now():
# TODO: Actually execute the action based on action_type
# For now, just log that it was triggered
```

### Existing Action Node Stub from Phase 2
```python
# Source: gathering/orchestration/pipeline/nodes.py:174-201
async def _handle_action(node, inputs, context):
    """Action node: log and return action metadata.
    Real action dispatch will be extended in Phase 3."""
    action_type = node.config.get("action", "unknown")
    return {"action": action_type, "executed": True, "inputs": summarized_inputs}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| APScheduler with SQLAlchemy | Custom async scheduler with croniter + PostgreSQL | Already in codebase | Simpler, no ORM dependency, full control over crash recovery |
| jsonschema library | Pydantic for structured validation | N/A | Use BOTH: Pydantic for request/response models, jsonschema for validating against arbitrary JSON Schema dicts |
| eval() for condition evaluation | Safe string matching (input.key lookups) | Phase 2 | Already correctly implemented, maintain this pattern |
| os.getcwd() for workspace path | Database project path lookup | Phase 3 | Fixes workspace resolving against wrong directory |

**Deprecated/outdated:**
- `ScheduledAction.goal` as sole action config: The newer `SchedulesSkill` schema uses `action_type` + `action_config` (JSON) which is more flexible. The Phase 3 dispatcher should read from `action_config`/`metadata` rather than just `goal`.
- The older scheduler model (orchestration/scheduler.py) uses `agent_id` + `goal` pattern (run_task only). The newer schedules skill model has `action_type` + `action_config` (supports all 4 types). These two models need to be reconciled.

## Open Questions

1. **Two Scheduler Data Models**
   - What we know: `gathering/orchestration/scheduler.py` uses the `ScheduledAction` dataclass with `agent_id + goal` (tied to run_task). `gathering/skills/gathering/schedules.py` uses the DB table with `action_type + action_config` (supports all types). The DB schema (`013_scheduled_actions.sql`) defines `goal TEXT NOT NULL` but the `SchedulesSkill` inserts `action_type` and `action_config` columns.
   - What's unclear: Whether the DB table already has `action_type` and `action_config` columns or if a migration is needed.
   - Recommendation: Check the actual DB schema. If `action_type`/`action_config` columns exist in the DB, extend the `ScheduledAction` dataclass to include them. If not, add a migration. The dispatcher should read `action_type` from the DB to determine which handler to call.

2. **Project Path Storage**
   - What we know: `get_project_path(project_id)` returns `os.getcwd()`. The workspace API takes `project_id` as a path parameter.
   - What's unclear: Whether there's a `projects` table with a `path` column, or if project paths need to be stored somewhere new.
   - Recommendation: Check for an existing projects table. If it exists with a path column, use it. If not, fall back to a configurable workspace root directory (e.g., `WORKSPACE_ROOT` env var) + project subdirectory, and add a `path` column to whatever projects table exists.

3. **SkillRegistry vs ToolRegistry Validation**
   - What we know: There are two registries. `SkillRegistry.execute_tool()` calls `skill.execute(tool_name, tool_input)` with no validation. `ToolRegistry.execute()` calls `tool.function(**kwargs)` with no validation. Both have TODO comments for adding validation.
   - What's unclear: Whether validation should be added to both registries or if one should delegate to the other.
   - Recommendation: Add validation to both. For `ToolRegistry`, validate `kwargs` against `tool.parameters`. For `SkillRegistry`, look up the tool's `input_schema` from `skill.get_tools_definition()` and validate before calling `skill.execute()`. This ensures validation regardless of which path invokes the tool.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `gathering/orchestration/scheduler.py` -- full Scheduler class with _execute_action, _load_actions, _run_loop
- Codebase analysis: `gathering/core/tool_registry.py` -- ToolRegistry with TODO markers for validation and async
- Codebase analysis: `gathering/skills/registry.py` -- SkillRegistry with lazy loading
- Codebase analysis: `gathering/skills/base.py` -- BaseSkill with execute_async() default impl
- Codebase analysis: `gathering/api/routers/workspace.py` -- get_project_path() returning os.getcwd()
- Codebase analysis: `gathering/orchestration/pipeline/executor.py` -- PipelineExecutor and PipelineRunManager
- Codebase analysis: `gathering/orchestration/pipeline/nodes.py` -- _handle_action stub noting "extended in Phase 3"
- Codebase analysis: `gathering/skills/gathering/schedules.py` -- SchedulesSkill with TODO for action execution
- Codebase analysis: `gathering/db/migrations/archive/013_scheduled_actions.sql` -- DB schema
- Package versions: croniter 2.0.7, pydantic 2.12.5, tenacity 8.5.0, fastapi 0.126.0, psycopg 3.3.2

### Secondary (MEDIUM confidence)
- [Pydantic JSON Schema docs](https://docs.pydantic.dev/latest/concepts/json_schema/) -- confirms Pydantic generates JSON Schema but does not validate against arbitrary schemas
- [Pydantic discussion #5135](https://github.com/pydantic/pydantic/discussions/5135) -- confirms jsonschema library needed for validating data against JSON Schema dicts
- [APScheduler user guide](https://apscheduler.readthedocs.io/en/master/userguide.html) -- reference for schedule/job store patterns (not used directly, confirms our custom approach is valid)
- [Python asyncio docs](https://docs.python.org/3/library/asyncio-task.html) -- asyncio.timeout, TaskGroup, event loop APIs

### Tertiary (LOW confidence)
- [Duplicate request prevention patterns](https://oneuptime.com/blog/post/2026-01-25-prevent-duplicate-requests-python/view) -- general idempotency patterns, not directly applicable but confirms our deduplication approach

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All core libraries already installed except jsonschema; codebase patterns well understood
- Architecture: HIGH - Codebase thoroughly analyzed; existing dispatching patterns (pipeline nodes, skill registry) provide clear templates
- Pitfalls: HIGH - Identified from direct code analysis; race conditions in existing code visible from reading the lock patterns
- Crash recovery: HIGH - Database schema already supports deduplication via scheduled_action_runs table; just needs query logic
- Workspace fix: MEDIUM - The bug is clear (os.getcwd()), but project path storage mechanism needs investigation during planning

**Research date:** 2026-02-10
**Valid until:** 2026-03-12 (30 days -- stable domain, codebase under our control)
