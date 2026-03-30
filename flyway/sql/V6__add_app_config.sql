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
    env TEXT NOT NULL,  -- 'staging', 'production'
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(key, env)
);

-- Index for faster lookups by environment
CREATE INDEX IF NOT EXISTS idx_app_config_env ON app_config(env);

-- ==================================================
-- SEED DATA: Staging (develop branch)
-- ==================================================
INSERT INTO app_config (key, value, env, description) VALUES
('site_name', 'PlayNexus (DEV)', 'staging', 'Site display name in staging'),
('maintenance_mode', 'false', 'staging', 'Enable maintenance mode (staging)'),
('registration_enabled', 'true', 'staging', 'Allow new user registrations'),
('debug_features_enabled', 'true', 'staging', 'Enable debug/experimental features'),
('max_upload_size', '10485760', 'staging', 'Max file upload size in bytes (10MB)'),
('rate_limit_requests', '1000', 'staging', 'Rate limit per hour per IP'),
('allow_cors', '*', 'staging', 'CORS allowed origins for staging');

-- ==================================================
-- SEED DATA: Production (main branch)
-- ==================================================
INSERT INTO app_config (key, value, env, description) VALUES
('site_name', 'PlayNexus', 'production', 'Site display name'),
('maintenance_mode', 'false', 'production', 'Enable maintenance mode (production)'),
('registration_enabled', 'true', 'production', 'Allow new user registrations'),
('debug_features_enabled', 'false', 'production', 'Disable debug/experimental features'),
('max_upload_size', '52428800', 'production', 'Max file upload size in bytes (50MB)'),
('rate_limit_requests', '10000', 'production', 'Rate limit per hour per IP'),
('allow_cors', 'https://playnexus.onrender.com', 'production', 'CORS allowed origins for production');
