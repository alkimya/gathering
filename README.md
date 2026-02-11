# GatheRing ䷬

A collaborative multi-agent AI framework built with Python, FastAPI, and React.

## Overview

GatheRing is a highly customizable and modular framework for creating and managing AI agents with complex personalities, diverse competencies, and professional expertise. Agents can collaborate in "Circles", use external tools, and be managed through a web dashboard.

## Key Features

- **Multi-Model Support**: Anthropic (Claude), OpenAI, DeepSeek, and local models via Ollama
- **Gathering Circles**: Team orchestration with task routing, reviews, and conflict detection
- **Agent Persistence**: Personas, memory, sessions with automatic context injection
- **Agent Conversations**: Direct inter-agent collaboration with turn strategies
- **Pipeline Execution**: DAG-based workflow engine with topological traversal, retry + circuit breakers, cancellation and timeout
- **Schedule System**: Cron-based action dispatch (run_task, execute_pipeline, send_notification, call_api) with crash recovery
- **REST API**: Full FastAPI backend with 206 rate-limited endpoints and WebSocket support
- **React Dashboard**: Modern Web3 dark theme UI for agents, circles, tasks, and conversations
- **RAG Support**: PostgreSQL + pgvector for semantic memory search
- **Knowledge Base**: Semantic search across documentation and best practices
- **Skills System**: 18+ skills (filesystem, git, code, shell, database, http, etc.) with JSON Schema validation and async execution
- **Agent Autonomy**: Background tasks, scheduled actions, goal management
- **Settings UI**: Configure API keys and application parameters via dashboard
- **Security**: JWT auth with DB-persisted token blacklist, constant-time comparisons, SQL injection prevention, path traversal defense, audit logging
- **Rate Limiting**: Per-endpoint rate limits with 4 tiers (strict/standard/relaxed/bulk) via slowapi
- **Multi-Instance**: PostgreSQL advisory locks for distributed task coordination, graceful shutdown with request draining
- **Observability**: Structured logging (structlog) with JSON output, request correlation IDs, OpenTelemetry instrumentation
- **Async Database**: pycopg async driver for non-blocking DB access in async handlers
- **Fully Tested**: 1200+ tests covering auth lifecycle, pipeline execution, scheduler recovery, event concurrency, and more

## Quick Start

```bash
# Clone the repository
git clone https://github.com/alkimya/gathering.git
cd gathering

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys and database credentials

# Setup database (PostgreSQL + pgvector)
python -m gathering.db.setup

# Run tests
pytest tests/ -v

# Start the API server
uvicorn gathering.api:app --reload

# Start the dashboard (in another terminal)
cd dashboard
npm install
npm run dev
```

## Architecture

```text
gathering/
├── core/           # Core abstractions and config
├── agents/         # Agent persistence (persona, memory, session)
├── orchestration/  # Circles, Facilitator, Events, Pipelines
├── llm/            # LLM providers (Anthropic, OpenAI, DeepSeek, Ollama)
├── skills/         # Tools (Git, Test, etc.) with JSON Schema validation
├── api/            # FastAPI REST API + WebSocket + Rate Limiting
├── rag/            # RAG services (embeddings, vector store, memory)
└── db/             # Database models (PostgreSQL + pgvector + pycopg)

dashboard/          # React + TypeScript + Tailwind (Web3 Dark Theme)
├── src/
│   ├── pages/      # Dashboard, Agents, Circles, Tasks, Schedules, Goals, Settings
│   ├── services/   # API client
│   └── hooks/      # WebSocket hook
```

## Documentation

- [User Guide](docs/user/guide.md) - Getting started guide
- [Dashboard Guide](docs/user/dashboard.md) - Web dashboard documentation
- [Architecture](docs/developer/architecture.md) - Technical documentation
- [API Reference](docs/api/endpoints.md) - REST API documentation
- [Contributing](docs/developer/contributing.md) - Developer guide

## Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.11+, FastAPI, Pydantic |
| Frontend | React 19, TypeScript, Tailwind CSS, Vite |
| Database | PostgreSQL 16 + pgvector |
| DB Layer | [pycopg](https://pypi.org/project/pycopg/) - High-level PostgreSQL API (sync + async) |
| LLM | Anthropic, OpenAI, DeepSeek, Mistral, Google, Ollama |
| Embeddings | OpenAI text-embedding-3-small (1536 dims) |
| Auth | PyJWT + bcrypt with DB-persisted token blacklist |
| Rate Limiting | slowapi with per-endpoint tiers |
| Logging | structlog with JSON output + correlation IDs |

## Environment Variables

```bash
# Required
DATABASE_URL=postgresql://user:pass@localhost:5432/gathering
OPENAI_API_KEY=sk-...          # For embeddings + OpenAI models

# Optional LLM providers
ANTHROPIC_API_KEY=sk-ant-...   # For Claude models
DEEPSEEK_API_KEY=sk-...        # For DeepSeek models
OLLAMA_HOST=http://localhost:11434  # For local models

# Dashboard
VITE_API_URL=http://localhost:8000  # API URL for frontend

# Authentication (production)
SECRET_KEY=your-secret-key-min-32-chars  # JWT signing key
ADMIN_EMAIL=admin@example.com            # Admin email
ADMIN_PASSWORD_HASH=$2b$12$...           # Bcrypt hash of admin password
```

## API Overview

```text
GET  /health                       # Health + readiness check
GET  /agents                       # List agents
POST /agents                       # Create agent
POST /agents/{id}/chat             # Chat with agent
GET  /circles                      # List circles
POST /circles/{name}/tasks         # Create task
POST /conversations                # Start conversation
POST /memories/agents/{id}/recall  # Semantic memory search
POST /memories/knowledge/search    # Knowledge base search
GET  /background-tasks             # List background tasks
POST /background-tasks             # Create background task
GET  /scheduled-actions            # List scheduled actions
POST /scheduled-actions            # Create scheduled action
GET  /goals                        # List agent goals
POST /goals                        # Create goal
GET  /settings                     # Get configuration
PATCH /settings/providers/{name}   # Update provider settings
POST /auth/login                   # Authenticate user
POST /auth/logout                  # Revoke token
WS   /ws?token=<jwt>               # Real-time updates (authenticated)
```

Full API docs at `/docs` (Swagger) or `/redoc` when server is running.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

- GitHub: [alkimya/gathering](https://github.com/alkimya/gathering)
- Email: [loc.cosnier@pm.me](mailto:loc.cosnier@pm.me)
