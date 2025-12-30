-- GatheRing Database Migration
-- Migration 012: Background Tasks - Autonomous Agent Execution
-- Schema: circle

-- =============================================================================
-- ENUM: Background Task Status
-- =============================================================================

CREATE TYPE public.background_task_status AS ENUM (
    'pending',      -- Created but not started
    'running',      -- Currently executing
    'paused',       -- Paused by user or system
    'completed',    -- Successfully finished
    'failed',       -- Failed with error
    'cancelled',    -- Cancelled by user
    'timeout'       -- Exceeded max time
);

COMMENT ON TYPE public.background_task_status IS 'Status of a background task execution';

-- =============================================================================
-- circle.background_tasks - Long-running Autonomous Tasks
-- =============================================================================

CREATE TABLE circle.background_tasks (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Agent assignment (required)
    agent_id BIGINT NOT NULL REFERENCES agent.agents(id) ON DELETE CASCADE,

    -- Circle assignment (optional - agent can work independently)
    circle_id BIGINT REFERENCES circle.circles(id) ON DELETE SET NULL,

    -- Task definition
    goal TEXT NOT NULL,
    goal_context JSONB DEFAULT '{}',  -- Additional context for the goal

    -- Status
    status public.background_task_status DEFAULT 'pending',

    -- Execution limits
    max_steps INTEGER DEFAULT 50,
    timeout_seconds INTEGER DEFAULT 3600,  -- 1 hour default
    checkpoint_interval INTEGER DEFAULT 5,  -- Checkpoint every N steps

    -- Progress tracking
    current_step INTEGER DEFAULT 0,
    progress_percent INTEGER DEFAULT 0,
    progress_summary TEXT,
    last_action TEXT,

    -- Checkpointing (for recovery)
    checkpoint_data JSONB DEFAULT '{}',
    last_checkpoint_at TIMESTAMP WITH TIME ZONE,

    -- Results
    final_result TEXT,
    artifacts JSONB DEFAULT '[]',  -- Files created, data generated, etc.
    error_message TEXT,

    -- Metrics
    total_llm_calls INTEGER DEFAULT 0,
    total_tokens_used INTEGER DEFAULT 0,
    total_tool_calls INTEGER DEFAULT 0,

    -- Priority (for scheduling)
    priority public.task_priority DEFAULT 'medium',

    -- Created by
    created_by_user_id VARCHAR(100),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    paused_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_bg_tasks_agent ON circle.background_tasks(agent_id);
CREATE INDEX idx_bg_tasks_circle ON circle.background_tasks(circle_id) WHERE circle_id IS NOT NULL;
CREATE INDEX idx_bg_tasks_status ON circle.background_tasks(status);
CREATE INDEX idx_bg_tasks_running ON circle.background_tasks(agent_id, status) WHERE status = 'running';
CREATE INDEX idx_bg_tasks_pending ON circle.background_tasks(priority, created_at) WHERE status = 'pending';

-- Trigger
CREATE TRIGGER update_bg_tasks_updated_at
    BEFORE UPDATE ON circle.background_tasks
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

COMMENT ON TABLE circle.background_tasks IS 'Long-running autonomous tasks executed by agents';

-- =============================================================================
-- circle.background_task_steps - Step-by-Step Audit Trail
-- =============================================================================

CREATE TABLE circle.background_task_steps (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    task_id BIGINT NOT NULL REFERENCES circle.background_tasks(id) ON DELETE CASCADE,

    -- Step info
    step_number INTEGER NOT NULL,

    -- Action taken
    action_type VARCHAR(50) NOT NULL,  -- plan, execute, tool_call, memory_recall, memory_store, checkpoint, complete_check
    action_input TEXT,
    action_output TEXT,

    -- Tool usage (if action_type = 'tool_call')
    tool_name VARCHAR(100),
    tool_input JSONB,
    tool_output JSONB,
    tool_success BOOLEAN,

    -- LLM usage
    llm_model VARCHAR(100),
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,

    -- Performance
    duration_ms INTEGER,

    -- Status
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,

    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_bg_task_steps_task ON circle.background_task_steps(task_id, step_number);
CREATE INDEX idx_bg_task_steps_type ON circle.background_task_steps(task_id, action_type);

COMMENT ON TABLE circle.background_task_steps IS 'Detailed audit trail of each step in a background task';

-- =============================================================================
-- Views
-- =============================================================================

-- View: Active background tasks with agent info
CREATE OR REPLACE VIEW public.background_tasks_dashboard AS
SELECT
    bt.id,
    bt.agent_id,
    a.name as agent_name,
    p.display_name as agent_display_name,
    bt.circle_id,
    c.name as circle_name,
    bt.goal,
    bt.status,
    bt.current_step,
    bt.max_steps,
    bt.progress_percent,
    bt.progress_summary,
    bt.last_action,
    bt.priority,
    bt.total_llm_calls,
    bt.total_tokens_used,
    bt.total_tool_calls,
    bt.error_message,
    bt.created_at,
    bt.started_at,
    bt.completed_at,
    CASE
        WHEN bt.started_at IS NOT NULL AND bt.completed_at IS NULL
        THEN EXTRACT(EPOCH FROM (NOW() - bt.started_at))::INTEGER
        WHEN bt.started_at IS NOT NULL AND bt.completed_at IS NOT NULL
        THEN EXTRACT(EPOCH FROM (bt.completed_at - bt.started_at))::INTEGER
        ELSE 0
    END as duration_seconds
FROM circle.background_tasks bt
JOIN agent.agents a ON a.id = bt.agent_id
LEFT JOIN agent.personas p ON p.id = a.persona_id
LEFT JOIN circle.circles c ON c.id = bt.circle_id
ORDER BY
    CASE bt.status
        WHEN 'running' THEN 1
        WHEN 'pending' THEN 2
        WHEN 'paused' THEN 3
        ELSE 4
    END,
    bt.priority DESC,
    bt.created_at DESC;

COMMENT ON VIEW public.background_tasks_dashboard IS 'Dashboard view of background tasks with agent and circle info';

-- =============================================================================
-- Functions
-- =============================================================================

-- Function: Get task step count
CREATE OR REPLACE FUNCTION circle.get_task_step_count(p_task_id BIGINT)
RETURNS INTEGER AS $$
BEGIN
    RETURN (SELECT COUNT(*) FROM circle.background_task_steps WHERE task_id = p_task_id);
END;
$$ LANGUAGE plpgsql STABLE;

-- Function: Update task progress
CREATE OR REPLACE FUNCTION circle.update_task_progress(
    p_task_id BIGINT,
    p_progress_percent INTEGER,
    p_progress_summary TEXT DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    UPDATE circle.background_tasks
    SET
        progress_percent = p_progress_percent,
        progress_summary = COALESCE(p_progress_summary, progress_summary),
        updated_at = NOW()
    WHERE id = p_task_id;
END;
$$ LANGUAGE plpgsql;

-- Function: Record checkpoint
CREATE OR REPLACE FUNCTION circle.checkpoint_task(
    p_task_id BIGINT,
    p_checkpoint_data JSONB
)
RETURNS VOID AS $$
BEGIN
    UPDATE circle.background_tasks
    SET
        checkpoint_data = p_checkpoint_data,
        last_checkpoint_at = NOW(),
        updated_at = NOW()
    WHERE id = p_task_id;
END;
$$ LANGUAGE plpgsql;
