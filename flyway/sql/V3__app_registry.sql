-- Migration V3: Create app_registry table
-- Central registry of all available apps in the platform

CREATE TABLE IF NOT EXISTS app_registry (
    id {AUTOINCREMENT},
    name VARCHAR(100) NOT NULL UNIQUE,
    route_path VARCHAR(200) NOT NULL UNIQUE,
    description TEXT,
    icon VARCHAR(50),
    version VARCHAR(20) DEFAULT '1.0.0',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for active apps lookups
CREATE INDEX IF NOT EXISTS idx_app_registry_active ON app_registry(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_app_registry_name ON app_registry(name);

-- Seed data: Register the Tic-Tac-Toe app
INSERT INTO app_registry (name, route_path, description, icon) VALUES
('tic-tac-toe', '/apps/tic-tac-toe', 'Classic Tic-Tac-Toe with AI opponent', '🎮')
ON CONFLICT (name) DO NOTHING;
