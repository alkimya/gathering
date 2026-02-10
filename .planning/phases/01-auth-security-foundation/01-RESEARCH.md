# Phase 1: Auth + Security Foundation - Research

**Researched:** 2026-02-10
**Domain:** Auth persistence, SQL injection elimination, security hardening, DB layer consolidation (Python/FastAPI/PostgreSQL)
**Confidence:** HIGH

## Summary

Phase 1 replaces the in-memory auth system with persistent PostgreSQL storage, eliminates SQL injection risks, hardens security defenses (constant-time auth, path traversal prevention), consolidates the DB driver on pycopg (which wraps psycopg 3), activates structured logging with audit trails, and fixes bare exception catches in security-critical paths. The existing codebase has a well-defined schema (`audit.logs`, `audit.security_events` tables already exist), a working migration system (SQL files in `gathering/db/migrations/`), and a clear auth module (`gathering/api/auth.py`) with explicit TODO markers for database replacement.

The key insight from codebase analysis is that this phase is primarily a **storage layer swap and security tightening**, not a feature build. The auth module's API surface (`authenticate_user`, `create_user`, `blacklist_token`, `decode_token`) already has the correct signatures -- the in-memory implementations just need PostgreSQL backends. The f-string SQL patterns in `pipelines.py`, `schedules.py`, `dependencies.py`, and `projects.py` are dynamic UPDATE builders where column names come from hardcoded strings -- the parameterized values already use `%(param)s`. These are safe but should be formalized with an allowlist helper. The JWT migration from `python-jose` to `PyJWT` is nearly a drop-in replacement with identical `encode`/`decode` APIs. The password hashing migration from `passlib` to direct `bcrypt` is straightforward since only bcrypt is used.

**Primary recommendation:** Execute in four sequential work streams: (1) DB layer + structured logging foundation, (2) auth persistence + JWT/password library swap, (3) security hardening (SQL audit, constant-time, path traversal), (4) exception handling cleanup in security paths + tests.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- User ID format must remain `str` to avoid forced re-login (from research findings)
- Constant-time auth responses required (from success criteria)
- Path traversal attempts must return 403 (from success criteria)
- Two separate EventBus implementations must be preserved at boundary minimum (from research findings)

### Claude's Discretion
All four discussion areas were delegated to Claude's judgment. Claude has full flexibility to make implementation decisions across auth migration, security responses, DB migration, and exception handling -- guided by the success criteria, research findings, and existing codebase patterns. The key constraints are:
- User ID format stays as `str`
- EventBus boundary preserved
- Tiered approach to bare exception fixes (security paths first)
- All success criteria from ROADMAP.md must be met

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.

</user_constraints>

## Discretion Decisions (Research Recommendations)

Based on codebase analysis, these are the recommended decisions for all areas delegated to Claude's discretion.

### Auth Persistence & Migration
| Decision | Recommendation | Rationale |
|----------|---------------|-----------|
| Migration strategy | Transparent swap (no forced re-login) | JWT tokens are self-contained with `sub` as `str`. Keep signing key unchanged, keep user ID as `str(uuid4())`. Old tokens continue to decode correctly; the only change is where user lookup happens. |
| Token revocation persistence | PostgreSQL table `auth.token_blacklist` with in-memory LRU cache | Two-layer: in-memory cache (30s TTL, bounded size) backed by DB table. Blacklist additions write-through to both. Sub-ms auth checks while ensuring persistence. |
| Token lifetimes | Access: 24h (keep current), Refresh: not needed yet | Current `ACCESS_TOKEN_EXPIRE_HOURS = 24` is reasonable for a dev tool. Refresh tokens add complexity with no current need. Revisit in Phase 4 if token overhead becomes an issue. |
| Multi-device sessions | Allow unlimited concurrent sessions | Current behavior allows it (no session tracking). No reason to restrict. Each device gets its own token; logout blacklists one token, not all sessions. |

