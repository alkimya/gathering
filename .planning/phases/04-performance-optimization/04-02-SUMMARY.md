---
phase: 04-performance-optimization
plan: 02
subsystem: api, caching
tags: [slowapi, rate-limiting, lru-cache, memory-management, fastapi]

# Dependency graph
requires:
  - phase: 01-auth-security-foundation
    provides: FastAPI application scaffold and middleware stack
provides:
  - slowapi-powered per-endpoint rate limiting with configurable tiers
  - BoundedLRUDict utility class for bounded in-memory caches
  - All identified unbounded caches retrofitted with size limits
affects: [api-endpoints, memory-service, embedding-service, ai-skills, orchestration-events]

# Tech tracking
tech-stack:
  added: [slowapi]
  patterns: [BoundedLRUDict for all in-memory caches, deque(maxlen=N) for event history]

key-files:
  created:
    - gathering/api/rate_limit.py
    - gathering/utils/bounded_lru.py
  modified:
    - gathering/api/middleware.py
    - gathering/agents/memory.py
    - gathering/rag/embeddings.py
    - gathering/skills/ai/models.py
    - gathering/orchestration/events.py
    - requirements.txt

key-decisions:
  - "slowapi with in-memory backend by default, Redis backend opt-in via REDIS_URL env var"
  - "Per-endpoint decorators are opt-in; default_limits apply globally to all endpoints"
  - "Auth endpoints skip per-endpoint decorators since they lack Request in signature; default_limits covers them"
  - "BoundedLRUDict inherits OrderedDict for drop-in compatibility with existing .get() and [key] patterns"
  - "LLM providers LRUCache already bounded -- left as-is for stability"
  - "EventBus history changed from List to deque(maxlen=N) for O(1) bounded append"

patterns-established:
  - "BoundedLRUDict pattern: import from gathering.utils.bounded_lru, configure max_size per use case"
  - "Rate tier constants: TIER_AUTH(5/min), TIER_WRITE(30/min), TIER_READ(120/min), TIER_HEALTH(300/min)"

# Metrics
duration: 8min
completed: 2026-02-11
---

# Phase 4 Plan 2: Rate Limiting & Cache Bounding Summary

**slowapi per-endpoint rate limiting with 4 tiers, BoundedLRUDict utility for all in-memory caches, deque-based event history**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-10T23:32:34Z
- **Completed:** 2026-02-10T23:41:21Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Replaced hand-rolled RateLimitMiddleware (unbounded defaultdict) with slowapi per-endpoint rate limiting with configurable tiers and optional Redis backend
- Created reusable BoundedLRUDict utility class with LRU eviction for all in-memory caches
- Retrofitted 5 unbounded caches across MemoryService, EmbeddingService, and AISkill with size-bounded replacements
- Changed orchestration EventBus history from List with manual trim to deque(maxlen=N) for O(1) bounded append

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace RateLimitMiddleware with slowapi** - `dd33c2a` (feat)
2. **Task 2: Create BoundedLRUDict and retrofit caches** - `63ddb34` (feat)

## Files Created/Modified
- `gathering/api/rate_limit.py` - slowapi Limiter singleton with rate tiers (TIER_AUTH, TIER_WRITE, TIER_READ, TIER_HEALTH)
- `gathering/utils/bounded_lru.py` - Reusable BoundedLRUDict class with configurable max_size and LRU eviction
- `gathering/api/middleware.py` - RateLimitMiddleware marked as deprecated
- `gathering/agents/memory.py` - _persona_cache(500), _project_cache(100), _session_cache(500) use BoundedLRUDict
- `gathering/rag/embeddings.py` - _memory_cache uses BoundedLRUDict(max_size=2000)
- `gathering/skills/ai/models.py` - _embedding_cache uses BoundedLRUDict(max_size=2000), manual size check removed
- `gathering/orchestration/events.py` - _history uses deque(maxlen=history_size)
- `requirements.txt` - Added slowapi>=0.1.9

## Decisions Made
- slowapi uses in-memory backend by default; Redis backend activates via REDIS_URL env var for distributed deployments
- Auth router endpoints skip per-endpoint @limiter.limit() decorators because they lack `request: Request` parameter in signatures; the limiter's default_limits provide global coverage
- BoundedLRUDict inherits from OrderedDict so existing `.get()` and `[key] = value` patterns work without code changes at call sites
- LLM providers' LRUCache (gathering/llm/providers.py) is already correctly bounded with manual popitem() -- left unchanged for stability
- event_bus.py (gathering/events/) already uses deque(maxlen=1000) -- no changes needed
- TokenBlacklist (gathering/api/auth.py) already uses bounded OrderedDict -- no changes needed

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- The main.py slowapi wiring (import, app.state.limiter assignment, exception handler) was already committed in a prior 04-01 commit. Task 1 committed the remaining pieces: rate_limit.py module, requirements.txt entry, and middleware deprecation comment.
- Linter auto-reverted some file edits (memory.py, embeddings.py, models.py) after initial application, requiring re-application of the same changes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Rate limiting infrastructure ready for per-endpoint decorator annotations on future routers
- BoundedLRUDict available as import for any new in-memory cache patterns
- All existing tests pass (1146 passed, 11 skipped; 3 pre-existing DB-related failures excluded)

## Self-Check: PASSED

- gathering/api/rate_limit.py: FOUND
- gathering/utils/bounded_lru.py: FOUND
- .planning/phases/04-performance-optimization/04-02-SUMMARY.md: FOUND
- Commit dd33c2a: FOUND
- Commit 63ddb34: FOUND

---
*Phase: 04-performance-optimization*
*Completed: 2026-02-11*
