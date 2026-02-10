# Technology Stack

**Analysis Date:** 2026-02-10

## Languages

**Primary:**
- Python 3.11+ - Core framework, backend services
- TypeScript 5.9 - Dashboard frontend
- JavaScript/JSX - React components

**Secondary:**
- SQL - Database queries and migrations
- Shell/Bash - CI/CD workflows

## Runtime

**Backend:**
- Python 3.11, 3.12, 3.13 supported
- FastAPI 0.109+ - Web framework
- Uvicorn 0.27+ - ASGI server

**Frontend:**
- Node.js (specified in package.json)
- React 19.2.0 - UI framework
- Vite 7.2.4 - Build tool and dev server

**Package Manager:**
- Python: Poetry (pyproject.toml) with poetry.lock
- Node: npm (package.json with package-lock.json)

## Frameworks

**Backend/Core:**
- FastAPI 0.109+ - REST API and WebSocket server (Location: `gathering/api/main.py`)
- SQLAlchemy 2.0+ with asyncio - ORM for PostgreSQL (Location: `gathering/db/database.py`)
- Alembic 1.13+ - Database migrations (Location: `gathering/db/migrations/`)
- Pydantic 2.0+ - Data validation and settings (Location: `gathering/core/config.py`)
- Pydantic Settings 2.0+ - Environment configuration management

**Testing (Backend):**
- pytest 7.4+ - Test runner
- pytest-cov 4.1+ - Coverage reporting
- pytest-asyncio 0.21+ - Async test support
- pytest-mock 3.12+ - Mocking framework

**Frontend/UI:**
- React 19.2.0 - Component framework
- React Router 7.11.0 - Client-side routing (Location: `dashboard/src/pages/`)
- Tailwind CSS 4.1.18 - Utility-first CSS
- TypeScript ESLint 8.46 - Linting

**Testing (Frontend):**
- Vitest 4.0+ - Unit test runner
- React Testing Library 16.3.1 - Component testing
- jsdom 27.3.0 - DOM implementation

**Build/Dev Tools:**
- Vite 7.2.4 - Bundle and dev server (Location: `dashboard/vite.config.ts`)
- @vitejs/plugin-react 5.1.1 - React support for Vite
- @tailwindcss/vite 4.1.18 - Tailwind integration
- ESLint 9.39.1 - Code linting (Location: `dashboard/eslint.config.js`)

**Documentation:**
- Sphinx 7.0+ - Documentation generator
- sphinx-rtd-theme 2.0+ - ReadTheDocs theme
- myst-parser 2.0+ - Markdown support in Sphinx
- sphinx-design 0.5+ - Design components

## Key Dependencies

**Critical (Backend):**
- anthropic 0.40+ - Claude API client for LLM integration
- openai 1.0+ - OpenAI API client (GPT-4, embeddings)
- httpx 0.26+ - Async HTTP client for external APIs
- asyncpg 0.29+ - PostgreSQL async driver (performance)
- pycopg 0.1.0+ - PostgreSQL sync driver alternative
- pgvector 0.3.0+ - Vector embeddings support for RAG
- sentence-transformers (optional) - Local embedding models

**Authentication & Security:**
- python-jose 3.3+ with cryptography - JWT token handling
- passlib 1.7+ with bcrypt backend - Password hashing
- bcrypt 4.0.0-4.1.0 (pinned) - Bcrypt implementation for passlib

**Utilities & Services:**
- structlog 24.0+ - Structured logging
- tenacity 8.2+ - Retry logic for API calls
- croniter 2.0+ - Cron expression parsing for scheduling
- aiofiles 23.0+ - Async file operations
- python-multipart 0.0.9+ - Multipart form data handling
- python-dotenv 1.0+ - .env file loading
- psutil 5.9+ - System metrics monitoring

**Optional (Feature-specific):**
- redis 5.0+ - Caching and session storage (opt-in)
- hiredis - Redis protocol optimization (with redis)
- ollama 0.3+ - Local LLM support
- pypdf 6.4.0+ - PDF document processing

**Observability (OpenTelemetry):**
- opentelemetry-api 1.20+ - Telemetry API
- opentelemetry-sdk 1.20+ - SDK implementation
- opentelemetry-exporter-otlp-proto-grpc 1.20+ - OTLP gRPC exporter (Jaeger, Prometheus)
- opentelemetry-instrumentation-requests 0.41+ - HTTP instrumentation
- opentelemetry-instrumentation-httpx 0.41+ - HTTPX instrumentation

**Frontend UI Libraries:**
- @monaco-editor/react 4.7.0 - Code editor component
- @tanstack/react-query 5.90+ - Server state management (with devtools)
- react-markdown 10.1.0 - Markdown rendering
- remark-gfm 4.0.1 - GitHub Flavored Markdown support
- marked 17.0.1 - Markdown parser
- mermaid 11.12.2 - Diagram rendering
- xterm 6.0.0 with xterm/addon-* - Terminal emulation
- lucide-react 0.562.0 - Icon library
- i18next 25.7+ - Internationalization framework

## Configuration Files

**Backend:**
- `pyproject.toml` - Poetry configuration, dependencies, metadata
- `.env.example` - Environment variable template (Never commit actual `.env`)
- `pytest.ini` - Pytest configuration
- `.coveragerc` - Coverage report configuration

**Frontend:**
- `dashboard/package.json` - NPM dependencies and scripts
- `dashboard/tsconfig.json` - TypeScript compiler options
- `dashboard/vite.config.ts` - Vite build and dev configuration
- `dashboard/eslint.config.js` - ESLint rules and extensions

**Project Root:**
- `.readthedocs.yaml` - ReadTheDocs documentation build config
- `.github/workflows/ci.yml` - GitHub Actions test pipeline
- `.github/workflows/publish.yml` - PyPI publishing pipeline

## Platform Requirements

**Development:**
- Python 3.11 or higher
- PostgreSQL 16+ with pgvector extension
- Node.js 18+ (for dashboard)
- Poetry for dependency management
- Git for version control

**Production:**
- PostgreSQL 16+ (externally managed or containerized)
- Python 3.11+ runtime
- Uvicorn ASGI server or compatible Docker setup
- Optional: Redis 5.0+ for caching
- Optional: OpenTelemetry collector (Jaeger/Prometheus) for observability

**Database:**
- PostgreSQL 16+ (required)
- pgvector extension (for vector embeddings/RAG)

## Architecture Overview

The stack follows a **Backend-for-Frontend (BFF) pattern** with separation of concerns:

1. **Backend (Python/FastAPI):** RESTful API + WebSocket server
2. **Frontend (React/TypeScript):** Single-page application
3. **Database (PostgreSQL):** Relational data + vector embeddings
4. **External Services:** LLM providers, optional Redis caching

Key integration flow:
```
Dashboard (React)
  → FastAPI Backend (REST/WebSocket)
    → PostgreSQL + pgvector
    → LLM APIs (OpenAI, Anthropic, Ollama)
    → OpenTelemetry (observability)
    → Optional: Redis (caching)
```

---

*Stack analysis: 2026-02-10*
