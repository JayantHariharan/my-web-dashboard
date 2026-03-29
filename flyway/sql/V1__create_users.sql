-- Migration V1: Create users table with audit fields
-- Placeholder {AUTOINCREMENT} expands to:
--   PostgreSQL: SERIAL PRIMARY KEY
--   SQLite: INTEGER PRIMARY KEY AUTOINCREMENT

CREATE TABLE IF NOT EXISTS users (
    id {AUTOINCREMENT},
    username VARCHAR(255) UNIQUE NOT NULL,
    password TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP NULL,
    created_ip TEXT NULL,
    last_login_ip TEXT NULL
);
