# External Integrations

**Analysis Date:** 2026-02-10

## LLM Provider APIs

**OpenAI:**
- Service: GPT-4, GPT-3.5, text-embedding-3-small/large
- What it's used for: Chat completions, code generation, embeddings for RAG
- SDK/Client: `openai` package (OpenAI class in `gathering/llm/providers.py`)
- Auth: `OPENAI_API_KEY` environment variable
- Configuration location: `gathering/core/config.py` (OpenAIConfig class)
- Implementation: `gathering/llm/providers.py` - OpenAIProvider class

**Anthropic (Claude):**
- Service: Claude 3 models (claude-3-opus-20240229, claude-sonnet-4-20250514)
- What it's used for: Advanced reasoning, multi-turn conversations
- SDK/Client: `anthropic` package (Anthropic class in `gathering/llm/providers.py`)
- Auth: `ANTHROPIC_API_KEY` environment variable
- Configuration location: `gathering/core/config.py` (AnthropicConfig class)
- Implementation: `gathering/llm/providers.py` - AnthropicProvider class
- Model specified: `ANTHROPIC_DEFAULT_MODEL` env var (default: claude-sonnet-4-20250514)

**Ollama (Local LLM):**
- Service: Local LLM inference via Ollama server
- What it's used for: Local model inference (llama2, llama3.2, etc.)
- SDK/Client: `ollama` package (Client class in `gathering/llm/providers.py`)
- Connection: `OLLAMA_BASE_URL` environment variable (default: http://localhost:11434)
- Configuration location: `gathering/core/config.py` (OllamaConfig class)
- Implementation: `gathering/llm/providers.py` - OllamaProvider class
- Model: `OLLAMA_DEFAULT_MODEL` env var

**DeepSeek (Optional):**
- Service: DeepSeek API (deepseek-chat, deepseek-coder)
- Auth: `DEEPSEEK_API_KEY` environment variable
- Configuration location: `gathering/core/config.py` (references deepseek_api_key)
- Status: Defined in config but no dedicated provider class yet

**LLM Provider Factory:**
- Location: `gathering/llm/providers.py` - LLMProviderFactory class
- Supported providers: "openai", "anthropic", "ollama", "mock" (for testing)
- Usage pattern: Factory creates provider instances based on provider name
- Built-in features: Rate limiting (RateLimiter class), LRU response caching (LRUCache class)

## Data Storage

**Primary Database:**
- Type/Provider: PostgreSQL 16+ with pgvector extension
- Connection: `DATABASE_URL` environment variable (or individual DB_* variables)
- Connection patterns:
  - `GATHERING_DATABASE_URL` (preferred for framework)
  - `DATABASE_URL` (fallback)
  - Individual: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
  - Standard PostgreSQL: `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`
- ORM: SQLAlchemy 2.0+ with asyncio support
- Async Driver: asyncpg (primary)
- Sync Driver: psycopg2-binary (for migrations)
- Sync Wrapper: pycopg (high-level API)
- Implementation: `gathering/db/database.py` - Database class
- Models location: `gathering/db/models.py` - SQLAlchemy models
- Database module: `gathering/db/__init__.py` - Database initialization

**Vector Database (Embeddings):**
- Type: PostgreSQL pgvector extension
- Used for: Semantic search, RAG memory retrieval
- Vector dimension: Configurable via `EMBEDDING_DIMENSION` env var (default: 1536 for OpenAI text-embedding-3-small)
- Memory retrieval: Configurable similarity threshold (`MEMORY_SIMILARITY_THRESHOLD`, default: 0.7)
- Recall limit: `MEMORY_RECALL_LIMIT` (default: 10 memories per query)
- Implementation: `gathering/rag/vectorstore.py` - Vector store operations

**Optional Cache Storage:**
- Type/Provider: Redis (optional feature)
- Connection: `REDIS_URL` environment variable (default: redis://localhost:6379/0)
- Used for: Session caching, response caching, optional distributed caching
- Client: `redis` package
- Implementation: `gathering/cache/redis_cache.py`, `gathering/cache/redis_manager.py`
- Status: Optional dependency - framework functions without it but uses if available

**File Storage:**
- Type: Local filesystem
- Base path: `FILE_STORAGE_BASE_PATH` environment variable (default: /tmp/gathering)
- Max size: `FILE_STORAGE_MAX_SIZE_MB` (default: 100 MB)
- Async operations: aiofiles for non-blocking file I/O
- Sandbox: Storage is contained within FILE_STORAGE_BASE_PATH
- Implementation: File operations handled in `gathering/utils/` and API routers

## Embeddings & Vector Operations

**Embedding Service:**
- Provider: OpenAI API (text-embedding-3-small by default)
- Location: `gathering/rag/embeddings.py` - EmbeddingService class
- API key: `OPENAI_API_KEY` (required for embeddings)
- Default model: `OPENAI_EMBEDDING_MODEL` (default: text-embedding-3-small, 1536 dims)
- Alternative dimensions: text-embedding-3-large (3072 dims)
- Caching: Optional integration with Redis via CacheManager
- Batch operations: Support for batch embedding requests

**Vector Store:**
- Location: `gathering/rag/vectorstore.py`
- Backend: PostgreSQL with pgvector
- Operations: Insert, search, delete embeddings
- Similarity search: Vector cosine similarity with threshold filtering
- TTL/Retention: Based on memory manager policies

**Memory Manager:**
- Location: `gathering/rag/memory_manager.py`
- Integrates: Vector store + embedding service
- Features: Long-term memory, semantic search, memory recall

## Authentication & Identity

**Auth Provider:**
- Type: Custom JWT-based authentication
- Implementation location: `gathering/api/auth.py`
- Token format: JWT with HS256 algorithm
- Token expiration: 24 hours (`ACCESS_TOKEN_EXPIRE_HOURS`)
- Password hashing: Bcrypt via passlib

**Admin User:**
- Source: Environment variables (not database)
- Credentials stored as: `ADMIN_EMAIL` and `ADMIN_PASSWORD_HASH`
- Password hash generation: Bcrypt hash (provide pre-hashed in env)
- Default admin: Can be created via `.env` configuration

**User Management:**
- User storage: PostgreSQL database
- Roles: "admin", "user"
- Registration endpoint: `/auth/register` (public)
- Login endpoint: `/auth/login` (public)
- Token endpoint: `/auth/login/json` (public)
- JWT validation: `decode_token()` function in `gathering/api/auth.py`

**Authentication Middleware:**
- Location: `gathering/api/middleware.py` - AuthenticationMiddleware class
- Public paths (no auth required):
  - `/` (root health check)
  - `/health`, `/health/ready`, `/health/live` (health checks)
  - `/auth/*` (authentication endpoints)
  - `/docs`, `/redoc`, `/openapi.json` (documentation)
  - `/ws` (WebSocket initial connection - auth passed in URL)
- Protected: All other endpoints require valid JWT Bearer token
- Token location: Authorization header (Bearer token)

**Security Configuration:**
- Secret key: `SECRET_KEY` environment variable (required for production)
- Rate limiting: `RATE_LIMIT_PER_MINUTE` (default: 60, enforced in middleware)
- Max tokens per request: `MAX_TOKENS_PER_REQUEST` (default: 4000)
- CORS origins: `CORS_ORIGINS` (comma-separated list, default: localhost:3000, localhost:5173)
- Auth disable flag: `DISABLE_AUTH` (false by default, true disables auth for development)

## Monitoring & Observability

**OpenTelemetry Stack:**
- Framework: OpenTelemetry 1.20+
- Location: `gathering/telemetry/config.py`, `gathering/telemetry/metrics.py`, `gathering/telemetry/decorators.py`

**Tracing:**
- Exporter: OTLP gRPC exporter (opentelemetry-exporter-otlp-proto-grpc)
- Collectors supported: Jaeger, Prometheus, any OTLP-compatible endpoint
- Auto-instrumentation:
  - HTTP requests (requests library)
  - HTTPX client calls
- Span processor: BatchSpanProcessor

**Metrics:**
- Exporter: OTLP gRPC metric exporter
- Reader: PeriodicExportingMetricReader
- Metrics include: Request counts, latencies, error rates, system metrics

**System Monitoring:**
- Library: psutil 5.9+
- Used for: CPU, memory, disk monitoring
- Integration: Custom metrics in telemetry module

**Error Tracking:**
- Method: Structured logging with structlog 24.0+
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL (configurable via LOG_LEVEL)
- Environment: `GATHERING_ENV` (development, staging, production)
- Debug mode: `DEBUG` environment variable

**Logging:**
- Framework: structlog 24.0+ - structured, async-safe logging
- Configuration: `LOG_LEVEL` environment variable
- Format: JSON-compatible structured logs
- Location: Various modules use `logging.getLogger()` for FastAPI modules

## CI/CD & Deployment

**Continuous Integration:**
- Platform: GitHub Actions
- Config location: `.github/workflows/ci.yml`
- Triggered on: push to main/develop, all pull requests
- Test environment: Ubuntu latest with PostgreSQL 16 (pgvector image)
- Test matrix: Python 3.11, 3.12
- Test runner: pytest with coverage
- Coverage: HTML and terminal reports

**Publishing Pipeline:**
- Config location: `.github/workflows/publish.yml`
- Target: PyPI (Python Package Index)
- Auth method: GitHub trusted publishing (no hardcoded tokens)
- Triggered on: Release creation
- Distribution: Includes SQL migrations in wheel/sdist

**Package Distribution:**
- Format: Python wheel + source distribution (sdist)
- Includes: SQL migration files (gathering/db/migrations/*.sql)
- Manifest: MANIFEST.in (specifies included non-Python files)
- Package name: gathering

**Docker:**
- Status: No Dockerfile in repo - applications containerized externally
- Database: External PostgreSQL 16+ with pgvector
- Backend: Runs on Uvicorn (included in requirements)
- Frontend: Built as static files (SPA)

## Webhooks & Callbacks

**WebSocket Connections:**
- Endpoint: `/ws` (general events)
- Endpoint: `/ws/terminal/{project_id}` (terminal output)
- Manager: `gathering/api/websocket/manager.py` - ConnectionManager class
- Integration: Event bus broadcasts to WebSocket clients via `setup_websocket_broadcasting()`
- Location: `gathering/websocket/integration.py`

**Event Broadcasting:**
- Event bus: In-memory event distribution
- Subscribers: WebSocket clients listen for agent updates, task progress, etc.
- Protocol: JSON messages over WebSocket

**Incoming Webhooks:**
- Status: Not explicitly configured in codebase
- Potential use: Agent skill plugins may accept webhooks (check `gathering/plugins/` and `gathering/skills/`)

**Outgoing Webhooks:**
- Status: Framework supports but not preconfigured
- Possible use: Agent orchestration may trigger external services via HTTP (uses httpx)

## Environment Configuration

**Required Environment Variables:**

*Database:*
- `DATABASE_URL` or individual `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`

*LLM Providers (at least one required):*
- `ANTHROPIC_API_KEY` - For Claude access
- `OPENAI_API_KEY` - For GPT-4 and embeddings

*Security:*
- `SECRET_KEY` - JWT signing key (generate with: python -c "import secrets; print(secrets.token_hex(32))")
- `ADMIN_EMAIL` - Admin user email
- `ADMIN_PASSWORD_HASH` - Bcrypt password hash (generate with: python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('password'))")

*Optional:*
- `REDIS_URL` - Redis connection (redis://host:port/db)
- `OPENAI_ORG_ID` - OpenAI organization ID
- `DEEPSEEK_API_KEY` - DeepSeek API key
- `OLLAMA_BASE_URL` - Local Ollama server URL
- All additional settings defined in `gathering/core/config.py`

**Secrets Management:**
- Method: Environment variables via `.env` file (development)
- Production: Use platform secrets (GitHub, AWS, GCP, etc.)
- Never commit: `.env` file is in `.gitignore`
- Template: `.env.example` provides documented variable reference
- Secret rotation: Implement by updating env vars in production platform
- Development mode: Can set `DISABLE_AUTH=true` for local testing

**Configuration Validation:**
- Framework: Pydantic Settings with validation
- Location: `gathering/core/config.py` - Settings class
- Behavior: Loads from `.env` file in development, environment variables elsewhere
- Validation: Type checking and range validation on settings
- Production check: Settings.require_production_ready() validates production configuration
- Environment: `GATHERING_ENV` determines development/staging/production mode

---

*Integration audit: 2026-02-10*
