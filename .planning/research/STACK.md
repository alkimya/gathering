# Stack Research: Production-Readiness Consolidation

**Domain:** Production hardening for Python/FastAPI multi-agent AI framework
**Researched:** 2026-02-10
**Confidence:** HIGH (versions verified from installed packages in venv)

## Situation Assessment

GatheRing already has a working stack. This research does NOT recommend changing frameworks -- it identifies what production-readiness tooling to ADD and what problematic dependencies to REPLACE. Every recommendation maps to a concrete deficiency documented in `.planning/codebase/CONCERNS.md`.

---

## Recommended Stack Changes

### 1. Async Database Driver: Consolidate on psycopg 3

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| psycopg[binary,pool] | 3.3.2 (installed) | Async PostgreSQL driver + connection pooling | Already installed. Native async support (AsyncConnection, AsyncCursor, AsyncPipeline). Replaces the need for BOTH asyncpg AND psycopg2-binary. Single driver for sync migrations (Alembic) AND async request handling. |
| psycopg-pool | 3.3.0 (installed) | Async connection pool | Already installed alongside psycopg. Provides AsyncConnectionPool with health checks, min/max sizing, connection recycling. Replaces SQLAlchemy's QueuePool for async paths. |

**Confidence: HIGH** -- psycopg 3.3.2 verified installed at `/home/loc/workspace/gathering/venv/lib/python3.13/site-packages/psycopg-3.3.2.dist-info/METADATA`. Exports AsyncConnection, AsyncCursor, AsyncPipeline confirmed in `psycopg/__init__.py`. SQLAlchemy 2.0.45 has explicit `postgresql-psycopg` extra for psycopg3 as async dialect.

**What changes:**
- Replace `create_engine()` sync calls with `create_async_engine()` using `postgresql+psycopg://` dialect
- Replace `Session` with `AsyncSession` from `sqlalchemy.ext.asyncio`
- Replace sync `DatabaseService.execute()` with async methods
- Remove `asyncpg` dependency (psycopg3 covers async natively)
- Remove `psycopg2-binary` dependency (psycopg3 handles sync via same package)

**Why NOT keep asyncpg alongside psycopg3:**
- asyncpg uses its own connection protocol, cannot share pools with psycopg3
- Maintaining two PostgreSQL drivers doubles the surface area for connection bugs
- psycopg3 async performance is comparable to asyncpg for ORM workloads (both use libpq under the hood with binary mode)
- SQLAlchemy 2.0 officially supports `postgresql+psycopg` dialect for async -- this is the recommended path per SQLAlchemy docs

### 2. Auth: Replace python-jose + passlib

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| PyJWT | >=2.9.0 | JWT token encoding/decoding | python-jose is effectively unmaintained (last meaningful update was compatibility fixes). PyJWT is the actively maintained standard. FastAPI's own security docs reference PyJWT. Already a transitive dependency via redis[jwt]. |
| bcrypt (direct) | 4.3.0 (installed) | Password hashing | passlib 1.7.4 is unmaintained (no release since 2020, no Python 3.12+ classifiers). bcrypt 4.3.0 is actively maintained by PyCA. Use bcrypt directly instead of through passlib's CryptContext wrapper. bcrypt's own METADATA says "you should really use argon2id or scrypt" but bcrypt is adequate for this use case and avoids adding another dependency. |

**Confidence: HIGH** -- passlib 1.7.4 METADATA shows no Python 3.12/3.13 classifiers, last release 2020. bcrypt 4.3.0 is actively maintained by PyCA (verified from installed METADATA). python-jose 3.5.0 pulls in ecdsa, rsa, pyasn1 as dependencies -- PyJWT with cryptography backend (already installed) is leaner and better maintained.

**What changes:**
- Replace `from jose import jwt` with `import jwt` (PyJWT)
- Replace `passlib.context.CryptContext` with direct `bcrypt.hashpw()` / `bcrypt.checkpw()`
- Remove python-jose, passlib, ecdsa, rsa, pyasn1 from dependencies
- Token blacklist moves from in-memory dict to Redis or PostgreSQL table

