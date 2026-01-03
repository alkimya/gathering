-- GatheRing Database Migration
-- Migration 005: Communication schema - Conversations & Messages
-- Schema: communication

-- =============================================================================
-- communication.conversations - Conversation Threads
-- =============================================================================

CREATE TABLE communication.conversations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Context
    circle_id BIGINT REFERENCES circle.circles(id) ON DELETE SET NULL,
    project_id BIGINT REFERENCES project.projects(id) ON DELETE SET NULL,
    task_id BIGINT,  -- References circle.tasks(id)

    -- Conversation metadata
    topic VARCHAR(500),
    conversation_type VARCHAR(50) DEFAULT 'chat',  -- chat, review, collaboration, brainstorm

    -- Participants
    participant_agent_ids BIGINT[] DEFAULT '{}',
    participant_names TEXT[] DEFAULT '{}',

    -- Configuration
    max_turns INTEGER DEFAULT 20,
    turn_strategy VARCHAR(50) DEFAULT 'round_robin',  -- round_robin, mention_based, free_form
    initial_prompt TEXT,

    -- Status
    status public.conversation_status DEFAULT 'pending',
    turns_taken INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,

    -- Results
    summary TEXT,
    conclusion TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    last_message_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_conversations_circle ON communication.conversations(circle_id);
CREATE INDEX idx_conversations_status ON communication.conversations(status) WHERE is_active = TRUE;
CREATE INDEX idx_conversations_participants ON communication.conversations USING GIN(participant_agent_ids);

-- Trigger
CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON communication.conversations
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

COMMENT ON TABLE communication.conversations IS 'Conversation threads between agents';

-- =============================================================================
-- communication.messages - Individual Messages
-- =============================================================================

CREATE TABLE communication.messages (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conversation_id BIGINT NOT NULL REFERENCES communication.conversations(id) ON DELETE CASCADE,

    -- Author
    role public.message_role NOT NULL,
    agent_id BIGINT REFERENCES agent.agents(id) ON DELETE SET NULL,
    agent_name VARCHAR(100),
    user_id VARCHAR(100),

    -- Content
    content TEXT NOT NULL,

    -- Mentions (for @agent notifications)
    mentions TEXT[] DEFAULT '{}',
    mentioned_agent_ids BIGINT[] DEFAULT '{}',

    -- Tool usage
    tool_calls JSONB,
    tool_results JSONB,

    -- Metrics
    model_used VARCHAR(100),
    tokens_input INTEGER,
    tokens_output INTEGER,
    thinking_time_ms INTEGER,

    -- Threading
    parent_message_id BIGINT REFERENCES communication.messages(id) ON DELETE SET NULL,
    reply_count INTEGER DEFAULT 0,

    -- Flags
    is_pinned BOOLEAN DEFAULT FALSE,
    is_sensitive BOOLEAN DEFAULT FALSE,
    is_broadcast BOOLEAN DEFAULT FALSE,
    is_system BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    edited_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_messages_conversation ON communication.messages(conversation_id, created_at);
CREATE INDEX idx_messages_agent ON communication.messages(agent_id) WHERE agent_id IS NOT NULL;
CREATE INDEX idx_messages_mentions ON communication.messages USING GIN(mentioned_agent_ids) WHERE mentioned_agent_ids != '{}';

COMMENT ON TABLE communication.messages IS 'Individual messages in conversations';

-- =============================================================================
-- communication.chat_history - Agent Chat History (outside conversations)
-- =============================================================================

CREATE TABLE communication.chat_history (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    agent_id BIGINT NOT NULL REFERENCES agent.agents(id) ON DELETE CASCADE,
    session_id BIGINT REFERENCES agent.sessions(id) ON DELETE SET NULL,

    -- Message
    role public.message_role NOT NULL,
    content TEXT NOT NULL,

    -- User info (if user message)
    user_id VARCHAR(100),

    -- Metrics
    model_used VARCHAR(100),
    tokens_input INTEGER,
    tokens_output INTEGER,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_chat_history_agent ON communication.chat_history(agent_id, created_at DESC);
CREATE INDEX idx_chat_history_session ON communication.chat_history(session_id) WHERE session_id IS NOT NULL;

COMMENT ON TABLE communication.chat_history IS 'Direct chat history with agents';

-- =============================================================================
-- communication.notifications - Agent Notifications
-- =============================================================================

CREATE TABLE communication.notifications (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    agent_id BIGINT NOT NULL REFERENCES agent.agents(id) ON DELETE CASCADE,

    -- Notification info
    notification_type VARCHAR(50) NOT NULL,  -- mention, task_assigned, review_requested, etc.
    title VARCHAR(200) NOT NULL,
    message TEXT,

    -- Source
    source_agent_id BIGINT REFERENCES agent.agents(id) ON DELETE SET NULL,
    source_type VARCHAR(50),  -- conversation, task, review
    source_id BIGINT,

    -- Status
    is_read BOOLEAN DEFAULT FALSE,
    is_dismissed BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    read_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_notifications_agent ON communication.notifications(agent_id) WHERE NOT is_dismissed;
CREATE INDEX idx_notifications_unread ON communication.notifications(agent_id) WHERE NOT is_read AND NOT is_dismissed;

COMMENT ON TABLE communication.notifications IS 'Agent notifications for mentions, tasks, etc.';
