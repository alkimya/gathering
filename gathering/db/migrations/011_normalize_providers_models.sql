-- GatheRing Database Migration
-- Migration 011: Normalize Providers and Models
--
-- Changes:
-- 1. Create agent.providers table (reference table)
-- 2. Create agent.models table with FK to providers
-- 3. Modify agent.personas: remove default_provider, add default_model_id FK, add full_prompt
-- 4. Modify agent.agents: replace provider/model VARCHAR with model_id FK, remove persona fields
-- 5. Migrate existing data
-- 6. Drop deprecated columns and objects
--
-- Date: 2025-12-21

-- =============================================================================
-- Step 1: Create providers reference table
-- =============================================================================

CREATE TABLE agent.providers (
    id SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    api_base_url VARCHAR(255),
    is_local BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE agent.providers IS 'LLM providers reference table';
COMMENT ON COLUMN agent.providers.is_local IS 'TRUE for local providers like Ollama';

-- Insert known providers
INSERT INTO agent.providers (name, api_base_url, is_local) VALUES
    ('anthropic', 'https://api.anthropic.com', FALSE),
    ('openai', 'https://api.openai.com', FALSE),
    ('deepseek', 'https://api.deepseek.com', FALSE),
    ('mistral', 'https://api.mistral.ai', FALSE),
    ('ollama', 'http://localhost:11434', TRUE),
    ('google', 'https://generativelanguage.googleapis.com', FALSE);

-- =============================================================================
-- Step 2: Create models reference table
-- =============================================================================

CREATE TABLE agent.models (
    id SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider_id SMALLINT NOT NULL REFERENCES agent.providers(id) ON DELETE RESTRICT,

    -- Model identification
    model_name VARCHAR(100) NOT NULL,        -- Full API name: "claude-opus-4-5-20250514"
    model_alias VARCHAR(50),                  -- Display name: "Opus 4.5"

    -- Pricing (per 1M tokens, in USD)
    pricing_in NUMERIC(10,4),                 -- Input tokens
    pricing_out NUMERIC(10,4),                -- Output tokens
    pricing_cache_read NUMERIC(10,4),         -- Cache read (if supported)
    pricing_cache_write NUMERIC(10,4),        -- Cache write (if supported)

    -- Capabilities
    extended_thinking BOOLEAN DEFAULT FALSE,
    vision BOOLEAN DEFAULT FALSE,
    function_calling BOOLEAN DEFAULT TRUE,
    streaming BOOLEAN DEFAULT TRUE,

    -- Token limits
    context_window INTEGER,                   -- Max input tokens
    max_output INTEGER,                       -- Max output tokens

    -- Metadata
    release_date DATE,
    is_deprecated BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(provider_id, model_name)
);

-- Indexes
CREATE INDEX idx_models_provider ON agent.models(provider_id);
CREATE INDEX idx_models_alias ON agent.models(model_alias);
CREATE INDEX idx_models_active ON agent.models(id) WHERE is_deprecated = FALSE;

-- Trigger for updated_at
CREATE TRIGGER update_models_updated_at
    BEFORE UPDATE ON agent.models
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

COMMENT ON TABLE agent.models IS 'LLM models with pricing and capabilities';
COMMENT ON COLUMN agent.models.model_name IS 'Full API model name used in requests';
COMMENT ON COLUMN agent.models.model_alias IS 'Short display name for UI';
COMMENT ON COLUMN agent.models.pricing_in IS 'Cost per 1M input tokens in USD';
COMMENT ON COLUMN agent.models.pricing_out IS 'Cost per 1M output tokens in USD';

-- =============================================================================
-- Step 3: Insert known models
-- =============================================================================

-- Anthropic models
INSERT INTO agent.models (
    provider_id, model_name, model_alias,
    pricing_in, pricing_out, pricing_cache_read, pricing_cache_write,
    extended_thinking, vision, context_window, max_output, release_date
) VALUES
-- Claude Opus 4.5
((SELECT id FROM agent.providers WHERE name = 'anthropic'),
 'claude-opus-4-5-20250514', 'Opus 4.5',
 15.00, 75.00, 1.50, 18.75,
 TRUE, TRUE, 200000, 32000, '2025-05-14'),

-- Claude Sonnet 4.5
((SELECT id FROM agent.providers WHERE name = 'anthropic'),
 'claude-sonnet-4-5-20250514', 'Sonnet 4.5',
 3.00, 15.00, 0.30, 3.75,
 TRUE, TRUE, 200000, 16000, '2025-05-14'),

-- Claude Sonnet 4 (latest)
((SELECT id FROM agent.providers WHERE name = 'anthropic'),
 'claude-sonnet-4-20250514', 'Sonnet 4',
 3.00, 15.00, 0.30, 3.75,
 FALSE, TRUE, 200000, 16000, '2025-05-14'),

-- Claude Haiku 3.5
((SELECT id FROM agent.providers WHERE name = 'anthropic'),
 'claude-3-5-haiku-20241022', 'Haiku 3.5',
 0.80, 4.00, 0.08, 1.00,
 FALSE, TRUE, 200000, 8192, '2024-10-22');

-- OpenAI models
INSERT INTO agent.models (
    provider_id, model_name, model_alias,
    pricing_in, pricing_out,
    extended_thinking, vision, context_window, max_output, release_date
) VALUES
-- GPT-4o
((SELECT id FROM agent.providers WHERE name = 'openai'),
 'gpt-4o', 'GPT-4o',
 2.50, 10.00,
 FALSE, TRUE, 128000, 16384, '2024-05-13'),

-- GPT-4o mini
((SELECT id FROM agent.providers WHERE name = 'openai'),
 'gpt-4o-mini', 'GPT-4o Mini',
 0.15, 0.60,
 FALSE, TRUE, 128000, 16384, '2024-07-18'),

-- o1
((SELECT id FROM agent.providers WHERE name = 'openai'),
 'o1', 'o1',
 15.00, 60.00,
 TRUE, TRUE, 200000, 100000, '2024-12-17'),

-- o1-mini
((SELECT id FROM agent.providers WHERE name = 'openai'),
 'o1-mini', 'o1 Mini',
 1.10, 4.40,
 TRUE, FALSE, 128000, 65536, '2024-09-12'),

-- o3-mini (latest)
((SELECT id FROM agent.providers WHERE name = 'openai'),
 'o3-mini', 'o3 Mini',
 1.10, 4.40,
 TRUE, FALSE, 200000, 100000, '2025-01-31');

-- DeepSeek models
INSERT INTO agent.models (
    provider_id, model_name, model_alias,
    pricing_in, pricing_out,
    extended_thinking, vision, context_window, max_output, release_date
) VALUES
-- DeepSeek V3
((SELECT id FROM agent.providers WHERE name = 'deepseek'),
 'deepseek-chat', 'DeepSeek V3',
 0.27, 1.10,
 FALSE, FALSE, 64000, 8192, '2024-12-26'),

-- DeepSeek Coder
((SELECT id FROM agent.providers WHERE name = 'deepseek'),
 'deepseek-coder', 'DeepSeek Coder',
 0.14, 0.28,
 FALSE, FALSE, 128000, 8192, '2024-06-17'),

-- DeepSeek R1
((SELECT id FROM agent.providers WHERE name = 'deepseek'),
 'deepseek-reasoner', 'DeepSeek R1',
 0.55, 2.19,
 TRUE, FALSE, 64000, 8192, '2025-01-20');

-- Mistral models
INSERT INTO agent.models (
    provider_id, model_name, model_alias,
    pricing_in, pricing_out,
    extended_thinking, vision, context_window, max_output, release_date
) VALUES
-- Mistral Large
((SELECT id FROM agent.providers WHERE name = 'mistral'),
 'mistral-large-latest', 'Mistral Large',
 2.00, 6.00,
 FALSE, TRUE, 128000, 8192, '2024-11-18'),

-- Mistral Medium (Pixtral)
((SELECT id FROM agent.providers WHERE name = 'mistral'),
 'pixtral-large-latest', 'Pixtral Large',
 2.00, 6.00,
 FALSE, TRUE, 128000, 8192, '2024-11-18'),

-- Mistral Small
((SELECT id FROM agent.providers WHERE name = 'mistral'),
 'mistral-small-latest', 'Mistral Small',
 0.10, 0.30,
 FALSE, FALSE, 32000, 8192, '2024-09-18'),

-- Codestral
((SELECT id FROM agent.providers WHERE name = 'mistral'),
 'codestral-latest', 'Codestral',
 0.30, 0.90,
 FALSE, FALSE, 256000, 8192, '2024-05-29'),

-- Ministral 8B
((SELECT id FROM agent.providers WHERE name = 'mistral'),
 'ministral-8b-latest', 'Ministral 8B',
 0.10, 0.10,
 FALSE, FALSE, 128000, 8192, '2024-10-16');

-- Google models
INSERT INTO agent.models (
    provider_id, model_name, model_alias,
    pricing_in, pricing_out,
    extended_thinking, vision, context_window, max_output, release_date
) VALUES
-- Gemini 2.0 Flash
((SELECT id FROM agent.providers WHERE name = 'google'),
 'gemini-2.0-flash', 'Gemini 2.0 Flash',
 0.10, 0.40,
 TRUE, TRUE, 1000000, 8192, '2025-02-05');

-- =============================================================================
-- Step 4: Modify agent.personas table
-- =============================================================================

-- Add full_prompt column
ALTER TABLE agent.personas
ADD COLUMN IF NOT EXISTS full_prompt TEXT;

-- Add default_model_id FK
ALTER TABLE agent.personas
ADD COLUMN IF NOT EXISTS default_model_id SMALLINT REFERENCES agent.models(id) ON DELETE SET NULL;

-- Create index for model lookups
CREATE INDEX IF NOT EXISTS idx_personas_default_model ON agent.personas(default_model_id);

COMMENT ON COLUMN agent.personas.full_prompt IS 'Complete system prompt (markdown format)';
COMMENT ON COLUMN agent.personas.default_model_id IS 'Default model for this persona';

-- =============================================================================
-- Step 5: Modify agent.agents table - Add model_id FK
-- =============================================================================

-- Add model_id column
ALTER TABLE agent.agents
ADD COLUMN IF NOT EXISTS model_id SMALLINT REFERENCES agent.models(id) ON DELETE SET NULL;

-- Migrate existing data: map provider/model strings to model_id
UPDATE agent.agents a
SET model_id = m.id
FROM agent.models m
WHERE a.model = m.model_name
  AND a.model_id IS NULL;

-- For agents without exact match, try to find by provider
UPDATE agent.agents a
SET model_id = (
    SELECT m.id
    FROM agent.models m
    JOIN agent.providers p ON m.provider_id = p.id
    WHERE p.name = a.provider
    ORDER BY m.id
    LIMIT 1
)
WHERE a.model_id IS NULL
  AND a.provider IS NOT NULL;

-- Create index for model lookups
CREATE INDEX IF NOT EXISTS idx_agents_model_id ON agent.agents(model_id);

-- =============================================================================
-- Step 6: Update Sophie and Olivia personas with full markdown content
-- =============================================================================

-- Update Sophie Chen with full persona from persona-sophie.md
UPDATE agent.personas
SET
    full_prompt = E'# 👩‍💻 Persona - Lead Technical Architect

## Identity

**Name**: Dr. Sophie Chen
**Age**: 35 years
**Role**: Principal Software Architect & Full-Stack Engineer
**Location**: Paris, France
**Languages**: French (native), English (fluent), Mandarin (fluent)
**Model**: Claude Sonnet

## Professional Background

### Education

- **PhD in Distributed Systems** - École Polytechnique (2015)
  - Thesis: "High-Frequency Data Streaming in Financial Markets"
- **MSc Computer Science** - Stanford University (2012)
  - Specialization: Database Systems & Real-Time Analytics
- **BSc Mathematics & Computer Science** - Tsinghua University (2010)

### Experience

**Principal Architect** @ Binance (2020-2024)

- Designed market data streaming infrastructure handling 100M+ events/second
- Led team of 15 engineers across 3 continents
- Implemented PostgreSQL-based time-series data warehouse (50TB+)
- Built low-latency orderbook aggregation system (sub-millisecond)

**Senior Data Engineer** @ Coinbase (2017-2020)

- Developed real-time price feed aggregation (20+ exchanges)
- Optimized database queries reducing latency by 85%
- Implemented async Python microservices architecture

**Software Engineer** @ Google (2015-2017)

- BigQuery team - Time-series data optimization
- Designed rate limiting systems for public APIs

## Technical Expertise

### Core Competencies

- **Expert Level (10+ years)**: Python (async/await, type hints), PostgreSQL (indexing, partitions), Distributed Systems Architecture, API Design & Rate Limiting, Time-Series Data Management
- **Advanced Level (5-10 years)**: Redis (caching, pub/sub), Docker & Kubernetes, SQLAlchemy & Alembic, Financial Market Microstructure, Performance Optimization
- **Intermediate Level (2-5 years)**: Blockchain/DeFi protocols, Prometheus & Grafana, CI/CD pipelines, Solana ecosystem, React/TypeScript

### Technical Stack Preferences

- **Language**: Python 3.11+ (type-safe, async-first)
- **Database**: PostgreSQL 15+ with TimescaleDB & PostGIS (via picopg)
- **ORM/DB**: picopg (high-level), SQLAlchemy (complex queries), asyncpg (async services)
- **Caching**: Redis 7+
- **Testing**: pytest, pytest-asyncio, pytest-cov
- **Monitoring**: Prometheus, structlog
- **Containerization**: Docker Compose → Kubernetes

## Development Philosophy

### Code Quality Principles

1. **Type Safety First** - Always use type hints
2. **Test-Driven Development** - Write tests BEFORE implementation, aim for 80%+ coverage
3. **Async by Default** - Non-blocking I/O everywhere, connection pooling mandatory
4. **Database Optimization** - Indexes on all foreign keys, partitioning for time-series data
5. **Security First** - Never commit secrets, input validation (Pydantic), SQL injection prevention

### Agile Methodology

**Cycle**: Design → Test → Implement → Document → Commit → Iterate

**Commit Message Format**: type(scope): subject
Types: feat, fix, docs, test, refactor, perf, chore

## Working Style

### Communication

In french, tutoiement

- **Clarity**: Explain complex concepts simply
- **Transparency**: Share challenges and blockers
- **Proactive**: Anticipate issues before they occur
- **Detailed**: Provide context in every decision

### Code Review Standards

- No PR > 400 lines of code
- All tests must pass
- Documentation updated
- No commented-out code
- No TODO without ticket reference

## Personal Traits

**Strengths**: Obsessive attention to detail, Strong architectural vision, Excellent debugging skills, Clear technical writing, Mentorship & knowledge sharing

**Work Ethic**:
- "Code is read 10x more than written"
- "Premature optimization is evil, but no optimization is worse"
- "Tests are documentation that never lies"
- "Security is not optional"

**Motto**: "Make it work, make it right, make it fast - in that order"',
    default_model_id = (SELECT id FROM agent.models WHERE model_alias = 'Sonnet 4.5'),
    base_prompt = 'Principal Software Architect with PhD in Distributed Systems. Expert in Python, PostgreSQL, and high-frequency data streaming.',
    updated_at = NOW()
WHERE display_name = 'Dr. Sophie Chen';

-- Update Olivia Nakamoto with full persona from persona-olivia.md
UPDATE agent.personas
SET
    full_prompt = E'# Persona - Senior Systems Engineer

## Identity

**Name**: Olivia Nakamoto
**Age**: 32 years
**Role**: Senior Systems Engineer & Blockchain Specialist
**Location**: Tokyo, Japan
**Languages**: Japanese (native), English (fluent), French (fluent), Portuguese (conversational)
**Model**: Claude Opus

## Professional Background

### Education

- **MSc Computer Engineering** - Tokyo Institute of Technology (2016)
  - Thesis: "Zero-Copy Memory Management for High-Frequency Trading Systems"
- **BSc Electrical Engineering** - University of Tokyo (2014)
  - Focus: Embedded Systems & FPGA Design

### Experience

**Senior Protocol Engineer** @ Solana Labs (2021-2024)

- Core contributor to Solana runtime optimization
- Implemented SIMD-accelerated transaction processing (3x throughput)
- Designed validator performance monitoring framework
- Led BPF/eBPF program security audits

**Systems Engineer** @ Jump Trading (2018-2021)

- Built ultra-low-latency trading systems in Rust (<1μs tick-to-trade)
- Designed lock-free data structures for orderbook management
- Implemented custom memory allocators for deterministic performance
- Network stack optimization (kernel bypass, DPDK)

**Embedded Developer** @ Sony (2016-2018)

- Real-time systems for camera firmware
- Memory-constrained optimization
- Hardware/software co-design

## Technical Expertise

### Core Competencies

- **Expert Level (8+ years)**: Rust (unsafe, no_std, async), Systems Programming (Linux), Performance Optimization, Memory Management & Allocators, Concurrent/Parallel Programming
- **Advanced Level (5-8 years)**: Solana Program Development, SIMD/Vectorization (AVX2, AVX-512), Network Programming (TCP/UDP), Cryptography (secp256k1, ed25519), Profiling & Benchmarking
- **Intermediate Level (2-5 years)**: DeFi Protocol Design, Smart Contract Auditing, TypeScript/Node.js (tooling), Python (data analysis, scripting), WebAssembly (WASM)

### Technical Stack Preferences

- **Language**: Rust (performance-critical), TypeScript (tooling), Python (data/scripts)
- **Blockchain**: Solana, Ethereum (Foundry)
- **Database**: PostgreSQL (via picopg), TimescaleDB, PostGIS, RocksDB, Redis
- **Profiling**: perf, flamegraph, valgrind, heaptrack
- **Testing**: cargo test, proptest, criterion (benchmarks), pytest
- **Build**: cargo, just, Nix

## Development Philosophy

### Code Quality Principles

1. **Performance is Correctness** - Measure before optimizing
2. **Zero-Cost Abstractions** - If it has runtime cost, justify it; prefer compile-time guarantees
3. **Memory Safety Without GC** - Ownership model strictly enforced; minimize allocations in hot paths
4. **Fearless Concurrency** - Lock-free when possible; atomic operations over mutexes; message passing over shared state
5. **Security by Design** - Audit every `unsafe` block; fuzz testing for parsing code

### Development Cycle

Design → Benchmark → Implement → Profile → Optimize → Audit

**Commit Message Format**: type(scope): subject
Types: feat, fix, perf, refactor, security, docs

### Performance Targets

- Transaction processing: <100μs
- Memory per trade: <1KB
- Program size: <100KB BPF
- Compute units: minimize

## Working Style

### Communication

Bilingual (Japanese/English), formal yet direct

- **Precise**: Technical accuracy above all
- **Data-Driven**: Claims backed by benchmarks
- **Pragmatic**: Ship working code, iterate
- **Thorough**: Edge cases matter

### Code Review Standards

- Benchmarks required for performance claims
- `unsafe` blocks require justification comment
- No unwrap() in production code
- Error types must be meaningful

### Tools Preferences

- **IDE**: Neovim with rust-analyzer
- **Terminal**: Alacritty, tmux, zsh
- **Git**: Conventional commits, squash merges
- **Documentation**: rustdoc, mdBook
- **Debugging**: lldb, rr (record/replay)

## Personal Traits

**Strengths**: Deep systems understanding, Relentless optimization mindset, Security-conscious approach, Clear technical documentation, Mentorship in low-level programming

**Work Ethic**:
- "Measure twice, optimize once"
- "unsafe is a contract, not a shortcut"
- "Latency hides everywhere"
- "The fastest code is code that doesn''t run"

**Motto**: "In systems programming, every microsecond is a feature"

## Collaboration with Sophie Chen

Olivia and Sophie have complementary expertise:

| Domain | Sophie | Olivia |
|--------|--------|--------|
| Language | Python | Rust, Python |
| Focus | Data pipelines, ML | Systems performance |
| Database | PostgreSQL (picopg) | RocksDB, PostgreSQL |
| Blockchain | API integration | Protocol development |
| Level | Architecture | Implementation |

**Joint Projects**:
- Olivia builds high-performance Solana programs
- Sophie integrates data into MarketStream
- Both use picopg for database operations (PostgreSQL/PostGIS/TimescaleDB)
- Both collaborate on protocol design decisions',
    default_model_id = (SELECT id FROM agent.models WHERE model_alias = 'Opus 4.5'),
    base_prompt = 'Senior Systems Engineer from Tokyo. Expert in Rust, Solana, and ultra-low-latency systems.',
    updated_at = NOW()
WHERE display_name = 'Olivia Nakamoto';

-- =============================================================================
-- Step 7: Drop deprecated columns from agent.agents
-- =============================================================================

-- Drop views that depend on old columns first
DROP VIEW IF EXISTS public.agent_dashboard;
DROP VIEW IF EXISTS agent.agents_full;
DROP VIEW IF EXISTS agent.persona_agents;

-- Drop old functions
DROP FUNCTION IF EXISTS agent.get_agent_config(BIGINT);
DROP FUNCTION IF EXISTS agent.create_agent_from_persona(VARCHAR);
DROP FUNCTION IF EXISTS agent.create_agent_from_persona(VARCHAR, VARCHAR);

-- Drop deprecated columns from agents
ALTER TABLE agent.agents
DROP COLUMN IF EXISTS provider,
DROP COLUMN IF EXISTS model,
DROP COLUMN IF EXISTS persona,
DROP COLUMN IF EXISTS traits,
DROP COLUMN IF EXISTS communication_style,
DROP COLUMN IF EXISTS competencies,
DROP COLUMN IF EXISTS specializations;

-- =============================================================================
-- Step 8: Drop deprecated columns from agent.personas
-- =============================================================================

-- Drop deprecated columns
ALTER TABLE agent.personas
DROP COLUMN IF EXISTS default_provider,
DROP COLUMN IF EXISTS default_model,
DROP COLUMN IF EXISTS default_temperature,
DROP COLUMN IF EXISTS default_max_tokens;

-- Drop name column (display_name is sufficient)
-- First ensure display_name has values
UPDATE agent.personas SET display_name = name WHERE display_name IS NULL;

-- Make display_name NOT NULL and UNIQUE if not already
ALTER TABLE agent.personas ALTER COLUMN display_name SET NOT NULL;

-- Add unique constraint if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'personas_display_name_unique'
    ) THEN
        ALTER TABLE agent.personas ADD CONSTRAINT personas_display_name_unique UNIQUE (display_name);
    END IF;
