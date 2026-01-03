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
│   │ Routers  │ │  Server  │ │  (Redis) │ │  System  │           │
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
│   │   PostgreSQL   │ │     Redis      │ │  File System   │      │
│   │   + pgvector   │ │    (Cache)     │ │  (Workspace)   │      │
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

### Event System

Publish-subscribe event bus using Redis:

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

### API Security

- Input validation with Pydantic
- SQL injection prevention (SQLAlchemy ORM)
- Rate limiting (configurable)
- CORS configuration

### Agent Security

- Tool permission system
- Filesystem sandboxing
- Code execution isolation
- Memory scope isolation

## Scalability

### Horizontal Scaling

- Stateless API servers
- Redis for session sharing
- PostgreSQL connection pooling
- Load balancer compatible

### Performance Optimizations

- Embedding caching
- Query result caching
- Connection pooling
- Async I/O throughout

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
