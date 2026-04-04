-- Migration V1: Complete initial schema (users + user_profiles + indexes)
-- Version: 1
-- Description: Creates all tables and indexes in a single migration
--
-- This replaces the previous separate V1, V2, V3 migrations.
--
-- Placeholders:
--   {AUTOINCREMENT} expands to:
--     PostgreSQL: SERIAL PRIMARY KEY
--     SQLite: INTEGER PRIMARY KEY AUTOINCREMENT
--   {TEXT} expands to TEXT (compatible with both DBs)
--   {table_suffix} is set by ENV variable:
--     ENV=prod or production → _prod
--     ENV=test or staging → _test
--     (local dev) → no suffix

-- 1. Users table (authentication)
CREATE TABLE IF NOT EXISTS users{table_suffix} (
    id {AUTOINCREMENT},
    username VARCHAR(255) UNIQUE NOT NULL,
    password {TEXT} NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP NULL,
    created_ip {TEXT} NULL,
    last_login_ip {TEXT} NULL
);

-- 2. User profiles table (additional user data)
CREATE TABLE IF NOT EXISTS user_profiles{table_suffix} (
    id {AUTOINCREMENT},
    user_id INTEGER NOT NULL UNIQUE,
    display_name VARCHAR(100),
    bio {TEXT},
    preferences JSON,
    avatar_url {TEXT},
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users{table_suffix}(id) ON DELETE CASCADE
);

-- 3. Indexes for performance
-- User profiles lookup by user_id
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id{table_suffix} ON user_profiles{table_suffix}(user_id);
-- Schema version lookup by script (Flyway performance)
CREATE INDEX IF NOT EXISTS idx_schema_version_script{table_suffix} ON schema_version{table_suffix}(script);
