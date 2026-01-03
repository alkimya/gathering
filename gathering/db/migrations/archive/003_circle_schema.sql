-- GatheRing Database Migration
-- Migration 003: Circle schema - Orchestration
-- Schema: circle

-- =============================================================================
-- circle.circles - Gathering Circles (Teams)
-- =============================================================================

CREATE TABLE circle.circles (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200),
    description TEXT,

    -- Owner (human user who created the circle)
    owner_id VARCHAR(100),

    -- Circle settings
    settings JSONB DEFAULT '{}',

    -- Review policy
    require_review BOOLEAN DEFAULT TRUE,
    min_reviewers INTEGER DEFAULT 1,
    auto_assign_reviewer BOOLEAN DEFAULT TRUE,
    self_review_allowed BOOLEAN DEFAULT FALSE,
    escalate_on_reject BOOLEAN DEFAULT TRUE,
    review_policy JSONB DEFAULT '{}',

    -- Routing
    auto_route BOOLEAN DEFAULT TRUE,

    -- Status
    status public.circle_status DEFAULT 'stopped',
    is_active BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    stopped_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_circles_status ON circle.circles(status) WHERE is_active = TRUE;
CREATE INDEX idx_circles_name ON circle.circles(name);

-- Trigger
CREATE TRIGGER update_circles_updated_at
    BEFORE UPDATE ON circle.circles
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

COMMENT ON TABLE circle.circles IS 'Gathering Circles - teams of agents working together';

-- =============================================================================
-- circle.members - Circle Membership
-- =============================================================================

CREATE TABLE circle.members (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    circle_id BIGINT NOT NULL REFERENCES circle.circles(id) ON DELETE CASCADE,
    agent_id BIGINT NOT NULL REFERENCES agent.agents(id) ON DELETE CASCADE,

    -- Membership info
    role public.agent_role DEFAULT 'member',
    permissions JSONB DEFAULT '{}',

    -- Agent config override for this circle
    competencies TEXT[] DEFAULT '{}',
    can_review TEXT[] DEFAULT '{}',

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Timestamps
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    left_at TIMESTAMP WITH TIME ZONE,

    UNIQUE(circle_id, agent_id)
);

-- Indexes
CREATE INDEX idx_members_circle ON circle.members(circle_id) WHERE is_active = TRUE;
CREATE INDEX idx_members_agent ON circle.members(agent_id);

COMMENT ON TABLE circle.members IS 'Circle membership with roles and permissions';

-- =============================================================================
-- circle.tasks - Task Board
-- =============================================================================

CREATE TABLE circle.tasks (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    circle_id BIGINT NOT NULL REFERENCES circle.circles(id) ON DELETE CASCADE,
    project_id BIGINT,  -- References project.projects(id)

    -- Task details
    title VARCHAR(200) NOT NULL,
    description TEXT,
    task_type VARCHAR(50) DEFAULT 'general',  -- code, docs, test, review, refactor

    -- Priority and status
    priority public.task_priority DEFAULT 'medium',
    status public.task_status DEFAULT 'pending',

    -- Required competencies to claim this task
    required_competencies TEXT[] DEFAULT '{}',

    -- Review requirement
    requires_review BOOLEAN DEFAULT TRUE,
    review_types TEXT[] DEFAULT '{"quality"}',

    -- Context
    context JSONB DEFAULT '{}',

    -- Results
    result TEXT,
    artifacts JSONB DEFAULT '[]',
    files_modified TEXT[] DEFAULT '{}',

    -- Assignment
    assigned_agent_id BIGINT REFERENCES agent.agents(id) ON DELETE SET NULL,

    -- Relationships
    parent_task_id BIGINT REFERENCES circle.tasks(id) ON DELETE SET NULL,
    conversation_id BIGINT,  -- References communication.conversations(id)

    -- Created by
    created_by_agent_id BIGINT REFERENCES agent.agents(id) ON DELETE SET NULL,
    created_by_user_id VARCHAR(100),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    due_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_tasks_circle ON circle.tasks(circle_id);
CREATE INDEX idx_tasks_status ON circle.tasks(status);
CREATE INDEX idx_tasks_priority ON circle.tasks(priority) WHERE status NOT IN ('completed', 'cancelled');
CREATE INDEX idx_tasks_assigned ON circle.tasks(assigned_agent_id) WHERE assigned_agent_id IS NOT NULL;
CREATE INDEX idx_tasks_competencies ON circle.tasks USING GIN(required_competencies);

-- Trigger
CREATE TRIGGER update_tasks_updated_at
    BEFORE UPDATE ON circle.tasks
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

COMMENT ON TABLE circle.tasks IS 'Task board for circle work items';

-- =============================================================================
-- circle.task_assignments - Task Assignment History
-- =============================================================================

CREATE TABLE circle.task_assignments (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    task_id BIGINT NOT NULL REFERENCES circle.tasks(id) ON DELETE CASCADE,
    agent_id BIGINT NOT NULL REFERENCES agent.agents(id) ON DELETE CASCADE,

    -- Assignment type
    assignment_role VARCHAR(50) DEFAULT 'assignee',  -- assignee, helper, reviewer

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Timestamps
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,

    UNIQUE(task_id, agent_id, assignment_role)
);

-- Indexes
CREATE INDEX idx_task_assignments_task ON circle.task_assignments(task_id);
CREATE INDEX idx_task_assignments_agent ON circle.task_assignments(agent_id) WHERE is_active = TRUE;

COMMENT ON TABLE circle.task_assignments IS 'History of task assignments to agents';

-- =============================================================================
-- circle.conflicts - Conflict Detection
-- =============================================================================

CREATE TABLE circle.conflicts (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    circle_id BIGINT NOT NULL REFERENCES circle.circles(id) ON DELETE CASCADE,

    -- Conflict type
    conflict_type VARCHAR(50) NOT NULL,  -- file_collision, task_deadlock, resource_contention, opinion_divergence

    -- Involved parties
    agent_ids BIGINT[] NOT NULL,
    task_ids BIGINT[],
    file_paths TEXT[],

    -- Conflict details
    description TEXT NOT NULL,
    context JSONB DEFAULT '{}',

    -- Resolution
    status VARCHAR(20) DEFAULT 'open',  -- open, in_progress, resolved, escalated
    resolution TEXT,
    resolved_by_agent_id BIGINT REFERENCES agent.agents(id),
    resolved_by_user_id VARCHAR(100),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_conflicts_circle ON circle.conflicts(circle_id);
CREATE INDEX idx_conflicts_status ON circle.conflicts(status) WHERE status != 'resolved';

COMMENT ON TABLE circle.conflicts IS 'Detected conflicts between agents';

-- =============================================================================
-- circle.events - Circle Events (Pub/Sub)
-- =============================================================================

CREATE TABLE circle.events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    circle_id BIGINT REFERENCES circle.circles(id) ON DELETE CASCADE,

    -- Event info
    event_type VARCHAR(100) NOT NULL,  -- agent.joined, task.completed, review.approved, etc.
    source_agent_id BIGINT REFERENCES agent.agents(id) ON DELETE SET NULL,

    -- Event data
    data JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_events_circle ON circle.events(circle_id, created_at DESC);
CREATE INDEX idx_events_type ON circle.events(event_type);

-- Partition by time for better performance (optional, for high-volume)
-- Consider partitioning by month if events grow large

COMMENT ON TABLE circle.events IS 'Event log for circle pub/sub system';
