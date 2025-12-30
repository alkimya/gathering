# GatheRing ䷬

A collaborative multi-agent AI framework built with Python, FastAPI, and React.

## Overview

GatheRing is a highly customizable and modular framework for creating and managing AI agents with complex personalities, diverse competencies, and professional expertise. Agents can collaborate in "Circles", use external tools, and be managed through a modern web dashboard.

## Key Features

- **Multi-Model Support**: Anthropic (Claude), OpenAI, DeepSeek, and local models via Ollama
- **Gathering Circles**: Team orchestration with task routing, reviews, and conflict detection
- **Agent Persistence**: Personas, memory, sessions with automatic context injection
- **Agent Conversations**: Direct inter-agent collaboration with turn strategies
- **REST API**: Full FastAPI backend with WebSocket support
- **React Dashboard**: Modern Web3 dark theme UI for agents, circles, tasks, and conversations
- **RAG Support**: PostgreSQL + pgvector for semantic memory search
- **Knowledge Base**: Semantic search across documentation and best practices
- **Skills System**: Git, Test, and extensible tool framework
- **Agent Autonomy**: Background tasks, scheduled actions, goal management
- **Settings UI**: Configure API keys and application parameters via dashboard
- **Fully Tested**: 205+ tests with TDD approach

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
├── orchestration/  # Circles, Facilitator, Events
├── llm/            # LLM providers (Anthropic, OpenAI, DeepSeek, Ollama)
├── skills/         # Tools (Git, Test, etc.)
├── api/            # FastAPI REST API + WebSocket
├── rag/            # RAG services (embeddings, vector store, memory)
└── db/             # Database models (PostgreSQL + pgvector)

dashboard/          # React + TypeScript + Tailwind (Web3 Dark Theme)
├── src/
│   ├── pages/      # Dashboard, Agents, Circles, Tasks, Schedules, Goals, Settings
│   ├── services/   # API client
│   └── hooks/      # WebSocket hook
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - Full technical documentation
- [Security Audit](docs/SECURITY_AUDIT.md) - Security analysis

## Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.11+, FastAPI, Pydantic |
| Frontend | React 19, TypeScript, Tailwind CSS, Vite |
| Database | PostgreSQL 16 + pgvector |
| LLM | Anthropic, OpenAI, DeepSeek, Ollama |
| Embeddings | OpenAI text-embedding-3-small (1536 dims) |

## Roadmap

### Completed

- [x] **Phase 1-3**: Core, Security, LLM Providers
- [x] **Phase 4**: Skills (Git, Test), DeepSeek Provider
- [x] **Phase 5**: Orchestration, Persistence, Conversations
- [x] **Phase 6**: FastAPI REST API
- [x] **Phase 7**: React Dashboard
- [x] **Phase 8**: RAG with pgvector (multi-schema database, migrations)
- [x] **Phase 9**: RAG Services (Embedding, VectorStore, Memory Manager, Knowledge Base UI)
- [x] **Phase 10**: Agent Autonomy
  - Background task execution with progress tracking
  - Scheduled actions (cron, interval, one-time, event-triggered)
  - Agent goals with hierarchical decomposition
  - Settings page for API keys and configuration

### Next Steps

- [ ] **Phase 11**: Advanced Skills
  - Web browsing skill
  - File system skill
  - Code execution sandbox
  - API integration skill

- [ ] **Phase 12**: Production Readiness
  - Authentication & authorization
  - Rate limiting
  - Monitoring & observability
  - Docker deployment

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
```

## API Overview

```text
GET  /health                       # Health check
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
WS   /ws                           # Real-time updates
```

Full API docs at `/docs` (Swagger) or `/redoc` when server is running.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

- GitHub: [alkimya/gathering](https://github.com/alkimya/gathering)
- Email: [gathering.ai@pm.me](mailto:gathering.ai@pm.me)
