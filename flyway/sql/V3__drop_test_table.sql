-- Migration V3: Drop the test table
-- Version: 3
-- Description: Drops the test_table created in V2
--
-- This migration removes the test_table after it has served its purpose
-- for testing the migration workflow.

DROP TABLE IF EXISTS test_table{table_suffix};