### Security Response Behavior
| Decision | Recommendation | Rationale |
|----------|---------------|-----------|
| Auth error verbosity | Generic "Incorrect email or password" (keep current) | Already implemented correctly in `auth.py`. Return same 401 regardless of which part failed. |
| Attack attempt logging | Log to `audit.security_events` table | Table already exists in schema. Log: `auth_failure`, `token_revoked_reuse`, `path_traversal_attempt`, `rate_limit_exceeded`. |
| Auth rate limiting timing | Phase 1 -- tighter limits on auth endpoints only | Add stricter per-endpoint rate limits (10/min on login, 5/min on register) using existing `RateLimitMiddleware` with path awareness. Full slowapi migration deferred to Phase 4. |
| Password hashing | bcrypt direct (remove passlib wrapper) | passlib 1.7.4 is unmaintained (last release 2020, no Python 3.13 support). bcrypt 4.3.0 is already installed and actively maintained. Direct `bcrypt.hashpw()`/`bcrypt.checkpw()` replaces `CryptContext`. Existing bcrypt hashes remain compatible. |

### DB Migration Strategy
| Decision | Recommendation | Rationale |
|----------|---------------|-----------|
| Migration approach | Incremental by domain: auth tables first, then audit activation | Auth is the critical path. Migrate auth.users + auth.token_blacklist first (new tables). Other schema tables already exist. |
| Migration tooling | Raw SQL files (continue existing pattern) | Project already uses numbered SQL migration files (`001_complete_schema.sql` through `005_agent_tools.sql`). Alembic is installed but not configured for this project's multi-schema architecture. Continue the established pattern: add `006_auth_users.sql`. |
| Dev/test database | PostgreSQL everywhere (no SQLite fallback) | Test conftest currently does not use a database at all (mocks only). Add a test PostgreSQL fixture using the existing DB infrastructure. SQLite would mask PostgreSQL-specific behavior (schemas, INET type, JSONB). |
| EventBus unification | Do NOT touch EventBus in Phase 1 | EventBus works. Phase 1 changes nothing about it. The two implementations serve different purposes (system-wide singleton vs circle-scoped). Preserving the boundary is explicitly required. |

### Exception Handling Policy
| Decision | Recommendation | Rationale |
|----------|---------------|-----------|
| Scope of fixes | Security paths only (~30 catches in auth.py, dependencies.py, database.py, middleware.py + workspace.py security paths) | Tiered approach from research. Phase 1 covers Tier 1 only. Tier 2 (features) in Phases 2-3. Tier 3 (skills/plugins) in Phase 4. |
| Logging strategy | Log unexpected exceptions only; expected errors (auth failure, not found) just raise | Avoid log noise. `except SpecificError` handles known cases. Unexpected exceptions get `logger.exception()` before re-raising or returning 500. |
| 500 error response format | Include request ID: `{"detail": "Internal server error", "request_id": "req_123"}` | RequestLoggingMiddleware already generates `X-Request-ID`. Include it in error responses so users can report specific failures. |
| Exception class strategy | Extend existing `GatheringError` hierarchy | `gathering/core/exceptions.py` already has `GatheringError` with 10+ subclasses. Add `AuthenticationError`, `AuthorizationError`, `DatabaseError` as new subclasses. Do not create a parallel hierarchy. |

## Standard Stack

### Core (Already Installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| psycopg | 3.3.2 | PostgreSQL driver (sync + async) | Already installed. Wraps libpq. Both sync and async support. Underlies the `pycopg` wrapper used throughout. |
| psycopg-pool | 3.3.0 | Connection pooling | Already installed. Provides `AsyncConnectionPool` for Phase 4 async migration. |
| pycopg | 0.1.0 | High-level PostgreSQL wrapper | Project's own wrapper around psycopg 3. Used by `DatabaseService`. Provides `Database`, `AsyncDatabase`, `Migrator`. |
| SQLAlchemy | 2.0.45 | ORM + engine | Already installed. Used for `Database.engine` in `gathering/db/database.py`. Supports `postgresql+psycopg` dialect. |
| Alembic | 1.17.2 | DB migration framework | Already installed but not actively used (project uses raw SQL migrations). Available as fallback. |
| bcrypt | 4.3.0 | Password hashing | Already installed. Replace passlib wrapper with direct `bcrypt.hashpw()`/`bcrypt.checkpw()`. |

