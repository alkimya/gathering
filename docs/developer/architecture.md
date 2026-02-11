# Architecture

This document describes the architecture of GatheRing.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Dashboard (React)                        │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│   │  Agents  │ │ Circles  │ │ Workspace│ │ Calendar │           │
│   └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP/WebSocket
┌─────────────────────────┴───────────────────────────────────────┐
│                        FastAPI Backend                           │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│   │   API    │ │ WebSocket│ │ Event Bus│ │  Skills  │           │
│   │ Routers  │ │  Server  │ │ (In-Mem) │ │  System  │           │
│   └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                        Core Services                             │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│   │  Agent   │ │  Circle  │ │  Memory  │ │Conversation│          │
│   │ Service  │ │ Service  │ │ Service  │ │  Service  │           │
│   └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                       Data Layer                                 │
│   ┌────────────────┐ ┌────────────────┐ ┌────────────────┐      │
│   │   PostgreSQL   │ │  Redis (opt.)  │ │  File System   │      │
│   │ + pgvector     │ │ Rate limit bk  │ │  (Workspace)   │      │
│   │ + adv. locks   │ │                │ │                │      │
│   └────────────────┘ └────────────────┘ └────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
gathering/
├── gathering/              # Python backend
│   ├── api/               # FastAPI routers
│   ├── core/              # Core domain logic
│   ├── agents/            # Agent implementations
│   ├── circles/           # Circle management
│   ├── memory/            # Memory systems
│   ├── skills/            # Skills framework
│   ├── tools/             # Agent tools
│   ├── db/                # Database layer
│   └── websocket/         # WebSocket handlers
├── dashboard/             # React frontend
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Page components
│   │   ├── stores/        # Zustand stores
│   │   ├── api/           # API client
│   │   └── lib/           # Utilities
│   └── public/
├── docs/                  # Documentation
├── tests/                 # Test suite
├── personas/              # Agent personas
└── scripts/               # Utility scripts
```

## Core Components

### Agent System

Agents are the primary actors in GatheRing.

```python
class Agent:
    """Core agent class."""
    id: int
    name: str
    role: str
    provider: str  # openai, anthropic, ollama
    model: str     # provider-specific model name
    personality: PersonalityConfig
    memory: MemorySystem
    tools: list[Tool]
```

Key concepts:

- **Personality**: Traits that influence behavior
- **Memory**: Short-term and long-term storage
- **Tools**: Capabilities the agent can use
- **Sessions**: Track agent activity

### Circle System

Circles organize agents into collaborative groups.

```python
class Circle:
    """Circle for agent collaboration."""
    id: int
    name: str
    agents: list[Agent]
    config: CircleConfig
    state: CircleState
```

Features:

- Agent membership management
- Conversation hosting
- Shared memory scope
- Configurable conversation modes

### Memory System

Multi-layered memory architecture:

```
┌─────────────────────────────────────┐
│         Semantic Search             │
│        (pgvector + RAG)             │
├─────────────────────────────────────┤
│         Long-term Memory            │
│      (PostgreSQL + embeddings)      │
├─────────────────────────────────────┤
│         Short-term Memory           │
│       (Session context)             │
└─────────────────────────────────────┘
```

Memory scopes:

- `global`: Shared across all agents
- `circle`: Shared within a circle
- `agent`: Private to an agent
- `conversation`: Specific to a conversation

### Pipeline Engine

DAG-based workflow execution with topological traversal:

```
┌─────────┐     ┌─────────┐     ┌─────────┐
│  Start  │────>│ Agent A │────>│  End    │
└─────────┘     └────┬────┘     └─────────┘
                     │               ▲
                     ▼               │
                ┌─────────┐    ┌─────────┐
                │Condition│───>│ Agent B │
                └─────────┘    └─────────┘
```

Key components:

- **PipelineExecutor**: Traverses DAG in topological order via `graphlib.TopologicalSorter`
- **Node dispatchers**: 6 types -- agent, condition, action, transform, filter, merge
- **CircuitBreaker**: Per-node with configurable failure threshold
- **Retry**: Exponential backoff via `tenacity`, only retries `NodeExecutionError`
- **PipelineRunManager**: Tracks active runs, enforces timeout (`asyncio.timeout`), handles cancellation (cooperative then forced)
- **Validation**: Rejects cyclic graphs, enforces node schema before execution

### Scheduler

Cron-based action dispatch with crash recovery:

- **Action types**: `run_task`, `execute_pipeline`, `send_notification`, `call_api`
- **Crash recovery**: Detects missed runs on startup, deduplicates via execution history
- **Advisory locks**: Multi-instance coordination via `pg_try_advisory_xact_lock`
- **Dispatcher functions**: Module-level async functions, not methods, for clean testability

### Event System

Publish-subscribe event bus (in-memory with backpressure):

```python
# Publishing events
await event_bus.publish("agent.message", {
    "agent_id": 1,
    "content": "Hello!"
})

# Subscribing to events
@event_bus.subscribe("agent.message")
async def handle_message(event):
    print(f"Agent said: {event['content']}")
