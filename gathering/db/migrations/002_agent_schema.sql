-- GatheRing Database Migration
-- Migration 002: Agent schema - Agents & Identity
-- Schema: agent

-- =============================================================================
-- agent.agents - AI Agents
-- =============================================================================

CREATE TABLE agent.agents (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL,

    -- LLM Configuration
    provider VARCHAR(50) NOT NULL,  -- claude, deepseek, openai, ollama
    model VARCHAR(100) NOT NULL,

    -- Personality
    persona TEXT,  -- System prompt / personality description
    traits TEXT[] DEFAULT '{}',
    communication_style VARCHAR(50) DEFAULT 'balanced',  -- formal, concise, technical, friendly, detailed

    -- Competencies and skills
    competencies TEXT[] DEFAULT '{}',  -- ["python", "architecture", "testing"]
    specializations TEXT[] DEFAULT '{}',

    -- Review capabilities
    can_review TEXT[] DEFAULT '{}',  -- Types of review this agent can do
    review_strictness FLOAT DEFAULT 0.7 CHECK (review_strictness >= 0 AND review_strictness <= 1),

    -- Configuration
    temperature FLOAT DEFAULT 0.7 CHECK (temperature >= 0 AND temperature <= 2),
    max_tokens INTEGER,

    -- Performance metrics
    tasks_completed INTEGER DEFAULT 0,
    reviews_done INTEGER DEFAULT 0,
    approval_rate FLOAT DEFAULT 0.0 CHECK (approval_rate >= 0 AND approval_rate <= 1),
    average_quality_score FLOAT DEFAULT 0.0 CHECK (average_quality_score >= 0 AND average_quality_score <= 100),

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    status VARCHAR(20) DEFAULT 'idle',  -- idle, busy, offline
    last_active_at TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_agents_provider ON agent.agents(provider);
CREATE INDEX idx_agents_status ON agent.agents(status) WHERE is_active = TRUE;
CREATE INDEX idx_agents_competencies ON agent.agents USING GIN(competencies);

-- Triggers
CREATE TRIGGER update_agents_updated_at
    BEFORE UPDATE ON agent.agents
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

COMMENT ON TABLE agent.agents IS 'AI agents with their personas and capabilities';

-- =============================================================================
-- agent.personas - Predefined Personas (Templates)
-- =============================================================================

CREATE TABLE agent.personas (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200),

    -- Persona definition
    role VARCHAR(100) NOT NULL,
    base_prompt TEXT NOT NULL,
    traits TEXT[] DEFAULT '{}',
    communication_style VARCHAR(50) DEFAULT 'balanced',
    specializations TEXT[] DEFAULT '{}',

    -- Default configuration
    default_provider VARCHAR(50),
    default_model VARCHAR(100),
    default_temperature FLOAT DEFAULT 0.7,

    -- Metadata
    description TEXT,
    icon VARCHAR(50),
    is_builtin BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Trigger
CREATE TRIGGER update_personas_updated_at
    BEFORE UPDATE ON agent.personas
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

COMMENT ON TABLE agent.personas IS 'Reusable persona templates for agents';

-- =============================================================================
-- agent.sessions - Agent Sessions
-- =============================================================================

CREATE TABLE agent.sessions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    agent_id BIGINT NOT NULL REFERENCES agent.agents(id) ON DELETE CASCADE,

    -- Session info
    session_token VARCHAR(64) UNIQUE,
    project_id BIGINT,  -- References project.projects(id)

    -- Session state
    working_files TEXT[] DEFAULT '{}',
    pending_actions TEXT[] DEFAULT '{}',

    -- Current task tracking
    current_task_id BIGINT,  -- References circle.tasks(id)
    current_task_title VARCHAR(200),
    current_task_progress TEXT,

    -- Context window
    context_window_start INTEGER DEFAULT 0,
    total_messages INTEGER DEFAULT 0,

    -- Timestamps
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE,

    -- Resume info
    needs_resume BOOLEAN DEFAULT FALSE,
    resume_reason TEXT
);

-- Indexes
CREATE INDEX idx_sessions_agent ON agent.sessions(agent_id);
CREATE INDEX idx_sessions_active ON agent.sessions(agent_id) WHERE ended_at IS NULL;

COMMENT ON TABLE agent.sessions IS 'Active agent sessions with state tracking';

-- =============================================================================
-- Insert builtin personas
-- =============================================================================

INSERT INTO agent.personas (name, display_name, role, base_prompt, traits, communication_style, specializations, is_builtin) VALUES
('architect', 'Architecte', 'Architecte Principal',
 'Tu es l''architecte principal du projet. Tu supervises l''architecture, guides les décisions techniques, et assures la cohérence du design.',
 ARRAY['rigoureux', 'pédagogue', 'visionnaire'], 'detailed',
 ARRAY['architecture', 'security', 'design-patterns'], TRUE),

('senior_dev', 'Développeur Senior', 'Développeur Senior',
 'Tu es un développeur senior expérimenté. Tu implémentes les features, écris des tests, et maintiens la qualité du code.',
 ARRAY['pragmatique', 'efficace', 'collaboratif'], 'balanced',
 ARRAY['python', 'testing', 'api'], TRUE),

('code_specialist', 'Spécialiste Code', 'Spécialiste Code',
 'Tu es un spécialiste du code et de l''optimisation. Tu analyses, optimises et débugues le code avec expertise.',
 ARRAY['analytique', 'précis', 'performant'], 'technical',
 ARRAY['algorithms', 'optimization', 'debugging'], TRUE),

('qa_engineer', 'Ingénieur QA', 'Ingénieur QA',
 'Tu es responsable de la qualité. Tu écris des tests, vérifies la couverture, et assures que le code respecte les standards.',
 ARRAY['méthodique', 'exigeant', 'documenteur'], 'formal',
 ARRAY['testing', 'automation', 'quality'], TRUE);