### New Dependencies (To Install)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PyJWT | >=2.9.0 | JWT encode/decode | Replace python-jose. Near-identical API. Fewer transitive dependencies. |
| structlog | >=24.0 | Structured logging | Already declared in pyproject.toml but not installed/used. Activate for JSON logging + request correlation. |
| asgi-correlation-id | >=4.0 | Request ID middleware | Generates/propagates X-Request-ID across async contexts. Works with structlog contextvars. |

### Dependencies to Remove
| Library | Reason | Replacement |
|---------|--------|-------------|
| python-jose | Unmaintained, pulls in ecdsa/rsa/pyasn1 | PyJWT with cryptography backend |
| passlib | Last release 2020, no Python 3.13 support | Direct bcrypt |
| Remove bcrypt pin `<4.1.0` | Pin exists only for passlib compatibility | Unpin to `>=4.0.0` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyJWT | joserfc (authlib) | joserfc is newer and more feature-complete (JWE, JWK), but PyJWT is the community standard with the simplest migration path from python-jose |
| Direct bcrypt | argon2-cffi | Argon2id is technically superior, but switching hash algorithms requires migrating ALL existing password hashes or running dual verification. Not worth it for consolidation. |
| asgi-correlation-id | Manual UUID in middleware | Library handles propagation to contextvars, which structlog reads automatically. Manual approach would duplicate this work. |

**Installation:**
```bash
pip install "PyJWT>=2.9"
pip install "structlog>=24.0"
pip install "asgi-correlation-id>=4.0"
pip uninstall python-jose passlib ecdsa rsa pyasn1 -y
```

## Architecture Patterns

### New Tables (auth schema)

```sql
-- New migration: 006_auth_users.sql

CREATE SCHEMA IF NOT EXISTS auth;

-- Users table
CREATE TABLE auth.users (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    external_id VARCHAR(36) NOT NULL UNIQUE DEFAULT gen_random_uuid()::text,
    email VARCHAR(255) NOT NULL,
    email_lower VARCHAR(255) GENERATED ALWAYS AS (LOWER(email)) STORED,
    name VARCHAR(100) NOT NULL,
    password_hash VARCHAR(72) NOT NULL,  -- bcrypt max length
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_users_email_lower ON auth.users(email_lower);
CREATE INDEX idx_users_external_id ON auth.users(external_id);

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

-- Token blacklist
CREATE TABLE auth.token_blacklist (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    token_hash VARCHAR(64) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    blacklisted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_id VARCHAR(36),
    reason VARCHAR(50) DEFAULT 'logout'
);

CREATE UNIQUE INDEX idx_token_blacklist_hash ON auth.token_blacklist(token_hash);
CREATE INDEX idx_token_blacklist_expires ON auth.token_blacklist(expires_at);
```

**Key design decisions:**
- `external_id` is `VARCHAR(36)` (UUID as string) -- this is the `id` field exposed in the API, preserving `str` format
- `email_lower` is a generated column for case-insensitive lookup with a UNIQUE index
- `password_hash` is `VARCHAR(72)` -- bcrypt output is exactly 60 chars, but 72 provides margin
- `token_hash` uses SHA-256 truncated to 32 hex chars (matching current `_get_token_hash`)

### Pattern 1: Repository Pattern for Auth Persistence

**What:** Swap in-memory dicts for DB-backed functions. Keep the same function signatures.
**When to use:** Replacing `_users_store` and `_token_blacklist` in `gathering/api/auth.py`.

```python
# Source: codebase analysis of gathering/api/auth.py + gathering/api/dependencies.py

# BEFORE (in-memory):
_users_store: dict[str, dict] = {}

async def get_user_by_email(email: str) -> Optional[dict]:
    return _users_store.get(email.lower())

# AFTER (database):
async def get_user_by_email(email: str, db: DatabaseService) -> Optional[dict]:
    return db.execute_one(
        "SELECT external_id as id, email, name, password_hash, role, is_active, created_at "
        "FROM auth.users WHERE email_lower = %(email)s",
        {"email": email.lower()}
    )
```

### Pattern 2: Two-Layer Token Blacklist

**What:** In-memory LRU cache backed by PostgreSQL for token blacklist.
**When to use:** Every auth check (called on every authenticated request).

