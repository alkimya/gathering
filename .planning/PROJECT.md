# GatheRing Consolidation

## What This Is

A production-readiness consolidation of GatheRing, a collaborative multi-agent AI framework built with Python/FastAPI/React/PostgreSQL. The codebase has functional architecture and 1071 tests, but core features are stubbed, security holes exist, and performance bottlenecks prevent production deployment. This project fixes everything that's broken, closes every gap, and makes GatheRing deployable.

## Core Value

Every existing feature works for real — auth persists, pipelines execute, schedules run, security is solid — so GatheRing can be deployed to production with confidence.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. Inferred from existing codebase. -->

- ✓ Multi-model LLM integration (Anthropic, OpenAI, DeepSeek, Ollama) — existing
- ✓ Agent persistence with personas, memory, sessions — existing
- ✓ Gathering Circles multi-agent orchestration — existing
- ✓ Event-driven architecture with EventBus pub/sub — existing
- ✓ Skill system with 18+ modular capabilities — existing
- ✓ FastAPI REST API with 18+ routers — existing
- ✓ WebSocket real-time updates — existing
- ✓ React dashboard with Web3 dark theme — existing
- ✓ RAG support with pgvector semantic search — existing
- ✓ JWT authentication with token revocation — existing (partial — in-memory)
- ✓ Background task execution framework — existing
- ✓ Scheduler framework for cron-like actions — existing
- ✓ Pipeline configuration and storage — existing
- ✓ Database layer with 8 schemas (SQLAlchemy + PostgreSQL) — existing
- ✓ Alembic migrations — existing
- ✓ 1071 tests with pytest — existing
- ✓ CI/CD with GitHub Actions — existing
- ✓ Agent conversations (inter-agent collaboration) — existing
- ✓ Knowledge base with semantic search — existing
- ✓ Settings UI for API keys and configuration — existing
- ✓ Structured logging with structlog — existing
- ✓ OpenTelemetry instrumentation — existing

### Active

<!-- Current scope. Consolidation targets from CONCERNS.md audit. -->

- [ ] Auth module uses database persistence instead of in-memory store
- [ ] Pipeline execution actually traverses nodes and runs agent tasks
- [ ] Schedule execution dispatches real actions based on action_type
- [ ] Tool registry validates parameters against JSON schema before execution
- [ ] Tool registry supports async function execution
- [ ] Workspace API resolves project-specific paths instead of hardcoded cwd
- [ ] Token blacklist persisted to database (survives restart)
- [ ] SQL injection eliminated — all queries use parameterized statements
- [ ] Timing-safe comparison applied to all auth checks
- [ ] Path traversal vulnerability in file serving fixed
- [ ] LSP input validation added (paths, content size limits)
- [ ] Bare exception catches replaced with specific error handling
- [ ] N+1 queries in circle member retrieval eliminated (JOIN optimization)
- [ ] Synchronous DB calls in async handlers replaced with async driver
- [ ] Event bus implements batching and deduplication for high-frequency events
- [ ] File tree caching invalidated properly (not stale git status)
- [ ] Large files split into smaller domain-specific modules
- [ ] Distributed task coordination for multi-instance deployment
- [ ] Pipeline error recovery (retry logic, circuit breakers, failure handlers)
- [ ] Audit logging for auth events (login attempts, token generation, privilege changes)
- [ ] Rate limiting on API endpoints
- [ ] Auth token lifecycle fully tested (expiry, blacklist cleanup, refresh)
- [ ] Pipeline execution tested (node flow, error propagation, task routing)
- [ ] Database persistence verified (user creation, conversation history, task tracking)
- [ ] Event bus concurrency tested (parallel handling, race conditions, ordering)
- [ ] Scheduler recovery tested (persistence, missed runs, crash recovery)
- [ ] LSP multi-language support tested

### Out of Scope

- New features or capabilities beyond what exists — consolidation only
- Frontend refactoring — dashboard works, leave it
- New LLM provider integrations — existing providers sufficient
- Mobile app — web-first
- Kubernetes/Docker orchestration — infrastructure is separate concern
- Documentation rewrite — existing docs adequate

## Context

GatheRing is a mature-architecture codebase with comprehensive API surface, 1071 tests, and a React dashboard. The problem isn't missing design — it's incomplete implementation. A codebase audit (`.planning/codebase/CONCERNS.md`) revealed:

- **Stub implementations**: Auth uses in-memory store, pipelines fake completion, schedules only log
- **Security holes**: SQL injection via f-string queries, timing attacks, path traversal, non-persistent token blacklist
- **Performance bottlenecks**: Sync DB in async handlers, N+1 queries, unbounded caches, event bus saturation
- **Missing critical features**: No distributed coordination, no pipeline error recovery, no audit logging, no rate limiting
- **Test gaps**: Core flows (auth lifecycle, pipeline execution, DB persistence, event concurrency) untested

The existing architecture is sound. The codebase map (`.planning/codebase/`) provides full structural analysis.

## Constraints

- **Tech stack**: Python 3.11+, FastAPI, SQLAlchemy, PostgreSQL 16+, React 19 — no stack changes
- **Backward compatibility**: API endpoints must maintain existing contracts — dashboard and clients shouldn't break
- **Test discipline**: Every fix includes tests that prove correctness
- **Database**: PostgreSQL + pgvector — no additional database systems (Redis optional stays optional)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Fix over rewrite | Architecture is sound, implementation has gaps | — Pending |
| All CONCERNS.md items in scope | User wants full production readiness | — Pending |
| Test every fix | Prevent regression, prove correctness | — Pending |
| Maintain API compatibility | Dashboard and external clients depend on existing contracts | — Pending |

---
*Last updated: 2026-02-10 after initialization*
