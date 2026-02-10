# Architecture

**Analysis Date:** 2026-02-10

## Pattern Overview

**Overall:** Layered service-oriented architecture with event-driven coordination

**Key Characteristics:**
- **Multi-tier composition**: Core abstractions → Agent wrapper layer → Orchestration → API/WebSocket
- **Event-driven coupling**: Decoupled components communicate via EventBus pub/sub
- **Skill-based capability model**: Agents acquire capabilities through pluggable skill modules
- **Persistent identity**: Agents maintain personas, memories, and sessions across API calls
- **Autonomous agent model**: Facilitator routes tasks, agents decide execution (not commanded)
- **Peer review workflow**: Work goes through review cycle before completion

## Layers

**Core Interfaces & Implementations:**
- Purpose: Define abstract protocols and provide basic implementations for testing
- Location: `gathering/core/`
- Contains: `IAgent`, `ILLMProvider`, `ITool`, `IMemory`, `IConversation` interfaces; `BasicAgent`, `BasicMemory`, `CalculatorTool` implementations; config and schema definitions
- Depends on: Pydantic (validation), tenacity (retry logic)
- Used by: All upper layers build on these interfaces

**Agent Layer:**
- Purpose: Wrap LLMs with persistent identity, memory context injection, skill integration
- Location: `gathering/agents/`
- Contains: `AgentWrapper` (main abstraction), `AgentPersona` (identity), `MemoryService` (context), `ProjectContext` (codebase awareness), `AgentSession` (session tracking), `AgentConversation` (multi-agent chats)
- Depends on: Core interfaces, Event bus, Skills registry, Memory stores
- Used by: Orchestration layer, API routers, conversation systems

**Skill System:**
- Purpose: Modular action capabilities (tools) organized by domain
- Location: `gathering/skills/`
- Contains: Base class `BaseSkill`, 19+ domain skill modules (code, git, database, deploy, etc.), skill registry
- Depends on: Core interfaces, external services (database, git, shell, HTTP)
- Used by: AgentWrapper injects skills into agents, LLM providers expose as tools

**Orchestration Layer:**
- Purpose: Coordinate multi-agent collaboration using event-driven facilitator pattern
- Location: `gathering/orchestration/`
- Contains: `GatheringCircle` (main orchestrator), `Facilitator` (task routing, conflict detection), `EventBus` (pub/sub), `BackgroundTaskExecutor` (persistent async jobs), `Scheduler` (cron-like actions)
- Depends on: Agent layer, Event system, Database models
- Used by: API routers, background task processing

**Data Persistence:**
- Purpose: Store agents, conversations, memories, tasks, audit logs with multi-schema PostgreSQL
- Location: `gathering/db/`
- Contains: `Database` connection manager, 8 schemas (agent, circle, project, communication, memory, review, audit), SQLAlchemy ORM models
- Depends on: SQLAlchemy, asyncpg, pgvector (optional)
- Used by: All components need persistence - agents, circles, tasks, memories

**API Layer:**
- Purpose: REST endpoints + WebSocket for real-time updates
- Location: `gathering/api/`
- Contains: FastAPI app (`main.py`), middleware (auth, rate limit, CORS), 18+ routers (agents, conversations, circles, tasks, etc.), WebSocket manager, auth scheme (JWT)
- Depends on: Orchestration, agents, skills, database
- Used by: Dashboard frontend, external clients

**Real-time Communication:**
- Purpose: WebSocket broadcast of events to dashboard
- Location: `gathering/websocket/`
- Contains: WebSocket manager, event-to-message bridging, connection lifecycle
- Depends on: Event bus, FastAPI WebSocket
- Used by: Dashboard receives live updates

**Supporting Systems:**
- **Events**: `gathering/events/event_bus.py` - Type-safe pub/sub system with event filtering
- **LLM**: `gathering/llm/providers.py` - Abstraction over Anthropic, OpenAI, DeepSeek
- **RAG**: `gathering/rag/` - Vector embeddings + semantic search (uses pgvector)
- **LSP**: `gathering/lsp/` - Language Server Protocol clients for code intelligence
- **Workspace**: `gathering/workspace/` - File, terminal, git, activity managers
- **Telemetry**: `gathering/telemetry/` - Metrics, decorators for instrumentation
- **Cache**: `gathering/cache/` - In-memory + Redis caching
- **Plugins**: `gathering/plugins/` - Extension system for custom capabilities

## Data Flow

**Agent Chat Request:**

1. API router receives `POST /agents/{id}/chat` with user message
2. Router fetches agent from database via `AgentWrapper.from_db()`
3. Wrapper's `chat()` method injects context:
   - Loads conversation history from memory store
   - Injects project context (venv, file structure)
   - Appends persona system prompt
4. Wrapper calls LLM provider with full context + available skills as tools
5. LLM may call tools → wrapper executes via skill system
6. Tool results fed back to LLM for agentic loop
7. Final response stored in conversation history
8. Response returned to client, event published to EventBus
9. WebSocket manager broadcasts to dashboard subscribers

**Circle Task Execution:**

