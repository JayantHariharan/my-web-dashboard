# System Architecture

This document describes the technical architecture of PlayNexus.

---

## Overview

PlayNexus is a **full-stack web application** with a FastAPI backend serving a static HTML/CSS/JavaScript frontend. It uses PostgreSQL for production (Render) and SQLite for local development.

```
┌──────────────────────────────────────────────────────────┐
│                     User's Browser                        │
│  ┌────────────────────────────────────────────────────┐  │
│  │           Frontend (Static HTML/CSS/JS)            │  │
│  │  - Crystal Portal UI with Matter.js physics       │  │
│  │  - Responsive design (mobile + desktop)           │  │
│  │  - Session management via sessionStorage          │  │
│  └────────────────────────────────────────────────────┘  │
└───────────────────────┬──────────────────────────────────┘
                        │ (served from same origin)
                        ▼
┌──────────────────────────────────────────────────────────┐
│              FastAPI Backend (Render)                    │
│  ┌────────────────────────────────────────────────────┐  │
│  │  • Serves static files from src/frontend/         │  │
│  │  • Authentication APIs: /api/login, /api/signup   │  │
│  │  • Health check: /health                          │  │
│  │  • Rate limiting (category-based)                 │  │
│  │  • Migration engine (Flyway-style, auto-apply)   │  │
│  └────────────────────────────────────────────────────┘  │
└───────────────────────┬──────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────┐
│              PostgreSQL (Render) / SQLite (dev)         │
│  ┌────────────────────────────────────────────────────┐  │
│  │  • users table (with audit fields)                │  │
│  │  • user_profiles table                            │  │
│  │  • app_registry table                             │  │
│  │  • user_app_activity table                        │  │
│  │  • game_scores table                              │  │
│  │  • schema_version table (migration tracking)      │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.12+)
- **Database**: PostgreSQL (production) / SQLite (development)
- **Authentication**: bcrypt with pepper (passlib)
- **Deployment**: Render.com (PaaS)
- **CI/CD**: GitHub Actions
- **Migrations**: Custom Flyway-style SQL migrator

### Frontend
- **Architecture**: Static HTML5 + CSS3 + ES6 JavaScript
- **Physics**: Matter.js (2D physics engine for UI effects)
- **Styling**: CSS custom properties, glassmorphism, responsive
- **Features**: Dark/light theme toggle, toast notifications, live search

### Database
- **Production**: PostgreSQL (Render-managed)
- **Development**: SQLite (local file: `./data/playnexus.db`)
- **Migrations**: Flyway-style versioned SQL scripts in `flyway/sql/`
- **Schema tracking**: `schema_version` table

---

## Key Design Patterns

### 1. Repository Pattern

Database operations are encapsulated in repository classes:

```python
class UserRepository(BaseRepository):
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        ...
    def create_user(self, username: str, password_hash: str) -> int:
        ...
```

**Benefits**:
- Separates data access from business logic
- Easy to test (mock repositories)
- Database-agnostic (works with SQLite/PostgreSQL)

### 2. Configuration Management

Centralized settings via `config.py`:

```python
@dataclass
class Settings:
    database: DatabaseConfig
    debug: bool = False
    secret_key: str = ...
    log_level: int = logging.INFO
