-- Migration V2: Add index on username for faster lookups
-- This improves performance of user authentication queries

CREATE INDEX IF NOT EXISTS idx_username ON users(username);
