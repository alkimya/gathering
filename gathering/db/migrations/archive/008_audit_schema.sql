-- GatheRing Database Migration
-- Migration 008: Audit schema - Audit & Logs
-- Schema: audit

-- =============================================================================
-- audit.logs - Comprehensive Audit Logging
-- =============================================================================

CREATE TABLE audit.logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Who
    agent_id BIGINT REFERENCES agent.agents(id) ON DELETE SET NULL,
    user_id VARCHAR(100),

    -- What
    category VARCHAR(50) NOT NULL,  -- agent, circle, task, review, memory, system
    action VARCHAR(100) NOT NULL,   -- created, updated, deleted, executed, etc.
    resource_type VARCHAR(50),      -- agent, task, review, etc.
    resource_id BIGINT,

    -- Details
    level public.log_level DEFAULT 'info',
    message TEXT NOT NULL,
    details JSONB DEFAULT '{}',

    -- Context
    circle_id BIGINT REFERENCES circle.circles(id) ON DELETE SET NULL,
    project_id BIGINT REFERENCES project.projects(id) ON DELETE SET NULL,
    task_id BIGINT,  -- References circle.tasks(id)
    review_id BIGINT,  -- References review.reviews(id)
    conversation_id BIGINT,  -- References communication.conversations(id)

    -- Request info
    request_id VARCHAR(64),
    session_id BIGINT REFERENCES agent.sessions(id) ON DELETE SET NULL,
    ip_address INET,
    user_agent TEXT,

    -- Performance
    duration_ms INTEGER,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_logs_timestamp ON audit.logs(created_at DESC);
CREATE INDEX idx_logs_agent ON audit.logs(agent_id) WHERE agent_id IS NOT NULL;
CREATE INDEX idx_logs_category ON audit.logs(category);
CREATE INDEX idx_logs_level ON audit.logs(level) WHERE level IN ('warning', 'error', 'critical');
CREATE INDEX idx_logs_resource ON audit.logs(resource_type, resource_id) WHERE resource_id IS NOT NULL;
CREATE INDEX idx_logs_request ON audit.logs(request_id) WHERE request_id IS NOT NULL;

-- Consider partitioning by time for high-volume deployments
-- CREATE TABLE audit.logs_2025 PARTITION OF audit.logs FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');

COMMENT ON TABLE audit.logs IS 'Comprehensive audit log for all actions';

-- =============================================================================
-- audit.escalations - Issues Requiring Human Intervention
-- =============================================================================

CREATE TABLE audit.escalations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- What triggered escalation
    escalation_type VARCHAR(50) NOT NULL,  -- review_rejected, conflict, security, error, manual

    -- Context
    circle_id BIGINT REFERENCES circle.circles(id) ON DELETE SET NULL,
    project_id BIGINT REFERENCES project.projects(id) ON DELETE SET NULL,
    task_id BIGINT,  -- References circle.tasks(id)
    review_id BIGINT,  -- References review.reviews(id)
    agent_id BIGINT REFERENCES agent.agents(id) ON DELETE SET NULL,

    -- Escalation details
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    context JSONB DEFAULT '{}',

    -- Priority (1 = highest, 10 = lowest)
    priority INTEGER DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
    severity VARCHAR(20) DEFAULT 'medium',  -- low, medium, high, critical

    -- Status
    status VARCHAR(50) DEFAULT 'open',  -- open, acknowledged, in_progress, resolved, dismissed

    -- Assignment
    assigned_to_user_id VARCHAR(100),

    -- Resolution
    resolution TEXT,
    resolution_type VARCHAR(50),  -- fixed, dismissed, deferred, duplicate
    resolved_by_user_id VARCHAR(100),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    due_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_escalations_status ON audit.escalations(status) WHERE status NOT IN ('resolved', 'dismissed');
CREATE INDEX idx_escalations_priority ON audit.escalations(priority) WHERE status NOT IN ('resolved', 'dismissed');
CREATE INDEX idx_escalations_circle ON audit.escalations(circle_id) WHERE circle_id IS NOT NULL;
CREATE INDEX idx_escalations_assigned ON audit.escalations(assigned_to_user_id) WHERE assigned_to_user_id IS NOT NULL;

-- Trigger
CREATE TRIGGER update_escalations_updated_at
    BEFORE UPDATE ON audit.escalations
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

