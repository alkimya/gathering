-- GatheRing Composite Indexes
-- Version: 1.0.0
-- Description: Additional composite indexes for improved query performance
--
-- These indexes optimize common query patterns identified during the audit.

-- =============================================================================
-- AGENT SCHEMA INDEXES
-- =============================================================================

-- Optimize goal queries by agent and status (common filter pattern)
CREATE INDEX IF NOT EXISTS idx_goals_agent_status
    ON agent.goals(agent_id, status);

-- Optimize goal queries for active goals by priority
CREATE INDEX IF NOT EXISTS idx_goals_status_priority
    ON agent.goals(status, priority DESC)
    WHERE status IN ('pending', 'active', 'blocked');

-- =============================================================================
-- CIRCLE SCHEMA INDEXES
-- =============================================================================

-- Optimize task queries by circle and status (dashboard views)
CREATE INDEX IF NOT EXISTS idx_tasks_circle_status
    ON circle.tasks(circle_id, status);

-- Optimize task queries by assigned agent and status
CREATE INDEX IF NOT EXISTS idx_tasks_assigned_status
    ON circle.tasks(assigned_agent_id, status)
    WHERE assigned_agent_id IS NOT NULL;

-- Optimize background task queries by status and creation time
CREATE INDEX IF NOT EXISTS idx_bg_tasks_status_created
    ON circle.background_tasks(status, created_at DESC);

-- Optimize scheduled actions by status and next run
CREATE INDEX IF NOT EXISTS idx_scheduled_status_next
    ON circle.scheduled_actions(status, next_run_at)
    WHERE status = 'active';

-- =============================================================================
-- MEMORY SCHEMA INDEXES
-- =============================================================================

-- Optimize memory queries by agent and type (common RAG pattern)
CREATE INDEX IF NOT EXISTS idx_memories_agent_type
    ON memory.memories(agent_id, memory_type);

-- Optimize memory queries by scope and type
CREATE INDEX IF NOT EXISTS idx_memories_scope_type
    ON memory.memories(scope, memory_type);

-- Optimize recent memories lookup
CREATE INDEX IF NOT EXISTS idx_memories_agent_created
    ON memory.memories(agent_id, created_at DESC);

-- =============================================================================
-- COMMUNICATION SCHEMA INDEXES
-- =============================================================================

-- Optimize conversation queries by circle and status
CREATE INDEX IF NOT EXISTS idx_conversations_circle_status
    ON communication.conversations(circle_id, status);

-- Optimize message queries by conversation and creation time
CREATE INDEX IF NOT EXISTS idx_messages_conversation_created
    ON communication.messages(conversation_id, created_at DESC);

-- Optimize chat history queries by agent and time
CREATE INDEX IF NOT EXISTS idx_chat_history_agent_created
    ON communication.chat_history(agent_id, created_at DESC);

-- =============================================================================
-- REVIEW SCHEMA INDEXES
-- =============================================================================

-- Optimize review queries by status and created time
CREATE INDEX IF NOT EXISTS idx_reviews_status_created
    ON review.reviews(status, created_at DESC);

-- =============================================================================
-- AUDIT SCHEMA INDEXES
-- =============================================================================

-- Optimize log queries by level and time (error monitoring)
CREATE INDEX IF NOT EXISTS idx_logs_level_created
    ON audit.logs(level, created_at DESC)
    WHERE level IN ('error', 'critical');

-- Optimize API request monitoring
CREATE INDEX IF NOT EXISTS idx_api_requests_path_created
    ON audit.api_requests(path, created_at DESC);

-- =============================================================================
-- STATISTICS UPDATE
-- =============================================================================

-- Refresh table statistics after index creation
ANALYZE agent.goals;
ANALYZE circle.tasks;
ANALYZE circle.background_tasks;
ANALYZE circle.scheduled_actions;
ANALYZE memory.memories;
ANALYZE communication.conversations;
ANALYZE communication.messages;
ANALYZE communication.chat_history;
ANALYZE review.reviews;
ANALYZE audit.logs;
ANALYZE audit.api_requests;
