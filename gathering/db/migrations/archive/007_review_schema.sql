-- GatheRing Database Migration
-- Migration 007: Review schema - Reviews & Quality Control
-- Schema: review

-- =============================================================================
-- review.reviews - Code Reviews
-- =============================================================================

CREATE TABLE review.reviews (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- What is being reviewed
    task_id BIGINT NOT NULL,  -- References circle.tasks(id)
    project_id BIGINT REFERENCES project.projects(id) ON DELETE SET NULL,
    circle_id BIGINT REFERENCES circle.circles(id) ON DELETE SET NULL,

    -- Who
    author_id BIGINT NOT NULL REFERENCES agent.agents(id) ON DELETE CASCADE,
    reviewer_id BIGINT NOT NULL REFERENCES agent.agents(id) ON DELETE CASCADE,

    -- Review details
    review_type public.review_type DEFAULT 'quality',
    status public.review_status DEFAULT 'pending',

    -- Scores (0-100 scale)
    overall_score INTEGER CHECK (overall_score >= 0 AND overall_score <= 100),
    scores JSONB DEFAULT '{}',  -- {"code_quality": 85, "test_coverage": 70, ...}

    -- Feedback
    summary TEXT,
    feedback TEXT,
    suggestions JSONB DEFAULT '[]',

    -- Issues found
    issues JSONB DEFAULT '[]',
    blocking_issues_count INTEGER DEFAULT 0,

    -- Changes requested
    changes_requested JSONB DEFAULT '[]',
    changes_addressed BOOLEAN DEFAULT FALSE,

    -- Review iteration
    iteration INTEGER DEFAULT 1,
    previous_review_id BIGINT REFERENCES review.reviews(id) ON DELETE SET NULL,

    -- Files reviewed
    files_reviewed TEXT[] DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Prevent self-review (enforced by trigger)
    CONSTRAINT no_self_review CHECK (author_id != reviewer_id)
);

-- Indexes
CREATE INDEX idx_reviews_task ON review.reviews(task_id);
CREATE INDEX idx_reviews_author ON review.reviews(author_id);
CREATE INDEX idx_reviews_reviewer ON review.reviews(reviewer_id);
CREATE INDEX idx_reviews_status ON review.reviews(status) WHERE status NOT IN ('approved', 'rejected');
CREATE INDEX idx_reviews_circle ON review.reviews(circle_id) WHERE circle_id IS NOT NULL;

-- Trigger
CREATE TRIGGER update_reviews_updated_at
    BEFORE UPDATE ON review.reviews
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

COMMENT ON TABLE review.reviews IS 'Code reviews between agents';

-- =============================================================================
-- review.comments - Inline Review Comments
-- =============================================================================

CREATE TABLE review.comments (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    review_id BIGINT NOT NULL REFERENCES review.reviews(id) ON DELETE CASCADE,

    -- Author
    author_id BIGINT NOT NULL REFERENCES agent.agents(id) ON DELETE CASCADE,

    -- Location
    file_path VARCHAR(500),
    line_start INTEGER,
    line_end INTEGER,
    code_snippet TEXT,

    -- Comment content
    comment TEXT NOT NULL,
    severity VARCHAR(20) DEFAULT 'suggestion',  -- suggestion, warning, error, blocking

    -- Code suggestion
    suggested_code TEXT,

    -- Resolution
    is_resolved BOOLEAN DEFAULT FALSE,
    resolution_note TEXT,
    resolved_by_id BIGINT REFERENCES agent.agents(id) ON DELETE SET NULL,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_comments_review ON review.comments(review_id);
CREATE INDEX idx_comments_file ON review.comments(file_path) WHERE file_path IS NOT NULL;
CREATE INDEX idx_comments_unresolved ON review.comments(review_id) WHERE NOT is_resolved;

COMMENT ON TABLE review.comments IS 'Inline comments on code during review';

-- =============================================================================
-- review.quality_metrics - Quality Metrics Over Time
-- =============================================================================

CREATE TABLE review.quality_metrics (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Context
    agent_id BIGINT REFERENCES agent.agents(id) ON DELETE CASCADE,
    project_id BIGINT REFERENCES project.projects(id) ON DELETE CASCADE,
    circle_id BIGINT REFERENCES circle.circles(id) ON DELETE CASCADE,

    -- Metrics
    metric_type VARCHAR(50) NOT NULL,  -- approval_rate, code_quality, review_time, etc.
    value FLOAT NOT NULL,
    unit VARCHAR(20),  -- percent, hours, count

    -- Additional data
    metric_data JSONB DEFAULT '{}',

    -- Time period
    period_type VARCHAR(20) DEFAULT 'daily',  -- daily, weekly, monthly
    period_start TIMESTAMP WITH TIME ZONE,
    period_end TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_quality_metrics_agent ON review.quality_metrics(agent_id, recorded_at DESC)
    WHERE agent_id IS NOT NULL;
CREATE INDEX idx_quality_metrics_project ON review.quality_metrics(project_id, recorded_at DESC)
    WHERE project_id IS NOT NULL;
CREATE INDEX idx_quality_metrics_type ON review.quality_metrics(metric_type);

COMMENT ON TABLE review.quality_metrics IS 'Historical quality metrics for agents and projects';

-- =============================================================================
-- review.standards - Quality Standards
-- =============================================================================

CREATE TABLE review.standards (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Scope
    project_id BIGINT REFERENCES project.projects(id) ON DELETE CASCADE,
    circle_id BIGINT REFERENCES circle.circles(id) ON DELETE CASCADE,
    is_global BOOLEAN DEFAULT FALSE,

    -- Standard definition
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,  -- code, testing, docs, security
    description TEXT,

    -- Rules
    rules JSONB DEFAULT '[]',  -- List of rules to check
    severity VARCHAR(20) DEFAULT 'warning',  -- suggestion, warning, error, blocking

    -- Thresholds
    min_score INTEGER,
    required_for_approval BOOLEAN DEFAULT FALSE,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_standards_project ON review.standards(project_id) WHERE project_id IS NOT NULL;
CREATE INDEX idx_standards_circle ON review.standards(circle_id) WHERE circle_id IS NOT NULL;
CREATE INDEX idx_standards_global ON review.standards(is_global) WHERE is_global = TRUE;
CREATE INDEX idx_standards_category ON review.standards(category);

-- Trigger
CREATE TRIGGER update_standards_updated_at
    BEFORE UPDATE ON review.standards
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

COMMENT ON TABLE review.standards IS 'Quality standards and rules for reviews';

-- =============================================================================
-- Add foreign key constraint for task_id (after circle schema is created)
-- =============================================================================

ALTER TABLE review.reviews
    ADD CONSTRAINT fk_reviews_task
    FOREIGN KEY (task_id) REFERENCES circle.tasks(id) ON DELETE CASCADE;
