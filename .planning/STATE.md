# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-10)

**Core value:** Every existing feature works for real -- auth persists, pipelines execute, schedules run, security is solid -- so GatheRing can be deployed to production with confidence.
**Current focus:** Phase 5 - Multi-Instance Production Hardening

## Current Position

Phase: 5 of 5 (Multi-Instance Production Hardening)
Plan: 1 of 2 in current phase -- COMPLETE
Status: Executing Phase 5
Last activity: 2026-02-11 -- Completed 05-01 (Advisory Lock Coordination)

Progress: [████████░░] 80%

## Performance Metrics

**Velocity:**
- Total plans completed: 15
- Average duration: 5.7min
- Total execution time: 1.49 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-auth-security-foundation | 3/3 | 24min | 8min |
| 02-pipeline-execution-engine | 3/3 | 17min | 5.7min |
| 03-schedule-execution-tool-hardening | 3/3 | 14min | 4.7min |
| 04-performance-optimization | 5/5 | 35min | 7min |
| 05-multi-instance-production-hardening | 1/2 | 3min | 3min |

**Recent Trend:**
- Last 5 plans: 04-03 (4min), 04-02 (8min), 04-04 (7min), 04-05 (12min), 05-01 (3min)
- Trend: Steady/Fast

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: Auth + security first because every feature authenticates through it
- [Roadmap]: DB layer (pycopg) consolidated in Phase 1 since auth persistence depends on it
- [Roadmap]: Tests accompany each phase rather than a separate testing phase
- [Roadmap]: Performance optimization deferred until correctness established (Phases 1-3)
- [01-01]: PyJWT[crypto] replaces python-jose (maintained, smaller, identical HS256 API)
- [01-01]: Direct bcrypt replaces passlib CryptContext (eliminates wrapper dependency)
- [01-01]: bcrypt upper bound unpinned to >=4.0.0 (passlib constraint no longer needed)
- [01-01]: structlog JSON in production, console in debug; correlation ID middleware runs first
- [01-02]: TokenBlacklist uses write-through pattern (LRU cache + PostgreSQL) for persistence with performance
- [01-02]: Auth functions accept optional db parameter for dependency injection and testability
- [01-02]: Audit logging silently catches exceptions to never block auth operations
- [01-02]: Tests use mock DatabaseService to avoid test-env DB password dependency
- [01-03]: safe_update_builder validates column names against allowlist before constructing SET clause
- [01-03]: validate_file_path double-decodes URLs to catch double-encoding path traversal attacks
- [01-03]: Bare exceptions in security paths split into specific catch + generic logger.exception fallback
- [02-01]: graphlib.TopologicalSorter (stdlib) for cycle detection -- zero-dependency, CycleError provides cycle path info
- [02-01]: PipelineEdge uses Field(alias="from") with populate_by_name=True for JSON reserved words
- [02-01]: Node config stored as generic dict; type-specific config models available for targeted validation
- [02-01]: Orphan nodes logged as warnings, not validation errors
- [02-02]: tenacity retry wraps node execution with configurable exponential backoff; only retries NodeExecutionError
- [02-02]: Agent nodes degrade gracefully when no agent_registry -- return simulated result
- [02-02]: Condition evaluation avoids eval() -- supports literals and safe input.key lookups
- [02-02]: Event emission and node run persistence wrapped in try/except to never block pipeline execution
- [02-02]: CircuitBreaker is per-node with configurable failure_threshold via node config
- [02-03]: PipelineRunManager uses asyncio.timeout (Python 3.11+) for per-pipeline timeout enforcement
- [02-03]: Cancellation is two-phase: cooperative request_cancel() first, then forced task.cancel()
- [02-03]: PipelineRunManager cleanup happens in finally block to prevent resource leaks on any exit path
- [03-02]: jsonschema import guarded with try/except ImportError for graceful degradation if not installed
- [03-02]: ToolRegistry.execute() raises RuntimeError for async tools -- sync callers must not silently block
- [03-02]: Workspace path uses project.projects.repository_path (actual DB column) -- no migration needed
- [03-02]: Workspace cache uses monotonic clock TTL dict (5min) instead of functools.lru_cache
- [03-01]: Dispatcher functions are module-level async, not Scheduler methods, keeping dispatch table clean and testable
- [03-01]: Pipeline action nodes use lightweight local dispatch instead of importing scheduler dispatchers to avoid coupling
- [03-01]: action_config JSONB stores skill_config, tool_name, and tool_input for notification/API dispatchers
- [03-01]: _insert_action SQL reconciled with actual DB schema columns (removed nonexistent columns)
- [03-01]: goal field defaulted to empty string for backward compat with action_config-based actions
- [03-03]: Lazy import patching: patch at source module path for deferred imports in dispatcher functions
- [03-03]: MockSkill concrete subclass avoids loading real skill modules for SkillRegistry validation testing
- [03-03]: Workspace path cache cleared per-test for isolation since module-level TTL dict persists between tests
- [04-01]: AsyncDatabaseService uses pycopg AsyncPooledDatabase with min_size=4, max_size=20 for web concurrency
- [04-01]: Async pool lifecycle wired into FastAPI lifespan: startup after scheduler, shutdown before scheduler
- [04-01]: get_circle_members_full() single JOIN replaces 2N+1 per-member get_agent() + skill_names queries
- [04-01]: Existing sync DatabaseService preserved for CLI/migrations; AsyncDatabaseService is for async route handlers
- [04-02]: slowapi with in-memory backend by default; Redis backend opt-in via REDIS_URL env var
- [04-02]: Per-endpoint rate limit decorators are opt-in; default_limits apply globally to all endpoints
- [04-02]: BoundedLRUDict inherits OrderedDict for drop-in compatibility with existing cache patterns
- [04-02]: EventBus history changed from List to deque(maxlen=N) for O(1) bounded append
- [04-03]: Dedup disabled by default for backward compatibility; callers opt-in via configure(dedup_enabled=True)
- [04-03]: Semaphore wraps _safe_invoke rather than adding separate wrapper, keeping gather() pattern unchanged
- [04-03]: Dedup key includes type, source_agent_id, circle_id, and data hash -- distinct data always passes through
- [04-03]: Dedup cache pruned every 1000 events with 2x window expiry to prevent unbounded memory growth
- [04-04]: Migrate 5 representative handlers (not all ~100+) to prove async DB pattern works at scale
- [04-04]: AsyncDatabaseService handlers use direct SQL (no convenience methods like get_providers)
- [04-04]: Concurrency test uses asyncio.gather + wall-clock timing to prove non-blocking execution
- [04-05]: Custom _rate_limit_handler replaces slowapi default to inject Retry-After + X-RateLimit-* headers on 429
- [04-05]: SlowAPIMiddleware not used (conflicts with decorator-based header injection); exception handler approach sufficient
- [04-05]: headers_enabled left False on Limiter; headers only injected on 429 via custom handler to avoid decorator crash
- [05-01]: Advisory lock uses two-integer form pg_try_advisory_xact_lock(namespace, action_id) to avoid collision with other lock users
- [05-01]: Fail-closed on DB error: returns False (skip execution) rather than risk duplicate
- [05-01]: async_db is optional -- single-instance mode (None) always returns True for backward compatibility
- [05-01]: Lock check is first gate in _execute_action, before existing concurrency check

### Pending Todos

None yet.

### Blockers/Concerns

- [Research]: 262 bare exception catches -- fixing all at once will destabilize tests. Tiered approach: security paths in Phase 1, feature paths in Phases 2-3, polish in Phase 4.
- [Research]: Auth migration may invalidate existing JWT tokens if user ID format changes. Keep user ID format as str to avoid forced re-login.
- [Research]: Two separate EventBus implementations exist -- must preserve boundary during hardening.

## Session Continuity

Last session: 2026-02-11
Stopped at: Completed 05-01-PLAN.md
Resume file: .planning/phases/05-multi-instance-production-hardening/05-01-SUMMARY.md
