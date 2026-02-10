# Codebase Structure

**Analysis Date:** 2026-02-10

## Directory Layout

```
gathering/                         # Main package
├── core/                          # Abstract interfaces & basic implementations
│   ├── interfaces.py              # IAgent, ILLMProvider, ITool, IPersonalityBlock, etc.
│   ├── implementations.py         # BasicAgent, BasicMemory, CalculatorTool (test helpers)
│   ├── exceptions.py              # GatheringError hierarchy (11 exception types)
│   ├── config.py                  # Settings via Pydantic, environment-based
│   ├── schemas.py                 # AgentConfig, Message, ToolResult, etc.
│   ├── competencies.py            # Competency definitions and validation
│   ├── competency_registry.py     # Registry for agent competencies
│   └── tool_registry.py           # Registry for tools across skills
│
├── agents/                        # Agent wrapper & identity system
│   ├── wrapper.py                 # AgentWrapper - main LLM abstraction with identity
│   ├── persona.py                 # AgentPersona - persistent agent identity
│   ├── project_context.py         # ProjectContext - codebase awareness
│   ├── session.py                 # AgentSession - session tracking for resume
│   ├── memory.py                  # MemoryService, MemoryStore, MemoryEntry
│   ├── resume.py                  # SessionResumeManager - resume interrupted work
│   ├── conversation.py            # AgentConversation - multi-agent conversations
│   ├── goals.py                   # Goal tracking & management
│   ├── postgres_store.py          # PostgreSQL persistence for agents
│   ├── personalities/             # Predefined persona configs
│   └── tools/                     # Agent-specific tools
│
├── orchestration/                 # Multi-agent coordination
│   ├── circle.py                  # GatheringCircle - main orchestrator
│   ├── circle_store.py            # CircleStore - PostgreSQL persistence
│   ├── facilitator.py             # Facilitator - task routing & conflict detection
│   ├── events.py                  # Orchestration-specific event types
│   ├── background.py              # BackgroundTaskExecutor - persistent async jobs
│   └── scheduler.py               # Scheduler - cron-like scheduled actions
│
├── api/                           # REST API & WebSocket
│   ├── main.py                    # FastAPI app, lifespan, middleware setup
│   ├── auth.py                    # JWT authentication
│   ├── middleware.py              # Auth, rate limit, logging, security headers
│   ├── schemas.py                 # Request/response Pydantic models
│   ├── dependencies.py            # FastAPI dependency injection
│   ├── websocket.py               # WebSocket manager
│   └── routers/                   # Endpoint modules (18 routers)
│       ├── agents.py              # /agents endpoints
│       ├── conversations.py       # /conversations endpoints
│       ├── circles.py             # /circles endpoints (Gathering Circle management)
│       ├── memories.py            # /memories endpoints
│       ├── background_tasks.py    # /background-tasks endpoints
│       ├── scheduled_actions.py   # /scheduled-actions endpoints
│       ├── tools.py               # /tools endpoints (list skills)
│       ├── models.py              # /models endpoints (LLM models)
│       ├── goals.py               # /goals endpoints
│       ├── health.py              # /health status
│       ├── websocket.py           # WebSocket handler
│       ├── auth.py                # /auth endpoints
│       ├── projects.py            # /projects endpoints
│       ├── workspace.py           # /workspace endpoints (files, terminal, git)
│       ├── lsp.py                 # /lsp endpoints (language server)
│       ├── plugins.py             # /plugins endpoints
│       ├── dashboard.py           # /dashboard endpoints
│       └── pipelines.py           # /pipelines endpoints
│
├── skills/                        # Modular action capabilities
│   ├── base.py                    # BaseSkill - abstract base class
│   ├── registry.py                # SkillRegistry - discovery and management
│   ├── code/                      # Code execution & analysis
│   ├── git/                       # Git operations
│   ├── database/                  # Database operations
│   ├── shell/                     # Shell command execution
│   ├── http/                      # HTTP requests
│   ├── filesystem/                # File operations
│   ├── deploy/                    # Deployment operations
│   ├── cloud/                     # Cloud provider operations
│   ├── ai/                        # AI/ML operations
│   ├── docs/                      # Documentation operations
│   ├── email/                     # Email operations
│   ├── notifications/             # Notification operations
│   ├── web/                       # Web scraping/automation
│   ├── image/                     # Image operations
│   ├── pdf/                       # PDF operations
│   ├── monitoring/                # System monitoring
│   ├── calendar/                  # Calendar operations
│   ├── analysis/                  # Data analysis
│   ├── social/                    # Social media operations
│   ├── test/                      # Testing operations
│   └── gathering/                 # GatheRing-specific operations
│
├── events/                        # Event bus & type definitions
│   └── event_bus.py               # EventBus pub/sub, EventType enum
│
├── db/                            # Database & persistence
│   ├── database.py                # Database connection manager
│   ├── models.py                  # SQLAlchemy ORM models (8 schemas)
│   ├── setup.py                   # Schema initialization
│   ├── __init__.py                # Public API
│   └── migrations/                # Alembic migrations (SQL)
│       └── archive/               # Old migrations
│
├── llm/                           # LLM provider abstraction
│   ├── providers.py               # AnthropicProvider, OpenAIProvider, DeepSeekProvider
│   └── __init__.py                # Public API
│
├── rag/                           # Retrieval Augmented Generation
│   └── (vector embedding, semantic search - optional)
│
├── lsp/                           # Language Server Protocol
│   ├── manager.py                 # LSP manager
│   ├── plugin_system.py           # Plugin interface for language servers
│   ├── python_server.py           # Python LSP implementation
│   ├── pylsp_client.py            # Python LSP client wrapper
│   ├── pylsp_wrapper.py           # Additional Python LSP wrapping
│   └── plugins/                   # Language-specific plugins
│       ├── python_pylsp.py        # Python implementation
│       ├── javascript_lsp.py      # JavaScript implementation
│       └── rust_lsp.py            # Rust implementation
│
├── workspace/                     # Workspace management
│   ├── manager.py                 # Workspace manager (files, git, terminal)
│   ├── file_manager.py            # File operations with safety
│   ├── git_manager.py             # Git operations
│   ├── terminal_manager.py        # Terminal session management
│   └── activity_tracker.py        # Track workspace changes
│
├── cache/                         # Caching layer
│   └── (in-memory cache, Redis support)
│
├── websocket/                     # WebSocket integration
│   └── integration.py             # EventBus to WebSocket bridging
│
├── plugins/                       # Extension system
│   ├── base.py                    # Plugin interface
│   └── examples/                  # Example plugins
│
├── telemetry/                     # Monitoring & metrics
│   ├── metrics.py                 # Metrics collection
│   ├── decorators.py              # @tracked_function for instrumentation
│   └── config.py                  # Telemetry configuration
│
├── utils/                         # Utility functions
│   └── (common helpers)
│
└── __init__.py                    # Package root
```

