-- Devmatrix PostgreSQL Initialization Script
-- This script runs automatically when the database is first created

-- Enable pgvector extension for future semantic search
CREATE EXTENSION IF NOT EXISTS vector;

-- Create initial schema
CREATE SCHEMA IF NOT EXISTS devmatrix;

-- Set search path
SET search_path TO devmatrix, public;

-- Projects table
CREATE TABLE IF NOT EXISTS devmatrix.projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT valid_status CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'cancelled'))
);

-- Tasks table (agent execution tracking)
CREATE TABLE IF NOT EXISTS devmatrix.tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES devmatrix.projects(id) ON DELETE CASCADE,
    agent_name VARCHAR(100) NOT NULL,
    task_type VARCHAR(100) NOT NULL,
    input TEXT,
    output TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT valid_task_status CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'cancelled'))
);

-- Agent decisions table (human-in-loop tracking)
CREATE TABLE IF NOT EXISTS devmatrix.agent_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES devmatrix.tasks(id) ON DELETE CASCADE,
    decision_type VARCHAR(100) NOT NULL,
    reasoning TEXT,
    approved BOOLEAN,
    feedback TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    decided_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Git commits table (version tracking)
CREATE TABLE IF NOT EXISTS devmatrix.git_commits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES devmatrix.tasks(id) ON DELETE SET NULL,
    commit_hash VARCHAR(40) NOT NULL,
    commit_message TEXT NOT NULL,
    files_changed JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Cost tracking table (LLM API usage)
CREATE TABLE IF NOT EXISTS devmatrix.cost_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES devmatrix.tasks(id) ON DELETE SET NULL,
    model_name VARCHAR(100) NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    total_cost_usd DECIMAL(10, 6) NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_projects_status ON devmatrix.projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_created_at ON devmatrix.projects(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON devmatrix.tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON devmatrix.tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_agent_name ON devmatrix.tasks(agent_name);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON devmatrix.tasks(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_decisions_task_id ON devmatrix.agent_decisions(task_id);
CREATE INDEX IF NOT EXISTS idx_decisions_approved ON devmatrix.agent_decisions(approved);

CREATE INDEX IF NOT EXISTS idx_commits_task_id ON devmatrix.git_commits(task_id);
CREATE INDEX IF NOT EXISTS idx_commits_hash ON devmatrix.git_commits(commit_hash);

CREATE INDEX IF NOT EXISTS idx_cost_task_id ON devmatrix.cost_tracking(task_id);
CREATE INDEX IF NOT EXISTS idx_cost_model ON devmatrix.cost_tracking(model_name);
CREATE INDEX IF NOT EXISTS idx_cost_created_at ON devmatrix.cost_tracking(created_at DESC);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION devmatrix.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to projects table
CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON devmatrix.projects
    FOR EACH ROW
    EXECUTE FUNCTION devmatrix.update_updated_at_column();

-- Insert sample data for testing (optional)
-- INSERT INTO devmatrix.projects (name, description, status)
-- VALUES ('Test Project', 'Initial test project', 'pending');

-- Grant permissions (if needed for specific users in production)
-- GRANT ALL PRIVILEGES ON SCHEMA devmatrix TO devmatrix_user;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA devmatrix TO devmatrix_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA devmatrix TO devmatrix_user;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Devmatrix database initialized successfully!';
    RAISE NOTICE 'Schema: devmatrix';
    RAISE NOTICE 'Tables: projects, tasks, agent_decisions, git_commits, cost_tracking';
    RAISE NOTICE 'Extensions: vector (pgvector enabled)';
END $$;