```

Event types:

- `agent.*`: Agent lifecycle events
- `circle.*`: Circle events
- `conversation.*`: Conversation events
- `workspace.*`: Workspace events

## API Layer

### REST Endpoints

Organized by domain:

```
/agents           # Agent CRUD
/circles          # Circle management
/conversations    # Conversation handling
/workspace        # Workspace operations
/memory           # Memory access
```

### WebSocket Channels

Real-time communication:

```
/ws/circles/{name}     # Circle events
/ws/workspace/{id}     # Workspace updates
/ws/agents/{id}        # Agent streams
```

Message format:

```json
{
  "type": "message",
  "data": {
    "agent_id": 1,
    "content": "Hello!",
    "timestamp": "2025-01-01T00:00:00Z"
  }
}
```

## Database Schema

### Core Tables

```
agent.agents           # Agent definitions
agent.sessions         # Agent sessions
agent.tools            # Agent tools

circle.circles         # Circle definitions
circle.memberships     # Agent-circle relationships

conversation.conversations  # Conversations
conversation.turns          # Conversation turns
conversation.messages       # Messages

memory.memories        # Long-term memories
memory.embeddings_cache    # Cached embeddings
memory.knowledge_base      # Shared knowledge

project.projects       # Projects
project.tasks          # Tasks
```

### Schemas

- `public`: Common types and functions
- `agent`: Agent-related tables
- `circle`: Circle-related tables
- `conversation`: Conversation tables
- `memory`: Memory and RAG
- `project`: Project management

## Frontend Architecture

### Tech Stack

- **React 18**: UI framework
- **TypeScript**: Type safety
- **Zustand**: State management
- **TanStack Query**: Data fetching
- **Tailwind CSS**: Styling
- **Monaco Editor**: Code editing
- **xterm.js**: Terminal emulation

### State Management

```typescript
// Zustand store example
const useAgentStore = create((set) => ({
  agents: [],
  selectedAgent: null,

  setAgents: (agents) => set({ agents }),
  selectAgent: (agent) => set({ selectedAgent: agent }),
}));
```

### Component Structure

```
src/
├── components/
│   ├── ui/            # Base UI components
│   ├── agents/        # Agent components
│   ├── circles/       # Circle components
│   └── workspace/     # Workspace components
├── pages/
│   ├── Dashboard.tsx
│   ├── AgentDetail.tsx
│   ├── CircleView.tsx
│   └── Workspace.tsx
└── stores/
    ├── agentStore.ts
    ├── circleStore.ts
    └── workspaceStore.ts
```

## Security

### Authentication

- **JWT tokens**: PyJWT with HS256, DB-persisted token blacklist (write-through LRU cache + PostgreSQL)
- **Password hashing**: Direct bcrypt (>= 4.0.0), constant-time comparisons to prevent timing attacks
- **Audit logging**: Auth events (login, logout, token creation, failed attempts) logged to audit table
- **Token lifecycle**: Creation, expiry, blacklist cleanup, concurrent use, refresh -- all tested

### API Security

- Input validation with Pydantic
- SQL injection prevention -- all queries use parameterized statements via `safe_update_builder`
- Path traversal defense -- `validate_file_path` double-decodes URLs, blocks `../`, `%2e%2e/`, symlink escape
- Rate limiting -- per-endpoint tiers (strict/standard/relaxed/bulk) via slowapi with 429 + Retry-After headers
- CORS configuration
- Structured logging (structlog) with JSON output and request correlation IDs

### Agent Security

- Tool permission system
- JSON Schema validation on all tool parameters before execution
- Filesystem sandboxing
- Code execution isolation
- Memory scope isolation

## Scalability

### Multi-Instance Support

- **Advisory locks**: `pg_try_advisory_xact_lock(namespace, action_id)` prevents duplicate task execution across instances
- **Fail-closed**: DB errors return False (skip execution) rather than risk duplicates
- **Graceful shutdown**: Ordered teardown -- stop accepting requests, drain in-flight, stop scheduler, close DB pool last
- **Readiness probe**: `/health/ready` returns 503 during shutdown for load balancer integration

### Horizontal Scaling

- Stateless API servers with PostgreSQL advisory lock coordination
- Redis optional (rate limiting backend, not required)
- pycopg async connection pooling (min 4, max 20)
- Load balancer compatible with graceful shutdown

### Performance Optimizations

- **Async DB**: pycopg `AsyncPooledDatabase` for non-blocking queries in async handlers
- **N+1 elimination**: `get_circle_members_full()` single JOIN replaces 2N+1 queries
- **Bounded caches**: `BoundedLRUDict` with configurable max size and LRU eviction
- **Event bus backpressure**: Semaphore-limited concurrent handlers, time-windowed deduplication
- Embedding caching
- Connection pooling

## Configuration

### Environment Variables

```env
# Database
DATABASE_URL=postgresql://...
REDIS_URL=redis://...

# AI Providers
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Server
API_HOST=0.0.0.0
API_PORT=8000

# Features
ENABLE_REDIS_CACHE=true
ENABLE_WEBSOCKET=true
```

### Configuration Files

- `pyproject.toml`: Python project config
- `pytest.ini`: Test configuration
- `.env`: Environment variables
- `dashboard/vite.config.ts`: Frontend config

## Related Topics

- [Contributing](contributing.md) - How to contribute
- [Database](database.md) - Database details
- [API](api.md) - API development
- [Testing](testing.md) - Test guidelines
