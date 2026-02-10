# Codebase Concerns

**Analysis Date:** 2026-02-10

## Tech Debt

**Incomplete Database Integration in Auth Module:**
- Issue: User authentication uses in-memory store instead of database
- Files: `gathering/api/auth.py` (lines 346-387)
- Impact: Users are not persisted across server restarts; multiple instances share no state; production deployment will lose all user data
- Fix approach: Replace `_users_store` with database queries using `DatabaseService` from `gathering/api/dependencies.py`; implement proper user persistence with unique email constraints

**Stub Pipeline Execution:**
- Issue: Pipeline node execution not implemented; system creates fake completion logs
- Files: `gathering/api/routers/pipelines.py` (line 413: TODO comment)
- Impact: Pipelines appear to complete but don't actually execute agent tasks or actions; runs report success when nothing was executed
- Fix approach: Implement actual pipeline node traversal and async task execution; call agent handlers for agent nodes; execute notification handlers for action nodes

**Stub Schedule Action Execution:**
- Issue: Schedule run_now triggers only log events, doesn't execute actual actions
- Files: `gathering/skills/gathering/schedules.py` (line 477: TODO comment)
- Impact: Scheduled actions can be created and monitored but never actually execute; agents don't run scheduled goals or tasks
- Fix approach: Implement action execution dispatcher based on action_type (run_task, send_notification, call_api, execute_pipeline)

**Missing Parameter Validation in Tool Registry:**
- Issue: Tool execution skips JSON schema validation against declared parameters
- Files: `gathering/core/tool_registry.py` (lines 354-355: TODO comments)
- Impact: Tools receive invalid input types; no early error detection; runtime failures in tool functions
- Fix approach: Validate kwargs against tool.parameters JSON schema before execution; raise ValueError with clear error message if validation fails

**Async Function Handling Not Implemented:**
- Issue: Tool registry.execute() doesn't support async functions despite async_function flag in ToolDefinition
- Files: `gathering/core/tool_registry.py` (line 355: TODO comment)
- Impact: Async tools cannot be registered or used; attempt to call async tools fails with confusing error
- Fix approach: Check tool.async_function flag; use asyncio.run() or await depending on context; handle both sync and async

**Unfinished Project Integration:**
- Issue: Workspace API hardcoded to return current working directory instead of project-specific paths
- Files: `gathering/api/routers/workspace.py` (lines 44-48: TODO comment)
- Impact: Multi-project support not functional; all agents access same workspace regardless of project_id
- Fix approach: Query projects table; resolve project_id to actual directory; implement project-level isolation

## Known Bugs

**Bare exception catch without handling in error paths:**
- Symptoms: Silent failures; incomplete error context logged
- Files: Multiple across codebase (90+ exception handlers found)
- Trigger: Any exceptional condition in try blocks
- Workaround: Enable verbose logging to catch error context; check logs manually for failures

**Path traversal vulnerability in file serving:**
- Symptoms: Although path validation exists, nested try-except blocks obscure error handling
- Files: `gathering/api/routers/workspace.py` (lines 175-188)
- Trigger: Malformed paths with encoding issues
- Workaround: Use absolute paths; avoid symbolic links in workspace

**Timing-safe comparison not applied to all auth checks:**
- Symptoms: Potential timing attack vectors in password verification
- Files: `gathering/api/auth.py` (lines 296-334)
- Trigger: Automated credential guessing attempts
- Workaround: None practical at application level; mitigate with rate limiting on auth endpoints

## Security Considerations

**In-Memory Token Blacklist Not Persistent:**
- Risk: Tokens blacklisted at logout are not stored in database; restarting server resets blacklist allowing reuse of "revoked" tokens
- Files: `gathering/api/auth.py` (lines 177-269)
- Current mitigation: Tokens expire after 24 hours; cleanup of expired entries
- Recommendations: Persist blacklist to database (Redis cache or PostgreSQL table); implement cross-instance token verification

**Admin Credentials from Environment:**
- Risk: Admin password hash exposed in environment variables; logged in startup/debugging; checked into version control accidentally
- Files: `gathering/api/auth.py` (lines 276-334)
- Current mitigation: Uses constants for timing-safe comparison; .env files gitignored
- Recommendations: Use secrets manager (AWS Secrets, HashiCorp Vault); implement OAuth2 for admin; rotate credentials on deployment

**Database Connection Strings May Contain Passwords:**
- Risk: DATABASE_URL environment variable frequently includes password in plaintext
- Files: `gathering/api/dependencies.py` (line 31-50), `gathering/db/database.py` (line 56-103)
- Current mitigation: .env files gitignored
- Recommendations: Use IAM database authentication where available; store connection secrets separately from code; never log connection strings