```python
# Source: pattern from research STACK.md + codebase analysis

from functools import lru_cache
from collections import OrderedDict

class TokenBlacklist:
    """Two-layer token blacklist: in-memory cache + PostgreSQL."""

    def __init__(self, db: DatabaseService, cache_max_size: int = 10000):
        self._db = db
        self._cache: OrderedDict[str, float] = OrderedDict()
        self._cache_max_size = cache_max_size

    def blacklist(self, token_hash: str, expires_at: float, user_id: str = None) -> None:
        """Add token to blacklist (write-through to both layers)."""
        self._cache[token_hash] = expires_at
        if len(self._cache) > self._cache_max_size:
            self._cache.popitem(last=False)  # Evict oldest

        self._db.execute(
            "INSERT INTO auth.token_blacklist (token_hash, expires_at, user_id) "
            "VALUES (%(hash)s, to_timestamp(%(exp)s), %(user_id)s) "
            "ON CONFLICT (token_hash) DO NOTHING",
            {"hash": token_hash, "exp": expires_at, "user_id": user_id}
        )

    def is_blacklisted(self, token_hash: str) -> bool:
        """Check cache first, fall back to DB."""
        # Check cache
        if token_hash in self._cache:
            exp = self._cache[token_hash]
            if exp > datetime.now(timezone.utc).timestamp():
                return True
            else:
                del self._cache[token_hash]
                return False

        # Check DB
        result = self._db.execute_one(
            "SELECT 1 FROM auth.token_blacklist "
            "WHERE token_hash = %(hash)s AND expires_at > NOW()",
            {"hash": token_hash}
        )
        if result:
            # Promote to cache
            self._cache[token_hash] = result.get("expires_at", 0)
            return True
        return False
```

### Pattern 3: Safe Dynamic UPDATE Builder

**What:** Validate that SET clause column names come from an allowlist.
**When to use:** All dynamic UPDATE queries in `pipelines.py`, `schedules.py`, `dependencies.py`, `projects.py`.

```python
# Source: codebase analysis of f-string SQL patterns

def safe_update_builder(
    allowed_columns: set[str],
    updates: dict[str, any],
    always_set: dict[str, str] | None = None,
) -> tuple[str, dict]:
    """Build a safe SET clause from allowed column names.

    Args:
        allowed_columns: Set of column names that are allowed in SET.
        updates: Dict of column_name -> value from user input.
        always_set: Dict of raw SQL expressions to always include (e.g., {"updated_at": "CURRENT_TIMESTAMP"}).

    Returns:
        Tuple of (SET clause string, params dict).

    Raises:
        ValueError: If a column name is not in the allowlist.
    """
    set_parts = []
    params = {}

    for col, val in updates.items():
        if col not in allowed_columns:
            raise ValueError(f"Column {col!r} not in allowed columns: {allowed_columns}")
        param_name = col
        set_parts.append(f"{col} = %({param_name})s")
        params[param_name] = val

    if always_set:
        for col, expr in always_set.items():
            set_parts.append(f"{col} = {expr}")

    return ", ".join(set_parts), params
```

### Pattern 4: Constant-Time Auth with Dummy Operations

**What:** Ensure auth endpoints take the same time regardless of whether the user exists.
**When to use:** Login, any credential verification.

```python
# Source: existing pattern in gathering/api/auth.py lines 296-334 (already implemented for admin)

# The current verify_admin_credentials() already does this correctly.
# Extend the same pattern to database user lookup:

async def authenticate_user(email: str, password: str, db: DatabaseService) -> Optional[dict]:
    """Constant-time authentication."""
    # Always check admin first (constant time)
    admin = verify_admin_credentials(email, password)
    if admin:
        return {"id": admin.id, "email": admin.email, "name": admin.name, "role": admin.role}

    # Always query database (even if we'll fail)
    user = await get_user_by_email(email, db)

    # Always verify password (use dummy hash if user not found)
    dummy_hash = b"$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYWWQIe0u0S."
    stored_hash = (user.get("password_hash", "").encode("utf-8") if user else dummy_hash)

    password_valid = bcrypt.checkpw(password.encode("utf-8"), stored_hash)

    if user and password_valid and user.get("is_active", False):
        return {
            "id": user["id"],
            "email": user["email"],
            "name": user.get("name", ""),
            "role": user.get("role", "user"),
        }
    return None
```

