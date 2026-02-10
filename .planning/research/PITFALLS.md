# Pitfalls Research

**Domain:** Production-readiness consolidation of a multi-agent AI framework (Python/FastAPI/PostgreSQL)
**Researched:** 2026-02-10
**Confidence:** HIGH (grounded in actual codebase analysis of GatheRing source files, CONCERNS.md audit, and established Python/FastAPI patterns)

## Critical Pitfalls

### Pitfall 1: Auth Migration Breaks Existing Sessions and API Contracts

**What goes wrong:**
Replacing the in-memory `_users_store` dict (auth.py line 343) with database queries changes response timing, error modes, and potentially return shapes. Existing tests that mock the in-memory store break. If the `UserResponse` schema changes (e.g., `id` goes from UUID string to integer), every client that parses user IDs breaks silently. The dashboard stores JWT tokens that reference in-memory user IDs -- after migration, those tokens decode to user IDs that don't exist in the database, causing 401 cascades.

**Why it happens:**
The in-memory store uses `str(uuid.uuid4())` for user IDs (auth.py line 375). A database migration will likely use auto-incrementing integers or a different UUID format. Developers replace the storage layer without freezing the ID format contract, creating an invisible API break. Additionally, `get_user_by_email()` and `get_user_by_id()` are async functions that currently do synchronous dict lookups -- switching to actual async DB calls changes error propagation paths.

**How to avoid:**
1. Freeze the `UserResponse` schema as the contract BEFORE touching the storage layer. Write contract tests that assert response shapes.
2. Keep user ID format as `str` in the API layer regardless of DB primary key type. Map at the persistence boundary.
3. Write a migration script that seeds the database with any users from the in-memory store (handle the dev-to-prod transition).
4. Add a `/auth/me` integration test that verifies token decode -> user fetch -> response shape as a single flow. This test must pass before AND after the migration.
5. The token blacklist migration (in-memory dict to DB table) must happen atomically with the user store migration -- if you do one without the other, tokens reference inconsistent state.

**Warning signs:**
- Dashboard returns 401 after server restart (tokens reference nonexistent users)
- Test suite shows failures in auth tests that previously passed with mocks
- User registration succeeds but subsequent login fails (ID format mismatch)
- `get_user_by_id` returns `None` for users that were just created

**Phase to address:**
Phase 1 (Auth Hardening) -- this is the foundation. Every other feature depends on auth working correctly. Do this first, with contract tests as the acceptance gate.

---

### Pitfall 2: Sync-to-Async DB Migration Blocks the Event Loop