**SQL Parameter Injection Possible in Dynamic Queries:**
- Risk: Some endpoints build SQL with string formatting instead of parameterized queries
- Files: `gathering/api/routers/pipelines.py` (line 311: f-string SQL concatenation), `gathering/skills/gathering/schedules.py` (line 390: f-string SQL)
- Current mitigation: Most queries use %(param)s parameterization
- Recommendations: Audit all f-string SQL constructions; use SQLAlchemy ORM or prepared statements throughout

**LSP Server Untrusted Input Processing:**
- Risk: LSP plugins receive file paths and code content from clients without validation
- Files: `gathering/lsp/manager.py` (lines 54-61)
- Current mitigation: Plugins run in same process
- Recommendations: Sandbox LSP processes; validate all input paths; implement size limits on code content

## Performance Bottlenecks

**File Tree Caching with Stale Git Status:**
- Problem: File listing cached for 1 minute but git status not refreshed during cache period
- Files: `gathering/api/routers/workspace.py` (lines 112-132)
- Cause: Optimization to reduce git command execution; inconsistent cache behavior
- Improvement path: Use Redis with per-file TTL; invalidate cache on file system changes; or include git status in cache key

**N+1 Queries in Circle Member Retrieval:**
- Problem: get_circle_members_with_info queries agent, model, provider for each member
- Files: `gathering/api/dependencies.py` (lines 310-320)
- Cause: Lazy relationship loading in SQL; no JOIN optimization
- Improvement path: Single query with pre-joined tables; cache provider/model info; implement query batching

**Large File Line Count Calculations:**
- Problem: Largest files exceed 1700 lines; complex logic not separated into smaller modules
- Files: `gathering/api/dependencies.py` (1694 lines), `gathering/skills/ai/models.py` (1217 lines)
- Cause: All dependency functions in single file; AI models bundled together
- Improvement path: Split by domain (agents, circles, conversations); separate model definitions from logic

**Synchronous Database Calls in Async Handlers:**
- Problem: FastAPI async endpoints call synchronous database methods
- Files: Multiple routers in `gathering/api/routers/`
- Cause: DatabaseService.execute() is synchronous; blocks event loop
- Improvement path: Implement async database driver (asyncpg); make DatabaseService async-compatible; use run_in_executor for legacy code

**Event Bus Not Batching Emissions:**
- Problem: Each event emission is separate async task; high-frequency events create task saturation
- Files: `gathering/orchestration/circle.py` (lines 256-260)
- Cause: create_task() for every emit; no batching or deduplication
- Improvement path: Implement event queue with periodic flush; deduplicate rapid events; rate-limit event processing

## Fragile Areas

**GatheringCircle Event Dependency System:**
- Files: `gathering/orchestration/circle.py` (full file), `gathering/orchestration/events.py`
- Why fragile: Event handlers assume specific event structure and order; circular task assignment dependencies; no validation of state transitions
- Safe modification: Add event schema validation; document expected event sequences; add state machine assertions
- Test coverage: No unit tests for event ordering; integration tests needed for task lifecycle

**Pipeline Configuration Validation Missing:**
- Files: `gathering/api/routers/pipelines.py` (lines 235-260)
- Why fragile: Accepts arbitrary node configs; no validation of node connections; JSONB storage allows invalid structure
- Safe modification: Implement PipelineValidator; check for cyclic dependencies; validate node types and required fields
- Test coverage: No tests for invalid pipeline creation; need schema enforcement tests

**In-Memory Scheduler Running State:**
- Files: `gathering/orchestration/scheduler.py` (lines 218-241)
- Why fragile: Running actions tracked in-memory; no persistence of execution state; loss on restart; concurrent execution not truly prevented
- Safe modification: Persist _running_actions to database; implement distributed lock for concurrent safety; add recovery on startup
- Test coverage: Single-node only; needs multi-instance concurrency tests

**LSP Manager Singleton Pattern:**
- Files: `gathering/lsp/manager.py` (lines 12-107)
- Why fragile: Class variable _servers shared globally; no cleanup on errors; memory leak if servers fail to shutdown
- Safe modification: Convert to proper singleton instance; add __del__ cleanup; implement weak references for server cleanup
- Test coverage: No tests for server lifecycle; needs cleanup and error recovery tests

**Authentication Token Expiry Calculation:**
- Files: `gathering/api/auth.py` (lines 114-138)
- Why fragile: Uses datetime.now(timezone.utc) inconsistently with utcnow(); token expiry comparison may have timezone issues
- Safe modification: Standardize on timezone-aware datetime everywhere; add unit tests for expiry edge cases; document timezone requirements
- Test coverage: No unit tests for token expiry; needs boundary condition tests