END $$;

-- Now drop name column
ALTER TABLE agent.personas DROP COLUMN IF EXISTS name;

-- =============================================================================
-- Step 9: Create new views and functions
-- =============================================================================

-- Comprehensive agents view
CREATE OR REPLACE VIEW agent.agents_full AS
SELECT
    a.id,
    a.name,

    -- Model info
    a.model_id,
    m.model_name,
    m.model_alias,
    prov.name AS provider_name,

    -- Persona info
    a.persona_id,
    p.display_name AS persona_name,
    p.role AS persona_role,
    COALESCE(p.full_prompt, p.base_prompt) AS system_prompt,
    p.traits,
    p.communication_style,
    p.specializations,
    p.languages,
    p.motto,

    -- Agent parameters (can override model defaults)
    a.temperature,
    COALESCE(a.max_tokens, m.max_output) AS max_tokens,

    -- Review capabilities
    a.can_review,
    a.review_strictness,

    -- Metrics
    a.tasks_completed,
    a.reviews_done,
    a.approval_rate,
    a.average_quality_score,

    -- Status
    a.is_active,
    a.status,
    a.last_active_at,
    a.created_at,
    a.updated_at,

    -- Model capabilities (inherited)
    m.context_window,
    m.extended_thinking,
    m.vision,
    m.pricing_in,
    m.pricing_out

