-- Migration V1: Complete Initial Schema
-- Version: 1
-- Description: Creates all tables and indexes in a single consolidated schema for the first production push
--
-- Placeholders:
--   {AUTOINCREMENT} expands to INTEGER PRIMARY KEY AUTOINCREMENT / SERIAL
--   {TEXT} expands to TEXT (compatible with both DBs)
--   {table_suffix} is set by ENV variable (e.g. _prod, _test, or empty)

-- 1. Users table (Authentication & Credentials)
CREATE TABLE IF NOT EXISTS users{table_suffix} (
    id {AUTOINCREMENT},
    username VARCHAR(255) UNIQUE NOT NULL,
    password {TEXT} NOT NULL,
    email VARCHAR(255) UNIQUE NULL,
    email_verified BOOLEAN DEFAULT 0,
    two_factor_enabled BOOLEAN DEFAULT 0,
    account_status VARCHAR(20) DEFAULT 'active', -- active, suspended, deleted
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP NULL,
    created_ip {TEXT} NULL,
    last_login_ip {TEXT} NULL
);

-- 2. User profiles table (Privacy & Identity)
CREATE TABLE IF NOT EXISTS user_profiles{table_suffix} (
    id {AUTOINCREMENT},
    user_id INTEGER NOT NULL UNIQUE,
    display_name VARCHAR(100),
    bio {TEXT},
    preferences JSON,
    avatar_url {TEXT},
    is_private_profile BOOLEAN DEFAULT 0,
    show_activity BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users{table_suffix}(id) ON DELETE CASCADE
);

-- 3. Games Table (Tic-Tac-Toe & Future)
CREATE TABLE IF NOT EXISTS games{table_suffix} (
    id {AUTOINCREMENT},
    game_type {TEXT} NOT NULL, -- 'single' or 'multi'
    status {TEXT} NOT NULL DEFAULT 'waiting', -- 'waiting', 'playing', 'finished'
    join_code {TEXT} UNIQUE, -- 6-character code for multiplayer
    capacity INTEGER DEFAULT 2, -- Total slots
    level {TEXT} DEFAULT 'medium', -- 'easy', 'medium', 'hard', 'god'
    winner_id INTEGER, -- User ID or NULL for draw/AI
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Game Players (Teams/Slots)
CREATE TABLE IF NOT EXISTS game_players{table_suffix} (
    id {AUTOINCREMENT},
    game_id INTEGER NOT NULL,
    user_id INTEGER, -- NULL if slot is occupied by an AI agent
    is_ai BOOLEAN DEFAULT 0,
    symbol {TEXT} NOT NULL, -- 'X' or 'O'
    team_index INTEGER DEFAULT 0, -- Support for team groups
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (game_id) REFERENCES games{table_suffix}(id) ON DELETE CASCADE
);

-- 5. Game Moves
CREATE TABLE IF NOT EXISTS game_moves{table_suffix} (
    id {AUTOINCREMENT},
    game_id INTEGER NOT NULL,
    player_id INTEGER, -- NULL for AI
    symbol {TEXT} NOT NULL,
    position INTEGER NOT NULL, -- 0-8 for 3x3 grid
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (game_id) REFERENCES games{table_suffix}(id) ON DELETE CASCADE
);

-- 6. Leaderboard Statistics
CREATE TABLE IF NOT EXISTS leaderboard{table_suffix} (
    user_id INTEGER PRIMARY KEY,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    draws INTEGER DEFAULT 0,
    elo_rating INTEGER DEFAULT 1200,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users{table_suffix}(id) ON DELETE CASCADE
);

-- 7. User Activity Tracking
CREATE TABLE IF NOT EXISTS user_activity{table_suffix} (
    id {AUTOINCREMENT},
    user_id INTEGER NOT NULL,
    activity_type VARCHAR(50) NOT NULL, -- 'game', 'app'
    activity_name VARCHAR(100) NOT NULL,
    activity_id VARCHAR(100), -- identifier or join_code
    metadata {TEXT}, -- JSON for extra stats
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users{table_suffix}(id) ON DELETE CASCADE
);

-- 8. User Awards (Trophies/Medals)
CREATE TABLE IF NOT EXISTS user_awards{table_suffix} (
    id {AUTOINCREMENT},
    user_id INTEGER NOT NULL,
    award_name VARCHAR(100) NOT NULL,
    award_tier VARCHAR(20) NOT NULL, -- 'bronze', 'silver', 'gold', 'platinum'
    award_ico VARCHAR(10) NOT NULL, 
    description {TEXT},
    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users{table_suffix}(id) ON DELETE CASCADE
);

-- 9. Complete Index Set for Performance
CREATE INDEX IF NOT EXISTS idx_users_email{table_suffix} ON users{table_suffix}(email);
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id{table_suffix} ON user_profiles{table_suffix}(user_id);
CREATE INDEX IF NOT EXISTS idx_schema_version_script{table_suffix} ON schema_version{table_suffix}(script);
CREATE INDEX IF NOT EXISTS idx_games_join_code{table_suffix} ON games{table_suffix}(join_code);
CREATE INDEX IF NOT EXISTS idx_game_players_game_id{table_suffix} ON game_players{table_suffix}(game_id);
CREATE INDEX IF NOT EXISTS idx_game_players_user_id{table_suffix} ON game_players{table_suffix}(user_id);
CREATE INDEX IF NOT EXISTS idx_game_moves_game_id{table_suffix} ON game_moves{table_suffix}(game_id);
CREATE INDEX IF NOT EXISTS idx_leaderboard_elo{table_suffix} ON leaderboard{table_suffix}(elo_rating DESC);
CREATE INDEX IF NOT EXISTS idx_user_activity_user_id_created{table_suffix} ON user_activity{table_suffix}(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_awards_user_id{table_suffix} ON user_awards{table_suffix}(user_id);