## Directory Purposes

**`gathering/core/`:**
- Purpose: Define protocols and provide test implementations
- Contains: Abstract interfaces (IAgent, ILLMProvider, ITool, etc.), basic implementations for testing, exception definitions
- Key files: `interfaces.py` (protocols), `exceptions.py` (error hierarchy), `config.py` (settings)

**`gathering/agents/`:**
- Purpose: Persistent agent identity and LLM wrapping
- Contains: AgentWrapper (main class), persona definitions, memory management, session tracking
- Key files: `wrapper.py` (main abstraction), `persona.py` (identity), `memory.py` (context injection)

**`gathering/orchestration/`:**
- Purpose: Multi-agent collaboration and task routing
- Contains: GatheringCircle (orchestrator), Facilitator (task routing), EventBus integration, background task execution
- Key files: `circle.py` (main orchestrator), `facilitator.py` (routing), `background.py` (async job persistence)

**`gathering/api/`:**
- Purpose: REST endpoints and WebSocket real-time updates
- Contains: FastAPI app, middleware, 18+ routers, WebSocket manager
- Key files: `main.py` (app setup), `routers/` (endpoint implementations)

**`gathering/skills/`:**
- Purpose: Modular capabilities organized by domain
- Contains: 19+ domain-specific skill modules, each with tool definitions and implementations
- Key files: `base.py` (skill interface), domain folders like `code/`, `git/`, `database/`

**`gathering/events/`:**
- Purpose: Decoupled inter-component communication
- Contains: EventBus pub/sub implementation, EventType enum for all event types
- Key files: `event_bus.py` (single file with complete implementation)

**`gathering/db/`:**
- Purpose: PostgreSQL persistence with multi-schema architecture
- Contains: SQLAlchemy models (8 schemas), database connection manager, migrations
- Key files: `models.py` (ORM definitions), `database.py` (connection management), `migrations/` (SQL)

**`gathering/llm/`:**
- Purpose: Abstract LLM provider interface
- Contains: Implementations for Anthropic, OpenAI, DeepSeek
- Key files: `providers.py` (all implementations)

**`gathering/workspace/`:**
- Purpose: Local file system, git, terminal, activity tracking
- Contains: File manager (with security), git operations, terminal sessions
- Key files: `manager.py` (coordinator), `file_manager.py`, `git_manager.py`, `terminal_manager.py`

## Key File Locations

**Entry Points:**
- `gathering/api/main.py`: FastAPI application initialization
- `gathering/quick_start.py`: Demo script showing framework usage

**Configuration:**
- `gathering/core/config.py`: Settings via Pydantic (from env vars)
- `pyproject.toml`: Project metadata, dependencies, tool config (black, mypy, ruff)

**Core Logic:**
- `gathering/agents/wrapper.py`: AgentWrapper - main agent abstraction
- `gathering/orchestration/circle.py`: GatheringCircle - multi-agent coordination
- `gathering/api/routers/agents.py`: Agent endpoints
- `gathering/api/routers/conversations.py`: Multi-agent conversation endpoints