1. Client/scheduler publishes task via `GatheringCircle.create_task()`
2. EventBus emits `TASK_CREATED` event
3. Facilitator subscribes to task events, analyzes task requirements
4. Facilitator uses agent metrics to select best-fit agent(s)
5. TaskOffer sent to selected agent
6. Agent's `accept_task()` callback decides (can refuse)
7. If accepted, agent moves to `IN_PROGRESS`, executes work
8. On completion, publishes `TASK_COMPLETED` + work artifacts
9. Facilitator detects peer needs review, routes to reviewer agent
10. Reviewer agent performs review via `perform_review()` callback
11. Review result published, task marked `COMPLETED` or `CHANGES_REQUESTED`
12. All state transitions persisted to database

**Memory Sharing:**

1. Agent adds memory via `MemoryService.add()`
2. Memory scope (private/circle/project) determines audience
3. EventBus publishes `MEMORY_CREATED` event with scope
4. Other agents in same scope subscribe to `MEMORY_SHARED` events
5. Recipients' memory stores updated, making knowledge available
6. For RAG-enabled memories: text embedded via sentence-transformer, stored in pgvector

**State Management:**

- **Agent state**: Persona (identity), current session, task assignment, last activity
- **Session state**: Conversation history, tool results, execution context
- **Circle state**: Members, tasks, events, conflicts, current status
- **Task state**: Assigned agent, review status, artifacts, iteration count
- **Memory state**: Scope, embedding vector, timestamps, recall count
- **All state**: Persisted to PostgreSQL via SQLAlchemy ORM after each operation

## Key Abstractions

**AgentWrapper:**
- Purpose: Primary abstraction for an LLM with identity and persistence
- Examples: `gathering/agents/wrapper.py`, factory functions like `create_architect_agent()`
- Pattern: Wraps ILLMProvider, composes with Persona + MemoryService + ProjectContext, exposes `chat()` method

**Skill:**
- Purpose: Modular capability that agents can use (tools)
- Examples: `gathering/skills/code/skill.py`, `gathering/skills/git/skill.py`
- Pattern: BaseSkill subclass defines `get_tools_definition()` and `execute()`, tools exposed to LLM via function calling

**GatheringCircle:**
- Purpose: Orchestrates multi-agent collaboration on shared tasks
- Examples: `gathering/orchestration/circle.py`
- Pattern: Maintains AgentHandles, uses Facilitator to route tasks, manages task lifecycle via event subscriptions

**Event & EventBus:**
- Purpose: Decoupled communication primitives
- Examples: `gathering/events/event_bus.py`, `gathering/orchestration/events.py`
- Pattern: Events typed by `EventType` enum, handlers subscribe via `EventBus.subscribe()`, handlers are async callbacks

**Memory Entry:**
- Purpose: Semantic knowledge unit with scope and embedding
- Examples: `gathering/agents/memory.py` defines `MemoryEntry`, `MemoryStore` manages them
- Pattern: Text + scope + optional vector embedding, searchable by semantic similarity (RAG) or keyword

**ProjectContext:**
- Purpose: Codebase-aware information for agents
- Examples: `gathering/agents/project_context.py`
- Pattern: Loads pyproject.toml, venv path, file tree, code conventions, exposes as text injection

## Entry Points

**FastAPI Application:**
- Location: `gathering/api/main.py`
- Triggers: Application startup (uvicorn server)
- Responsibilities: FastAPI lifespan, middleware setup, router registration, WebSocket integration, background task recovery

**WebSocket Handler:**
- Location: `gathering/api/routers/websocket.py`
- Triggers: Client connects to `/ws` endpoint
- Responsibilities: Connection management, EventBus event broadcasting, message serialization

**Background Task Executor:**
- Location: `gathering/orchestration/background.py`
- Triggers: Task enqueued via `BackgroundTaskExecutor.enqueue()`
- Responsibilities: Task persistence, execution with recovery on restart, step tracking

**Scheduler:**
- Location: `gathering/orchestration/scheduler.py`
- Triggers: Scheduled time reached (cron-like)
- Responsibilities: Action execution, run history, next run calculation

**Agent Chat Endpoint:**
- Location: `gathering/api/routers/agents.py`
- Triggers: POST to `/agents/{id}/chat`
- Responsibilities: Load agent, inject context, call LLM, execute tools, persist results

## Error Handling

**Strategy:** Exception hierarchy with specific error types, caught at boundary layers

**Patterns:**
- `GatheringError` base exception at `gathering/core/exceptions.py`, 10+ specific subclasses
- Skill execution failures in `SkillResponse.error` field (non-throwing)
- LLM provider failures caught and wrapped in `LLMProviderError`
- Tool execution errors logged but don't crash agentic loop
- API routers catch exceptions, return appropriate HTTP status codes
- Database transaction rollback on conflicts
- EventBus handlers wrapped in try/except to prevent handler exceptions blocking other subscribers

## Cross-Cutting Concerns

**Logging:** `structlog` configured for structured logging, decorators at `gathering/telemetry/decorators.py` for function tracing

**Validation:** Pydantic models in `gathering/api/schemas.py`, `gathering/db/models.py` enforce type safety

**Authentication:** JWT tokens, `gathering/api/auth.py` handles encode/decode, `AuthenticationMiddleware` validates requests

**Rate Limiting:** `RateLimitMiddleware` in `gathering/api/middleware.py`, per-endpoint configuration

**Telemetry:** Metrics collection at `gathering/telemetry/metrics.py`, agent performance tracking, task timing

**Security:** Permission checks via `SkillPermission` enum, `gathering/gathering/api/auth.py` enforces ownership

---

*Architecture analysis: 2026-02-10*
