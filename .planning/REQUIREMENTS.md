# Requirements: GatheRing Consolidation

**Defined:** 2026-02-10
**Core Value:** Every existing feature works for real -- auth persists, pipelines execute, schedules run, security is solid -- so GatheRing can be deployed to production with confidence.

## v1 Requirements

Requirements for production-ready deployment. Each maps to roadmap phases.

### Security Hardening

- [ ] **SEC-01**: User accounts persist in PostgreSQL via pycopg, surviving server restarts
- [ ] **SEC-02**: Token blacklist persists in database, preventing reuse of revoked tokens after restart
- [ ] **SEC-03**: All SQL queries use parameterized statements -- no f-string SQL construction with user input
- [ ] **SEC-04**: All auth comparisons use constant-time operations (timing-safe), preventing account enumeration
- [ ] **SEC-05**: File serving validates paths against traversal attacks (encoded paths, symlinks)
- [ ] **SEC-06**: Auth events (login, logout, token creation, failed attempts) are logged to audit table
- [ ] **SEC-07**: Server shuts down gracefully, draining in-flight requests before stopping

### Core Feature Completion

- [ ] **FEAT-01**: Pipeline execution traverses DAG nodes and runs agent tasks, conditions, and actions for real
- [ ] **FEAT-02**: Pipeline validation rejects cyclic graphs and enforces node schema before execution
- [ ] **FEAT-03**: Pipeline execution supports per-node retry with exponential backoff and circuit breakers
- [ ] **FEAT-04**: Pipeline runs are cancellable and enforce timeout limits
- [ ] **FEAT-05**: Schedule execution dispatches real actions based on action_type (run_task, execute_pipeline, send_notification, call_api)
- [ ] **FEAT-06**: Schedule execution persists state, preventing duplicate runs after crash recovery
- [ ] **FEAT-07**: Tool registry validates parameters against JSON schema before execution
- [ ] **FEAT-08**: Tool registry supports async function execution via async_function flag

### Performance

- [ ] **PERF-01**: Database access in async handlers uses pycopg async driver, not sync calls blocking the event loop
- [ ] **PERF-02**: Circle member retrieval uses JOIN queries instead of N+1 individual queries
- [ ] **PERF-03**: API endpoints enforce rate limits with per-endpoint tiers and distributed support (slowapi)
- [ ] **PERF-04**: Event bus batches high-frequency events and deduplicates rapid emissions
- [ ] **PERF-05**: In-memory caches (token blacklist, file tree, event history) have size bounds with LRU eviction

### Reliability & Observability

- [ ] **RLBL-01**: Bare exception catches in security and feature paths are replaced with specific error handling
- [ ] **RLBL-02**: Structured logging (structlog) with JSON output and request correlation IDs is active
- [ ] **RLBL-03**: Multi-instance task coordination uses PostgreSQL advisory locks to prevent duplicate execution
- [ ] **RLBL-04**: Workspace API resolves project-specific paths instead of hardcoded current directory

### Database Layer

- [ ] **DBLR-01**: Database layer uses pycopg (high-level PostgreSQL wrapper) as the single DB driver for both sync and async
- [ ] **DBLR-02**: asyncpg and psycopg2-binary dependencies are removed -- pycopg handles all PostgreSQL access

### Test Coverage

- [ ] **TEST-01**: Auth token lifecycle is fully tested (creation, expiry, blacklist cleanup, concurrent use, refresh)
- [ ] **TEST-02**: Pipeline execution is tested (DAG traversal, node execution, error propagation, cycle rejection, timeout)
- [ ] **TEST-03**: Database persistence is verified (user creation, conversation history, task tracking survive restart)
- [ ] **TEST-04**: Event bus concurrency is tested (parallel handling, race conditions, event ordering)
- [ ] **TEST-05**: Scheduler recovery is tested (persistence, missed run detection, crash recovery, duplicate prevention)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Authentication Enhancements

- **AUTH-01**: User can log in via OAuth2/OIDC providers (Google, GitHub)
- **AUTH-02**: Two-factor authentication support

### Infrastructure

- **INFRA-01**: Kubernetes deployment manifests and Helm charts
- **INFRA-02**: Docker Compose production configuration
- **INFRA-03**: OpenTelemetry full activation with Jaeger/Prometheus integration

### Frontend

- **FRNT-01**: Dashboard component library refresh
- **FRNT-02**: Real-time collaboration features

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| New LLM provider integrations | Existing providers (Anthropic, OpenAI, DeepSeek, Ollama) are sufficient |
| New skills or capabilities | Consolidation only -- fix what exists |
| Mobile app | Web-first, mobile is v2+ |
| Frontend refactoring | Dashboard works, leave it |
| Kafka/RabbitMQ event bus | Over-engineering for current scale, PostgreSQL LISTEN/NOTIFY suffices |
| Full async-only DB rewrite | Incremental migration via pycopg async, not wholesale rewrite |
| Documentation rewrite | Existing docs adequate |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DBLR-01 | Phase 1 | Pending |
| DBLR-02 | Phase 1 | Pending |
| SEC-01 | Phase 1 | Pending |
| SEC-02 | Phase 1 | Pending |
| SEC-03 | Phase 1 | Pending |
| SEC-04 | Phase 1 | Pending |
| SEC-05 | Phase 1 | Pending |
| SEC-06 | Phase 1 | Pending |
| RLBL-01 | Phase 1 | Pending |
| RLBL-02 | Phase 1 | Pending |
| TEST-01 | Phase 1 | Pending |
| TEST-03 | Phase 1 | Pending |
| FEAT-01 | Phase 2 | Pending |
| FEAT-02 | Phase 2 | Pending |
| FEAT-03 | Phase 2 | Pending |
| FEAT-04 | Phase 2 | Pending |
| TEST-02 | Phase 2 | Pending |
| FEAT-05 | Phase 3 | Pending |
| FEAT-06 | Phase 3 | Pending |
| FEAT-07 | Phase 3 | Pending |
| FEAT-08 | Phase 3 | Pending |
| RLBL-04 | Phase 3 | Pending |
| TEST-05 | Phase 3 | Pending |
| PERF-01 | Phase 4 | Pending |
| PERF-02 | Phase 4 | Pending |
| PERF-03 | Phase 4 | Pending |
| PERF-04 | Phase 4 | Pending |
| PERF-05 | Phase 4 | Pending |
| TEST-04 | Phase 4 | Pending |
| RLBL-03 | Phase 5 | Pending |
| SEC-07 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 31 total
- Mapped to phases: 31
- Unmapped: 0

---
*Requirements defined: 2026-02-10*
*Last updated: 2026-02-10 after roadmap creation*
