-- Migration 014: Agent Goals
-- Adds long-term goal management with hierarchical decomposition

-- Enum for goal status
DO $$ BEGIN
    CREATE TYPE goal_status AS ENUM (
        'pending',      -- Not yet started
        'active',       -- Currently being worked on
        'blocked',      -- Waiting on something
        'paused',       -- Temporarily paused
        'completed',    -- Successfully achieved
        'failed',       -- Could not be achieved
        'cancelled'     -- Cancelled by user
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Enum for goal priority
DO $$ BEGIN
    CREATE TYPE goal_priority AS ENUM (
        'low',
        'medium',
        'high',
        'critical'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Main goals table with hierarchical structure
CREATE TABLE IF NOT EXISTS agent.goals (
    id SERIAL PRIMARY KEY,

    -- Ownership
    agent_id INTEGER NOT NULL REFERENCES agent.agents(id) ON DELETE CASCADE,
    circle_id INTEGER REFERENCES circle.circles(id) ON DELETE SET NULL,

    -- Hierarchy (self-referencing for subgoals)
    parent_id INTEGER REFERENCES agent.goals(id) ON DELETE CASCADE,
    depth INTEGER DEFAULT 0,  -- 0 = root goal, 1 = subgoal, etc.

    -- Goal definition
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    success_criteria TEXT,  -- How do we know when it's done?
    context JSONB DEFAULT '{}',  -- Additional context for the agent

    -- Status and priority
    status goal_status NOT NULL DEFAULT 'pending',
    priority goal_priority NOT NULL DEFAULT 'medium',
    progress_percent INTEGER DEFAULT 0 CHECK (progress_percent >= 0 AND progress_percent <= 100),
    status_message TEXT,  -- Current status explanation

    -- Timing
    deadline TIMESTAMPTZ,
    estimated_hours DECIMAL(6,2),
    actual_hours DECIMAL(6,2) DEFAULT 0,

    -- Decomposition
    is_decomposed BOOLEAN DEFAULT false,
    decomposition_strategy VARCHAR(50),  -- 'manual', 'auto', 'hybrid'
    max_subgoals INTEGER DEFAULT 5,

    -- Execution
    background_task_id INTEGER REFERENCES circle.background_tasks(id) ON DELETE SET NULL,
    last_worked_at TIMESTAMPTZ,
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,

    -- Results
    result_summary TEXT,
    artifacts JSONB DEFAULT '[]',  -- Files, outputs, etc.
    lessons_learned TEXT,

    -- Metadata
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_by VARCHAR(100),  -- 'user', 'agent', 'system'

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

-- Goal dependencies (blocked by other goals)
CREATE TABLE IF NOT EXISTS agent.goal_dependencies (
    id SERIAL PRIMARY KEY,
    goal_id INTEGER NOT NULL REFERENCES agent.goals(id) ON DELETE CASCADE,
    depends_on_id INTEGER NOT NULL REFERENCES agent.goals(id) ON DELETE CASCADE,
    dependency_type VARCHAR(50) DEFAULT 'blocks',  -- 'blocks', 'informs', 'enhances'
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT no_self_dependency CHECK (goal_id != depends_on_id),
    UNIQUE(goal_id, depends_on_id)
);

-- Goal activity log
CREATE TABLE IF NOT EXISTS agent.goal_activities (
    id SERIAL PRIMARY KEY,
    goal_id INTEGER NOT NULL REFERENCES agent.goals(id) ON DELETE CASCADE,

    activity_type VARCHAR(50) NOT NULL,  -- 'status_change', 'progress', 'note', 'decomposed', 'attempt'
    description TEXT,
    old_value TEXT,
    new_value TEXT,

    -- Who made this change
    actor_type VARCHAR(20),  -- 'agent', 'user', 'system'
    actor_id INTEGER,

    -- Metrics for this activity
    tokens_used INTEGER DEFAULT 0,
    duration_ms INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_goals_agent ON agent.goals(agent_id);
CREATE INDEX IF NOT EXISTS idx_goals_parent ON agent.goals(parent_id);
CREATE INDEX IF NOT EXISTS idx_goals_status ON agent.goals(status);
CREATE INDEX IF NOT EXISTS idx_goals_priority ON agent.goals(priority);
CREATE INDEX IF NOT EXISTS idx_goals_circle ON agent.goals(circle_id);
CREATE INDEX IF NOT EXISTS idx_goals_deadline ON agent.goals(deadline) WHERE deadline IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_goal_deps_goal ON agent.goal_dependencies(goal_id);
CREATE INDEX IF NOT EXISTS idx_goal_deps_depends ON agent.goal_dependencies(depends_on_id);
CREATE INDEX IF NOT EXISTS idx_goal_activities_goal ON agent.goal_activities(goal_id);

-- View for dashboard with hierarchy info
CREATE OR REPLACE VIEW public.goals_dashboard AS
WITH RECURSIVE goal_tree AS (
    -- Root goals
    SELECT
        g.*,
        g.title as path,
        1 as tree_depth,
        ARRAY[g.id] as ancestors
    FROM agent.goals g
    WHERE g.parent_id IS NULL

    UNION ALL

    -- Child goals
    SELECT
        g.*,
        gt.path || ' > ' || g.title,
        gt.tree_depth + 1,
        gt.ancestors || g.id
    FROM agent.goals g
    JOIN goal_tree gt ON g.parent_id = gt.id
)
SELECT
    gt.id,
    gt.agent_id,
    gt.circle_id,
    gt.parent_id,
    gt.depth,
    gt.title,
    gt.description,
    gt.success_criteria,
    gt.status,
    gt.priority,
    gt.progress_percent,
    gt.status_message,
    gt.deadline,
    gt.is_decomposed,
    gt.background_task_id,
    gt.attempts,
    gt.result_summary,
    gt.tags,
    gt.created_at,
    gt.started_at,
    gt.completed_at,
    gt.path,
    gt.tree_depth,
    gt.ancestors,
    a.name as agent_name,
    p.display_name as agent_display_name,
    c.name as circle_name,
    -- Subgoal stats
    (SELECT COUNT(*) FROM agent.goals WHERE parent_id = gt.id) as subgoal_count,
    (SELECT COUNT(*) FROM agent.goals WHERE parent_id = gt.id AND status = 'completed') as completed_subgoals,
    -- Dependency info
    (SELECT COUNT(*) FROM agent.goal_dependencies WHERE goal_id = gt.id) as dependency_count,
    (SELECT COUNT(*) FROM agent.goal_dependencies gd
     JOIN agent.goals dep ON dep.id = gd.depends_on_id
     WHERE gd.goal_id = gt.id AND dep.status != 'completed') as blocking_count
FROM goal_tree gt
JOIN agent.agents a ON a.id = gt.agent_id
LEFT JOIN agent.personas p ON p.id = a.persona_id
LEFT JOIN circle.circles c ON c.id = gt.circle_id;

-- Function to calculate goal progress from subgoals
CREATE OR REPLACE FUNCTION agent.calculate_goal_progress(p_goal_id INTEGER)
RETURNS INTEGER AS $$
DECLARE
    v_subgoal_count INTEGER;
    v_total_progress INTEGER;
BEGIN
    SELECT COUNT(*), COALESCE(SUM(progress_percent), 0)
    INTO v_subgoal_count, v_total_progress
    FROM agent.goals
    WHERE parent_id = p_goal_id;

    IF v_subgoal_count = 0 THEN
        RETURN (SELECT progress_percent FROM agent.goals WHERE id = p_goal_id);
    END IF;

    RETURN v_total_progress / v_subgoal_count;
END;
$$ LANGUAGE plpgsql;

-- Function to check if goal is blocked by dependencies
CREATE OR REPLACE FUNCTION agent.is_goal_blocked(p_goal_id INTEGER)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1
        FROM agent.goal_dependencies gd
        JOIN agent.goals dep ON dep.id = gd.depends_on_id
        WHERE gd.goal_id = p_goal_id
          AND gd.dependency_type = 'blocks'
          AND dep.status NOT IN ('completed', 'cancelled')
    );
END;
$$ LANGUAGE plpgsql;

-- Trigger to update parent progress when subgoal changes
CREATE OR REPLACE FUNCTION agent.update_parent_goal_progress()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.parent_id IS NOT NULL THEN
        UPDATE agent.goals
        SET
            progress_percent = agent.calculate_goal_progress(NEW.parent_id),
            updated_at = NOW()
        WHERE id = NEW.parent_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_goal_progress_update
    AFTER UPDATE OF progress_percent, status ON agent.goals
    FOR EACH ROW
    EXECUTE FUNCTION agent.update_parent_goal_progress();

-- Trigger to log status changes
CREATE OR REPLACE FUNCTION agent.log_goal_status_change()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        INSERT INTO agent.goal_activities (goal_id, activity_type, old_value, new_value, actor_type)
        VALUES (NEW.id, 'status_change', OLD.status::TEXT, NEW.status::TEXT, 'system');

        -- Update timestamps based on status
        IF NEW.status = 'active' AND OLD.status = 'pending' THEN
            NEW.started_at = NOW();
        ELSIF NEW.status IN ('completed', 'failed', 'cancelled') THEN
            NEW.completed_at = NOW();
        END IF;
    END IF;

    IF OLD.progress_percent IS DISTINCT FROM NEW.progress_percent THEN
        INSERT INTO agent.goal_activities (goal_id, activity_type, old_value, new_value, actor_type)
        VALUES (NEW.id, 'progress', OLD.progress_percent::TEXT, NEW.progress_percent::TEXT, 'system');
    END IF;

    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_goal_status_log
    BEFORE UPDATE ON agent.goals
    FOR EACH ROW
    EXECUTE FUNCTION agent.log_goal_status_change();

-- Auto-update timestamp
CREATE TRIGGER trg_goals_updated
    BEFORE UPDATE ON agent.goals
    FOR EACH ROW
    EXECUTE FUNCTION public.update_timestamp();

COMMENT ON TABLE agent.goals IS 'Agent goals with hierarchical decomposition support';
COMMENT ON TABLE agent.goal_dependencies IS 'Dependencies between goals (blocking relationships)';
COMMENT ON TABLE agent.goal_activities IS 'Activity log for goal changes and progress';
COMMENT ON VIEW public.goals_dashboard IS 'Dashboard view for goals with hierarchy and stats';