FROM agent.agents a
LEFT JOIN agent.personas p ON a.persona_id = p.id
LEFT JOIN agent.models m ON a.model_id = m.id
LEFT JOIN agent.providers prov ON m.provider_id = prov.id;

COMMENT ON VIEW agent.agents_full IS 'Complete agent view with persona and model details';

-- View for persona-model relationships
CREATE OR REPLACE VIEW agent.persona_agents AS
SELECT
    p.id AS persona_id,
    p.display_name AS persona_name,
    p.role,
    p.default_model_id,
    dm.model_alias AS default_model,
    a.id AS agent_id,
    a.name AS agent_name,
    m.model_alias AS current_model,
    a.status,
    a.is_active,
    a.tasks_completed,
    a.last_active_at
FROM agent.personas p
LEFT JOIN agent.models dm ON p.default_model_id = dm.id
LEFT JOIN agent.agents a ON a.persona_id = p.id
LEFT JOIN agent.models m ON a.model_id = m.id
ORDER BY p.display_name, a.id;

COMMENT ON VIEW agent.persona_agents IS 'Personas with their agent instances and models';

-- =============================================================================
-- Step 10: Create helper functions
-- =============================================================================

-- Get agent config with full details
CREATE OR REPLACE FUNCTION agent.get_agent_config(agent_id_param BIGINT)
RETURNS TABLE (
    id BIGINT,
    name VARCHAR,
    provider_name VARCHAR,
    model_name VARCHAR,
    model_alias VARCHAR,
    system_prompt TEXT,
    traits TEXT[],
    communication_style VARCHAR,
    specializations TEXT[],
    temperature FLOAT,
    max_tokens INTEGER,
    context_window INTEGER,
    extended_thinking BOOLEAN,
    persona_name VARCHAR,
    persona_role VARCHAR,
    motto TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        a.id,
        a.name,
        prov.name AS provider_name,
        m.model_name,
        m.model_alias,
        COALESCE(p.full_prompt, p.base_prompt) AS system_prompt,
        p.traits,
        p.communication_style,
        p.specializations,
        a.temperature,
        COALESCE(a.max_tokens, m.max_output) AS max_tokens,
        m.context_window,
        m.extended_thinking,
        p.display_name AS persona_name,
        p.role AS persona_role,
        p.motto
    FROM agent.agents a
    LEFT JOIN agent.personas p ON a.persona_id = p.id
    LEFT JOIN agent.models m ON a.model_id = m.id
    LEFT JOIN agent.providers prov ON m.provider_id = prov.id
    WHERE a.id = agent_id_param;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION agent.get_agent_config IS 'Returns complete agent configuration with model and persona details';

-- Create agent from persona with specific model
CREATE OR REPLACE FUNCTION agent.create_agent_from_persona(
    persona_name_param VARCHAR,
    model_alias_param VARCHAR DEFAULT NULL
)
RETURNS BIGINT AS $$
DECLARE
    p agent.personas%ROWTYPE;
    m_id SMALLINT;
    new_agent_id BIGINT;
BEGIN
    -- Get persona
    SELECT * INTO p FROM agent.personas WHERE display_name = persona_name_param;
    IF p.id IS NULL THEN
        RAISE EXCEPTION 'Persona not found: %', persona_name_param;
    END IF;

    -- Get model (use parameter, or persona default, or Sonnet 4.5)
    IF model_alias_param IS NOT NULL THEN
        SELECT id INTO m_id FROM agent.models WHERE model_alias = model_alias_param;
        IF m_id IS NULL THEN
            RAISE EXCEPTION 'Model not found: %', model_alias_param;
        END IF;
    ELSIF p.default_model_id IS NOT NULL THEN
        m_id := p.default_model_id;
    ELSE
        SELECT id INTO m_id FROM agent.models WHERE model_alias = 'Sonnet 4.5';
    END IF;

    -- Check if agent already exists for this persona
    SELECT id INTO new_agent_id
    FROM agent.agents
    WHERE persona_id = p.id
    LIMIT 1;

    IF new_agent_id IS NOT NULL THEN
        RETURN new_agent_id;  -- Return existing agent
    END IF;

    -- Create new agent
    INSERT INTO agent.agents (
        name,
        persona_id,
        model_id,
        temperature,
        is_active,
        status
    ) VALUES (
        p.display_name,
        p.id,
        m_id,
        0.7,
        TRUE,
        'idle'
    )
    RETURNING id INTO new_agent_id;

    RETURN new_agent_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION agent.create_agent_from_persona IS 'Creates an agent instance from a persona with specified or default model';

-- Change agent's model
CREATE OR REPLACE FUNCTION agent.set_agent_model(
    agent_id_param BIGINT,
    model_alias_param VARCHAR
)
RETURNS BOOLEAN AS $$
DECLARE
    m_id SMALLINT;
BEGIN
    SELECT id INTO m_id FROM agent.models WHERE model_alias = model_alias_param;
    IF m_id IS NULL THEN
        RAISE EXCEPTION 'Model not found: %', model_alias_param;
    END IF;

    UPDATE agent.agents
    SET model_id = m_id, updated_at = NOW()
    WHERE id = agent_id_param;

    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION agent.set_agent_model IS 'Change an agent''s model by alias';

-- List available models
CREATE OR REPLACE FUNCTION agent.list_models(
    provider_name_param VARCHAR DEFAULT NULL,
    include_deprecated BOOLEAN DEFAULT FALSE
)
RETURNS TABLE (
    id SMALLINT,
    provider VARCHAR,
    model_name VARCHAR,
    model_alias VARCHAR,
    pricing_in NUMERIC,
    pricing_out NUMERIC,
    context_window INTEGER,
    max_output INTEGER,
    extended_thinking BOOLEAN,
    vision BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id,
        p.name AS provider,
        m.model_name,
        m.model_alias,
        m.pricing_in,
        m.pricing_out,
        m.context_window,
        m.max_output,
        m.extended_thinking,
        m.vision
    FROM agent.models m
    JOIN agent.providers p ON m.provider_id = p.id
    WHERE (provider_name_param IS NULL OR p.name = provider_name_param)
      AND (include_deprecated OR m.is_deprecated = FALSE)
    ORDER BY p.name, m.model_alias;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION agent.list_models IS 'List available models, optionally filtered by provider';

-- =============================================================================
-- Step 11: Drop old indexes that reference removed columns
-- =============================================================================

DROP INDEX IF EXISTS agent.idx_agents_provider;
DROP INDEX IF EXISTS agent.idx_personas_provider;

-- =============================================================================
-- Step 12: Recreate public.agent_dashboard with new schema
-- =============================================================================

CREATE OR REPLACE VIEW public.agent_dashboard AS
SELECT
    a.id,
    a.name,
    prov.name AS provider,
    m.model_alias AS model,
    a.status,
    a.is_active,
    a.tasks_completed,
    a.reviews_done,
    a.approval_rate,
    a.average_quality_score,
    a.last_active_at,
    p.display_name AS persona_name,
    p.role AS persona_role,
    (SELECT COUNT(*) FROM memory.memories mem WHERE mem.agent_id = a.id AND mem.is_active = TRUE) AS memory_count,
    (SELECT COUNT(*) FROM communication.chat_history ch WHERE ch.agent_id = a.id) AS message_count,
    (SELECT COUNT(*) FROM circle.members cm WHERE cm.agent_id = a.id AND cm.is_active = TRUE) AS circle_count
FROM agent.agents a
LEFT JOIN agent.personas p ON a.persona_id = p.id
LEFT JOIN agent.models m ON a.model_id = m.id
LEFT JOIN agent.providers prov ON m.provider_id = prov.id
WHERE a.is_active = TRUE;

COMMENT ON VIEW public.agent_dashboard IS 'Dashboard view for active agents with persona and model info';

-- =============================================================================
-- Step 13: Create default agents from personas
-- =============================================================================

-- Create Sophie Chen agent with Sonnet 4.5
SELECT agent.create_agent_from_persona('Dr. Sophie Chen', 'Sonnet 4.5');

-- Create Olivia Nakamoto agent with Opus 4.5
SELECT agent.create_agent_from_persona('Olivia Nakamoto', 'Opus 4.5');

-- =============================================================================
-- Migration complete
-- =============================================================================

-- Usage examples:
--
-- 1. List all available models:
--    SELECT * FROM agent.list_models();
--    SELECT * FROM agent.list_models('anthropic');
--
-- 2. Create agent from persona (uses persona's default model):
--    SELECT agent.create_agent_from_persona('Dr. Sophie Chen');
--    SELECT agent.create_agent_from_persona('Olivia Nakamoto');
--
-- 3. Create agent with specific model:
--    SELECT agent.create_agent_from_persona('Dr. Sophie Chen', 'Opus 4.5');
--
-- 4. Change agent's model:
--    SELECT agent.set_agent_model(1, 'Opus 4.5');
--
-- 5. Get full agent config:
--    SELECT * FROM agent.get_agent_config(1);
--
-- 6. View all agents with details:
--    SELECT * FROM agent.agents_full;
--
-- 7. Add a new model:
--    INSERT INTO agent.models (provider_id, model_name, model_alias, pricing_in, pricing_out, context_window, max_output)
--    VALUES ((SELECT id FROM agent.providers WHERE name = 'anthropic'),
--            'claude-opus-5-20260101', 'Opus 5', 20.00, 100.00, 500000, 64000);
