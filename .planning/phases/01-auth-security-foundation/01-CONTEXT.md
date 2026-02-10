# Phase 1: Auth + Security Foundation - Context

**Gathered:** 2026-02-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Users and tokens persist across restarts, all security vulnerabilities are closed, and the database layer is consolidated on pycopg. This phase covers persistent auth, SQL injection elimination, security hardening, and DB layer consolidation. Creating new auth features (OAuth, SSO, etc.) or new API capabilities are out of scope.

</domain>

<decisions>
## Implementation Decisions

### Auth persistence & migration
- Claude's Discretion: migration strategy (force re-login vs graceful window) — pick simplest and safest
- Claude's Discretion: token revocation persistence — decide based on project security posture
- Claude's Discretion: token lifetimes (access + refresh durations) — pick appropriate balance
- Claude's Discretion: multi-device session policy — assess based on existing codebase behavior
- User ID format must remain `str` to avoid forced re-login (from research findings)

### Security response behavior
- Claude's Discretion: auth error message verbosity — balance security with usability
- Claude's Discretion: attack attempt logging — decide based on practical monitoring needs
- Claude's Discretion: auth-specific rate limiting timing (Phase 1 vs Phase 4) — assess based on risk
- Claude's Discretion: password hashing algorithm (bcrypt vs argon2) — pick based on existing dependencies
- Constant-time auth responses required (from success criteria)
- Path traversal attempts must return 403 (from success criteria)

### DB migration strategy
- Claude's Discretion: migration approach (big bang vs incremental by domain) — pick based on codebase structure and risk
- Claude's Discretion: migration tooling (Alembic vs raw SQL) — pick based on existing dependencies
- Claude's Discretion: dev/test database backend (PostgreSQL everywhere vs SQLite fallback) — pick based on test infrastructure
- Claude's Discretion: EventBus unification timing — assess whether safe alongside DB migration or should wait
- Two separate EventBus implementations must be preserved at boundary minimum (from research findings)

### Exception handling policy
- Claude's Discretion: scope of bare exception fixes (security paths only vs all 262) — follow tiered approach from research
- Claude's Discretion: logging strategy (always log vs log unexpected only) — pick based on existing logging setup
- Claude's Discretion: 500 error response format (with request ID vs plain) — pick based on existing error handling
- Claude's Discretion: exception class strategy (custom hierarchy vs built-in) — pick based on existing patterns

### Claude's Discretion
All four discussion areas were delegated to Claude's judgment. Claude has full flexibility to make implementation decisions across auth migration, security responses, DB migration, and exception handling — guided by the success criteria, research findings, and existing codebase patterns. The key constraints are:
- User ID format stays as `str`
- EventBus boundary preserved
- Tiered approach to bare exception fixes (security paths first)
- All success criteria from ROADMAP.md must be met

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. User trusts Claude's judgment on all implementation details for this infrastructure/security phase.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-auth-security-foundation*
*Context gathered: 2026-02-10*