### Pattern 5: structlog Configuration for FastAPI

**What:** Configure structlog with request correlation IDs and JSON output.
**When to use:** Application startup.

```python
# Source: structlog docs + FastAPI community patterns

import structlog
import logging

def configure_logging(json_output: bool = True):
    """Configure structlog for GatheRing."""
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if json_output:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
```

### Recommended File Changes Structure

```
gathering/
├── api/
│   ├── auth.py              # MAJOR: Replace in-memory with DB, swap jose->PyJWT, passlib->bcrypt
│   ├── middleware.py         # MODERATE: Add auth rate limiting awareness, update logging
│   └── routers/
│       ├── auth.py           # MINOR: Pass db dependency to auth functions
│       ├── pipelines.py      # MINOR: Formalize safe_update_builder
│       ├── projects.py       # MINOR: Same pattern
│       ├── workspace.py      # MODERATE: Harden path traversal, fix bare excepts
│       └── ...
├── core/
│   ├── config.py             # MINOR: Add structlog config, remove disable_auth in prod
│   ├── exceptions.py         # MINOR: Add AuthenticationError, AuthorizationError
│   └── logging.py            # NEW: structlog configuration + audit logging
├── db/
│   ├── database.py           # MINOR: Fix bare exceptions, parameterize schema name
│   └── migrations/
│       └── 006_auth_users.sql # NEW: auth.users + auth.token_blacklist tables
├── api/
│   └── dependencies.py       # MODERATE: Fix bare exceptions in security paths, formalize updates
└── skills/gathering/
    └── schedules.py          # MINOR: Formalize safe_update_builder
```

### Anti-Patterns to Avoid

- **Big-bang JWT library swap:** Do NOT change jose->PyJWT and passlib->bcrypt in the same commit as the auth persistence change. Library swaps first (API is identical), then storage swap.
- **Merging EventBus implementations:** Both must remain separate. Phase 1 does not touch EventBus at all.
- **Fixing all 262 bare exceptions at once:** Only fix ~30 in security paths (Tier 1). The rest wait for their respective phases.
- **Using SQLite for tests:** PostgreSQL-specific features (schemas, INET, generated columns, ON CONFLICT) would be invisible. Use test PostgreSQL or mock the DB layer.
- **Storing full JWT tokens in blacklist:** Store SHA-256 hash only (current pattern is correct, keep it).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Request correlation IDs | Manual UUID middleware | `asgi-correlation-id` | Handles propagation to contextvars, header extraction/generation, async context safety |
| Structured JSON logging | Custom JSON formatter | `structlog` | Already a declared dependency. Handles log context binding, processor chains, stdlib integration |
| JWT encode/decode | Custom token handling | `PyJWT` | Battle-tested, simple API, handles expiry validation, algorithm enforcement |
| Password hashing | Custom bcrypt wrapper | `bcrypt` directly | PyCA-maintained, constant-time comparison built-in to `checkpw()` |
| Token hash function | Custom hashing | `hashlib.sha256` (stdlib) | Already used in current code. SHA-256 truncated to 32 hex chars is fine for blacklist keys |
| Constant-time comparison | Manual byte-by-byte | `hmac.compare_digest` or `secrets.compare_digest` (stdlib) | Already used in admin auth. Extend to all auth comparisons. |

**Key insight:** Every security-critical operation in this phase has a well-tested stdlib or library solution. The existing codebase already uses most of them -- the gap is that they're not applied consistently.

## Common Pitfalls

### Pitfall 1: Auth Migration Invalidates Existing Sessions
**What goes wrong:** Changing the JWT signing key, user ID format, or token payload structure causes all existing tokens to fail validation after deployment.
**Why it happens:** Developers change the storage backend AND the token format simultaneously.
**How to avoid:** Keep the JWT signing key (`SECRET_KEY`) unchanged. Keep `sub` field as `str` (UUID string). Keep token payload structure identical. Only change where user data is stored, not how tokens reference it.
**Warning signs:** Dashboard returns 401 after server restart. `decode_token()` returns `None` for previously valid tokens.

