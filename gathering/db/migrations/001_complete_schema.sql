-- GatheRing Database Schema
-- Version: 1.0.0
-- Description: Complete database schema for GatheRing multi-agent AI framework
--
-- This migration creates the full database structure from scratch.
-- Schemas: agent, circle, project, communication, memory, review, audit

-- =============================================================================
-- EXTENSIONS
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";  -- pgvector for RAG
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- Trigram similarity

-- =============================================================================
-- SCHEMAS
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS agent;
CREATE SCHEMA IF NOT EXISTS circle;
CREATE SCHEMA IF NOT EXISTS project;
CREATE SCHEMA IF NOT EXISTS communication;
CREATE SCHEMA IF NOT EXISTS memory;
CREATE SCHEMA IF NOT EXISTS review;
CREATE SCHEMA IF NOT EXISTS audit;

-- =============================================================================
-- ENUM TYPES
-- =============================================================================

-- Agent types
CREATE TYPE public.agent_status AS ENUM ('idle', 'active', 'busy', 'offline');
CREATE TYPE public.agent_role AS ENUM ('lead', 'member', 'specialist', 'reviewer', 'observer');

-- Circle types
CREATE TYPE public.circle_status AS ENUM ('created', 'stopped', 'running', 'active', 'paused', 'archived');

-- Task types
CREATE TYPE public.task_status AS ENUM ('pending', 'in_progress', 'in_review', 'blocked', 'completed', 'cancelled');
CREATE TYPE public.task_priority AS ENUM ('low', 'medium', 'high', 'critical');

-- Communication types
CREATE TYPE public.conversation_status AS ENUM ('pending', 'active', 'completed', 'cancelled');
CREATE TYPE public.message_role AS ENUM ('user', 'assistant', 'system', 'tool');

-- Memory types
CREATE TYPE public.memory_scope AS ENUM ('global', 'circle', 'agent', 'conversation', 'project');
CREATE TYPE public.memory_type AS ENUM ('fact', 'preference', 'experience', 'skill', 'relationship', 'context', 'decision');

-- Review types
CREATE TYPE public.review_status AS ENUM ('pending', 'in_progress', 'approved', 'changes_requested', 'rejected');
CREATE TYPE public.review_type AS ENUM ('code', 'architecture', 'security', 'documentation', 'quality', 'final');

-- Background task types
CREATE TYPE public.background_task_status AS ENUM ('pending', 'running', 'paused', 'completed', 'failed', 'cancelled', 'timeout');

-- Goal types
CREATE TYPE public.goal_status AS ENUM ('pending', 'active', 'blocked', 'paused', 'completed', 'failed', 'cancelled');
CREATE TYPE public.goal_priority AS ENUM ('low', 'medium', 'high', 'critical');

-- Scheduled action types
CREATE TYPE public.scheduled_action_status AS ENUM ('active', 'paused', 'disabled', 'expired');
CREATE TYPE public.schedule_type AS ENUM ('cron', 'interval', 'once', 'event');

-- Log types
CREATE TYPE public.log_level AS ENUM ('debug', 'info', 'warning', 'error', 'critical');

-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

CREATE OR REPLACE FUNCTION public.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- AGENT SCHEMA
-- =============================================================================

-- LLM Providers (anthropic, openai, ollama, etc.)
CREATE TABLE agent.providers (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100),
    api_base_url TEXT,
    is_local BOOLEAN DEFAULT FALSE,
    config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE agent.providers IS 'LLM providers (OpenAI, Anthropic, Ollama, etc.)';

