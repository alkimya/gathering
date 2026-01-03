-- GatheRing Database Migration
-- Migration 009: Cross-schema Foreign Keys and Final Setup
-- Add foreign keys that reference tables in other schemas

-- =============================================================================
-- Agent Schema Foreign Keys
-- =============================================================================

-- agent.sessions references to other schemas
ALTER TABLE agent.sessions
    ADD CONSTRAINT fk_sessions_project
    FOREIGN KEY (project_id) REFERENCES project.projects(id) ON DELETE SET NULL;

ALTER TABLE agent.sessions
    ADD CONSTRAINT fk_sessions_current_task
    FOREIGN KEY (current_task_id) REFERENCES circle.tasks(id) ON DELETE SET NULL;

-- =============================================================================
-- Circle Schema Foreign Keys
-- =============================================================================

-- circle.tasks references to other schemas
ALTER TABLE circle.tasks
    ADD CONSTRAINT fk_tasks_project
    FOREIGN KEY (project_id) REFERENCES project.projects(id) ON DELETE SET NULL;

ALTER TABLE circle.tasks
    ADD CONSTRAINT fk_tasks_conversation
    FOREIGN KEY (conversation_id) REFERENCES communication.conversations(id) ON DELETE SET NULL;

-- =============================================================================
-- Communication Schema Foreign Keys
-- =============================================================================

-- communication.conversations references to other schemas
ALTER TABLE communication.conversations
    ADD CONSTRAINT fk_conversations_task
    FOREIGN KEY (task_id) REFERENCES circle.tasks(id) ON DELETE SET NULL;

-- =============================================================================
-- Audit Schema Foreign Keys
-- =============================================================================

-- audit.logs references to other schemas
ALTER TABLE audit.logs
    ADD CONSTRAINT fk_logs_task
    FOREIGN KEY (task_id) REFERENCES circle.tasks(id) ON DELETE SET NULL;

ALTER TABLE audit.logs
    ADD CONSTRAINT fk_logs_review
    FOREIGN KEY (review_id) REFERENCES review.reviews(id) ON DELETE SET NULL;

ALTER TABLE audit.logs
    ADD CONSTRAINT fk_logs_conversation
    FOREIGN KEY (conversation_id) REFERENCES communication.conversations(id) ON DELETE SET NULL;

-- audit.escalations references to other schemas
ALTER TABLE audit.escalations
    ADD CONSTRAINT fk_escalations_task
    FOREIGN KEY (task_id) REFERENCES circle.tasks(id) ON DELETE SET NULL;

ALTER TABLE audit.escalations
    ADD CONSTRAINT fk_escalations_review
    FOREIGN KEY (review_id) REFERENCES review.reviews(id) ON DELETE SET NULL;

-- =============================================================================
-- Cross-Schema Views
-- =============================================================================

-- Agent dashboard view
CREATE VIEW public.agent_dashboard AS
SELECT
    a.id,
    a.name,
    a.provider,
    a.model,
    a.status,
    a.is_active,
    a.tasks_completed,
    a.reviews_done,
    a.approval_rate,
    a.average_quality_score,
    a.last_active_at,
    (SELECT COUNT(*) FROM memory.memories m WHERE m.agent_id = a.id AND m.is_active = TRUE) AS memory_count,
    (SELECT COUNT(*) FROM communication.chat_history ch WHERE ch.agent_id = a.id) AS message_count,
    (SELECT COUNT(*) FROM circle.members cm WHERE cm.agent_id = a.id AND cm.is_active = TRUE) AS circle_count
FROM agent.agents a
WHERE a.is_active = TRUE;

-- Circle dashboard view
CREATE VIEW public.circle_dashboard AS
SELECT
    c.id,
    c.name,
    c.display_name,
    c.status,
    c.is_active,
    c.created_at,
    c.started_at,
    (SELECT COUNT(*) FROM circle.members m WHERE m.circle_id = c.id AND m.is_active = TRUE) AS agent_count,
    (SELECT COUNT(*) FROM circle.tasks t WHERE t.circle_id = c.id AND t.status NOT IN ('completed', 'cancelled')) AS active_tasks,
    (SELECT COUNT(*) FROM circle.tasks t WHERE t.circle_id = c.id AND t.status = 'completed') AS completed_tasks,
    (SELECT COUNT(*) FROM circle.conflicts cf WHERE cf.circle_id = c.id AND cf.status = 'open') AS open_conflicts,
    (SELECT COUNT(*) FROM communication.conversations cv WHERE cv.circle_id = c.id AND cv.status = 'active') AS active_conversations
