---
phase: 04-performance-optimization
plan: 05
subsystem: api
tags: [slowapi, rate-limiting, fastapi, security, brute-force-protection]

# Dependency graph
requires:
  - phase: 04-02
    provides: "slowapi limiter singleton, tier constants (TIER_AUTH/WRITE/READ/HEALTH), create_app rate limit toggle"
provides:
  - "Per-endpoint @limiter.limit() decorators on all 206 route handlers across 18 router files"
  - "Custom 429 handler with Retry-After and X-RateLimit-* headers"
  - "Rate limit tier integration tests proving 429 + header behavior"
affects: [api, auth, deployment]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-endpoint rate limit decoration: @router.method() -> @limiter.limit(TIER_X) -> async def fn(request: Request, ...)"
    - "Custom 429 handler extracting window stats for Retry-After and X-RateLimit-* headers"
    - "Rate limit test pattern: raise_server_exceptions=False + limiter storage reset between tests"

key-files:
  created:
    - tests/test_rate_limit_tiers.py
  modified:
    - gathering/api/main.py
    - gathering/api/routers/auth.py
    - gathering/api/routers/health.py
    - gathering/api/routers/agents.py
    - gathering/api/routers/circles.py
    - gathering/api/routers/conversations.py
    - gathering/api/routers/dashboard.py
    - gathering/api/routers/goals.py
    - gathering/api/routers/models.py
    - gathering/api/routers/pipelines.py
    - gathering/api/routers/projects.py
    - gathering/api/routers/scheduled_actions.py
    - gathering/api/routers/settings.py
    - gathering/api/routers/background_tasks.py
    - gathering/api/routers/memories.py
    - gathering/api/routers/tools.py
    - gathering/api/routers/workspace.py
    - gathering/api/routers/lsp.py
    - gathering/api/routers/plugins.py

key-decisions:
  - "Custom _rate_limit_handler replaces slowapi's default handler to inject Retry-After + X-RateLimit-* headers on 429 responses"
  - "SlowAPIMiddleware not used (conflicts with decorator-based header injection); exception handler approach sufficient"
  - "headers_enabled left as False on Limiter to avoid decorator crash on non-Response returns; headers only on 429 via custom handler"

patterns-established:
  - "Rate limit tiers: TIER_AUTH=5/min for login/register, TIER_HEALTH=300/min for health, TIER_WRITE=30/min for mutations, TIER_READ=120/min for reads"
  - "Every rate-limited endpoint MUST have request: Request in its signature (slowapi requirement)"

# Metrics
duration: 12min
completed: 2026-02-11
---

# Phase 4 Plan 5: Rate Limit Tier Enforcement Summary

**206 per-endpoint @limiter.limit() decorators across 18 router files with TIER_AUTH/WRITE/READ/HEALTH tiers, custom 429 handler with Retry-After headers, and 8 integration tests proving enforcement**

## Performance

- **Duration:** 12 min
- **Started:** 2026-02-11T00:09:44Z
- **Completed:** 2026-02-11T00:21:23Z
- **Tasks:** 2
- **Files modified:** 20

## Accomplishments
- All 206 route handlers across 18 router files decorated with correct rate limit tier
- Auth endpoints (login, register) protected with TIER_AUTH (5/minute) for brute-force prevention
- Health endpoints use TIER_HEALTH (300/minute), mutation endpoints use TIER_WRITE (30/minute), read endpoints use TIER_READ (120/minute)
- Custom 429 handler returns Retry-After, X-RateLimit-Limit, X-RateLimit-Remaining, and X-RateLimit-Reset headers
- 8 integration tests prove real 429 enforcement with actual slowapi middleware

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix mangled variable names in rate-limited router endpoints** - `b408a8a` (fix)
2. **Task 2: Add rate limit tier integration tests and custom 429 handler** - `f6b2b68` (feat)

**Plan metadata:** pending (docs: complete plan)

