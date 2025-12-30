-- Migration 013: Scheduled Actions
-- Adds cron-like scheduling for agents to execute recurring tasks

-- Enum for schedule status
DO $$ BEGIN
    CREATE TYPE scheduled_action_status AS ENUM (
        'active',      -- Schedule is active
        'paused',      -- Temporarily paused
        'disabled',    -- Disabled by user
        'expired'      -- Past end_date
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Enum for schedule type
DO $$ BEGIN
    CREATE TYPE schedule_type AS ENUM (
        'cron',        -- Cron expression (e.g., "0 9 * * *")
        'interval',    -- Fixed interval (e.g., every 30 minutes)
        'once',        -- One-time scheduled execution
        'event'        -- Triggered by an event
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Main scheduled actions table
CREATE TABLE IF NOT EXISTS circle.scheduled_actions (
    id SERIAL PRIMARY KEY,

    -- What to execute
    agent_id INTEGER NOT NULL REFERENCES agent.agents(id) ON DELETE CASCADE,
    circle_id INTEGER REFERENCES circle.circles(id) ON DELETE SET NULL,

    -- Schedule definition
    name VARCHAR(255) NOT NULL,
    description TEXT,
    schedule_type schedule_type NOT NULL DEFAULT 'cron',
    cron_expression VARCHAR(100),           -- For cron type: "0 9 * * MON-FRI"
    interval_seconds INTEGER,               -- For interval type
    event_trigger VARCHAR(100),             -- For event type: event name to listen for

    -- Task to execute
    goal TEXT NOT NULL,                     -- The goal/prompt for the agent
    max_steps INTEGER DEFAULT 50,
    timeout_seconds INTEGER DEFAULT 3600,

    -- Constraints
    status scheduled_action_status NOT NULL DEFAULT 'active',
    start_date TIMESTAMPTZ DEFAULT NOW(),
    end_date TIMESTAMPTZ,                   -- NULL = no end date
    max_executions INTEGER,                 -- NULL = unlimited
    execution_count INTEGER DEFAULT 0,

    -- Behavior
    retry_on_failure BOOLEAN DEFAULT true,
    max_retries INTEGER DEFAULT 3,
    retry_delay_seconds INTEGER DEFAULT 300,
    allow_concurrent BOOLEAN DEFAULT false, -- Allow overlapping executions

    -- Metadata
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_by VARCHAR(100),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_run_at TIMESTAMPTZ,
    next_run_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT valid_cron_or_interval CHECK (
        (schedule_type = 'cron' AND cron_expression IS NOT NULL) OR
        (schedule_type = 'interval' AND interval_seconds IS NOT NULL AND interval_seconds > 0) OR
        (schedule_type = 'once' AND next_run_at IS NOT NULL) OR
        (schedule_type = 'event' AND event_trigger IS NOT NULL)
    ),
    CONSTRAINT valid_max_executions CHECK (max_executions IS NULL OR max_executions > 0),
    CONSTRAINT valid_interval CHECK (interval_seconds IS NULL OR interval_seconds >= 60)
);

-- Execution history for scheduled actions
CREATE TABLE IF NOT EXISTS circle.scheduled_action_runs (
    id SERIAL PRIMARY KEY,
    scheduled_action_id INTEGER NOT NULL REFERENCES circle.scheduled_actions(id) ON DELETE CASCADE,
    background_task_id INTEGER REFERENCES circle.background_tasks(id) ON DELETE SET NULL,

    -- Execution details
    run_number INTEGER NOT NULL,
    triggered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    triggered_by VARCHAR(50) DEFAULT 'scheduler',  -- 'scheduler', 'manual', 'event'

    -- Status
    status background_task_status NOT NULL DEFAULT 'pending',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- Results
    result_summary TEXT,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,

    -- Metrics
    duration_ms INTEGER,
    steps_executed INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_scheduled_actions_agent
    ON circle.scheduled_actions(agent_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_actions_circle
    ON circle.scheduled_actions(circle_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_actions_status
    ON circle.scheduled_actions(status);
CREATE INDEX IF NOT EXISTS idx_scheduled_actions_next_run
    ON circle.scheduled_actions(next_run_at) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_scheduled_actions_event
    ON circle.scheduled_actions(event_trigger) WHERE schedule_type = 'event' AND status = 'active';
CREATE INDEX IF NOT EXISTS idx_scheduled_action_runs_action
    ON circle.scheduled_action_runs(scheduled_action_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_action_runs_status
    ON circle.scheduled_action_runs(status);

-- View for dashboard
CREATE OR REPLACE VIEW public.scheduled_actions_dashboard AS
SELECT
    sa.id,
    sa.name,
    sa.description,
    sa.schedule_type,
    sa.cron_expression,
    sa.interval_seconds,
    sa.event_trigger,
    sa.goal,
    sa.status,
    sa.execution_count,
    sa.max_executions,
    sa.last_run_at,
    sa.next_run_at,
    sa.allow_concurrent,
    sa.tags,
    sa.created_at,
    a.name as agent_name,
    a.id as agent_id,
    c.name as circle_name,
    -- Last run info
    lr.status as last_run_status,
    lr.duration_ms as last_run_duration,
    lr.result_summary as last_run_result,
    -- Stats
    (SELECT COUNT(*) FROM circle.scheduled_action_runs WHERE scheduled_action_id = sa.id AND status = 'completed') as successful_runs,
    (SELECT COUNT(*) FROM circle.scheduled_action_runs WHERE scheduled_action_id = sa.id AND status = 'failed') as failed_runs
FROM circle.scheduled_actions sa
JOIN agent.agents a ON sa.agent_id = a.id
LEFT JOIN circle.circles c ON sa.circle_id = c.id
LEFT JOIN LATERAL (
    SELECT status, duration_ms, result_summary
    FROM circle.scheduled_action_runs
    WHERE scheduled_action_id = sa.id
    ORDER BY triggered_at DESC
    LIMIT 1
) lr ON true;

-- Function to calculate next run time from cron expression
-- Note: Full cron parsing would need a Python library, this is a placeholder
CREATE OR REPLACE FUNCTION circle.calculate_next_run(
    p_schedule_type schedule_type,
    p_cron_expression VARCHAR(100),
    p_interval_seconds INTEGER,
    p_last_run TIMESTAMPTZ DEFAULT NULL
) RETURNS TIMESTAMPTZ AS $$
DECLARE
    v_now TIMESTAMPTZ := NOW();
    v_base TIMESTAMPTZ;
BEGIN
    v_base := COALESCE(p_last_run, v_now);

    IF p_schedule_type = 'interval' THEN
        -- Simple interval calculation
        RETURN v_base + (p_interval_seconds || ' seconds')::INTERVAL;
    ELSIF p_schedule_type = 'cron' THEN
        -- Placeholder: Return 1 hour from now (actual parsing done in Python)
        RETURN v_now + INTERVAL '1 hour';
    ELSE
        RETURN NULL;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update next_run_at after execution
CREATE OR REPLACE FUNCTION circle.update_scheduled_action_after_run()
RETURNS TRIGGER AS $$
BEGIN
    -- Update the scheduled action
    UPDATE circle.scheduled_actions
    SET
        execution_count = execution_count + 1,
        last_run_at = NEW.triggered_at,
        next_run_at = CASE
            WHEN schedule_type = 'once' THEN NULL
            WHEN schedule_type = 'interval' THEN NEW.triggered_at + (interval_seconds || ' seconds')::INTERVAL
            -- Cron calculated in application
            ELSE next_run_at
        END,
        status = CASE
            WHEN schedule_type = 'once' THEN 'expired'::scheduled_action_status
            WHEN max_executions IS NOT NULL AND execution_count + 1 >= max_executions THEN 'expired'::scheduled_action_status
            WHEN end_date IS NOT NULL AND NOW() > end_date THEN 'expired'::scheduled_action_status
            ELSE status
        END,
        updated_at = NOW()
    WHERE id = NEW.scheduled_action_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_scheduled_action_run_insert
    AFTER INSERT ON circle.scheduled_action_runs
    FOR EACH ROW
    EXECUTE FUNCTION circle.update_scheduled_action_after_run();

-- Create update_timestamp function if not exists
CREATE OR REPLACE FUNCTION public.update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Auto-update timestamp
CREATE TRIGGER trg_scheduled_actions_updated
    BEFORE UPDATE ON circle.scheduled_actions
    FOR EACH ROW
    EXECUTE FUNCTION public.update_timestamp();

COMMENT ON TABLE circle.scheduled_actions IS 'Cron-like scheduling for agent tasks';
COMMENT ON TABLE circle.scheduled_action_runs IS 'Execution history for scheduled actions';
COMMENT ON VIEW public.scheduled_actions_dashboard IS 'Dashboard view for scheduled actions with agent info and stats';
