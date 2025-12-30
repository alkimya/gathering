-- GatheRing Database Migration
-- Migration 006: Memory schema - Memory & RAG with pgvector
-- Schema: memory

-- =============================================================================
-- memory.memories - Long-term Memory Storage
-- =============================================================================

CREATE TABLE memory.memories (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Scope
    scope public.memory_scope NOT NULL,
    scope_id BIGINT,  -- agent_id, circle_id, project_id, or NULL for global

    -- For agent-scoped memories
    agent_id BIGINT REFERENCES agent.agents(id) ON DELETE CASCADE,

    -- Memory content
    memory_type public.memory_type DEFAULT 'fact',
    key VARCHAR(200) NOT NULL,
    value TEXT NOT NULL,

    -- Source (where this memory came from)
    source_type VARCHAR(50),  -- conversation, task, review, user_input
    source_id BIGINT,

    -- Additional metadata
    tags TEXT[] DEFAULT '{}',
    extra_data JSONB DEFAULT '{}',

    -- Vector embedding for semantic search (RAG)
    embedding vector(1536),  -- OpenAI embeddings dimension

    -- Importance and recency for memory management
    importance FLOAT DEFAULT 0.5 CHECK (importance >= 0 AND importance <= 1),
    access_count INTEGER DEFAULT 0,
    relevance_score FLOAT DEFAULT 0.0,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_accessed_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_memories_scope ON memory.memories(scope, scope_id);
CREATE INDEX idx_memories_agent ON memory.memories(agent_id) WHERE agent_id IS NOT NULL;
CREATE INDEX idx_memories_type ON memory.memories(memory_type);
CREATE INDEX idx_memories_key ON memory.memories(key);
CREATE INDEX idx_memories_tags ON memory.memories USING GIN(tags);
CREATE INDEX idx_memories_active ON memory.memories(agent_id, is_active) WHERE is_active = TRUE;

-- Vector similarity search index
CREATE INDEX idx_memories_embedding ON memory.memories
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Trigger
CREATE TRIGGER update_memories_updated_at
    BEFORE UPDATE ON memory.memories
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

COMMENT ON TABLE memory.memories IS 'Long-term memory storage with vector embeddings for RAG';

-- =============================================================================
-- memory.embeddings_cache - Cached Embeddings
-- =============================================================================

CREATE TABLE memory.embeddings_cache (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Content hash for deduplication
    content_hash VARCHAR(64) NOT NULL UNIQUE,
    content_preview VARCHAR(500),  -- First 500 chars for reference

    -- Embedding
    embedding vector(1536) NOT NULL,

    -- Provider info
    model VARCHAR(100) NOT NULL,  -- text-embedding-3-small, etc.
    dimension INTEGER NOT NULL,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Usage stats
    usage_count INTEGER DEFAULT 1
);

-- Indexes
CREATE INDEX idx_embeddings_cache_hash ON memory.embeddings_cache(content_hash);
CREATE INDEX idx_embeddings_cache_model ON memory.embeddings_cache(model);

COMMENT ON TABLE memory.embeddings_cache IS 'Cache for computed embeddings to avoid recomputation';

-- =============================================================================
-- memory.knowledge_base - Shared Knowledge Base
-- =============================================================================

CREATE TABLE memory.knowledge_base (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Knowledge item
    title VARCHAR(300) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(100),  -- documentation, best_practice, decision, faq

    -- Scope
    project_id BIGINT REFERENCES project.projects(id) ON DELETE CASCADE,
    circle_id BIGINT REFERENCES circle.circles(id) ON DELETE CASCADE,
    is_global BOOLEAN DEFAULT FALSE,

    -- Metadata
    tags TEXT[] DEFAULT '{}',
    source_url VARCHAR(500),
    author_agent_id BIGINT REFERENCES agent.agents(id) ON DELETE SET NULL,

    -- Vector embedding for search
    embedding vector(1536),

    -- Quality
    quality_score FLOAT DEFAULT 0.5,
    upvotes INTEGER DEFAULT 0,
    downvotes INTEGER DEFAULT 0,

    -- Status
    is_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_knowledge_base_project ON memory.knowledge_base(project_id) WHERE project_id IS NOT NULL;
CREATE INDEX idx_knowledge_base_circle ON memory.knowledge_base(circle_id) WHERE circle_id IS NOT NULL;
CREATE INDEX idx_knowledge_base_global ON memory.knowledge_base(is_global) WHERE is_global = TRUE;
CREATE INDEX idx_knowledge_base_category ON memory.knowledge_base(category);
CREATE INDEX idx_knowledge_base_tags ON memory.knowledge_base USING GIN(tags);
CREATE INDEX idx_knowledge_base_embedding ON memory.knowledge_base
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Trigger
CREATE TRIGGER update_knowledge_base_updated_at
    BEFORE UPDATE ON memory.knowledge_base
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

COMMENT ON TABLE memory.knowledge_base IS 'Shared knowledge base for RAG retrieval';

-- =============================================================================
-- memory.context_snapshots - Context Window Snapshots
-- =============================================================================

CREATE TABLE memory.context_snapshots (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    agent_id BIGINT NOT NULL REFERENCES agent.agents(id) ON DELETE CASCADE,
    session_id BIGINT REFERENCES agent.sessions(id) ON DELETE CASCADE,

    -- Snapshot reason
    reason VARCHAR(50) NOT NULL,  -- compaction, session_end, manual

    -- Context summary
    summary TEXT NOT NULL,
    key_points TEXT[] DEFAULT '{}',
    decisions TEXT[] DEFAULT '{}',

    -- Original context info
    message_count INTEGER,
    token_count INTEGER,
    start_message_id BIGINT,
    end_message_id BIGINT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_context_snapshots_agent ON memory.context_snapshots(agent_id, created_at DESC);
CREATE INDEX idx_context_snapshots_session ON memory.context_snapshots(session_id);

COMMENT ON TABLE memory.context_snapshots IS 'Snapshots of context windows for recovery';

-- =============================================================================
-- Helper Functions for RAG
-- =============================================================================

-- Function to search memories by semantic similarity
CREATE OR REPLACE FUNCTION memory.search_similar_memories(
    query_embedding vector(1536),
    p_agent_id BIGINT DEFAULT NULL,
    p_scope public.memory_scope DEFAULT NULL,
    p_limit INTEGER DEFAULT 10,
    p_threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    memory_id BIGINT,
    key VARCHAR(200),
    value TEXT,
    memory_type public.memory_type,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id,
        m.key,
        m.value,
        m.memory_type,
        1 - (m.embedding <=> query_embedding) AS similarity
    FROM memory.memories m
    WHERE m.is_active = TRUE
        AND m.embedding IS NOT NULL
        AND (p_agent_id IS NULL OR m.agent_id = p_agent_id)
        AND (p_scope IS NULL OR m.scope = p_scope)
        AND (1 - (m.embedding <=> query_embedding)) >= p_threshold
    ORDER BY m.embedding <=> query_embedding
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to search knowledge base
CREATE OR REPLACE FUNCTION memory.search_knowledge_base(
    query_embedding vector(1536),
    p_project_id BIGINT DEFAULT NULL,
    p_circle_id BIGINT DEFAULT NULL,
    p_category VARCHAR(100) DEFAULT NULL,
    p_limit INTEGER DEFAULT 10,
    p_threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    kb_id BIGINT,
    title VARCHAR(300),
    content TEXT,
    category VARCHAR(100),
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        kb.id,
        kb.title,
        kb.content,
        kb.category,
        1 - (kb.embedding <=> query_embedding) AS similarity
    FROM memory.knowledge_base kb
    WHERE kb.is_active = TRUE
        AND kb.embedding IS NOT NULL
        AND (p_project_id IS NULL OR kb.project_id = p_project_id OR kb.is_global = TRUE)
        AND (p_circle_id IS NULL OR kb.circle_id = p_circle_id OR kb.is_global = TRUE)
        AND (p_category IS NULL OR kb.category = p_category)
        AND (1 - (kb.embedding <=> query_embedding)) >= p_threshold
    ORDER BY kb.embedding <=> query_embedding
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;