-- LLM Models
CREATE TABLE agent.models (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider_id BIGINT NOT NULL REFERENCES agent.providers(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    display_name VARCHAR(200),
    model_id VARCHAR(100) NOT NULL,  -- API model identifier

    -- Pricing (per 1M tokens, USD)
    pricing_input DECIMAL(10, 4) DEFAULT 0,
    pricing_output DECIMAL(10, 4) DEFAULT 0,
    pricing_cache_read DECIMAL(10, 4) DEFAULT 0,
    pricing_cache_write DECIMAL(10, 4) DEFAULT 0,

    -- Capabilities
    context_window INTEGER DEFAULT 128000,
    max_output INTEGER DEFAULT 4096,
    supports_vision BOOLEAN DEFAULT FALSE,
    supports_tools BOOLEAN DEFAULT TRUE,
    supports_streaming BOOLEAN DEFAULT TRUE,
    supports_extended_thinking BOOLEAN DEFAULT FALSE,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(provider_id, model_id)
);

CREATE INDEX idx_models_provider ON agent.models(provider_id);
CREATE INDEX idx_models_active ON agent.models(is_active) WHERE is_active = TRUE;

COMMENT ON TABLE agent.models IS 'Available LLM models with pricing and capabilities';

-- Personas (templates for agents)
CREATE TABLE agent.personas (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,  -- slug: sophie_chen
    display_name VARCHAR(200),           -- Dr. Sophie Chen

    -- Identity
    role VARCHAR(200) NOT NULL,
    location VARCHAR(100),
    languages TEXT[] DEFAULT '{}',

    -- Prompt content
    base_prompt TEXT,                    -- Short system prompt
    full_prompt TEXT,                    -- Full persona markdown

    -- Personality
    traits TEXT[] DEFAULT '{}',
    communication_style VARCHAR(50) DEFAULT 'professional',
    work_ethic TEXT[] DEFAULT '{}',
    motto TEXT,
    collaboration_notes TEXT,

    -- Skills
    competencies TEXT[] DEFAULT '{}',
    specializations TEXT[] DEFAULT '{}',

    -- Defaults
    default_model_id BIGINT REFERENCES agent.models(id),
    default_temperature FLOAT DEFAULT 0.7,

    -- Metadata
    description TEXT,
    icon VARCHAR(50),
    is_builtin BOOLEAN DEFAULT FALSE,
    category VARCHAR(50),  -- tech, business, creative, coaching, legal

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_personas_category ON agent.personas(category);
CREATE INDEX idx_personas_competencies ON agent.personas USING GIN(competencies);

CREATE TRIGGER update_personas_updated_at
    BEFORE UPDATE ON agent.personas
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

COMMENT ON TABLE agent.personas IS 'Reusable persona templates for agents';

-- Agents
CREATE TABLE agent.agents (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL,

    -- Model & Persona
    model_id BIGINT REFERENCES agent.models(id),
    persona_id BIGINT REFERENCES agent.personas(id),

    -- Custom personality (overrides persona if set)
    custom_prompt TEXT,
    traits TEXT[] DEFAULT '{}',
    communication_style VARCHAR(50),

    -- Competencies
    competencies TEXT[] DEFAULT '{}',
    specializations TEXT[] DEFAULT '{}',

    -- Review capabilities
    can_review TEXT[] DEFAULT '{}',
    review_strictness FLOAT DEFAULT 0.7 CHECK (review_strictness >= 0 AND review_strictness <= 1),

    -- LLM Configuration
    temperature FLOAT DEFAULT 0.7 CHECK (temperature >= 0 AND temperature <= 2),
    max_tokens INTEGER,

    -- Performance metrics
    tasks_completed INTEGER DEFAULT 0,
    reviews_done INTEGER DEFAULT 0,
    approval_rate FLOAT DEFAULT 0.0 CHECK (approval_rate >= 0 AND approval_rate <= 1),
    average_quality_score FLOAT DEFAULT 0.0 CHECK (average_quality_score >= 0 AND average_quality_score <= 100),

    -- Status
    status public.agent_status DEFAULT 'idle',
    is_active BOOLEAN DEFAULT TRUE,
    last_active_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_agents_model ON agent.agents(model_id);
CREATE INDEX idx_agents_persona ON agent.agents(persona_id);
CREATE INDEX idx_agents_status ON agent.agents(status) WHERE is_active = TRUE;
CREATE INDEX idx_agents_competencies ON agent.agents USING GIN(competencies);

CREATE TRIGGER update_agents_updated_at
    BEFORE UPDATE ON agent.agents
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

COMMENT ON TABLE agent.agents IS 'AI agents with their configurations';

-- Agent Sessions
CREATE TABLE agent.sessions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    agent_id BIGINT NOT NULL REFERENCES agent.agents(id) ON DELETE CASCADE,

    session_token UUID DEFAULT uuid_generate_v4() UNIQUE,

    -- Context
    current_project_id BIGINT,
    current_task_id BIGINT,
    context_window_used INTEGER DEFAULT 0,

    -- State
    state JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,

    -- Resumption
    last_checkpoint JSONB,
    can_resume BOOLEAN DEFAULT TRUE,

    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    last_activity_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sessions_agent ON agent.sessions(agent_id);
CREATE INDEX idx_sessions_active ON agent.sessions(is_active) WHERE is_active = TRUE;

COMMENT ON TABLE agent.sessions IS 'Agent session tracking';

-- Agent Goals
CREATE TABLE agent.goals (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    agent_id BIGINT NOT NULL REFERENCES agent.agents(id) ON DELETE CASCADE,

    -- Hierarchy
    parent_id BIGINT REFERENCES agent.goals(id) ON DELETE SET NULL,

    -- Goal definition
    title VARCHAR(500) NOT NULL,
    description TEXT,
    success_criteria TEXT[],

    -- Status
    status public.goal_status DEFAULT 'pending',
    priority public.goal_priority DEFAULT 'medium',
    progress_percent FLOAT DEFAULT 0 CHECK (progress_percent >= 0 AND progress_percent <= 100),

    -- Time
    deadline TIMESTAMPTZ,
    estimated_hours FLOAT,
    actual_hours FLOAT,

    -- Decomposition
    is_decomposed BOOLEAN DEFAULT FALSE,
    max_subgoals INTEGER DEFAULT 10,

    -- Links
    background_task_id BIGINT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_goals_agent ON agent.goals(agent_id);
CREATE INDEX idx_goals_parent ON agent.goals(parent_id);
CREATE INDEX idx_goals_status ON agent.goals(status);

CREATE TRIGGER update_goals_updated_at
    BEFORE UPDATE ON agent.goals
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

COMMENT ON TABLE agent.goals IS 'Hierarchical agent goals';

-- Goal Dependencies
CREATE TABLE agent.goal_dependencies (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    goal_id BIGINT NOT NULL REFERENCES agent.goals(id) ON DELETE CASCADE,
    depends_on_id BIGINT NOT NULL REFERENCES agent.goals(id) ON DELETE CASCADE,
    dependency_type VARCHAR(50) DEFAULT 'blocks',  -- blocks, informs, enhances
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(goal_id, depends_on_id),
    CHECK (goal_id != depends_on_id)
);

-- Goal Activity Log
CREATE TABLE agent.goal_activities (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    goal_id BIGINT NOT NULL REFERENCES agent.goals(id) ON DELETE CASCADE,
    activity_type VARCHAR(50) NOT NULL,
    description TEXT,
    old_status public.goal_status,
    new_status public.goal_status,
    progress_change FLOAT,
    actor_type VARCHAR(20),  -- agent, system, user
    actor_id BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_goal_activities_goal ON agent.goal_activities(goal_id);

-- =============================================================================
-- PROJECT SCHEMA
-- =============================================================================

CREATE TABLE project.projects (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(100) UNIQUE,
    description TEXT,

    -- Repository
    repository_url TEXT,
    repository_path TEXT,
    default_branch VARCHAR(100) DEFAULT 'main',

    -- Tech stack
    tech_stack TEXT[] DEFAULT '{}',
    languages TEXT[] DEFAULT '{}',
    frameworks TEXT[] DEFAULT '{}',

    -- Configuration
    quality_standards JSONB DEFAULT '{}',
    tools_config JSONB DEFAULT '{}',

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_projects_active ON project.projects(is_active) WHERE is_active = TRUE;

CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON project.projects
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

COMMENT ON TABLE project.projects IS 'Software projects';

-- Project Files (for RAG)
CREATE TABLE project.files (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES project.projects(id) ON DELETE CASCADE,

    file_path TEXT NOT NULL,
    file_type VARCHAR(50),
    language VARCHAR(50),

    -- Content
    content TEXT,
    content_hash VARCHAR(64),  -- SHA256 for change detection

    -- RAG
    embedding vector(1536),
    importance FLOAT DEFAULT 0.5 CHECK (importance >= 0 AND importance <= 1),

    -- Metadata
    line_count INTEGER,
    size_bytes BIGINT,

    last_indexed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(project_id, file_path)
);

CREATE INDEX idx_files_project ON project.files(project_id);
CREATE INDEX idx_files_embedding ON project.files USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE TRIGGER update_files_updated_at
    BEFORE UPDATE ON project.files
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

-- =============================================================================
-- CIRCLE SCHEMA
-- =============================================================================

CREATE TABLE circle.circles (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200),
    description TEXT,

    -- Owner (optional)
    owner_id BIGINT REFERENCES agent.agents(id) ON DELETE SET NULL,

    -- Project link
    project_id BIGINT REFERENCES project.projects(id) ON DELETE SET NULL,

    -- Configuration
    config JSONB DEFAULT '{}',
    settings JSONB DEFAULT '{}',
    review_policy VARCHAR(50) DEFAULT 'required',  -- required, optional, none
    require_review BOOLEAN DEFAULT TRUE,
    auto_route_tasks BOOLEAN DEFAULT TRUE,
    auto_route BOOLEAN DEFAULT TRUE,
    max_agents INTEGER DEFAULT 10,

    -- Status
    status public.circle_status DEFAULT 'created',
    is_active BOOLEAN DEFAULT TRUE,
    started_at TIMESTAMPTZ,
    stopped_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_circles_status ON circle.circles(status);
CREATE INDEX idx_circles_project ON circle.circles(project_id);

CREATE TRIGGER update_circles_updated_at
    BEFORE UPDATE ON circle.circles
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

COMMENT ON TABLE circle.circles IS 'Agent collaboration circles';

-- Circle Members
CREATE TABLE circle.members (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    circle_id BIGINT NOT NULL REFERENCES circle.circles(id) ON DELETE CASCADE,
    agent_id BIGINT NOT NULL REFERENCES agent.agents(id) ON DELETE CASCADE,

    role public.agent_role DEFAULT 'member',
    permissions JSONB DEFAULT '{}',
    competencies TEXT[] DEFAULT '{}',
    can_review TEXT[] DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,

    joined_at TIMESTAMPTZ DEFAULT NOW(),
    left_at TIMESTAMPTZ,

    UNIQUE(circle_id, agent_id)
);

CREATE INDEX idx_members_circle ON circle.members(circle_id);
CREATE INDEX idx_members_agent ON circle.members(agent_id);

-- Circle Tasks
CREATE TABLE circle.tasks (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    circle_id BIGINT NOT NULL REFERENCES circle.circles(id) ON DELETE CASCADE,

    -- Task definition
    title VARCHAR(500) NOT NULL,
    description TEXT,
    requirements TEXT[],

    -- Hierarchy
    parent_task_id BIGINT REFERENCES circle.tasks(id) ON DELETE SET NULL,

    -- Assignment
    assigned_agent_id BIGINT REFERENCES agent.agents(id) ON DELETE SET NULL,
    created_by_agent_id BIGINT REFERENCES agent.agents(id),

    -- Status
    status public.task_status DEFAULT 'pending',
    priority public.task_priority DEFAULT 'medium',

    -- Review
    requires_review BOOLEAN DEFAULT TRUE,
    reviewer_agent_id BIGINT REFERENCES agent.agents(id) ON DELETE SET NULL,

    -- Links
    project_id BIGINT REFERENCES project.projects(id) ON DELETE SET NULL,
    conversation_id BIGINT,

    -- Time tracking
    estimated_hours FLOAT,
    actual_hours FLOAT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    due_date TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tasks_circle ON circle.tasks(circle_id);
CREATE INDEX idx_tasks_status ON circle.tasks(status);
CREATE INDEX idx_tasks_assigned ON circle.tasks(assigned_agent_id);

CREATE TRIGGER update_tasks_updated_at
    BEFORE UPDATE ON circle.tasks
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

-- Background Tasks (autonomous long-running tasks)
CREATE TABLE circle.background_tasks (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    circle_id BIGINT REFERENCES circle.circles(id) ON DELETE SET NULL,
    agent_id BIGINT NOT NULL REFERENCES agent.agents(id) ON DELETE CASCADE,

    -- Goal
    goal TEXT NOT NULL,
    context JSONB DEFAULT '{}',

    -- Execution
    status public.background_task_status DEFAULT 'pending',
    current_step INTEGER DEFAULT 0,
    max_steps INTEGER DEFAULT 100,

    -- Progress
    progress_percent FLOAT DEFAULT 0,
    progress_summary TEXT,

    -- Results
    result JSONB,
    error_message TEXT,

    -- Checkpointing
    checkpoint_data JSONB,
    checkpoint_interval INTEGER DEFAULT 10,
    last_checkpoint_at TIMESTAMPTZ,

    -- Timing
    timeout_seconds INTEGER DEFAULT 3600,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_bg_tasks_agent ON circle.background_tasks(agent_id);
CREATE INDEX idx_bg_tasks_status ON circle.background_tasks(status);

CREATE TRIGGER update_bg_tasks_updated_at
    BEFORE UPDATE ON circle.background_tasks
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

-- Background Task Steps (audit trail)
CREATE TABLE circle.background_task_steps (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    task_id BIGINT NOT NULL REFERENCES circle.background_tasks(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,

    -- Action
    action_type VARCHAR(100),
    action_description TEXT,

    -- Tool usage
    tool_name VARCHAR(100),
    tool_input JSONB,
    tool_output JSONB,

    -- LLM details
    llm_model VARCHAR(100),
    tokens_input INTEGER,
    tokens_output INTEGER,

    -- Timing
    duration_ms INTEGER,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_bg_task_steps_task ON circle.background_task_steps(task_id);

-- Scheduled Actions
CREATE TABLE circle.scheduled_actions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    circle_id BIGINT REFERENCES circle.circles(id) ON DELETE CASCADE,
    agent_id BIGINT NOT NULL REFERENCES agent.agents(id) ON DELETE CASCADE,

    -- Definition
    name VARCHAR(200) NOT NULL,
    description TEXT,
    action_type VARCHAR(100) NOT NULL,
    action_config JSONB DEFAULT '{}',

    -- Schedule
    schedule_type public.schedule_type NOT NULL,
    cron_expression VARCHAR(100),
    interval_seconds INTEGER,
    next_run_at TIMESTAMPTZ,

    -- Limits
    max_executions INTEGER,
    execution_count INTEGER DEFAULT 0,
    expires_at TIMESTAMPTZ,

    -- Retry
    retry_on_failure BOOLEAN DEFAULT TRUE,
    max_retries INTEGER DEFAULT 3,
    retry_delay_seconds INTEGER DEFAULT 60,

    -- Status
    status public.scheduled_action_status DEFAULT 'active',
    last_run_at TIMESTAMPTZ,
    last_status VARCHAR(50),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_scheduled_actions_next ON circle.scheduled_actions(next_run_at) WHERE status = 'active';

CREATE TRIGGER update_scheduled_actions_updated_at
    BEFORE UPDATE ON circle.scheduled_actions
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

-- Circle Events (pub/sub)
CREATE TABLE circle.events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    circle_id BIGINT NOT NULL REFERENCES circle.circles(id) ON DELETE CASCADE,

    event_type VARCHAR(100) NOT NULL,
    source_agent_id BIGINT REFERENCES agent.agents(id),

    data JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_events_circle ON circle.events(circle_id);
CREATE INDEX idx_events_type ON circle.events(event_type);
CREATE INDEX idx_events_created ON circle.events(created_at DESC);

-- =============================================================================
-- COMMUNICATION SCHEMA
-- =============================================================================

CREATE TABLE communication.conversations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    circle_id BIGINT REFERENCES circle.circles(id) ON DELETE SET NULL,

    -- Definition
    topic VARCHAR(500),
    conversation_type VARCHAR(50) DEFAULT 'collaboration',
    participant_agent_ids BIGINT[] DEFAULT '{}',
    participant_names TEXT[] DEFAULT '{}',
    initial_prompt TEXT,

    -- Turn management
    current_turn INTEGER DEFAULT 0,
    turns_taken INTEGER DEFAULT 0,
    max_turns INTEGER DEFAULT 50,
    turn_strategy VARCHAR(50) DEFAULT 'round_robin',  -- round_robin, mention_based, free_form

    -- Links
    task_id BIGINT,

    -- Status
    status public.conversation_status DEFAULT 'pending',
    is_active BOOLEAN DEFAULT TRUE,

    -- Summary
    summary TEXT,

    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_conversations_circle ON communication.conversations(circle_id);
CREATE INDEX idx_conversations_status ON communication.conversations(status);

COMMENT ON TABLE communication.conversations IS 'Agent conversation threads';

-- Messages
CREATE TABLE communication.messages (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conversation_id BIGINT NOT NULL REFERENCES communication.conversations(id) ON DELETE CASCADE,

    -- Sender
    agent_id BIGINT REFERENCES agent.agents(id) ON DELETE SET NULL,
    agent_name VARCHAR(200),  -- Denormalized for performance
    role public.message_role NOT NULL,

    -- Content
    content TEXT NOT NULL,

    -- Tool usage
    tool_calls JSONB,
    tool_results JSONB,

    -- Threading
    parent_message_id BIGINT REFERENCES communication.messages(id),
    mentions BIGINT[] DEFAULT '{}',

    -- Metadata
    is_pinned BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation ON communication.messages(conversation_id);
CREATE INDEX idx_messages_agent ON communication.messages(agent_id);
CREATE INDEX idx_messages_mentions ON communication.messages USING GIN(mentions);

-- Chat History (1:1 agent chats outside conversations)
CREATE TABLE communication.chat_history (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    agent_id BIGINT NOT NULL REFERENCES agent.agents(id) ON DELETE CASCADE,
    session_id BIGINT REFERENCES agent.sessions(id) ON DELETE SET NULL,

    role public.message_role NOT NULL,
    content TEXT NOT NULL,

    -- Token tracking
    tokens_input INTEGER,
    tokens_output INTEGER,
    thinking_time_ms INTEGER,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chat_history_agent ON communication.chat_history(agent_id);
CREATE INDEX idx_chat_history_session ON communication.chat_history(session_id);

-- Notifications
CREATE TABLE communication.notifications (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    agent_id BIGINT NOT NULL REFERENCES agent.agents(id) ON DELETE CASCADE,

    notification_type VARCHAR(100) NOT NULL,
    title VARCHAR(500),
    message TEXT,

    -- Source
    source_type VARCHAR(50),
    source_id BIGINT,

    -- Status
    is_read BOOLEAN DEFAULT FALSE,
    is_dismissed BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_notifications_agent ON communication.notifications(agent_id);
CREATE INDEX idx_notifications_unread ON communication.notifications(agent_id) WHERE is_read = FALSE;

-- =============================================================================
-- MEMORY SCHEMA
-- =============================================================================

CREATE TABLE memory.memories (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Scope
    scope public.memory_scope NOT NULL,
    scope_id BIGINT,
    agent_id BIGINT REFERENCES agent.agents(id) ON DELETE CASCADE,

    -- Content
    memory_type public.memory_type DEFAULT 'fact',
    key VARCHAR(200) NOT NULL,
    value TEXT NOT NULL,

    -- RAG
    embedding vector(1536),

    -- Scoring
    importance FLOAT DEFAULT 0.5 CHECK (importance >= 0 AND importance <= 1),
    relevance FLOAT DEFAULT 0.5,

    -- Expiration
    expires_at TIMESTAMPTZ,

    -- Metadata
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_memories_scope ON memory.memories(scope, scope_id);
CREATE INDEX idx_memories_agent ON memory.memories(agent_id);
CREATE INDEX idx_memories_key ON memory.memories(key);
CREATE INDEX idx_memories_embedding ON memory.memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_memories_tags ON memory.memories USING GIN(tags);

CREATE TRIGGER update_memories_updated_at
    BEFORE UPDATE ON memory.memories
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

COMMENT ON TABLE memory.memories IS 'Long-term agent memory with vector embeddings';

-- Embeddings Cache
CREATE TABLE memory.embeddings_cache (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    content_hash VARCHAR(64) NOT NULL UNIQUE,
    embedding vector(1536) NOT NULL,
    model VARCHAR(100),
    usage_count INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_embeddings_cache_hash ON memory.embeddings_cache(content_hash);

-- Knowledge Base
CREATE TABLE memory.knowledge_base (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Scope
    project_id BIGINT REFERENCES project.projects(id) ON DELETE CASCADE,
    circle_id BIGINT REFERENCES circle.circles(id) ON DELETE CASCADE,

    -- Content
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(100),

    -- RAG
    embedding vector(1536),

    -- Quality
    quality_score FLOAT DEFAULT 0.5,
    upvotes INTEGER DEFAULT 0,
    downvotes INTEGER DEFAULT 0,
    is_verified BOOLEAN DEFAULT FALSE,

    -- Author
    created_by_agent_id BIGINT REFERENCES agent.agents(id),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_kb_project ON memory.knowledge_base(project_id);
CREATE INDEX idx_kb_circle ON memory.knowledge_base(circle_id);
CREATE INDEX idx_kb_embedding ON memory.knowledge_base USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE TRIGGER update_kb_updated_at
    BEFORE UPDATE ON memory.knowledge_base
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

-- Context Snapshots
CREATE TABLE memory.context_snapshots (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    agent_id BIGINT NOT NULL REFERENCES agent.agents(id) ON DELETE CASCADE,
    session_id BIGINT REFERENCES agent.sessions(id) ON DELETE SET NULL,

    reason VARCHAR(100),  -- compaction, session_end, manual

    -- Content
    key_points TEXT[],
    decisions TEXT[],
    context_data JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_context_snapshots_agent ON memory.context_snapshots(agent_id);

-- =============================================================================
-- REVIEW SCHEMA
-- =============================================================================

CREATE TABLE review.reviews (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    task_id BIGINT NOT NULL REFERENCES circle.tasks(id) ON DELETE CASCADE,

    -- Participants
    author_agent_id BIGINT NOT NULL REFERENCES agent.agents(id),
    reviewer_agent_id BIGINT NOT NULL REFERENCES agent.agents(id),

    -- Review
    review_type public.review_type DEFAULT 'code',
    status public.review_status DEFAULT 'pending',
    iteration INTEGER DEFAULT 1,

    -- Feedback
    summary TEXT,
    changes_requested TEXT,
    blocking_issues_count INTEGER DEFAULT 0,

    -- Score
    overall_score FLOAT CHECK (overall_score >= 0 AND overall_score <= 100),

    -- Flags
    changes_addressed BOOLEAN DEFAULT FALSE,

    submitted_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CHECK (author_agent_id != reviewer_agent_id)
);

CREATE INDEX idx_reviews_task ON review.reviews(task_id);
CREATE INDEX idx_reviews_status ON review.reviews(status);

CREATE TRIGGER update_reviews_updated_at
    BEFORE UPDATE ON review.reviews
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

-- Review Comments
CREATE TABLE review.comments (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    review_id BIGINT NOT NULL REFERENCES review.reviews(id) ON DELETE CASCADE,

    -- Location
    file_path TEXT,
    line_start INTEGER,
    line_end INTEGER,

    -- Content
    content TEXT NOT NULL,
    severity VARCHAR(50) DEFAULT 'suggestion',  -- suggestion, warning, error, blocking
    category VARCHAR(100),

    -- Suggested fix
    suggested_fix TEXT,

    -- Resolution
    is_resolved BOOLEAN DEFAULT FALSE,
    resolution_note TEXT,
    resolved_by_agent_id BIGINT REFERENCES agent.agents(id),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_comments_review ON review.comments(review_id);
CREATE INDEX idx_comments_file ON review.comments(file_path);

-- Quality Metrics
CREATE TABLE review.quality_metrics (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Scope
    agent_id BIGINT REFERENCES agent.agents(id) ON DELETE CASCADE,
    project_id BIGINT REFERENCES project.projects(id) ON DELETE CASCADE,
    circle_id BIGINT REFERENCES circle.circles(id) ON DELETE CASCADE,

    -- Metric
    metric_type VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,

    -- Time
    period_type VARCHAR(20) DEFAULT 'daily',
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_metrics_agent ON review.quality_metrics(agent_id);
CREATE INDEX idx_metrics_period ON review.quality_metrics(period_start, period_end);

-- =============================================================================
-- AUDIT SCHEMA
-- =============================================================================

CREATE TABLE audit.logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Classification
    level public.log_level DEFAULT 'info',
    category VARCHAR(100),
    action VARCHAR(100) NOT NULL,

    -- Message
    message TEXT,

    -- Context
    agent_id BIGINT REFERENCES agent.agents(id) ON DELETE SET NULL,
    circle_id BIGINT REFERENCES circle.circles(id) ON DELETE SET NULL,
    resource_type VARCHAR(100),
    resource_id BIGINT,

    -- Details
    details JSONB DEFAULT '{}',
    duration_ms INTEGER,

    -- Tracking
    request_id UUID,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_logs_level ON audit.logs(level);
CREATE INDEX idx_logs_category ON audit.logs(category);
CREATE INDEX idx_logs_created ON audit.logs(created_at DESC);
CREATE INDEX idx_logs_agent ON audit.logs(agent_id);

-- Escalations
CREATE TABLE audit.escalations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    escalation_type VARCHAR(100) NOT NULL,
    circle_id BIGINT REFERENCES circle.circles(id) ON DELETE SET NULL,

    title VARCHAR(500) NOT NULL,
    description TEXT,

    -- Source
    source_task_id BIGINT,
    source_review_id BIGINT,
    source_agent_id BIGINT REFERENCES agent.agents(id),

    -- Priority
    priority INTEGER DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
    severity VARCHAR(50) DEFAULT 'medium',

    -- Resolution
    status VARCHAR(50) DEFAULT 'open',
    assigned_to VARCHAR(200),
    resolution_notes TEXT,
    resolved_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_escalations_status ON audit.escalations(status) WHERE status = 'open';
CREATE INDEX idx_escalations_priority ON audit.escalations(priority DESC);

CREATE TRIGGER update_escalations_updated_at
    BEFORE UPDATE ON audit.escalations
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

-- System Events
CREATE TABLE audit.system_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    event_type VARCHAR(100) NOT NULL,
    component VARCHAR(100),  -- api, worker, scheduler, database
    level public.log_level DEFAULT 'info',

    message TEXT,
    error_message TEXT,
    stack_trace TEXT,

    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_system_events_type ON audit.system_events(event_type);
CREATE INDEX idx_system_events_created ON audit.system_events(created_at DESC);

-- API Requests
CREATE TABLE audit.api_requests (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    method VARCHAR(10) NOT NULL,
    path TEXT NOT NULL,
    query_params JSONB,

    -- Response
    status_code INTEGER,
    response_time_ms INTEGER,

    -- Context
    user_id BIGINT,
    agent_id BIGINT,
    request_id UUID,

    -- Client
    client_ip INET,
    user_agent TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_api_requests_created ON audit.api_requests(created_at DESC);
CREATE INDEX idx_api_requests_path ON audit.api_requests(path);

-- =============================================================================
-- VIEWS
-- =============================================================================

-- Agent Dashboard View
CREATE OR REPLACE VIEW public.agent_dashboard AS
SELECT
    a.id,
    a.name,
    p.display_name as persona_name,
    m.display_name as model_name,
    pr.name as provider_name,
    a.status,
    a.tasks_completed,
    a.reviews_done,
    a.average_quality_score,
    (SELECT COUNT(*) FROM memory.memories WHERE agent_id = a.id) as memory_count,
    (SELECT COUNT(*) FROM communication.messages WHERE agent_id = a.id) as message_count,
    (SELECT COUNT(*) FROM circle.members WHERE agent_id = a.id) as circle_count
FROM agent.agents a
LEFT JOIN agent.personas p ON a.persona_id = p.id
LEFT JOIN agent.models m ON a.model_id = m.id
LEFT JOIN agent.providers pr ON m.provider_id = pr.id
WHERE a.is_active = TRUE;

-- Circle Dashboard View
CREATE OR REPLACE VIEW public.circle_dashboard AS
SELECT
    c.id,
    c.name,
    c.display_name,
    c.status,
    p.name as project_name,
    (SELECT COUNT(*) FROM circle.members WHERE circle_id = c.id) as agent_count,
    (SELECT COUNT(*) FROM circle.tasks WHERE circle_id = c.id AND status NOT IN ('completed', 'cancelled')) as active_tasks,
    (SELECT COUNT(*) FROM communication.conversations WHERE circle_id = c.id AND status = 'active') as active_conversations
FROM circle.circles c
LEFT JOIN project.projects p ON c.project_id = p.id;

-- Goals Dashboard View
CREATE OR REPLACE VIEW public.goals_dashboard AS
WITH RECURSIVE goal_tree AS (
    SELECT
        id, agent_id, parent_id, title, status, priority,
        progress_percent, deadline, 1 as depth, ARRAY[id] as path
    FROM agent.goals
    WHERE parent_id IS NULL

    UNION ALL

    SELECT
        g.id, g.agent_id, g.parent_id, g.title, g.status, g.priority,
        g.progress_percent, g.deadline, gt.depth + 1, gt.path || g.id
    FROM agent.goals g
    JOIN goal_tree gt ON g.parent_id = gt.id
    WHERE gt.depth < 10
)
SELECT
    gt.*,
    a.name as agent_name,
    (SELECT COUNT(*) FROM agent.goals WHERE parent_id = gt.id) as subgoal_count
FROM goal_tree gt
JOIN agent.agents a ON gt.agent_id = a.id;

-- Background Tasks Dashboard View
CREATE OR REPLACE VIEW public.background_tasks_dashboard AS
SELECT
    bt.id,
    bt.goal,
    bt.status,
    bt.progress_percent,
    bt.current_step,
    bt.max_steps,
    a.name as agent_name,
    c.name as circle_name,
    (SELECT COUNT(*) FROM circle.background_task_steps WHERE task_id = bt.id) as total_steps,
    bt.started_at,
    EXTRACT(EPOCH FROM (COALESCE(bt.completed_at, NOW()) - bt.started_at))::INTEGER as duration_seconds
FROM circle.background_tasks bt
JOIN agent.agents a ON bt.agent_id = a.id
LEFT JOIN circle.circles c ON bt.circle_id = c.id;

-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

-- Search similar memories
CREATE OR REPLACE FUNCTION memory.search_similar_memories(
    query_embedding vector(1536),
    p_agent_id BIGINT DEFAULT NULL,
    p_scope public.memory_scope DEFAULT NULL,
    p_limit INTEGER DEFAULT 10,
    p_threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    id BIGINT,
    key VARCHAR(200),
    value TEXT,
    similarity FLOAT,
    scope public.memory_scope
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id,
        m.key,
        m.value,
        (1 - (m.embedding <=> query_embedding))::FLOAT as similarity,
        m.scope
    FROM memory.memories m
    WHERE m.embedding IS NOT NULL
        AND (p_agent_id IS NULL OR m.agent_id = p_agent_id)
        AND (p_scope IS NULL OR m.scope = p_scope)
        AND (1 - (m.embedding <=> query_embedding)) >= p_threshold
    ORDER BY m.embedding <=> query_embedding
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Get agent with full configuration
CREATE OR REPLACE FUNCTION agent.get_agent_config(p_agent_id BIGINT)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'id', a.id,
        'name', a.name,
        'status', a.status,
        'model', jsonb_build_object(
            'id', m.id,
            'name', m.display_name,
            'model_id', m.model_id,
            'provider', pr.name
        ),
        'persona', CASE WHEN p.id IS NOT NULL THEN jsonb_build_object(
            'id', p.id,
            'name', p.display_name,
            'role', p.role
        ) ELSE NULL END,
        'temperature', a.temperature,
        'competencies', a.competencies,
        'traits', COALESCE(a.traits, p.traits),
        'custom_prompt', a.custom_prompt,
        'base_prompt', p.base_prompt
    ) INTO result
    FROM agent.agents a
    LEFT JOIN agent.models m ON a.model_id = m.id
    LEFT JOIN agent.providers pr ON m.provider_id = pr.id
    LEFT JOIN agent.personas p ON a.persona_id = p.id
    WHERE a.id = p_agent_id;

    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Create agent from persona
CREATE OR REPLACE FUNCTION agent.create_agent_from_persona(
    p_persona_name VARCHAR(100),
    p_agent_name VARCHAR(100) DEFAULT NULL,
    p_model_id BIGINT DEFAULT NULL
)
RETURNS BIGINT AS $$
DECLARE
    v_persona agent.personas%ROWTYPE;
    v_agent_id BIGINT;
BEGIN
    SELECT * INTO v_persona FROM agent.personas WHERE name = p_persona_name;

    IF v_persona.id IS NULL THEN
        RAISE EXCEPTION 'Persona not found: %', p_persona_name;
    END IF;

    INSERT INTO agent.agents (
        name,
        model_id,
        persona_id,
        traits,
        communication_style,
        competencies,
        specializations,
        temperature
    ) VALUES (
        COALESCE(p_agent_name, v_persona.display_name),
        COALESCE(p_model_id, v_persona.default_model_id),
        v_persona.id,
        v_persona.traits,
        v_persona.communication_style,
        v_persona.competencies,
        v_persona.specializations,
        v_persona.default_temperature
    ) RETURNING id INTO v_agent_id;

    RETURN v_agent_id;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- PERMISSIONS
-- =============================================================================

-- Create application role if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'gathering_app') THEN
        CREATE ROLE gathering_app;
    END IF;
END
$$;

-- Grant schema permissions
GRANT USAGE ON SCHEMA agent TO gathering_app;
GRANT USAGE ON SCHEMA circle TO gathering_app;
GRANT USAGE ON SCHEMA project TO gathering_app;
GRANT USAGE ON SCHEMA communication TO gathering_app;
GRANT USAGE ON SCHEMA memory TO gathering_app;
GRANT USAGE ON SCHEMA review TO gathering_app;
GRANT USAGE ON SCHEMA audit TO gathering_app;

-- Grant table permissions
GRANT ALL ON ALL TABLES IN SCHEMA agent TO gathering_app;
GRANT ALL ON ALL TABLES IN SCHEMA circle TO gathering_app;
GRANT ALL ON ALL TABLES IN SCHEMA project TO gathering_app;
GRANT ALL ON ALL TABLES IN SCHEMA communication TO gathering_app;
GRANT ALL ON ALL TABLES IN SCHEMA memory TO gathering_app;
GRANT ALL ON ALL TABLES IN SCHEMA review TO gathering_app;
GRANT ALL ON ALL TABLES IN SCHEMA audit TO gathering_app;
GRANT ALL ON ALL TABLES IN SCHEMA public TO gathering_app;

-- Grant sequence permissions
GRANT ALL ON ALL SEQUENCES IN SCHEMA agent TO gathering_app;
GRANT ALL ON ALL SEQUENCES IN SCHEMA circle TO gathering_app;
GRANT ALL ON ALL SEQUENCES IN SCHEMA project TO gathering_app;
GRANT ALL ON ALL SEQUENCES IN SCHEMA communication TO gathering_app;
GRANT ALL ON ALL SEQUENCES IN SCHEMA memory TO gathering_app;
GRANT ALL ON ALL SEQUENCES IN SCHEMA review TO gathering_app;
GRANT ALL ON ALL SEQUENCES IN SCHEMA audit TO gathering_app;

-- Grant function permissions
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA agent TO gathering_app;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA memory TO gathering_app;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO gathering_app;
