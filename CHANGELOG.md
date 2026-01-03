# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-01-03

### Added

- **Skills Configuration UI**: Dashboard panel to enable/disable agent skills with toggle switches
- **Agent Skills API**: CRUD endpoints for managing agent skills (`GET/PUT/POST/DELETE /agents/{id}/skills`)
- **Responsive Mobile Layout**: Collapsible sidebars for Agents, Circles, and Conversations pages
- **Documentation Lightbox**: Click-to-zoom images in Sphinx documentation
- **Projects Section in Docs**: Added Projects documentation with workflow guide
- **pycopg Integration**: Using pycopg from PyPI for database operations

### Changed

- **Dashboard Documentation**: Reorganized with Quick Start Workflow (Projects → Agents → Circles → Launch)
- **Package Structure**: SQL migrations now included in wheel distribution
- **Dependencies**: Removed local pycopg, now using `pycopg>=0.1.0` from PyPI

### Fixed

- **Mobile UX**: Sidebar no longer takes full screen on mobile devices
- **Image Visibility**: Documentation images now clickable with lightbox overlay

### Technical

- Added `AgentSkillsPanel` component with skill toggles and tools expansion
- Skills loaded from database per agent via `SkillRegistry`
- Added `include` directive in pyproject.toml for SQL migrations

---

## [0.4.0] - 2026-01-01

### Added

- **Real-time System Monitoring**: New `/health/system` endpoint providing real CPU, memory, disk, and load average metrics via psutil
- **Detailed Health Checks**: New `/health/checks` endpoint with service-by-service health status (API, Database, Memory, Disk, Agents, Circles)
- **Kubernetes Probes**: Added `/health/ready` and `/health/live` endpoints for container orchestration
- **Settings/Models Integration**: Settings page now displays available models per provider from the database
- **Provider Model Display**: Each LLM provider card shows registered models with vision and extended thinking indicators

### Changed

- **Monitoring Page**: Replaced demo/fake data with real system metrics from backend API
- **Settings API**: Enhanced `/settings` to include models from database grouped by provider
- **Health Response**: Updated to include uptime, agent count, circle count, and active tasks

### Fixed

- **Database Health Check**: Fixed `DatabaseService.fetch_one()` method usage in health checks

### Technical

- Added Pydantic schemas: `CpuMetrics`, `MemoryMetrics`, `DiskMetrics`, `LoadAverage`, `SystemMetricsResponse`, `ServiceHealth`, `HealthChecksResponse`
- Added TypeScript interfaces synced with backend schemas
- TanStack Query integration for real-time data fetching with auto-refresh (5s metrics, 10s health checks)

---

## [0.3.0] - 2025-12-20

### Security

- **WebSocket Authentication**: All WebSocket endpoints (`/ws`, `/ws/terminal/{project_id}`) now require JWT token
- **Timing Attack Protection**: Admin authentication uses `secrets.compare_digest()` for constant-time comparison
- **Token Revocation**: Implemented token blacklist with `POST /auth/logout` endpoint
- **Security Headers**: Added CSP, HSTS, Permissions-Policy, COOP, CORP headers
- **Shell Injection Protection**: Extended to 55+ blocked patterns (shells, credentials, env injection, exfiltration)
- **Path Traversal Protection**: All file operations validate paths with `relative_to()`
- **Production Validation**: `validate_for_production()` checks secret key, debug mode, auth configuration

### Added

- **Token Blacklist System**: In-memory blacklist with automatic cleanup for logout functionality
- **Blacklist Stats Endpoint**: `GET /auth/blacklist/stats` (admin only) for monitoring
- **Security Headers Middleware**: Configurable HSTS, comprehensive CSP policies

### Changed

- **Database Pool**: Increased from 15 to 40 connections (`pool_size=20, max_overflow=20`)
- **Event History**: Changed from `List` to `deque(maxlen=1000)` for O(1) append

### Fixed

- Memory leak in EventBus history storage
- Timing vulnerabilities in admin authentication

### Tests

- Added 122 new tests (LSP: 22, Background Tasks: 13, Shell Security: 61, Database: 26)
- Total test count: 1071 tests

---

## [0.2.0] - 2025-12-15

### Added

- **React Dashboard**: Complete Web3 dark theme UI with TypeScript and Tailwind CSS
- **WebSocket Support**: Real-time updates for agents, circles, tasks, conversations
- **Workspace Manager**: File browser, Git integration, terminal emulator
- **LSP Integration**: Language Server Protocol support with plugin system
- **Skills System**: Git, Test, Shell skills with security sandboxing
- **Plugin Architecture**: Extensible plugin system for custom functionality
- **Background Tasks**: Async task execution with progress tracking
- **Scheduled Actions**: Cron, interval, one-time, and event-triggered actions
- **Agent Goals**: Hierarchical goal decomposition and tracking
- **Settings UI**: Configure API keys and application parameters
- **RAG Services**: Embedding, VectorStore, Memory Manager, Knowledge Base
- **Media Viewers**: Image, audio, video, PDF, markdown preview
- **Monaco Editor**: Full code editor with syntax highlighting

### Database

- **Multi-Schema Architecture**: 7 schemas (agent, circle, communication, memory, rag, settings, workspace)
- **44 Tables**: Complete data model for agents, memories, conversations, tasks
- **Composite Indexes**: Optimized queries for common access patterns
- **pgvector Extension**: Vector similarity search for RAG

### API

- **~150 Endpoints**: Complete REST API for all features
- **Authentication**: JWT-based auth with admin from environment
- **Rate Limiting**: Per-IP rate limiting middleware
- **Request Logging**: Comprehensive request/response logging

### Architecture

- **Event Bus**: Pub/sub system for decoupled components
- **Orchestration**: Circle-based task routing with facilitator
- **DeepSeek Provider**: Added DeepSeek LLM support

---

## [0.1.0] - 2025-07-25

### Added

- Initial release of GatheRing framework
- Core agent system with customizable personalities
- Multi-LLM provider support (OpenAI, Anthropic, Ollama)
- Modular personality block system
- Tool system with Calculator and FileSystem tools
- Multi-agent conversation support
- Memory management system
- Comprehensive test suite with 61% coverage
- Complete API documentation
- User guide and developer documentation

### Architecture

- Interface-based design for extensibility
- Factory pattern for object creation
- Dependency injection for flexibility
- Plugin-ready architecture

### Testing

- TDD approach with pytest
- Unit, integration, and e2e test structure
- Fixtures and mocking support
- CI/CD ready configuration

### Known Limitations

- Mock LLM provider for testing only
- Basic tool implementations
- Memory is in-memory only (no persistence)
- Web interface not yet implemented