### 3. Rate Limiting: slowapi

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| slowapi | >=0.1.9 | Request rate limiting for FastAPI/Starlette | Built on top of limits library with Redis backend support. Drop-in middleware for FastAPI. Supports per-route limits, custom key functions (IP, user, API key), Redis-backed distributed counters. |

**Confidence: MEDIUM** -- slowapi is the de facto standard for FastAPI rate limiting based on training data. Version needs verification at install time (not currently installed). The current in-memory RateLimitMiddleware in `gathering/api/middleware.py` is single-instance only and has no persistence.

**What changes:**
- Replace custom `RateLimitMiddleware` class with slowapi's `Limiter`
- Configure Redis backend for distributed rate limiting (when Redis is available)
- Falls back to in-memory when Redis unavailable (development mode)
- Per-route decorators: `@limiter.limit("60/minute")` on each router

**Why NOT write a custom implementation:**
- The existing custom middleware (middleware.py lines 131-205) is already 75 lines and only handles basic IP-based limiting
- It uses in-memory defaultdict -- useless for multi-instance deployment
- slowapi handles: multiple backends, key extraction, exemptions, custom responses, rate limit headers -- all production requirements

### 4. Structured Logging + Audit Trail: structlog

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| structlog | >=24.0 | Structured logging with context binding | Already in pyproject.toml dependencies. Provides bound loggers with automatic context (request_id, user_id, ip). JSON output for log aggregation. Integrates with stdlib logging. |

**Confidence: HIGH** -- structlog is already declared as a dependency in `pyproject.toml` line 50. Just not installed in the current venv and not used in the codebase (the middleware uses `logging.getLogger()` instead).

**What changes:**
- Replace all `logging.getLogger()` calls with `structlog.get_logger()`
- Configure structlog processors: add timestamps, request_id, user context
- Create audit log processor that writes security events to a dedicated `audit.audit_log` table
- Audit events: login_success, login_failure, token_created, token_revoked, permission_denied, user_created, password_changed

### 5. Distributed Task Coordination: PostgreSQL Advisory Locks + Background Workers

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| PostgreSQL Advisory Locks | (built-in PG 16) | Distributed locking for task coordination | Zero additional infrastructure. `pg_advisory_lock()` / `pg_try_advisory_lock()` provide cross-instance mutual exclusion. Perfect for preventing duplicate pipeline execution and scheduler coordination. |
| APScheduler | >=4.0 | Persistent scheduled task execution | APScheduler 4.x (rewrite) has native async support, PostgreSQL job store, and distributed execution. Replaces the custom in-memory scheduler. |

**Confidence: MEDIUM** -- PostgreSQL advisory locks are well-documented PostgreSQL core functionality (HIGH confidence on that). APScheduler 4.x is a major rewrite; verify version availability at install time. If APScheduler 4.x is not stable enough, fall back to the existing croniter-based scheduler with advisory lock coordination.

**Why NOT Celery:**
- Celery requires a message broker (RabbitMQ or Redis) -- adds mandatory infrastructure
- GatheRing's constraint is "Redis optional stays optional" (from PROJECT.md)
- The task coordination needed is locking and scheduling, not high-throughput task distribution
- Advisory locks + PostgreSQL are already in the stack

**Why NOT arq:**
- arq requires Redis -- same constraint violation
- Smaller ecosystem, fewer production war stories

### 6. Pipeline Error Recovery: tenacity (upgrade use)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| tenacity | >=8.2 | Retry logic with exponential backoff, circuit breakers | Already in pyproject.toml. Provides `@retry` decorator with configurable strategies (exponential backoff, jitter, stop conditions). Use for pipeline node execution, LLM API calls, external service calls. |

**Confidence: HIGH** -- tenacity is already declared in pyproject.toml line 52. Standard Python retry library. Pipeline error recovery is a usage pattern, not a new dependency.

