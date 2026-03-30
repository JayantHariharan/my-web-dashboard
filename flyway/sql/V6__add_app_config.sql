-- ==================================================
-- MIGRATION: V6__add_app_config.sql
-- PURPOSE: Store environment-specific application configuration
-- CREATED: 2026-03-30
-- ==================================================

-- Drop table if exists (for clean re-runs in dev)
DROP TABLE IF EXISTS app_config;

-- Main configuration table with environment scoping
CREATE TABLE app_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    env TEXT NOT NULL,  -- 'test', 'production'
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(key, env)
);

-- Index for faster lookups by environment
CREATE INDEX IF NOT EXISTS idx_app_config_env ON app_config(env);

-- ==================================================
-- SEED DATA: Test (develop branch)
-- ==================================================
INSERT INTO app_config (key, value, env, description) VALUES
('registration_enabled', 'true', 'test', 'Allow new user registrations');

-- ==================================================
-- SEED DATA: Production (main branch)
-- ==================================================
INSERT INTO app_config (key, value, env, description) VALUES
('registration_enabled', 'true', 'production', 'Allow new user registrations');
