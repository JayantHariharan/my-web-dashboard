-- Migration V4: Create user_app_activity table
-- Tracks when users launch and use apps

CREATE TABLE IF NOT EXISTS user_app_activity (
    id {AUTOINCREMENT},
    user_id INTEGER NOT NULL,
    app_id INTEGER NOT NULL,
    session_id VARCHAR(100) NOT NULL,
    metadata TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (app_id) REFERENCES app_registry(id) ON DELETE CASCADE
);

-- Indexes (separate statements for SQLite compatibility)
CREATE INDEX IF NOT EXISTS idx_user_app_activity_user ON user_app_activity(user_id);
CREATE INDEX IF NOT EXISTS idx_user_app_activity_app ON user_app_activity(app_id);
CREATE INDEX IF NOT EXISTS idx_user_app_activity_session ON user_app_activity(session_id);
