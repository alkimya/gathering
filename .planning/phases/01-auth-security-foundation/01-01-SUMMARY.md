---
phase: 01-auth-security-foundation
plan: 01
subsystem: auth
tags: [jwt, pyjwt, bcrypt, structlog, correlation-id, postgresql, migration]

# Dependency graph
requires: []
provides:
  - "PyJWT-based JWT operations (import jwt replacing python-jose)"
  - "Direct bcrypt password hashing (replacing passlib CryptContext)"
  - "AuthenticationError, AuthorizationError, DatabaseError exception classes"
  - "structlog JSON logging with correlation ID support"
  - "Migration 006: auth.users, auth.token_blacklist, audit.security_events tables"
  - "asgi-correlation-id middleware on FastAPI app"
affects: [01-02, 01-03]

# Tech tracking
tech-stack:
  added: [PyJWT, asgi-correlation-id]
  removed: [python-jose, passlib]
  patterns: [direct-bcrypt-hashing, structlog-json-logging, correlation-id-middleware]

key-files:
  created:
    - gathering/core/logging.py
    - gathering/db/migrations/006_auth_users.sql
  modified:
    - gathering/api/auth.py
    - gathering/core/exceptions.py
    - gathering/api/main.py
    - pyproject.toml

key-decisions:
  - "PyJWT[crypto]>=2.9 chosen over python-jose (maintained, smaller, identical API for HS256)"
  - "Direct bcrypt.hashpw/checkpw used instead of passlib CryptContext (eliminates wrapper dependency)"
  - "bcrypt upper bound unpinned to >=4.0.0 (passlib compatibility constraint no longer needed)"
  - "CorrelationIdMiddleware added last in middleware stack so it runs first in request lifecycle"
  - "structlog configured with JSON output in production, console renderer in debug mode"

patterns-established:
  - "Exception hierarchy: domain-specific subclasses of GatheringError with typed attributes"
  - "Logging: structlog.configure() called once at app startup via configure_logging()"
  - "Auth tables in 'auth' schema, audit tables in 'audit' schema (PostgreSQL schema separation)"

# Metrics
duration: 4min
completed: 2026-02-10
---

# Phase 1 Plan 01: Auth Foundation Summary

**PyJWT/bcrypt library swap with structured logging, exception hierarchy, and auth migration SQL**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-10T19:10:42Z
- **Completed:** 2026-02-10T19:14:57Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Swapped python-jose to PyJWT and passlib to direct bcrypt with full backward compatibility (all 31 tests pass unchanged)
- Added AuthenticationError, AuthorizationError, DatabaseError exception classes to the framework hierarchy
- Created structlog configuration with JSON output and correlation ID middleware integration
- Created migration 006 defining auth.users, auth.token_blacklist, and audit.security_events tables

## Task Commits

Each task was committed atomically:

1. **Task 1: Library swap -- PyJWT, bcrypt direct, dependency updates** - `991af49` (feat)
2. **Task 2: Exception classes, structured logging, and auth migration SQL** - `70c407e` (feat)

## Files Created/Modified
- `pyproject.toml` - Updated dependencies: PyJWT replaces python-jose, passlib removed, bcrypt unpinned, asgi-correlation-id added
- `gathering/api/auth.py` - JWT operations via PyJWT, password hashing via direct bcrypt
- `gathering/core/exceptions.py` - AuthenticationError, AuthorizationError, DatabaseError subclasses added
- `gathering/core/logging.py` - New: structlog configuration with JSON output and correlation ID support
- `gathering/db/migrations/006_auth_users.sql` - New: auth.users, auth.token_blacklist, audit.security_events tables
- `gathering/api/main.py` - configure_logging() at startup, CorrelationIdMiddleware added

## Decisions Made
- PyJWT chosen over python-jose: better maintained, smaller footprint, identical encode/decode API for HS256
- Direct bcrypt instead of passlib: eliminates unnecessary wrapper, bcrypt $2b$ hash format is identical
- bcrypt upper bound unpinned (>=4.0.0): passlib compatibility constraint no longer relevant
- CorrelationIdMiddleware placed last in add_middleware calls so it executes first in the request lifecycle
- structlog uses console renderer when debug=True, JSON renderer otherwise (controlled by settings.debug)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Auth library foundation complete: Plans 02 and 03 can build on PyJWT/bcrypt APIs
- Exception hierarchy ready: Plans 02/03 can use AuthenticationError/AuthorizationError in auth flows
- Migration SQL ready for execution against PostgreSQL (not yet applied -- Plan 02 handles DB persistence)
- structlog + correlation IDs wired into app startup for request tracing

## Self-Check: PASSED

- All 7 created/modified files verified present on disk
- Both task commits verified in git log (991af49, 70c407e)
- All 31 auth tests pass with new library implementations

---
*Phase: 01-auth-security-foundation*
*Completed: 2026-02-10*
