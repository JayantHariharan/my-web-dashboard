-- Migration V5: Create game_scores table
-- Stores high scores and game statistics

CREATE TABLE IF NOT EXISTS game_scores (
    id {AUTOINCREMENT},
    user_id INTEGER NOT NULL,
    game_name VARCHAR(100) NOT NULL,
    score INTEGER NOT NULL,
    metadata TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_game_scores_user_game ON game_scores(user_id, game_name);
CREATE INDEX IF NOT EXISTS idx_game_scores_leaderboard ON game_scores(game_name, score DESC);