## Scaling Limits

**In-Memory Token Blacklist:**
- Current capacity: All tokens for session lifetime; grows unbounded
- Limit: Memory exhaustion on long-running servers; expires only at cleanup interval (3600s)
- Scaling path: Move to Redis with automatic TTL; implement token revocation API with pagination; use token families for batch revocation

**Single Database Connection Pool:**
- Current capacity: Pool size 20, max overflow 20 (40 total connections)
- Limit: Under load, 40 concurrent queries fail; queuing increases latency
- Scaling path: Increase pool_size via DB_POOL_SIZE env var; implement connection pooling service; migrate to pgBouncer

**Event Bus In-Memory Storage:**
- Current capacity: All events for lifecycle of circle instance
- Limit: Memory grows unbounded; no event history cleanup; event replay impossible on crash
- Scaling path: Implement event store (PostgreSQL); add event retention policy; implement event sourcing pattern

**File Tree Caching Without Size Limits:**
- Current capacity: Full directory tree cached as JSON
- Limit: Large projects (>10k files) create 10+ MB cache entries
- Scaling path: Implement pagination in file listing; add size-based cache eviction; use streaming responses

## Dependencies at Risk

**Croniter Library Unconstrained:**
- Risk: Accepts arbitrary cron expressions without limits; malformed expressions cause CPU spin
- Impact: Scheduling skill can be DoS'd with invalid cron; blocks scheduler thread
- Migration plan: Add cron expression validation with croniter.is_valid() before accepting; implement timeout in calculate_next_run()

**Pycopg Direct Module with Fallback:**
- Risk: Pycopg availability checked at import time; fallback to psycopg is untested
- Impact: If pycopg unavailable, DatabaseService silently uses None; database operations fail with AttributeError
- Migration plan: Test both code paths; implement explicit fallback with clear error messages; validate on startup

**LSP Plugin System Extensibility:**
- Risk: Plugins loaded from unknown locations; no signature verification
- Impact: Malicious LSP plugins execute with full application privileges
- Migration plan: Implement plugin manifest signing; restrict plugin directories; implement capability-based permissions

## Missing Critical Features

**No Distributed Task Coordination:**
- Problem: Multiple GatheringCircle instances cannot coordinate on same tasks
- Blocks: Horizontal scaling of agent system; multi-instance deployment
- Implementation priority: High - prevents production deployment

**No Pipeline Error Recovery:**
- Problem: Pipeline execution has no retry logic, circuit breakers, or failure handlers
- Blocks: Running resilient multi-step workflows; production reliability
- Implementation priority: High - pipelines currently non-functional anyway

**No Audit Logging for Auth:**
- Problem: No log of login attempts, token generation, or privilege escalation
- Blocks: Security compliance; incident investigation; user accountability
- Implementation priority: Medium - required for regulated deployments

**No Rate Limiting:**
- Problem: API endpoints accept unlimited requests
- Blocks: Protection against DoS; fair resource sharing; API quota enforcement
- Implementation priority: Medium - production security requirement

## Test Coverage Gaps

**Auth Token Lifecycle Not Covered:**
- What's not tested: Token expiry, blacklist cleanup, timing attack resistance, token refresh
- Files: `gathering/api/auth.py`
- Risk: Auth bypass possible through edge cases; timing attacks undetected
- Priority: High

**Pipeline Execution Not Testable:**
- What's not tested: Node execution flow, error propagation, task routing
- Files: `gathering/api/routers/pipelines.py`
- Risk: Broken pipelines undetected; feature unusable in production
- Priority: Critical - blocks pipeline feature entirely

**Database Persistence Not Verified:**
- What's not tested: User creation, conversation history, task tracking
- Files: `gathering/api/auth.py`, `gathering/api/dependencies.py`
- Risk: Data loss on server restart undetected; persistence guarantees not validated
- Priority: Critical - data loss on deployment

**LSP Server Multi-Language Support:**
- What's not tested: Python, JavaScript, Rust LSP fallback behavior
- Files: `gathering/lsp/manager.py`, `gathering/lsp/plugins/`
- Risk: Language support silently broken; plugins fail to load
- Priority: Medium - affects IDE integration

**Event Bus Concurrency:**
- What's not tested: Parallel event handling, race conditions, event ordering
- Files: `gathering/orchestration/events.py`
- Risk: Task state corruption under concurrent activity; deadlocks possible
- Priority: High

**Scheduler Recovery on Restart:**
- What's not tested: Scheduled action persistence, missed run recovery, cleanup after crash
- Files: `gathering/orchestration/scheduler.py`
- Risk: Lost or orphaned scheduled executions; duplicate executions possible
- Priority: High

---

*Concerns audit: 2026-02-10*