COMMENT ON TABLE audit.escalations IS 'Issues requiring human intervention';

-- =============================================================================
-- audit.system_events - System-level Events
-- =============================================================================

CREATE TABLE audit.system_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Event info
    event_type VARCHAR(100) NOT NULL,  -- startup, shutdown, config_change, migration, backup
    component VARCHAR(100),  -- api, worker, scheduler, database

    -- Details
    level public.log_level DEFAULT 'info',
    message TEXT NOT NULL,
    details JSONB DEFAULT '{}',

    -- Error info (if applicable)
    error_type VARCHAR(200),
    error_message TEXT,
    stack_trace TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_system_events_type ON audit.system_events(event_type);
CREATE INDEX idx_system_events_level ON audit.system_events(level) WHERE level IN ('error', 'critical');
CREATE INDEX idx_system_events_timestamp ON audit.system_events(created_at DESC);

COMMENT ON TABLE audit.system_events IS 'System-level events and errors';

-- =============================================================================
-- audit.api_requests - API Request Logging (Optional, high volume)
-- =============================================================================

CREATE TABLE audit.api_requests (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Request info
    request_id VARCHAR(64) NOT NULL,
    method VARCHAR(10) NOT NULL,
    path VARCHAR(500) NOT NULL,
    query_params JSONB,

    -- Response info
    status_code INTEGER,
    response_time_ms INTEGER,
    response_size_bytes INTEGER,

    -- Auth
    user_id VARCHAR(100),
    agent_id BIGINT REFERENCES agent.agents(id) ON DELETE SET NULL,
    api_key_id VARCHAR(64),

    -- Client info
    ip_address INET,
    user_agent TEXT,

    -- Error (if applicable)
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_api_requests_timestamp ON audit.api_requests(created_at DESC);
CREATE INDEX idx_api_requests_path ON audit.api_requests(path);
CREATE INDEX idx_api_requests_user ON audit.api_requests(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_api_requests_errors ON audit.api_requests(status_code) WHERE status_code >= 400;

-- Consider partitioning by time for high-volume deployments
COMMENT ON TABLE audit.api_requests IS 'API request logging for analytics and debugging';

-- =============================================================================
-- audit.security_events - Security-specific Events
-- =============================================================================

CREATE TABLE audit.security_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Event info
    event_type VARCHAR(100) NOT NULL,  -- auth_failure, rate_limit, suspicious_activity, etc.
    severity VARCHAR(20) NOT NULL,  -- low, medium, high, critical

    -- Source
    agent_id BIGINT REFERENCES agent.agents(id) ON DELETE SET NULL,
    user_id VARCHAR(100),
    ip_address INET,

    -- Details
    message TEXT NOT NULL,
    details JSONB DEFAULT '{}',

    -- Action taken
    action_taken VARCHAR(100),  -- blocked, warned, logged, escalated

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_security_events_type ON audit.security_events(event_type);
CREATE INDEX idx_security_events_severity ON audit.security_events(severity) WHERE severity IN ('high', 'critical');
CREATE INDEX idx_security_events_ip ON audit.security_events(ip_address);
CREATE INDEX idx_security_events_timestamp ON audit.security_events(created_at DESC);

COMMENT ON TABLE audit.security_events IS 'Security-related events for monitoring';

-- =============================================================================
-- Helper Views
-- =============================================================================

-- Recent errors view
CREATE VIEW audit.recent_errors AS
SELECT
    l.id,
    l.created_at,
    l.category,
    l.action,
    l.message,
    l.details,
    a.name AS agent_name
FROM audit.logs l
LEFT JOIN agent.agents a ON l.agent_id = a.id
WHERE l.level IN ('error', 'critical')
    AND l.created_at > NOW() - INTERVAL '24 hours'
ORDER BY l.created_at DESC;

-- Open escalations view
CREATE VIEW audit.open_escalations AS
SELECT
    e.*,
    c.name AS circle_name,
    a.name AS agent_name
FROM audit.escalations e
LEFT JOIN circle.circles c ON e.circle_id = c.id
LEFT JOIN agent.agents a ON e.agent_id = a.id
WHERE e.status NOT IN ('resolved', 'dismissed')
ORDER BY e.priority, e.created_at;