**What goes wrong:**
Every `async def` router in `gathering/api/routers/` currently calls `db.execute()` and `db.execute_one()` synchronously (the DatabaseService wraps SQLAlchemy's synchronous engine). In FastAPI, when you declare `async def` endpoints, they run on the main asyncio event loop. A synchronous DB call inside an `async def` handler blocks the ENTIRE event loop for the duration of the query -- no other request can be processed. This is worse than using `def` (which FastAPI runs in a threadpool automatically).

**Why it happens:**
This is the single most common FastAPI performance mistake. Developers see `async def` as "faster" and use it everywhere, not realizing that `async def` + synchronous I/O = event loop starvation. The current codebase has this pattern across ALL routers (confirmed: models.py, pipelines.py, workspace.py, agents.py, etc. all use `async def` with synchronous `db.execute()`). The fix seems simple (just add `await`) but requires changing the entire database layer to actually be async.

**How to avoid:**
1. Do NOT attempt a gradual migration where some calls are async and some are sync. This creates two code paths through the database layer that interact unpredictably with connection pooling.
2. Strategy A (Recommended): Replace the DatabaseService with an async implementation using `asyncpg` (already in dependencies). Create `AsyncDatabaseService` with `await execute()`. Migrate all routers in one pass.
3. Strategy B (Interim): Change all `async def` router functions to `def` (plain functions). FastAPI will run them in a threadpool, which actually FIXES the blocking problem without changing the DB layer. Then migrate to async DB later.
4. NEVER use `asyncio.run()` or `loop.run_in_executor()` as permanent solutions inside async handlers -- they add complexity and hide the real problem.
5. Test with concurrent load. A single-user test will never catch event loop blocking. Use `locust` or `httpx` with concurrent requests to verify.

**Warning signs:**
- Response latency increases linearly with concurrent users (not just load)
- WebSocket connections drop during DB-heavy operations
- Health check endpoint becomes slow when other endpoints are under load
- `asyncio` warning logs about slow callbacks (> 100ms)

**Phase to address:**
Phase 2 (Performance) -- but start with Strategy B (sync def) in Phase 1 as a quick fix. The full async migration is Phase 2 work because it requires changing the database layer, connection pooling, and transaction management.

---

### Pitfall 3: Pipeline Execution Without Timeouts or Resource Limits Enables Infinite Loops

**What goes wrong:**
The pipeline system (pipelines.py line 413) currently fakes completion. When real execution is implemented, a pipeline with cyclic node connections runs forever. A pipeline that calls an LLM agent in a loop burns API credits unboundedly. A pipeline node that spawns background tasks without limits exhausts memory. There is no validation of pipeline node configurations (CONCERNS.md confirms: "Accepts arbitrary node configs; no validation of node connections; JSONB storage allows invalid structure").

**Why it happens:**
Pipeline execution engines are deceptively complex. The "happy path" (linear sequence of nodes) is easy to implement. But real pipelines have branches, loops, error handlers, and conditional flows. Without upfront constraints, developers implement the happy path and discover the edge cases in production when a user creates a cyclic pipeline.

**How to avoid:**
1. Implement pipeline validation BEFORE execution: check for cycles (topological sort), validate node types, enforce maximum node count per pipeline (e.g., 50).
2. Every pipeline run gets a hard timeout (configurable, default 30 minutes). Use `asyncio.wait_for()` wrapping the entire execution.
3. Every individual node execution gets a timeout (configurable per node type, default 5 minutes for LLM calls, 60 seconds for actions).
4. Track execution depth. If a node has been visited more than `max_iterations` times (default: 3), abort the pipeline with a clear error.
5. Implement a cost budget: total LLM tokens consumed per pipeline run, with a hard cap.
6. Pipeline runs must be cancellable. Store the `asyncio.Task` reference and expose a cancel endpoint.
7. Log every node entry/exit to the pipeline run's `logs` JSONB field for debugging.

**Warning signs:**
- Pipeline run status stuck in "running" indefinitely
- Memory usage growing during pipeline execution
- LLM API costs spike without corresponding user activity
- Background task executor queue growing unboundedly

**Phase to address:**
Phase 3 (Feature Implementation) -- but pipeline validation (cycle detection, schema validation) should be Phase 2 because it prevents data corruption. Execution with timeouts is Phase 3.

---

### Pitfall 4: 262 Bare Exception Catches Create Silent Failure Cascades

**What goes wrong:**
The codebase has 262 `except Exception` catches across 74 files (confirmed by grep). Most of these log the error and return a default value (False, None, empty list) or silently continue. When a real bug occurs -- say, a database connection failure -- it gets caught 6 layers deep, logged as a warning, and the caller receives `None` instead of an error. The user sees "no results" instead of "service unavailable." Debugging requires correlating logs across multiple catch points to find the original failure.

**Why it happens:**
Bare exception catches accumulate naturally during development. Each developer adds `try/except Exception` to prevent crashes during demos. Over time, these become load-bearing: removing them might surface exceptions that no caller handles. The codebase already has a proper exception hierarchy (`GatheringError` with 10+ subclasses) but it's underused -- most code catches `Exception` instead of specific types.

**How to avoid:**
1. Do NOT attempt to fix all 262 catches in one pass. This will surface hundreds of unhandled exceptions and break the test suite catastrophically.
2. Categorize the catches into tiers:
   - **Tier 1 (Fix immediately):** Catches in auth paths, database operations, and security-critical code. These mask real failures. (~30 catches in auth.py, dependencies.py, database.py)
   - **Tier 2 (Fix in feature phase):** Catches in pipeline, scheduler, and orchestration code. Fix these when implementing the features they guard.
   - **Tier 3 (Fix last):** Catches in skill modules, LSP plugins, and UI-facing routers. These are defensive and less dangerous.
3. For each catch you fix: replace `except Exception` with the specific exception types that can actually occur. Add the specific types to catch, and let unexpected exceptions propagate.
4. Add a linting rule (ruff S110 or custom) that flags new bare exception catches in code review.
5. Create a `@safe_handler` decorator for EventBus handlers where broad catches are actually appropriate (you don't want one bad handler to crash all subscribers).

**Warning signs:**
- Bugs reported as "feature doesn't work" instead of "got an error"
- Logs show errors that never surface to the user
- Tests pass but the feature doesn't actually work (because errors are swallowed)
- Debugging requires log correlation across 3+ files to find root cause

**Phase to address:**
Tier 1 catches in Phase 1 (Auth + Security). Tier 2 catches in Phase 3 (Feature Implementation). Tier 3 catches in Phase 4 (Polish). Add the linting rule in Phase 1 to prevent new bare catches.

---

### Pitfall 5: SQL Injection Fix Breaks Dynamic Query Builders

**What goes wrong:**
The codebase uses f-string SQL in several places (confirmed: pipelines.py line 311, schedules.py line 390, dependencies.py line 424, projects.py line 402). These are all in dynamic UPDATE builders that construct `SET` clauses from variable column lists. Naively replacing these with parameterized queries breaks because you cannot parameterize column names or SET clause structure -- only values. A developer who doesn't understand this distinction will either: (a) leave the injection in place, or (b) break the UPDATE functionality trying to parameterize it.

**Why it happens:**
The dynamic UPDATE pattern (`SET {', '.join(updates)}`) is actually safe IF the column names come from a hardcoded allowlist (which they do in this codebase -- the column names are hardcoded strings like `"name = %(name)s"`). The SQL injection risk is NOT in the f-string SET clause construction. The risk is if user input ever reaches the column name position. The actual f-string SQL injection risk is in any place where user-provided values are interpolated into SQL without parameterization.

**How to avoid:**
1. Audit EVERY f-string SQL query to determine if the interpolated parts are column names (safe, from code) or values (unsafe, from user input).
2. For dynamic UPDATE builders: keep the f-string for SET clause construction BUT validate that column names come from an explicit allowlist. Add a helper function: `def safe_update_builder(allowed_columns: set, updates: dict) -> tuple[str, dict]`.
3. For actual injection risks: convert to parameterized queries. Use `%(param)s` placeholders (which most of the codebase already does correctly).
4. Add a SQL audit test that greps for f-string SQL and asserts each instance is in an approved list. This prevents regression.
5. Consider migrating the dynamic UPDATE patterns to SQLAlchemy Core `update().values()` which handles parameterization automatically.

**Warning signs:**
- UPDATE endpoints return 500 errors after "fix" (broken SET clause construction)
- Tests that update partial fields start failing
- SQL syntax errors in logs mentioning malformed SET clauses

**Phase to address:**
Phase 1 (Security) -- but with surgical precision. Do not bulk-replace f-strings. Audit each one individually.

---

### Pitfall 6: Schedule Execution Runs Duplicate Actions After Recovery

**What goes wrong:**
The scheduler tracks running actions in-memory (`_running_actions: Set[int]`, scheduler.py line 239). When the server restarts, this set is empty. If a scheduled action was mid-execution when the server crashed, the scheduler doesn't know it already ran. On recovery, it sees the action is "due" and executes it again. For idempotent actions (like "check status"), this is harmless. For non-idempotent actions (like "send notification" or "execute pipeline"), this causes duplicate execution.

**Why it happens:**
The scheduler was designed as an in-memory-only system. The `_running_actions` set, `_actions` dict, and `_event_subscriptions` dict are all in-memory with no persistence. Adding persistence after the fact is harder than designing for it upfront because you need to handle partial writes (action started but completion wasn't recorded).

**How to avoid:**
1. Persist schedule execution state to the `circle.scheduled_actions` table. Add columns: `last_execution_id` (UUID), `execution_status` (running/completed/failed), `execution_started_at`.
2. On startup recovery: query for actions with `execution_status = 'running'`. These are the crashed-mid-execution actions. Mark them as `failed` (not `completed`) and let the normal retry logic handle them.
3. Use a "claim" pattern: before executing, write a row to an `execution_log` table with status `claimed`. After completion, update to `completed`. This makes execution idempotent -- if the same execution_id is already claimed, skip it.
4. For truly critical actions (send_notification, execute_pipeline), implement idempotency keys at the action level.
5. Add timezone-aware scheduling. The current code uses `datetime.utcnow()` (schedules.py line 487) which is timezone-naive and deprecated. Use `datetime.now(timezone.utc)` consistently.

**Warning signs:**
- Users report receiving duplicate notifications after server restart
- Pipeline runs appear twice in the run history
- Scheduled action execution_count increments by 2 instead of 1
- Actions that should run daily run twice on days with server restarts

**Phase to address:**
Phase 3 (Feature Implementation) -- schedule execution is a stub today, so build it correctly from the start rather than retrofitting persistence.

---

### Pitfall 7: Test Suite Becomes Unreliable During Consolidation (1071 Tests)

**What goes wrong:**
With 1071 existing tests, consolidation work inevitably breaks tests that were testing the OLD (stub) behavior. For example: tests that assert pipeline.run() returns "completed" immediately will fail when real execution is implemented (because now it returns "running" and completes asynchronously). Tests that mock the in-memory user store will fail when the store becomes a database. Developers start skipping broken tests, adding `@pytest.mark.skip`, or worse -- changing assertions to match new behavior without understanding if the new behavior is actually correct.

**Why it happens:**
The existing tests test the stub implementations as if they were real. The tests are passing today, but they're testing the WRONG behavior. When you fix the implementation, the tests correctly fail -- but now you can't tell the difference between "test failed because I fixed a bug" and "test failed because I introduced a regression."

**How to avoid:**
1. Before ANY code changes, tag all existing tests by category:
   - `@pytest.mark.stub` -- tests that verify stub behavior (will intentionally break)
   - `@pytest.mark.contract` -- tests that verify API contracts (must never break)
   - `@pytest.mark.unit` -- tests that verify isolated logic (should not break)
2. Create a CI configuration that runs `pytest -m "not stub"` as the gate. Stub-tagged tests are expected to fail and are tracked separately.
3. For each stub you replace, write the NEW tests FIRST (TDD). The new tests define correct behavior. Then implement. Then update or remove the stub tests.
4. Never use `@pytest.mark.skip` without a linked issue/ticket. Every skip must have a plan to unskip.
5. Track test count: it should go UP during consolidation (new tests added), not down (tests deleted or skipped).
6. Run the full suite after every consolidation PR. Do not batch multiple changes -- each change should have a clear, attributable impact on the test results.

**Warning signs:**
- Number of skipped tests increasing
- Test suite runtime dropping (tests removed or skipped, not faster)
- PR descriptions say "updated tests to match new behavior" without explaining what the new behavior is
- CI pipeline has `|| true` or `--no-fail` flags

**Phase to address:**
Phase 0 (Pre-work) -- test tagging and CI configuration should happen BEFORE any consolidation code changes. This is a 1-2 day task that prevents weeks of confusion.

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Using `run_in_executor()` instead of async DB driver | Quick fix for event loop blocking | Two code paths through DB layer, connection pool contention, harder to reason about transactions | Never as permanent solution. Acceptable as 1-sprint interim while building async DB layer |
| Catching `Exception` in new code "just to be safe" | Prevents crashes during development | Masks real bugs, makes debugging exponentially harder | Only in event bus handlers where isolation is required. Everywhere else: never |
| Skipping pipeline validation (cycle detection) | Ship pipeline execution faster | Users create cyclic pipelines that infinite-loop in production | Never. Validation is cheaper than debugging infinite loops |
| Using `datetime.utcnow()` instead of `datetime.now(timezone.utc)` | Shorter to type, existing code uses it | Timezone-naive datetimes cause comparison bugs, scheduling errors across timezones | Never. Python deprecates `utcnow()` for this reason |
| Keeping in-memory caches without size limits | Fast access, simple implementation | Memory exhaustion on long-running servers (token blacklist, file tree cache, event history) | Only for caches with natural expiry under 10 minutes AND bounded entry count |
| Adding `DISABLE_AUTH=true` escape hatch | Easy local development | Accidentally deployed to production, complete auth bypass | Development only. Must be blocked in production via startup validation |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| PostgreSQL async (asyncpg) | Using SQLAlchemy sync engine with asyncpg driver | Use `create_async_engine()` from `sqlalchemy.ext.asyncio`. The sync `create_engine()` cannot use asyncpg. These are completely separate code paths. |
| Token blacklist in DB | Querying the blacklist table on EVERY request (adding DB round-trip to auth) | Use a two-layer cache: in-memory LRU with short TTL (30s) backed by DB table. Blacklist additions write-through to both. This maintains sub-ms auth checks while ensuring persistence. |
| Croniter schedule parsing | Trusting user-provided cron expressions without validation or timeout | Call `croniter.is_valid(expression)` before storing. Wrap `croniter.get_next()` in a timeout. Some pathological expressions cause CPU-intensive computation. |
| Event bus to WebSocket bridge | Broadcasting every event to every WebSocket client | Filter events by subscription. Send only events the client subscribed to. Batch rapid events (e.g., task progress) into periodic updates (every 500ms max). |
| LLM API calls in pipelines | No timeout on LLM calls, no cost tracking | Wrap every LLM call with `asyncio.wait_for(timeout=120)`. Track tokens consumed per pipeline run. Abort pipeline if budget exceeded. |
| Alembic migrations with schema changes | Running migrations that alter tables while the application is serving traffic | Use online DDL patterns. Add new columns as nullable first, backfill, then add constraints. Never rename columns in production -- add new, migrate data, drop old. |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Sync DB calls in async handlers (current state) | Latency proportional to concurrent users, not load | Migrate to async DB or use `def` handlers (FastAPI threadpool) | 5+ concurrent requests (~immediately under real usage) |
| N+1 queries in circle member retrieval | Circle page load time grows linearly with member count | Eager-load with JOINs: `SELECT agents.*, models.*, providers.* FROM circle_members JOIN ...` | 10+ circle members (noticeable), 50+ (unusable) |
| Unbounded in-memory token blacklist | Memory grows without limit until cleanup interval (3600s) | Add size cap (LRU eviction) + persist to DB. Cleanup on every blacklist_token() call, not just hourly | 10K+ token revocations (high-traffic auth) |
| Event bus `create_task()` per emission | Task saturation under high event volume, asyncio task count unbounded | Implement event queue with batch processing (flush every 100ms or 50 events) | 100+ events/second (e.g., during active circle collaboration) |
| File tree cached as single JSON blob | Cache miss requires full directory traversal; large JSON serialization blocks event loop | Paginated file listing, incremental cache updates, streaming response for large directories | 10K+ files in workspace |
| Pipeline runs storing full logs in JSONB | Row size grows with pipeline complexity; queries slow as log arrays grow | Separate `pipeline_run_logs` table with foreign key. Index by run_id + timestamp. | 100+ node executions per pipeline run |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Fixing SQL injection by removing f-strings but breaking dynamic UPDATE builders | UPDATE endpoints stop working, developers revert the fix, injection remains | Understand that f-string SET clause construction from hardcoded column names is safe. Focus on parameterizing VALUES, not column names. |
| Making token blacklist persistent but not cleaning up expired entries | Blacklist table grows unboundedly, eventually slowing every auth check | Add a `expires_at` column with index. Run periodic cleanup (pg_cron or application-level). |
| Implementing pipeline execution without sandboxing agent tool calls | A pipeline node that executes code tools can access the server filesystem | Pipeline-executed tools must run with restricted permissions. Enforce `SkillPermission` checks per pipeline context, not just per user. |
| Adding rate limiting per-IP instead of per-user | Users behind NAT share rate limits; attackers use distributed IPs to bypass | Rate limit by authenticated user ID (primary), fall back to IP for unauthenticated endpoints. Use sliding window, not fixed window. |
| Logging full SQL queries including parameter values | Database passwords, user data, API keys in log files | Log query templates without parameter values. Use structured logging with parameter redaction. |
| `DISABLE_AUTH=true` reachable in production | Complete authentication bypass | Add startup check: if `GATHERING_ENV == "production"` and `DISABLE_AUTH == True`, refuse to start. Hard fail, not warning. |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Pipeline execution returns 201 immediately but runs fail silently in background | User thinks pipeline succeeded when it didn't | Return 202 Accepted with a `run_id`. Provide `/runs/{id}/status` endpoint. Push status updates via WebSocket. |
| Auth errors return generic 401 for all failure modes | User can't distinguish expired token from revoked token from invalid credentials | Use `WWW-Authenticate` header with descriptive error: `Bearer error="invalid_token", error_description="Token expired"`. Keep 401 status but differentiate in body. |
| Schedule timezone assumed as UTC without user configuration | Users in non-UTC timezones get unexpected execution times | Store timezone per schedule. Display next_run in user's timezone. Default to UTC but require explicit acknowledgment. |
| Replacing in-memory auth causes all active sessions to invalidate | Every user forced to re-login after server update | Implement token migration: on first request with old-format token, issue a new token transparently. Or ensure token format doesn't change -- only the storage backend changes. |
| Bare exceptions swallowed in agent chat endpoint | User sends message, gets no response, no error | Agent chat endpoint must always return a response. If LLM fails, return a structured error message, not silence. |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Auth DB migration:** Often missing -- unique constraint on email (in-memory dict used email as key, DB needs explicit constraint), case-insensitive email lookup (LOWER index), password hash column length (bcrypt needs 72+ chars)
- [ ] **Pipeline execution:** Often missing -- cancellation support (what happens when user cancels mid-run?), partial failure handling (3 of 5 nodes succeeded, now what?), result propagation between nodes (node A output is node B input)
- [ ] **Schedule execution:** Often missing -- missed run recovery (server was down during scheduled time), overlapping execution prevention (previous run still going when next is due), execution timeout (action runs forever)
- [ ] **SQL injection fix:** Often missing -- testing with actual malicious payloads, not just "parameterized queries work". Need negative tests: `'; DROP TABLE users; --` in every user-input field that reaches SQL.
- [ ] **Async DB migration:** Often missing -- transaction isolation (async connections need explicit transaction management), connection pool exhaustion handling (what happens when pool is full?), migration rollback plan (if async breaks, can you revert to sync?)
- [ ] **Token blacklist persistence:** Often missing -- cross-instance consistency (two servers must agree on blacklist), cache invalidation (in-memory cache stale after DB update), startup hydration (load active blacklist entries on boot)
- [ ] **Rate limiting:** Often missing -- per-endpoint configuration (auth endpoints need stricter limits), rate limit headers in response (X-RateLimit-Remaining), graceful degradation (429 with Retry-After header, not connection drop)
- [ ] **Exception handling cleanup:** Often missing -- structured error responses for every exception type (not just 500 Internal Server Error), error correlation IDs in responses (so users can report specific errors), monitoring alerts on new exception types

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Auth migration breaks active sessions | LOW | Tokens are self-contained JWTs. If the signing key hasn't changed, old tokens still decode. Issue: the user IDs in tokens must still resolve. Recovery: add a compatibility layer that maps old-format IDs to new DB IDs. |
| Event loop blocked by sync DB calls | LOW | Change `async def` to `def` in affected routers. FastAPI handles the rest via threadpool. This is a one-line change per router function. |
| Pipeline infinite loop in production | MEDIUM | Kill the pipeline run's asyncio task. Mark run as "failed" in DB. Add the timeout enforcement, then re-run. Requires the Task reference to be stored (hence why cancellation support matters). |
| Duplicate schedule execution after crash | MEDIUM | Query execution log for recent completions. Deduplicate by comparing `execution_id` + `action_id` + timestamp window. Mark duplicates as "duplicate" in log. Notify affected users if the action had side effects. |
| Test suite destabilized during consolidation | HIGH | Stop all consolidation work. Revert to last green build. Tag tests as described in Pitfall 7. Rebuild confidence in the test suite before resuming. This costs 2-3 days but prevents weeks of confusion. |
| SQL injection exploited in production | HIGH | Immediately patch the vulnerable endpoints. Audit database for signs of injection (unexpected data, dropped tables). Rotate all credentials. Review access logs for exploitation evidence. Disclose per security policy. |
| Bare exception masking data corruption | HIGH | This is the hardest to recover from because you don't know what was corrupted or when. Run data integrity checks across all tables. Compare against backups. The 262 catch sites mean corruption could have been happening silently for weeks. |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Auth migration breaks sessions (P1) | Phase 1: Auth Hardening | Contract tests pass. Dashboard login works. Token decode->user fetch->response is end-to-end tested. |
| Sync DB blocks event loop (P2) | Phase 1: Quick fix (sync def). Phase 2: Full async migration | Load test with 20 concurrent requests. P95 latency under 500ms. WebSocket stays connected during load. |
| Pipeline infinite loops (P3) | Phase 2: Validation. Phase 3: Execution with timeouts | Pipeline with cycle rejected at creation. Running pipeline cancelled after timeout. No orphaned "running" pipelines after 24h. |
| Bare exception cascades (P4) | Phase 1: Tier 1 (auth/security). Phase 3: Tier 2 (features). Phase 4: Tier 3 (polish) | `ruff` rule blocks new bare catches. Exception count trending down per phase. No silent failures in auth or DB paths. |
| SQL injection fix breaks queries (P5) | Phase 1: Security audit | Negative security tests pass (injection payloads rejected). All UPDATE endpoints still function correctly. |
| Duplicate schedule execution (P6) | Phase 3: Schedule implementation | Execution log shows exactly 1 entry per scheduled time. Server restart doesn't trigger re-execution of completed actions. |
| Test suite unreliable (P7) | Phase 0: Pre-work (test tagging) | CI runs `pytest -m "not stub"` as gate. Stub test count tracked. Total test count increases each phase. |

## Sources

- Codebase audit: `/home/loc/workspace/gathering/.planning/codebase/CONCERNS.md` (2026-02-10)
- Architecture analysis: `/home/loc/workspace/gathering/.planning/codebase/ARCHITECTURE.md` (2026-02-10)
- Stack analysis: `/home/loc/workspace/gathering/.planning/codebase/STACK.md` (2026-02-10)
- Direct source inspection: `gathering/api/auth.py` (in-memory store lines 343-387, token blacklist lines 177-269)
- Direct source inspection: `gathering/api/routers/pipelines.py` (stub execution line 413, f-string SQL line 311)
- Direct source inspection: `gathering/skills/gathering/schedules.py` (stub run_now line 477, f-string SQL line 390)
- Direct source inspection: `gathering/orchestration/scheduler.py` (in-memory state lines 236-241)
- Direct source inspection: `gathering/db/database.py` (synchronous engine, no async support)
- Grep analysis: 262 `except Exception` occurrences across 74 files in `gathering/` directory
- Grep analysis: f-string SQL in pipelines.py, schedules.py, dependencies.py, projects.py
- FastAPI documentation on async def vs def behavior (HIGH confidence, well-established pattern)
- SQLAlchemy async documentation on `create_async_engine` requirements (HIGH confidence, official docs)
- Python datetime deprecation of `utcnow()` (HIGH confidence, PEP 495 and Python docs)

---
*Pitfalls research for: GatheRing production-readiness consolidation*
*Researched: 2026-02-10*
