-- GatheRing Database Initialization
-- Migration 001: Create schemas and extensions
-- Database: gathering

-- =============================================================================
-- Extensions
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";  -- pgvector for RAG

-- =============================================================================
-- Schemas
-- =============================================================================

-- Agent schema: Agents & Identity
CREATE SCHEMA IF NOT EXISTS agent;
COMMENT ON SCHEMA agent IS 'Agents, personas, and identity management';

-- Circle schema: Orchestration (Gathering Circles)
CREATE SCHEMA IF NOT EXISTS circle;
COMMENT ON SCHEMA circle IS 'Team orchestration, circles, and facilitation';

-- Project schema: Projects and files
CREATE SCHEMA IF NOT EXISTS project;
COMMENT ON SCHEMA project IS 'Projects, files, and codebase tracking';

-- Communication schema: Conversations and messages
CREATE SCHEMA IF NOT EXISTS communication;
COMMENT ON SCHEMA communication IS 'Conversations, messages, and inter-agent communication';

-- Memory schema: Memory & RAG with pgvector
CREATE SCHEMA IF NOT EXISTS memory;
COMMENT ON SCHEMA memory IS 'Long-term memory storage with vector embeddings for RAG';

-- Review schema: Reviews and quality control
CREATE SCHEMA IF NOT EXISTS review;
COMMENT ON SCHEMA review IS 'Code reviews, quality metrics, and approval workflow';

-- Audit schema: Audit & Logs
CREATE SCHEMA IF NOT EXISTS audit;
COMMENT ON SCHEMA audit IS 'Audit logs, escalations, and system tracking';

-- =============================================================================
-- Enum Types (in public schema for cross-schema usage)
-- =============================================================================

-- Agent roles within a circle
CREATE TYPE public.agent_role AS ENUM (
    'lead',
    'member',
    'specialist',
    'reviewer',
    'observer'
);

-- Message author role
CREATE TYPE public.message_role AS ENUM (
    'user',
    'assistant',
    'system',
    'tool'
);

-- Task lifecycle states
CREATE TYPE public.task_status AS ENUM (
    'pending',
    'claimed',
    'in_progress',
    'review',
    'changes_requested',
    'blocked',
    'completed',
    'cancelled'
);

-- Task priority levels
CREATE TYPE public.task_priority AS ENUM (
    'low',
    'medium',
    'high',
    'critical'
);

-- Review lifecycle states
CREATE TYPE public.review_status AS ENUM (
    'pending',
    'in_progress',
    'approved',
    'changes_requested',
    'rejected'
);

-- Types of review
CREATE TYPE public.review_type AS ENUM (
    'code',
    'architecture',
    'security',
    'docs',
    'quality',
    'final'
);

-- Memory visibility scope
CREATE TYPE public.memory_scope AS ENUM (
    'agent',
    'circle',
    'project',
    'global'
);

-- Type of memory entry
CREATE TYPE public.memory_type AS ENUM (
    'fact',
    'preference',
    'context',
    'decision',
    'error',
    'feedback',
    'learning'
);

-- Audit log severity levels
CREATE TYPE public.log_level AS ENUM (
    'debug',
    'info',
    'warning',
    'error',
    'critical'
);

-- Circle status
CREATE TYPE public.circle_status AS ENUM (
    'stopped',
    'starting',
    'running',
    'stopping'
);

-- Conversation status
CREATE TYPE public.conversation_status AS ENUM (
    'pending',
    'active',
    'completed',
    'cancelled'
);

-- =============================================================================
-- Helper Functions
-- =============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION public.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
