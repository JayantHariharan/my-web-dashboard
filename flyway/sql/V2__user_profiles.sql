-- Migration V2: Create user_profiles table
-- Stores additional user information beyond authentication

CREATE TABLE IF NOT EXISTS user_profiles (
    id {AUTOINCREMENT},
    user_id INTEGER NOT NULL UNIQUE,
    display_name VARCHAR(100),
    bio TEXT,
    preferences JSON,
    avatar_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Index for fast lookup by user_id
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);