## Files Created/Modified
- `tests/test_rate_limit_tiers.py` - 8 integration tests for rate limit tier enforcement (429, Retry-After, tier independence)
- `gathering/api/main.py` - Custom _rate_limit_handler with Retry-After and X-RateLimit-* headers
- `gathering/api/routers/memories.py` - Fixed mangled variable names (recall_recall_request -> recall_request, etc.)
- `gathering/api/routers/lsp.py` - Fixed mangled variable names (lsp_lsp_lsp_lsp_request -> lsp_request)
- `gathering/api/routers/tools.py` - Fixed mangled variable names (toggle_bulk_request -> toggle_request/bulk_request)
- `gathering/api/routers/plugins.py` - Fixed mangled variable names (load_create_request -> load_request/create_request)
- 14 additional router files with @limiter.limit() decorators (applied in plan 04-04)

## Decisions Made
- **Custom 429 handler over default slowapi handler:** Default handler does not inject Retry-After when headers_enabled=False. Custom handler extracts window stats from limiter storage and always includes Retry-After + X-RateLimit-* headers on 429 responses.
- **SlowAPIMiddleware not used:** Adding SlowAPIMiddleware alongside the decorator approach causes conflicts (decorator tries to inject headers on Response objects that don't exist in FastAPI dict-return endpoints). Exception handler approach is sufficient.
- **raise_server_exceptions=False for tests:** Auth/login endpoint hits DB (which is unavailable in test env), but rate limiter checks run before endpoint body. Using raise_server_exceptions=False allows tests to see 500s that still count toward rate limit, then verify 429 on the 6th request.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed mangled variable names in 4 router files**
- **Found during:** Task 1 (verification of rate limit decorators applied in plan 04-04)
- **Issue:** Automation script from plan 04-04 mangled variable names when renaming `request` parameters to avoid duplicates with starlette `request: Request`. Variables like `recall_recall_search_request`, `lsp_lsp_lsp_lsp_request`, `toggle_bulk_request`, and `load_create_request` would cause NameError at runtime.
- **Fix:** Corrected all variable references to use the proper parameter names (recall_request, lsp_request, toggle_request, bulk_request, load_request, create_request)
- **Files modified:** memories.py, lsp.py, tools.py, plugins.py
- **Verification:** `grep -r "recall_recall\|lsp_lsp\|toggle_bulk\|load_create\|search_recall"` returns no matches; app creates without errors
- **Committed in:** b408a8a (Task 1 commit)

**2. [Rule 2 - Missing Critical] Custom 429 handler with Retry-After header**
- **Found during:** Task 2 (rate limit test development)
- **Issue:** slowapi's default `_rate_limit_exceeded_handler` only injects Retry-After when `headers_enabled=True` on the Limiter. But enabling headers causes the decorator to crash on dict-return endpoints. Without Retry-After, clients have no guidance on when to retry.
- **Fix:** Created custom `_rate_limit_handler` in main.py that extracts window stats from limiter storage and always includes Retry-After, X-RateLimit-Limit, X-RateLimit-Remaining, and X-RateLimit-Reset headers on 429 responses.
- **Files modified:** gathering/api/main.py
- **Verification:** Integration test `test_429_response_has_retry_after_header` passes; Retry-After value is positive integer
- **Committed in:** f6b2b68 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 missing critical)
**Impact on plan:** Both fixes essential for correctness. Bug fix prevents NameError on 4 router files. Custom handler ensures proper HTTP 429 semantics with Retry-After header. No scope creep.

## Issues Encountered
- DB unavailable in test environment (pre-existing PostgreSQL auth failure for user 'loc'). Worked around by using `raise_server_exceptions=False` in test client and testing against endpoints that fail with 500 (rate limit still counts requests regardless of endpoint outcome).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Rate limiting fully operational across all endpoints
- Plan 04-05 completes Phase 4 (Performance Optimization)
- All rate limit tiers enforced: TIER_AUTH (5/min), TIER_WRITE (30/min), TIER_READ (120/min), TIER_HEALTH (300/min)
- Ready for Phase 5 or deployment

## Self-Check: PASSED

- FOUND: tests/test_rate_limit_tiers.py
- FOUND: gathering/api/main.py
- FOUND: gathering/api/routers/memories.py
- FOUND: gathering/api/routers/lsp.py
- FOUND: gathering/api/routers/tools.py
- FOUND: gathering/api/routers/plugins.py
- FOUND: commit b408a8a (fix: mangled variable names)
- FOUND: commit f6b2b68 (feat: rate limit tests + custom handler)

---
*Phase: 04-performance-optimization*
*Completed: 2026-02-11*