**What changes:**
- Wrap pipeline node execution with `@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=30))`
- Implement circuit breaker pattern using tenacity's `before_sleep` callback + state tracking
- Add dead letter handling: failed pipeline nodes after max retries are logged to a `pipeline.failed_nodes` table
- LLM API calls already use tenacity in some places -- standardize the retry policy across all providers

### 7. Security Hardening

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| SQLAlchemy ORM (existing) | 2.0.45 | Parameterized queries | Eliminates SQL injection. Already in stack. The issue is that `DatabaseService` in dependencies.py uses raw SQL strings. Move to ORM queries or use SQLAlchemy `text()` with bound parameters exclusively. |
| cryptography (existing) | 46.0.3 | TLS, token signing | Already installed. Used by python-jose's cryptography backend. Will continue to be used by PyJWT. |

**Confidence: HIGH** -- These are existing dependencies that need better utilization, not new additions.

**What changes:**
- Audit every f-string SQL construction (identified in CONCERNS.md: pipelines.py line 311, schedules.py line 390)
- Replace with parameterized queries using `%(param)s` syntax or SQLAlchemy ORM
- Add `bandit` to CI pipeline (already in requirements-dev.txt) with SQL injection rules enabled
- Implement input sanitization middleware for all API endpoints

### 8. OpenTelemetry (already planned, needs activation)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| opentelemetry-api | >=1.20 | Distributed tracing API | Already in requirements.txt. Not installed or integrated. Provides trace context propagation across async boundaries. |
| opentelemetry-sdk | >=1.20 | Tracing SDK | Already in requirements.txt. Implements trace export to Jaeger/OTLP collectors. |
| opentelemetry-instrumentation-fastapi | >=0.41 | Auto-instrument FastAPI | Automatically creates spans for each request. Adds trace_id to structured logs. |
| opentelemetry-instrumentation-sqlalchemy | >=0.41 | Auto-instrument DB queries | Traces every database query with timing and parameters. Critical for N+1 detection. |
| opentelemetry-instrumentation-httpx | >=0.41 | Auto-instrument outbound HTTP | Traces LLM API calls with timing. Already in requirements.txt. |

**Confidence: MEDIUM** -- Libraries exist and are in requirements.txt but exact version compatibility needs verification at install time. The instrumentation packages must match the opentelemetry-api version.

---

## Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| redis | 7.1.0 (installed) | Distributed rate limiting, token blacklist, caching | When deploying multi-instance. Already optional dependency. Use for: slowapi backend, token blacklist, session store. |
| hiredis | >=3.2.0 | Redis protocol parser acceleration | Always install alongside redis for 5-10x parsing speedup. |
| psycopg[binary] | 3.3.2 | C-accelerated psycopg3 | Always in production. Pure-python fallback acceptable for development only. |
| uvloop | 0.22.1 (installed) | Fast asyncio event loop | Already installed via uvicorn[standard]. Provides 2-4x event loop performance over default asyncio. Verify it's being used (uvicorn `--loop uvloop`). |

---

## Development Tools (additions)

| Tool | Purpose | Notes |
|------|---------|-------|
| ruff | Fast linter + formatter | Already in requirements-dev.txt. Replace both black and flake8 -- ruff does both faster. Already configured in pyproject.toml. |
| bandit | Security linter | Already in requirements-dev.txt. Add to CI with `bandit -r gathering/ -ll` to catch SQL injection and other security issues. |
| pip-audit | Dependency vulnerability scanner | Already in requirements-dev.txt. Add to CI to catch known CVEs in dependencies. |
| pytest-asyncio | Async test support | Already installed (1.3.0). Critical for testing the async database layer migration. |

---

## Installation

