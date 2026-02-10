-- Migration 007: Pipeline execution engine schema extensions
--
-- Adds execution configuration to pipelines table, timeout status to runs,
-- and creates pipeline_node_runs table for per-node execution tracking.
--
-- Idempotent: Uses IF NOT EXISTS / IF NOT EXISTS patterns.

-- 1. Add execution config columns to circle.pipelines
ALTER TABLE circle.pipelines
    ADD COLUMN IF NOT EXISTS timeout_seconds INTEGER DEFAULT 3600;
ALTER TABLE circle.pipelines
    ADD COLUMN IF NOT EXISTS max_retries_per_node INTEGER DEFAULT 3;
ALTER TABLE circle.pipelines
    ADD COLUMN IF NOT EXISTS retry_backoff_base FLOAT DEFAULT 1.0;
ALTER TABLE circle.pipelines
    ADD COLUMN IF NOT EXISTS retry_backoff_max FLOAT DEFAULT 60.0;

-- 2. Update circle.pipeline_runs status constraint to include 'timeout'
--    DROP existing CHECK, then ADD new CHECK with 'timeout' option.
ALTER TABLE circle.pipeline_runs
    DROP CONSTRAINT IF EXISTS pipeline_runs_status_check;
ALTER TABLE circle.pipeline_runs
    ADD CONSTRAINT pipeline_runs_status_check
    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled', 'timeout'));

-- Add duration_seconds column to pipeline_runs
ALTER TABLE circle.pipeline_runs
    ADD COLUMN IF NOT EXISTS duration_seconds INTEGER DEFAULT 0;

-- 3. Create pipeline_node_runs table for per-node execution tracking
CREATE TABLE IF NOT EXISTS circle.pipeline_node_runs (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES circle.pipeline_runs(id) ON DELETE CASCADE,
    node_id VARCHAR(100) NOT NULL,
    node_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'skipped', 'cancelled')),
    input_data JSONB DEFAULT '{}'::jsonb,
    output_data JSONB DEFAULT '{}'::jsonb,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_ms INTEGER DEFAULT 0
);

-- Indexes for pipeline_node_runs
CREATE INDEX IF NOT EXISTS idx_pipeline_node_runs_run_id
    ON circle.pipeline_node_runs(run_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_node_runs_run_node
    ON circle.pipeline_node_runs(run_id, node_id);
