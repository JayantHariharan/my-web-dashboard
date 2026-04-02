-- Migration V2: Create a dummy test table
-- Version: 2
-- Description: Creates a simple test table to verify migration workflow
--
-- This is a test migration to verify that the migration system can create
-- and later drop tables as needed.

CREATE TABLE IF NOT EXISTS test_table{table_suffix} (
    id {AUTOINCREMENT},
    name {TEXT},
    description {TEXT},
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
