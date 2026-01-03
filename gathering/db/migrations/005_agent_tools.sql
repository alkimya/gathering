-- Agent Tools Migration
-- Version: 0.4.0
-- Description: Add agent tools/capabilities management

-- =============================================================================
-- SKILL DEFINITIONS
-- =============================================================================

-- Available skills (populated from SkillRegistry)
CREATE TABLE IF NOT EXISTS agent.skills (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100),
    description TEXT,
    category VARCHAR(50) DEFAULT 'general',  -- core, web, code, system, ai, productivity

    -- Permissions required
    required_permissions TEXT[] DEFAULT '{}',

    -- Metadata
    version VARCHAR(20) DEFAULT '1.0.0',
    is_dangerous BOOLEAN DEFAULT FALSE,  -- Requires extra confirmation
    is_enabled BOOLEAN DEFAULT TRUE,     -- Globally enabled/disabled

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_skills_category ON agent.skills(category);
CREATE INDEX idx_skills_enabled ON agent.skills(is_enabled) WHERE is_enabled = TRUE;

COMMENT ON TABLE agent.skills IS 'Available skills that can be assigned to agents';

-- =============================================================================
-- AGENT TOOLS (Skills assigned to agents)
-- =============================================================================

CREATE TABLE IF NOT EXISTS agent.agent_tools (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    agent_id BIGINT NOT NULL REFERENCES agent.agents(id) ON DELETE CASCADE,
    skill_id BIGINT NOT NULL REFERENCES agent.skills(id) ON DELETE CASCADE,

    -- Status
    is_enabled BOOLEAN DEFAULT TRUE,

    -- Configuration override per agent
    config JSONB DEFAULT '{}',

    -- Usage tracking
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(agent_id, skill_id)
);

CREATE INDEX idx_agent_tools_agent ON agent.agent_tools(agent_id);
CREATE INDEX idx_agent_tools_skill ON agent.agent_tools(skill_id);
CREATE INDEX idx_agent_tools_enabled ON agent.agent_tools(agent_id, is_enabled) WHERE is_enabled = TRUE;

CREATE TRIGGER update_agent_tools_updated_at
    BEFORE UPDATE ON agent.agent_tools
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

COMMENT ON TABLE agent.agent_tools IS 'Skills/tools assigned to each agent with enable/disable status';

-- =============================================================================
-- SEED DEFAULT SKILLS
-- =============================================================================

INSERT INTO agent.skills (name, display_name, description, category, required_permissions, is_dangerous) VALUES
-- Core Development
('git', 'Git', 'Repository management, commits, branches, PRs', 'core', ARRAY['git', 'read', 'write'], false),
('test', 'Test Runner', 'Execute tests and analyze coverage', 'core', ARRAY['execute', 'read'], false),
('filesystem', 'File System', 'Secure file operations', 'core', ARRAY['read', 'write'], false),
('code', 'Code Execution', 'Sandboxed code execution', 'code', ARRAY['execute'], true),
('analysis', 'Code Analysis', 'Static code analysis and linting', 'code', ARRAY['read'], false),

-- System
('shell', 'Shell', 'Execute shell commands', 'system', ARRAY['execute'], true),
('database', 'Database', 'Database queries and management', 'system', ARRAY['read', 'write', 'execute'], true),
('deploy', 'Deploy', 'Deployment operations', 'system', ARRAY['deploy'], true),

-- Web & Network
('web', 'Web Search', 'Search Google, Wikipedia, news', 'web', ARRAY['network'], false),
('scraper', 'Web Scraper', 'Extract data from websites', 'web', ARRAY['network'], false),
('http', 'HTTP Client', 'Make HTTP requests', 'web', ARRAY['network'], false),

-- AI & Analysis
('ai', 'AI/ML', 'AI and ML operations', 'ai', ARRAY['network', 'execute'], false),

-- Communication
('email', 'Email', 'Send and manage emails', 'communication', ARRAY['network'], false),
('notifications', 'Notifications', 'Send notifications', 'communication', ARRAY['network'], false),
('social', 'Social Media', 'Social media integrations', 'communication', ARRAY['network'], false),

-- Productivity
('calendar', 'Calendar', 'Calendar and scheduling', 'productivity', ARRAY['read', 'write'], false),
('docs', 'Documentation', 'Generate documentation', 'productivity', ARRAY['read', 'write'], false),

-- Media
('image', 'Image Processing', 'Image manipulation', 'media', ARRAY['read', 'write'], false),
('pdf', 'PDF', 'PDF handling', 'media', ARRAY['read', 'write'], false),

-- Cloud & Monitoring
('cloud', 'Cloud', 'Cloud provider operations', 'cloud', ARRAY['network', 'deploy'], true),
('monitoring', 'Monitoring', 'System monitoring', 'cloud', ARRAY['read'], false),

-- GatheRing System
('goals', 'Goals', 'Goal management', 'gathering', ARRAY['read', 'write'], false),
('pipelines', 'Pipelines', 'Pipeline management', 'gathering', ARRAY['read', 'write', 'execute'], false),
('tasks', 'Background Tasks', 'Background task management', 'gathering', ARRAY['read', 'write', 'execute'], false),
('schedules', 'Schedules', 'Schedule management', 'gathering', ARRAY['read', 'write'], false),
('circles', 'Circles', 'Circle/team management', 'gathering', ARRAY['read', 'write'], false),
('projects', 'Projects', 'Project management', 'gathering', ARRAY['read', 'write'], false)

ON CONFLICT (name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    category = EXCLUDED.category,
    required_permissions = EXCLUDED.required_permissions,
    is_dangerous = EXCLUDED.is_dangerous,
    updated_at = NOW();

-- =============================================================================
-- VIEW: Agent with enabled tools
-- =============================================================================

CREATE OR REPLACE VIEW agent.agent_tools_view AS
SELECT
    a.id AS agent_id,
    a.name AS agent_name,
    s.id AS skill_id,
    s.name AS skill_name,
    s.display_name AS skill_display_name,
    s.category AS skill_category,
    s.required_permissions,
    s.is_dangerous,
    COALESCE(at.is_enabled, false) AS is_enabled,
    COALESCE(at.usage_count, 0) AS usage_count,
    at.last_used_at,
    at.config AS custom_config
FROM agent.agents a
CROSS JOIN agent.skills s
LEFT JOIN agent.agent_tools at ON at.agent_id = a.id AND at.skill_id = s.id
WHERE s.is_enabled = true
ORDER BY a.id, s.category, s.name;

COMMENT ON VIEW agent.agent_tools_view IS 'Complete view of all skills for each agent with enabled status';