**Testing:**
- `tests/`: Test files mirror source structure
- Key test patterns: `test_agents.py`, `test_orchestration_*.py`, `test_api_*.py`
- `pytest.ini`: Pytest configuration with markers (unit, integration, e2e)

## Naming Conventions

**Files:**
- `wrapper.py`: Wrapping pattern (AgentWrapper, LSPWrapper)
- `manager.py`: Management pattern (WorkspaceManager, TerminalManager)
- `providers.py`: Provider implementations (LLMProviders, CloudProviders)
- `models.py`: SQLAlchemy ORM definitions
- `schemas.py`: Pydantic request/response models
- `base.py`: Abstract base classes (BaseSkill, BasePlugin)
- `registry.py`: Registration/discovery pattern (SkillRegistry, CompetencyRegistry)

**Directories:**
- Domain-based: `skills/code/`, `skills/git/`, etc. (one per skill domain)
- Feature-based: `api/routers/` (one per feature area)
- Functionality-based: `workspace/`, `orchestration/`, `agents/` (grouped by purpose)

**Classes:**
- Agent-related: `Agent*` prefix (`AgentWrapper`, `AgentPersona`, `AgentSession`)
- Provider-related: `*Provider` suffix (`AnthropicProvider`, `PostgreSQLProvider`)
- Skill-related: `*Skill` suffix for implementations, `ISkill` for interfaces
- Store-related: `*Store` suffix (`MemoryStore`, `CircleStore`)

## Where to Add New Code

**New Feature (e.g., new chat endpoint):**
- Primary code: `gathering/api/routers/conversations.py` (add new route)
- Tests: `tests/test_api_conversations.py` (add test for new route)
- Database models: `gathering/db/models.py` (if new table needed)
- Schemas: `gathering/api/schemas.py` (if new request/response type)

**New Component/Module (e.g., new skill domain):**
- Implementation: `gathering/skills/{domain}/skill.py` (subclass BaseSkill)
- Tools definition: `gathering/skills/{domain}/tools/` (optional subdirectory)
- Tests: `tests/test_skills_{domain}.py`
- Registration: Auto-discovered via `SkillRegistry.discover()`

**New Skill/Tool:**
- Implement in: `gathering/skills/{domain}/skill.py`
- Add to tools definition: Return from `get_tools_definition()`
- Add implementation: `execute()` method in same class
- Test: `tests/test_skills_{domain}.py`

**New Agent Capability (persona, memory feature):**
- Persona: `gathering/agents/persona.py` (add to PERSONA_REGISTRY)
- Memory feature: `gathering/agents/memory.py` (extend MemoryService)
- Tests: `tests/test_agents.py` or new `tests/test_agents_{feature}.py`

**New Orchestration Feature (circle behavior, task routing):**
- Feature code: `gathering/orchestration/circle.py` or new `gathering/orchestration/{feature}.py`
- Event types: Add to `gathering/orchestration/events.py` EventType enum
- Tests: `tests/test_orchestration_{feature}.py`

**New Database Table/Schema:**
- Model definition: `gathering/db/models.py` (add SQLAlchemy class)
- Migration: `gathering/db/migrations/` (Alembic migration)
- API access: `gathering/api/routers/` (new endpoint if public)

**New LLM Provider:**
- Implementation: `gathering/llm/providers.py` (add class implementing ILLMProvider)
- Tests: `tests/test_llm_providers.py`
- Config: `gathering/core/config.py` (add provider name to Settings)

## Special Directories

**`gathering/db/migrations/`:**
- Purpose: Alembic SQL migrations for schema changes
- Generated: No (manually created)
- Committed: Yes (tracked in git)
- Usage: `alembic upgrade head` to apply, `alembic downgrade` to revert

**`gathering/agents/personalities/`:**
- Purpose: YAML/JSON persona configuration files
- Generated: No (curated)
- Committed: Yes
- Usage: Loaded by `AgentPersona.from_file()`

**`gathering/plugins/examples/`:**
- Purpose: Example plugins demonstrating the plugin system
- Generated: No (reference implementations)
- Committed: Yes
- Usage: Template for users creating custom plugins

**`gathering/rag/`:**
- Purpose: Retrieval Augmented Generation (vector embeddings)
- Generated: No (embeddings are generated, code is not)
- Committed: Yes (code only)
- Usage: Optional feature, requires pgvector and sentence-transformers

**`tests/`:**
- Purpose: Parallel test structure mirroring source
- Generated: No
- Committed: Yes
- Structure: `test_{module}.py`, `test_{module}_{feature}.py` patterns

**`.planning/`:**
- Purpose: GSD planning documents (created during analysis)
- Generated: Yes (by gsd commands)
- Committed: Typically yes (for team reference)
- Contains: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, STACK.md, INTEGRATIONS.md, CONCERNS.md

---

*Structure analysis: 2026-02-10*