FROM circle.circles c;

-- Task board view
CREATE VIEW public.task_board AS
SELECT
    t.id,
    t.title,
    t.description,
    t.task_type,
    t.priority,
    t.status,
    t.requires_review,
    t.created_at,
    t.started_at,
    t.completed_at,
    t.due_at,
    c.name AS circle_name,
    p.name AS project_name,
    a.name AS assigned_agent_name,
    (SELECT COUNT(*) FROM review.reviews r WHERE r.task_id = t.id) AS review_count
FROM circle.tasks t
LEFT JOIN circle.circles c ON t.circle_id = c.id
LEFT JOIN project.projects p ON t.project_id = p.id
LEFT JOIN agent.agents a ON t.assigned_agent_id = a.id;

-- Recent activity view
CREATE VIEW public.recent_activity AS
SELECT
    'event' AS source,
    e.id,
    e.event_type AS activity_type,
    e.data->>'title' AS title,
    e.created_at,
    c.name AS circle_name,
    a.name AS agent_name
FROM circle.events e
LEFT JOIN circle.circles c ON e.circle_id = c.id
LEFT JOIN agent.agents a ON e.source_agent_id = a.id
WHERE e.created_at > NOW() - INTERVAL '24 hours'

UNION ALL

SELECT
    'audit' AS source,
    l.id,
    l.action AS activity_type,
    l.message AS title,
    l.created_at,
    c.name AS circle_name,
    a.name AS agent_name
FROM audit.logs l
LEFT JOIN circle.circles c ON l.circle_id = c.id
LEFT JOIN agent.agents a ON l.agent_id = a.id
WHERE l.created_at > NOW() - INTERVAL '24 hours'
    AND l.level != 'debug'

ORDER BY created_at DESC
LIMIT 100;

-- =============================================================================
-- Grant Permissions (example for application role)
-- =============================================================================

-- Create application role if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'gathering_app') THEN
        CREATE ROLE gathering_app WITH LOGIN PASSWORD 'changeme';
    END IF;
END $$;

-- Grant usage on all schemas
GRANT USAGE ON SCHEMA agent, circle, project, communication, memory, review, audit TO gathering_app;

-- Grant all privileges on all tables in each schema
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA agent TO gathering_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA circle TO gathering_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA project TO gathering_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA communication TO gathering_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA memory TO gathering_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA review TO gathering_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA audit TO gathering_app;

-- Grant usage on all sequences
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA agent TO gathering_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA circle TO gathering_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA project TO gathering_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA communication TO gathering_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA memory TO gathering_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA review TO gathering_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA audit TO gathering_app;

-- Grant execute on functions
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA memory TO gathering_app;
GRANT EXECUTE ON FUNCTION public.update_updated_at() TO gathering_app;

-- Grant select on views
GRANT SELECT ON public.agent_dashboard TO gathering_app;
GRANT SELECT ON public.circle_dashboard TO gathering_app;
GRANT SELECT ON public.task_board TO gathering_app;
GRANT SELECT ON public.recent_activity TO gathering_app;
GRANT SELECT ON audit.recent_errors TO gathering_app;
GRANT SELECT ON audit.open_escalations TO gathering_app;

-- =============================================================================
-- Migration Tracking (handled by setup.py, kept for standalone SQL execution)
-- =============================================================================

-- Note: When using `python -m gathering.db.setup`, migrations are tracked
-- automatically. This section is only for direct SQL execution.

-- CREATE TABLE IF NOT EXISTS public.migrations (
--     id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
--     version VARCHAR(50) NOT NULL UNIQUE,
--     name VARCHAR(200) NOT NULL,
--     applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
-- );
--
-- INSERT INTO public.migrations (version, name) VALUES ... ON CONFLICT DO NOTHING;