### Pitfall 2: f-String SQL "Fix" Breaks Dynamic Updates
**What goes wrong:** Developer sees `f"UPDATE ... SET {', '.join(updates)}"` and replaces the entire thing with parameterized queries, breaking the SET clause construction.
**Why it happens:** Confusion between parameterizing VALUES (necessary) vs parameterizing COLUMN NAMES (impossible in SQL). The existing patterns already parameterize values with `%(param)s`. The column names in the SET clause come from hardcoded Python strings, not user input.
**How to avoid:** Audit each f-string individually. The `updates` lists in `pipelines.py:280-303`, `dependencies.py:405-423`, `projects.py:370-401`, and `schedules.py:340-396` all construct column assignments from hardcoded strings. Add the `safe_update_builder` helper for formalization, but do NOT try to parameterize column names.
**Warning signs:** UPDATE endpoints return 500 errors. Tests that update partial fields start failing.

### Pitfall 3: passlib Removal Breaks Existing Password Hashes
**What goes wrong:** Switching from passlib's `CryptContext.verify()` to `bcrypt.checkpw()` with incorrect encoding causes all existing password verifications to fail.
**Why it happens:** passlib accepts `str`, bcrypt requires `bytes`. The hash format is identical (`$2b$12$...`) but the byte encoding must be explicit.
**How to avoid:** Ensure `bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))` is used. Test with hashes generated by passlib -- they are format-compatible.
**Warning signs:** All login attempts fail with "Incorrect email or password" after migration.

### Pitfall 4: Path Traversal Check Bypassed by Encoded Paths
**What goes wrong:** Current `resolve().relative_to()` check works for `../` but may not catch `%2e%2e/`, URL-encoded sequences, or symlink escapes.
**Why it happens:** `Path.resolve()` handles `../` but does not decode URL-encoded characters. The FastAPI/Starlette URL parser may or may not decode these before they reach the handler.
**How to avoid:** Decode URL-encoded paths BEFORE path resolution. Check for symlinks that point outside the project root. Explicitly reject paths containing `..` at any position (before and after decoding). Return 403 (not 404) for traversal attempts.
**Warning signs:** Test with `%2e%2e%2f` and double-encoded variants. If any return file contents from outside the project, the check is bypassed.

### Pitfall 5: Token Blacklist Cache Grows Unbounded
**What goes wrong:** In-memory cache layer for token blacklist grows without limit, eventually consuming server memory.
**Why it happens:** The current `_token_blacklist` dict has a cleanup interval of 3600s (1 hour). High-traffic deployments can accumulate thousands of entries between cleanups.
**How to avoid:** Use `OrderedDict` with a max size cap. Evict oldest entries when full. Clean expired entries on every `blacklist()` call, not on a timer.
**Warning signs:** Memory usage grows linearly over time. `get_blacklist_stats()` shows increasing counts.

### Pitfall 6: Bare Exception Cleanup Surfaces Hidden Bugs
**What goes wrong:** Replacing `except Exception` with specific exceptions in auth/security paths causes previously-swallowed errors to propagate as 500s.
**Why it happens:** The bare catches were suppressing real bugs (database connection failures, type errors, etc.) and returning `None` or `False` instead.
**How to avoid:** For each bare catch, first identify what exceptions can actually occur. Replace incrementally: one function at a time. Run the test suite after each change. Some catches ARE legitimate (e.g., in EventBus handlers where you want isolation) -- keep those with an explicit comment.
**Warning signs:** New 500 errors after deployment. Features that "worked" before start failing.

## Code Examples

Verified patterns from codebase analysis and official documentation:

### PyJWT Migration (from python-jose)
```python
# BEFORE (python-jose):
from jose import JWTError, jwt
encoded_jwt = jwt.encode(to_encode, secret_key, algorithm="HS256")
payload = jwt.decode(token, secret_key, algorithms=["HS256"])

# AFTER (PyJWT):
import jwt
from jwt.exceptions import PyJWTError  # replaces JWTError
encoded_jwt = jwt.encode(to_encode, secret_key, algorithm="HS256")
payload = jwt.decode(token, secret_key, algorithms=["HS256"])
# Source: PyJWT docs https://pyjwt.readthedocs.io/en/latest/
# Migration guide: https://github.com/jpadilla/pyjwt/issues/942
```