```bash
# Production dependencies (new additions to existing stack)
pip install "psycopg[binary,pool]>=3.3"  # Already installed
pip install PyJWT>=2.9
pip install slowapi>=0.1.9
pip install "APScheduler>=4.0"  # Verify availability

# Already declared but ensure installed
pip install structlog>=24.0
pip install tenacity>=8.2

# OpenTelemetry stack
pip install opentelemetry-api>=1.20
pip install opentelemetry-sdk>=1.20
pip install opentelemetry-instrumentation-fastapi>=0.41
pip install opentelemetry-instrumentation-sqlalchemy>=0.41
pip install opentelemetry-instrumentation-httpx>=0.41

# Remove deprecated
pip uninstall python-jose passlib psycopg2-binary asyncpg ecdsa rsa pyasn1
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| psycopg 3 (async) | asyncpg | Never for this project -- psycopg3 already installed, covers both sync and async, official SQLAlchemy support |
| psycopg 3 (async) | psycopg2-binary | Never -- psycopg2 is the legacy version, no async support |
| PyJWT | python-jose | Never -- python-jose pulls in 3 extra deps (ecdsa, rsa, pyasn1) and is less actively maintained |
| bcrypt (direct) | passlib | Only if you need support for 30+ hashing schemes -- GatheRing only uses bcrypt |
| bcrypt (direct) | argon2-cffi | When starting a new project -- argon2id is technically superior but switching hashing algorithms requires migrating existing hashes |
| slowapi | Custom middleware | Never -- the custom middleware is already 75 lines and lacks distributed support |
| PostgreSQL Advisory Locks | Redis-based distributed locks | Only if Redis becomes a required dependency -- current constraint says "Redis optional" |
| APScheduler 4.x | Celery Beat | Only if the project needs high-throughput task distribution (100k+ tasks/hour) -- overkill for GatheRing's scheduling needs |
| structlog | loguru | Never -- structlog is already in the dependency list and provides better integration with stdlib logging and OpenTelemetry |
| tenacity | stamina | stamina is newer and simpler but tenacity is already in the stack and more feature-complete |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| python-jose | Pulls in ecdsa, rsa, pyasn1 as dependencies; slower maintenance cadence than PyJWT; FastAPI security docs now reference PyJWT | PyJWT with cryptography backend |
| passlib | Last release 2020; no Python 3.12/3.13 classifiers; wraps bcrypt with unnecessary abstraction layer; known compatibility issues with bcrypt >= 4.1 (hence the pinned `bcrypt>=4.0.0,<4.1.0` in pyproject.toml) | bcrypt directly (already installed, actively maintained by PyCA) |
| psycopg2-binary | Legacy driver; no async support; separate codebase from psycopg3; keeping both means maintaining two connection paths | psycopg 3 (handles both sync and async) |
| asyncpg | Good library but redundant when psycopg3 is already installed; different connection protocol means no pool sharing; SQLAlchemy prefers psycopg3 dialect for new projects | psycopg 3 with SQLAlchemy `postgresql+psycopg://` dialect |
| Celery | Requires mandatory broker infrastructure (RabbitMQ or Redis); GatheRing's constraint is "Redis optional stays optional"; massive dependency tree | PostgreSQL advisory locks + APScheduler for scheduling |
| arq | Requires Redis as mandatory dependency | PostgreSQL advisory locks for distributed coordination |
| Dramatiq | Requires RabbitMQ or Redis | Same as Celery -- infrastructure constraint |
| loguru | Not in current deps; doesn't integrate with OpenTelemetry as cleanly as structlog; global logger pattern conflicts with dependency injection | structlog (already declared as dependency) |

---

## Stack Patterns by Variant

**If deploying single-instance (development/staging):**
- Use in-memory rate limiting fallback (slowapi with MemoryStorage)
- Token blacklist in PostgreSQL table (not Redis)
- APScheduler with PostgreSQL job store
- No Redis required

**If deploying multi-instance (production):**
- Redis-backed rate limiting via slowapi
- Token blacklist in Redis with TTL (fast reads)
- PostgreSQL advisory locks for pipeline execution coordination
- APScheduler with PostgreSQL job store + advisory lock for leader election
- Redis for session caching and EventBus cross-instance pub/sub