```

Environment variables override defaults.

### 3. Modular Routing

Backend is split into feature modules:
- `auth/` - Authentication endpoints
- `games/` - Game-specific APIs
- `apps/` - General app registry

Each module defines its own router with prefix, making it easy to add new app categories.

### 4. Middleware Pipeline

Ordered middleware chain in `core/app.py`:
1. Request ID middleware (adds `X-Request-ID`)
2. CORS middleware
3. Rate limiting middleware (per-route configuration)

---

## Database Schema

### Tables

1. **users**
   - `id` (PK, autoincrement)
   - `username` (unique, indexed)
   - `password` (bcrypt hash)
   - `created_at`, `last_login_at`
   - `created_ip`, `last_login_ip` (audit)

2. **user_profiles**
   - `user_id` (FK to users, 1:1)
   - `display_name`, `bio`, `avatar_url`
   - `created_at`, `updated_at`

3. **app_registry**
   - `id` (PK)
   - `name`, `route_path` (unique)
   - `description`, `icon`, `version`
   - `is_active` (boolean)
   - `created_at`
   - Seed: Tic-Tac-Toe app registered on V3 migration

4. **user_app_activity**
   - `id` (PK)
   - `user_id` (FK)
   - `app_id` (FK)
   - `session_id`
   - `metadata` (TEXT, stores JSON)
   - `created_at`, `last_accessed`

5. **game_scores**
   - `id` (PK)
   - `user_id` (FK)
   - `game_name` (e.g., "tic-tac-toe")
   - `score` (integer)
   - `metadata` (TEXT, stores JSON)
   - `created_at`
   - Indexes: `(user_id, game_name)`, `(game_name, score DESC)`

6. **schema_version**
   - `id` (PK)
   - `version` (INTEGER, but stores filename like "V1__create_users.sql")
   - `script` (TEXT, migration filename)
   - `installed_on` (TIMESTAMP)

7. **app_config** (Runtime Configuration)
   - `key` (TEXT, part of composite PK)
   - `value` (TEXT, config value)
   - `env` (TEXT, environment: 'staging' or 'production', part of composite PK)
   - `description` (TEXT, optional)
   - `updated_at` (TIMESTAMP)
   - Unique constraint on `(key, env)`
   - Index on `env` for fast lookup
   - Purpose: Store environment-specific settings (site_name, maintenance_mode, etc.)
   - Values loaded at startup based on `APP_ENV` environment variable

---

## Security Considerations

### Authentication
- Passwords hashed with bcrypt (cost factor 12)
- Pepper (`SECRET_KEY`) added to password before hashing
- Constant-time comparison prevents timing attacks
- Generic error messages (don't reveal if username exists)

### Rate Limiting
- **Auth endpoints**: 20 requests/hour, block 15min
- **Games endpoints**: 100 requests/hour, block 10min
- **Apps endpoints**: 200 requests/hour, block 10min
- In-memory storage (suitable for single instance); for multi-instance, use Redis

### Input Validation
- Pydantic schemas validate all request bodies
- Parameterized queries prevent SQL injection
- CORS configured (wildcard in dev, restricted in prod)

---

## Deployment Architecture

```
GitHub Repository
    │
    │ push to main
    ▼
GitHub Actions (CI/CD)
    │
    ├─► Pre-checks (lint, type, syntax)
    ├─► Apply migrations to Render PostgreSQL
    ├─► Trigger Render deploy
    ├─► Health check wait (max 30min)
    └─► Smoke test (Playwright)
```

**Render Setup**:
- Web Service (Python 3.12)
- Build: `pip install -r requirements.txt`
- Start: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- Env vars: `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`, `SECRET_KEY`, `DEBUG=false`

---

## Performance Considerations

### Backend
- FastAPI async request handling
- SQLite for dev (zero config), PostgreSQL for prod (connection pooling)
- In-memory rate limiter (fast but not distributed)

### Frontend
- Matter.js physics runs on canvas (GPU-accelerated)
- Debounced search input (300ms delay)
- Mobile-optimized: particle count reduced on small screens
- CSS animations use `transform` and `opacity` (composited)

---

## Future Enhancements (Roadmap)

- JWT authentication for persistent sessions
- Redis-backed rate limiting for multi-instance scaling
- User profile pictures (DiceBear/Cloudinary)
- More games: puzzle, arcade, strategy
- Achievements & badges system
- Social features (friends, chat)
- Admin dashboard
- Email verification (SendGrid)
- Password reset flow
- Two-factor authentication (2FA)
- API analytics dashboard
- PWA offline support
- Docker containerization

---

## Project Structure

```
my-web-dashboard/
├── src/
│   ├── backend/
│   │   ├── config.py         # Settings
│   │   ├── log_config.py     # Logging
│   │   ├── main.py           # Entry point
│   │   ├── migrator.py       # DB migrations
│   │   ├── core/             # App factory, middleware
│   │   ├── shared/           # Database, security, schemas, exceptions
│   │   ├── auth/             # Auth module
│   │   ├── games/            # Games module
│   │   └── apps/             # Apps module
│   └── frontend/
│       ├── index.html        # Hub
│       ├── games/            # Games pages
│       ├── author/           # Vault
│       ├── community/        # Community
│       ├── news/             # Trending
│       ├── css/              # Styles
│       ├── js/               # Scripts
│       └── assets/           # Images, SVGs
├── flyway/
│   └── sql/                  # Migration files (V1..V5)
├── docs/
│   ├── ARCHITECTURE.md       # This file
│   ├── FLYWAY.md            # Migration guide
│   └── API-REFERENCE.html   # API docs (offline)
├── tests/
├── .github/workflows/
├── CLAUDE.md                 # Claude Code guidance
├── README.md                 # Quick start
├── requirements.txt          # Dependencies
├── runtime.txt              # Python version
├── .env.example             # Env template
└── data/
    └── playnexus.db         # SQLite dev database (gitignored)
```

---

## Last Updated: 2026-03-31