### bcrypt Direct Usage (replacing passlib)
```python
# BEFORE (passlib):
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
hashed = pwd_context.hash(password)
valid = pwd_context.verify(password, hashed)

# AFTER (bcrypt direct):
import bcrypt

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )
# Source: bcrypt PyPI https://pypi.org/project/bcrypt/
```

### Audit Event Logging
```python
# Source: existing audit.security_events schema from 001_complete_schema.sql

def log_auth_event(
    db: DatabaseService,
    event_type: str,
    user_id: str | None,
    ip_address: str,
    message: str,
    details: dict | None = None,
    severity: str = "info",
) -> None:
    """Log authentication event to audit table."""
    db.execute(
        "INSERT INTO audit.security_events "
        "(event_type, severity, user_id, ip_address, message, details) "
        "VALUES (%(event_type)s, %(severity)s, %(user_id)s, %(ip_address)s::inet, "
        "%(message)s, %(details)s::jsonb)",
        {
            "event_type": event_type,
            "severity": severity,
            "user_id": user_id,
            "ip_address": ip_address,
            "message": message,
            "details": json.dumps(details or {}),
        }
    )
```

### Path Traversal Hardening
```python
# Source: codebase analysis of workspace.py + security best practices

import os
from pathlib import Path
from urllib.parse import unquote

def validate_file_path(project_path: str, user_path: str) -> Path:
    """Validate and resolve a user-provided file path.

    Returns resolved path if safe, raises HTTPException(403) if traversal detected.
    """
    # Step 1: URL-decode the path (handles %2e%2e etc.)
    decoded_path = unquote(unquote(user_path))  # Double-decode for double encoding

    # Step 2: Reject any remaining '..' components
    if ".." in decoded_path:
        raise HTTPException(status_code=403, detail="Path traversal detected")

    # Step 3: Resolve paths
    project_root = Path(project_path).resolve()
    target = (project_root / decoded_path).resolve()

    # Step 4: Verify target is within project root
    try:
        target.relative_to(project_root)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied: path outside project")

    # Step 5: Check for symlink escape
    if target.is_symlink():
        real_target = target.resolve()
        try:
            real_target.relative_to(project_root)
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied: symlink escape")

    return target
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| python-jose for JWT | PyJWT | python-jose effectively unmaintained since 2022 | Drop 3 transitive deps (ecdsa, rsa, pyasn1), simpler API |
| passlib for password hashing | bcrypt direct | passlib last release 2020, no Python 3.12+ | Remove unmaintained wrapper, direct PyCA-maintained library |
| psycopg2-binary | psycopg 3 (psycopg) | psycopg 3 stable since 2023 | Single driver for sync+async, native async support |
| `logging.getLogger()` | structlog | structlog mature since 2024+ | JSON output, context binding, request correlation |
| In-memory token blacklist | DB-backed with LRU cache | Standard practice | Survives restarts, bounded memory |

**Deprecated/outdated:**
- `python-jose`: Effectively unmaintained. Community has moved to PyJWT or joserfc.
- `passlib`: Last release 2020. Known compatibility issues with bcrypt >= 4.1.
- `psycopg2-binary`: Legacy driver. psycopg 3 is the actively developed successor.
- `datetime.utcnow()`: Deprecated in Python 3.12+. Use `datetime.now(timezone.utc)` (codebase already uses the correct form in most places).

## Open Questions

1. **How does `pycopg` (the project's wrapper) handle async?**
   - What we know: `pycopg` 0.1.0 exports `AsyncDatabase` which wraps `psycopg.AsyncConnection`. The `DatabaseService` in `dependencies.py` currently uses only the sync `Database` class.
   - What's unclear: Whether the async path is tested/stable in the project's wrapper.
   - Recommendation: For Phase 1, keep using sync `DatabaseService.execute()` (it works). The async migration is Phase 4 scope (`PERF-01`). For the new auth functions, use the same sync `execute()` pattern. This avoids introducing async DB in Phase 1 while still meeting all requirements.

2. **How many tests currently depend on the in-memory auth store?**
   - What we know: `tests/test_auth.py` tests token creation/validation and password hashing. The conftest has no database fixtures.
   - What's unclear: Exactly how many integration tests mock the auth layer.
   - Recommendation: Survey `_users_store` and `_token_blacklist` references in tests before starting. Tag tests that will break. Write replacement tests first (TDD).

3. **Does the existing `audit.security_events` table match the needed schema?**
   - What we know: The table exists in `001_complete_schema.sql` with `event_type`, `severity`, `user_id`, `ip_address`, `message`, `details` columns.
   - What's unclear: Whether the table has been actually created in the development database.
   - Recommendation: The migration `006_auth_users.sql` should include `CREATE TABLE IF NOT EXISTS` for both new tables. The audit tables should already exist from the initial schema migration. Verify during implementation.

## Sources

### Primary (HIGH confidence)
- `gathering/api/auth.py` -- Direct analysis of current auth implementation (in-memory stores, token handling, admin verification)
- `gathering/api/dependencies.py` -- Direct analysis of DatabaseService, SQL patterns, f-string UPDATE builders
- `gathering/db/database.py` -- Direct analysis of Database class, SQLAlchemy engine, sync-only operations
- `gathering/db/migrations/001_complete_schema.sql` -- Full schema definition including audit tables
- `gathering/db/migrations/archive/008_audit_schema.sql` -- Detailed audit schema with security_events table
- `gathering/api/routers/workspace.py` -- Direct analysis of path traversal defense (lines 170-224)
- `gathering/api/middleware.py` -- Direct analysis of auth enforcement, rate limiting, request logging
- `gathering/core/exceptions.py` -- Existing exception hierarchy (GatheringError + 10 subclasses)
- `gathering/core/config.py` -- Settings including `secret_key`, `disable_auth`, environment config
- `pyproject.toml` -- Dependency declarations (python-jose, passlib, bcrypt pin, structlog, pycopg)
- `venv/lib/python3.13/site-packages/pycopg/` -- pycopg wrapper source (Database, AsyncDatabase, Migrator)
- Installed package versions: psycopg 3.3.2, bcrypt 4.3.0, SQLAlchemy 2.0.45, Alembic 1.17.2

### Secondary (MEDIUM confidence)
- [psycopg 3 docs - parameterized queries](https://www.psycopg.org/psycopg3/docs/basic/params.html) -- Verified %s placeholder syntax
- [psycopg 3 docs - async operations](https://www.psycopg.org/psycopg3/docs/advanced/async.html) -- AsyncConnection/AsyncCursor API
- [PyJWT documentation](https://pyjwt.readthedocs.io/en/latest/) -- encode/decode API, version 2.11.0
- [PyJWT migration from python-jose](https://github.com/jpadilla/pyjwt/issues/942) -- Drop-in replacement confirmed
- [bcrypt PyPI](https://pypi.org/project/bcrypt/) -- hashpw/checkpw API, bytes requirement
- [structlog + FastAPI integration patterns](https://wazaari.dev/blog/fastapi-structlog-integration) -- Configuration, contextvars, JSON renderer
- [asgi-correlation-id PyPI](https://pypi.org/project/asgi-correlation-id/) -- Request ID middleware

### Tertiary (LOW confidence)
- structlog exact version compatibility with Python 3.13 -- needs verification at install time
- asgi-correlation-id compatibility with Starlette 0.50.0 -- needs verification at install time
- APScheduler 4.x availability -- mentioned in research STACK.md but not relevant for Phase 1

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- All core libraries verified as installed with exact versions. Migration paths confirmed via API analysis.
- Architecture: HIGH -- Based on direct codebase analysis of every relevant file. SQL schema design follows existing conventions.
- Pitfalls: HIGH -- Grounded in actual code patterns found in the codebase. f-string SQL analysis confirmed the UPDATE builders are safe (column names are hardcoded).
- Security: HIGH -- Path traversal, constant-time comparison, and SQL injection patterns verified against current implementation.

**Research date:** 2026-02-10
**Valid until:** 2026-03-12 (30 days -- stable domain, no fast-moving dependencies)
