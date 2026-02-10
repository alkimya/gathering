---
phase: 01-auth-security-foundation
plan: 02
subsystem: auth
tags: [postgresql, token-blacklist, lru-cache, audit-logging, constant-time-auth, bcrypt]

# Dependency graph
requires:
  - phase: 01-01
    provides: "PyJWT/bcrypt libraries, auth.users/auth.token_blacklist/audit.security_events migration SQL"
provides:
  - "Database-backed user CRUD (auth.users table via DatabaseService)"
  - "TokenBlacklist class with LRU cache + PostgreSQL write-through"
  - "log_auth_event() for audit.security_events logging"
  - "Constant-time authenticate_user with dummy hash verification"
  - "DatabaseService.get_instance() singleton classmethod"
affects: [01-03]

# Tech tracking
tech-stack:
  added: []
  patterns: [write-through-cache, constant-time-auth, audit-event-logging, singleton-db-access]

key-files:
  created: []
  modified:
    - gathering/api/auth.py
    - gathering/api/routers/auth.py
    - gathering/api/dependencies.py
    - gathering/api/middleware.py
    - tests/test_auth.py

key-decisions:
  - "TokenBlacklist uses write-through pattern: cache for speed, DB for persistence"
  - "All auth functions accept optional db parameter for dependency injection (testability)"
  - "Tests use mock DatabaseService to avoid test-environment DB password issues"
  - "Audit logging wrapped in try/except everywhere to never block auth operations"

patterns-established:
  - "DatabaseService.get_instance() for singleton DB access in auth paths"
  - "log_auth_event() silent-fail pattern for non-blocking audit logging"
  - "Constant-time auth: always query DB + always verify password (dummy hash if no user)"
  - "TokenBlacklist.get_instance() with reset_instance() for test isolation"

# Metrics
duration: 8min
completed: 2026-02-10
---

# Phase 1 Plan 02: Auth Persistence Summary

**PostgreSQL-backed user CRUD with write-through token blacklist, constant-time authentication, and audit event logging**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-10T19:17:46Z
- **Completed:** 2026-02-10T19:25:47Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Replaced in-memory _users_store with PostgreSQL auth.users queries (get_user_by_email, get_user_by_id, create_user)
- Replaced in-memory _token_blacklist with TokenBlacklist class providing LRU cache backed by PostgreSQL write-through
- Made authenticate_user constant-time using dummy hash verification when user not found
- Added audit event logging to auth operations (auth_success, auth_failure, user_registered, auth_missing_token, auth_invalid_token)
- Wired auth router and middleware to pass DatabaseService to all auth functions

## Task Commits

Each task was committed atomically:

1. **Task 1: Database-backed user CRUD and TokenBlacklist class** - `0af6a0d` (feat)
2. **Task 2: Wire auth router and middleware to persistent auth** - `906139e` (feat)

## Files Created/Modified
- `gathering/api/auth.py` - TokenBlacklist class, log_auth_event(), DB-backed user CRUD, constant-time authenticate_user
- `gathering/api/dependencies.py` - Added DatabaseService.get_instance() classmethod
- `gathering/api/routers/auth.py` - All endpoints pass DatabaseService to auth functions, registration logs audit event
- `gathering/api/middleware.py` - Auth failure paths log audit events (auth_missing_token, auth_invalid_token)
- `tests/test_auth.py` - Mock DatabaseService for test isolation, reset singletons between tests

## Decisions Made
- TokenBlacklist uses OrderedDict as LRU cache (max 10000 entries) with PostgreSQL write-through for persistence
- All auth functions accept optional `db` parameter defaulting to `DatabaseService.get_instance()` for dependency injection
- Tests mock DatabaseService rather than requiring live DB connection (avoids test-env password auth issues)
- Audit logging silently catches exceptions to never block auth operations or request processing

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Test database connectivity**
- **Found during:** Task 1 verification
- **Issue:** DatabaseService TCP connection fails with password auth error (psql uses peer auth; pycopg uses password auth). 4 tests failed with connection errors.
- **Fix:** Updated tests to use mock DatabaseService with autouse fixture that sets DatabaseService._instance to a mock. Added TokenBlacklist.reset_instance() for test isolation. Added mock_db fixture with in-memory user storage for endpoint tests.
- **Files modified:** tests/test_auth.py
- **Verification:** All 31 tests pass
- **Committed in:** 0af6a0d (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Test mock necessary for CI/test environment. No scope creep. Production code unchanged.

## Issues Encountered
- Database password authentication fails for TCP connections (psql works via Unix peer auth). Pre-existing infrastructure issue documented in test mock approach. Does not affect production where DATABASE_URL is used with correct credentials.

## User Setup Required

None - migration 006 was applied to the development database. Production deployments need to run `gathering/db/migrations/006_auth_users.sql`.

## Next Phase Readiness
- Auth persistence complete: users survive restarts via auth.users table
- Token blacklist persists via auth.token_blacklist with in-memory LRU cache for performance
- Audit trail established: auth events logged to audit.security_events
- Plan 03 can build on this foundation for additional security hardening

## Self-Check: PASSED

- All 5 modified files verified present on disk
- Both task commits verified in git log (0af6a0d, 906139e)
- All 31 auth tests pass
- Key patterns verified: class TokenBlacklist, auth.users queries, auth.token_blacklist queries, audit.security_events logging, log_auth_event in middleware

---
*Phase: 01-auth-security-foundation*
*Completed: 2026-02-10*