**If Redis is unavailable:**
- Everything falls back to PostgreSQL
- Rate limiting: PostgreSQL-backed counter table with periodic cleanup
- Token blacklist: PostgreSQL table with index on token_hash
- Task coordination: PostgreSQL advisory locks (no change)
- Slightly higher DB load but fully functional

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| psycopg 3.3.2 | SQLAlchemy 2.0.45 | Use `postgresql+psycopg://` dialect for async, `postgresql+psycopg://` for sync too |
| psycopg 3.3.2 | Python 3.11, 3.12, 3.13 | All supported per METADATA classifiers |
| psycopg-pool 3.3.0 | psycopg 3.3.2 | Same release cycle, version-matched |
| SQLAlchemy 2.0.45 | psycopg >=3.0.7 | Explicit `postgresql-psycopg` extra in SQLAlchemy METADATA |
| bcrypt 4.3.0 | Python 3.8-3.13 | Remove the `<4.1.0` pin in pyproject.toml -- that pin exists only for passlib compatibility, which we are removing |
| FastAPI 0.126.0 | Starlette 0.40-0.51 | slowapi is built on Starlette -- verify compatible with Starlette 0.50.0 (installed) |
| redis 7.1.0 | Python 3.10-3.14 | Built-in async support (`redis.asyncio`) |
| PyJWT >=2.9 | cryptography >=46.0 | Use `jwt.encode()`/`jwt.decode()` with `algorithms=["HS256"]` -- same interface as python-jose |
| structlog >=24.0 | Python 3.8+ | Configure with `structlog.configure()` at application startup |

---

## Migration Order (Dependency-Aware)

The order matters because some changes depend on others:

1. **structlog activation** -- No deps on other changes; enables audit logging for everything that follows
2. **Async database layer** (psycopg3 + AsyncSession) -- Foundation for all DB-touching changes
3. **Auth replacement** (PyJWT + bcrypt direct) -- Depends on async DB for token blacklist persistence
4. **SQL injection fixes** -- Depends on async DB layer being in place
5. **Rate limiting** (slowapi) -- Independent but benefits from structlog being active
6. **Distributed coordination** (advisory locks + APScheduler) -- Depends on async DB layer
7. **Pipeline error recovery** (tenacity patterns) -- Depends on pipeline execution being implemented
8. **OpenTelemetry activation** -- Can happen anytime but best after all other changes so traces cover the production code

---

## Sources

- psycopg 3.3.2 METADATA: `/home/loc/workspace/gathering/venv/lib/python3.13/site-packages/psycopg-3.3.2.dist-info/METADATA` -- verified async support, Python 3.10-3.14 support
- psycopg `__init__.py`: verified exports AsyncConnection, AsyncCursor, AsyncPipeline, AsyncTransaction
- psycopg-pool 3.3.0 METADATA: `/home/loc/workspace/gathering/venv/lib/python3.13/site-packages/psycopg_pool-3.3.0.dist-info/METADATA` -- verified connection pool package
- asyncpg 0.31.0 METADATA: `/home/loc/workspace/gathering/venv/lib/python3.13/site-packages/asyncpg-0.31.0.dist-info/METADATA` -- Production/Stable, but redundant with psycopg3
- SQLAlchemy 2.0.45 METADATA: verified `postgresql-psycopg` extra (line 63-64)
- python-jose 3.5.0 METADATA: verified dependencies (ecdsa, rsa, pyasn1)
- passlib 1.7.4 METADATA: no Python 3.12/3.13 classifiers, old Metadata-Version 2.1
- bcrypt 4.3.0 METADATA: actively maintained by PyCA, Python 3.8-3.13 support
- redis 7.1.0 METADATA: verified PyJWT as optional dependency (`jwt` extra requires `pyjwt>=2.9.0`)
- FastAPI 0.126.0 METADATA: requires Starlette >=0.40.0,<0.51.0
- Existing codebase: `gathering/db/database.py` (sync-only Database class), `gathering/api/auth.py` (in-memory stores, python-jose, passlib), `gathering/api/middleware.py` (custom rate limiting)
- Project constraints: `.planning/PROJECT.md` -- "Redis optional stays optional", "no stack changes" (interpreted as no framework changes; library upgrades and replacements within the Python/FastAPI ecosystem are in scope)

---
*Stack research for: GatheRing Production-Readiness Consolidation*
*Researched: 2026-02-10*
