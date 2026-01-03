-- GatheRing Database Migration
-- Migration 015: Add project_id to circles
-- Schema: circle

-- Add project_id to circles table to link circles to projects
ALTER TABLE circle.circles
ADD COLUMN project_id BIGINT REFERENCES project.projects(id) ON DELETE SET NULL;

-- Index for quick project → circles lookup
CREATE INDEX idx_circles_project ON circle.circles(project_id) WHERE project_id IS NOT NULL;

COMMENT ON COLUMN circle.circles.project_id IS 'Project this circle is working on (optional)';
