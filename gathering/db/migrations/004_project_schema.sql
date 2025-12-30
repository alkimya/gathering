-- GatheRing Database Migration
-- Migration 004: Project schema - Projects
-- Schema: project

-- =============================================================================
-- project.projects - Software Projects
-- =============================================================================

CREATE TABLE project.projects (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Basic info
    name VARCHAR(200) NOT NULL,
    display_name VARCHAR(300),
    description TEXT,

    -- Project location
    repository_url VARCHAR(500),
    local_path VARCHAR(500),
    branch VARCHAR(100) DEFAULT 'main',

    -- Project metadata
    tech_stack TEXT[] DEFAULT '{}',
    languages TEXT[] DEFAULT '{}',
    frameworks TEXT[] DEFAULT '{}',

    -- Status
    status VARCHAR(50) DEFAULT 'active',  -- active, archived, on_hold

    -- Context for agents
    context TEXT,
    conventions JSONB DEFAULT '{}',
    key_files JSONB DEFAULT '{}',
    commands JSONB DEFAULT '{}',
    notes TEXT[] DEFAULT '{}',

    -- Python-specific
    venv_path VARCHAR(500),
    python_version VARCHAR(20),

    -- Quality standards
    quality_standards JSONB DEFAULT '{
        "code_coverage_min": 80,
        "require_tests": true,
        "require_docs": true,
        "linting_enabled": true,
        "security_scan": true
    }',

    -- Tools configuration
    tools JSONB DEFAULT '{}',

    -- Owner
    owner_id VARCHAR(100),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_projects_status ON project.projects(status);
CREATE INDEX idx_projects_tech_stack ON project.projects USING GIN(tech_stack);

-- Trigger
CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON project.projects
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

COMMENT ON TABLE project.projects IS 'Software projects managed by gathering';

-- =============================================================================
-- project.files - Project Files (for RAG indexing)
-- =============================================================================

CREATE TABLE project.files (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES project.projects(id) ON DELETE CASCADE,

    -- File info
    file_path VARCHAR(500) NOT NULL,
    file_type VARCHAR(50),  -- python, typescript, markdown, etc.
    file_name VARCHAR(200),

    -- Content summary for context (not full content)
    summary TEXT,
    symbols TEXT[] DEFAULT '{}',  -- Classes, functions, etc.

    -- For RAG - vector embedding
    embedding vector(1536),  -- OpenAI embeddings dimension

    -- File metadata
    size_bytes INTEGER,
    line_count INTEGER,
    last_modified TIMESTAMP WITH TIME ZONE,
    content_hash VARCHAR(64),  -- SHA256 for change detection

    -- Importance score (0-1)
    importance FLOAT DEFAULT 0.5 CHECK (importance >= 0 AND importance <= 1),

    -- Timestamps
    indexed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(project_id, file_path)
);

-- Indexes
CREATE INDEX idx_files_project ON project.files(project_id);
CREATE INDEX idx_files_type ON project.files(file_type);
CREATE INDEX idx_files_embedding ON project.files USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Trigger
CREATE TRIGGER update_files_updated_at
    BEFORE UPDATE ON project.files
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

COMMENT ON TABLE project.files IS 'Indexed project files for RAG search';

-- =============================================================================
-- project.circle_projects - Link circles to projects
-- =============================================================================

CREATE TABLE project.circle_projects (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    circle_id BIGINT NOT NULL REFERENCES circle.circles(id) ON DELETE CASCADE,
    project_id BIGINT NOT NULL REFERENCES project.projects(id) ON DELETE CASCADE,

    -- Link info
    is_primary BOOLEAN DEFAULT FALSE,

    -- Timestamps
    linked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(circle_id, project_id)
);

-- Indexes
CREATE INDEX idx_circle_projects_circle ON project.circle_projects(circle_id);
CREATE INDEX idx_circle_projects_project ON project.circle_projects(project_id);

COMMENT ON TABLE project.circle_projects IS 'Link between circles and projects';
