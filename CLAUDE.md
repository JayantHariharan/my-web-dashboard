# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Quick Reference

### Running Locally

```bash
# Backend (FastAPI + serves frontend)
python src/backend/main.py
# Open http://localhost:8000

# Frontend only (dev server)
cd src/frontend
python -m http.server 3000
# Open http://localhost:3000
```

### Development Commands

**Git hooks** (automatic):
- `pre-commit` – Syntax, lint, secrets check, updates doc timestamps
- `pre-push` – Full suite (lint, type, format, security, smoke test), updates doc timestamps

**Skip hooks**: `git commit --no-verify` or `git push --no-verify` (NOT recommended)

**Note**: Hooks automatically update "Last Updated" dates in `CLAUDE.md`, `docs/ARCHITECTURE.md`, `docs/FLYWAY.md` and stage them. Commit these changes separately.

**Claude Code slash commands**:
- `/security-scan` – Security audit (bandit, auth patterns, secrets)
- `/code-quality` – Lint, type check, formatting review
- `/deploy-ready` – Verify deployment readiness

**Install dev tools** (for hooks & manual checks):
```bash
pip install flake8 mypy black bandit
npm install playwright && npx playwright install chromium --with-deps
```

**Manual checks**:
```bash
flake8 src/backend/main.py --count --select=E9,F63,F7,F82
mypy src/backend/main.py
black --check src/backend/
bandit -r src/backend/
python -m py_compile src/backend/main.py  # syntax
node tests/smoke.test.js  # with SITE_URL set
```

**API testing**:
```bash
# Auth
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"Test1234"}'

curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"username":"newuser","password":"Test1234","confirm_password":"Test1234"}'

curl http://localhost:8000/api/auth/me?username=test

# Apps
curl http://localhost:8000/api/apps/

# Games
curl http://localhost:8000/api/games/
curl -X POST http://localhost:8000/api/games/tic-tac-toe/scores?username=test \
  -H "Content-Type: application/json" \
  -d '{"score":1500,"metadata":{"won":true}}'

curl http://localhost:8000/api/games/tic-tac-toe/leaderboard?limit=10

# Health
curl http://localhost:8000/health

# Swagger UI
# Open http://localhost:8000/docs (interactive)
```

---

## Architecture

**Stack**: FastAPI (Python 3.12) + static HTML/CSS/JS frontend + PostgreSQL (Render) / SQLite (local)

**Pattern**: Modular monolith with repository pattern, Flyway-style migrations, bcrypt + pepper authentication.

### Backend Structure (Multi-App)

```
src/backend/
├── config.py              # Settings (env-based) – database, debug, secret_key
├── log_config.py          # Logging configuration
├── main.py                # Entry point – creates app, includes routers, mounts static
├── migrator.py            # Database migration engine (auto-applies on startup)
├── core/
│   ├── app.py             # FastAPI factory, middleware, static files
│   └── middlewares.py     # RateLimitMiddleware, RequestIdMiddleware, CORS
├── shared/
│   ├── database.py        # BaseRepository + repositories (User, App, Profile, Activity, GameScore)
│   ├── security.py        # Password hashing (bcrypt + pepper)
│   ├── schemas.py         # Shared Pydantic models
│   └── exceptions.py      # Custom exceptions
├── auth/
│   ├── router.py          # /api/auth/login, /api/auth/signup, /api/auth/me
│   └── service.py         # Authentication business logic
├── games/
│   └── router.py          # /api/games/, /api/games/{name}/scores, /leaderboard
└── apps/
    └── router.py          # /apps/, /apps/{id}/launch
```

**Note**: Rate limiting is implemented in `core/middlewares.py` using `SimpleRateLimiter` class. Separate `rate_limiter.py` files were removed as unused.

### Frontend Structure (Current)

```
src/frontend/
├── index.html                 # Main hub (login + dashboard)
├── games/
│   ├── games.html            # Games catalog with search & carousel
│   └── tic-tac-toe.html      # Tic-Tac-Toe game
├── author/
│   └── author.html           # "The Vault" - developer portfolio
├── community/
│   └── community.html        # Community Nexus
├── news/
│   └── news.html             # Trending World
├── css/
│   ├── style.css             # Main styles (dark/light theme, components)
│   └── crystal-portal.css    # Auth portal specific styles
├── js/
│   ├── cinematic-startup.js  # Canvas background animation (Matter.js)
│   ├── main.js               # Physics engine, gravity effects
│   └── toast.js              # Toast notification system
└── assets/
    ├── logo.png
    ├── dashboard_bg.png
    ├── tictactoe-cover.svg
    └── coming-soon-cover.svg
```

**Features**:
- Dark/Light theme toggle with localStorage persistence
- Live search filtering on games page
- Toast notifications (success/error/info/warning)
- Matter.js physics effects
- PS5-style cinematic entrance
- Mobile-optimized (reduced particles on small screens)

---

## API Endpoints

### Authentication (`/api/auth/*`)
- `POST /api/auth/login` - Authenticate user (returns user_id)
- `POST /api/auth/signup` - Register new account
- `GET /api/auth/me` - Get current user profile

**Rate limit**: 20 requests/hour per IP (combined)

### Apps
- `GET /api/apps/` - List all active apps
- `GET /api/apps/{id}` - Get app details
- `POST /api/apps/{id}/launch` - Track app launch

**Rate limit**: 200 requests/hour per IP

### Games
- `GET /api/games/` - List available games
- `POST /api/games/{game_name}/scores` - Submit score
- `GET /api/games/{game_name}/leaderboard?limit=10` - Top scores
- `GET /api/games/{game_name}/my-best?username=...` - User's best score

**Rate limit**: 100 requests/hour per IP

### Health
- `GET /health` - Service health check (no rate limit)

---

## Rate Limiting Strategy

| App Category | Endpoints | Limit | Block | Purpose |
|--------------|-----------|-------|-------|---------|
| Auth | `/api/auth/*` | 20/hr | 15min | Prevent brute force |
| Games | `/api/games/*` | 100/hr | 10min | Allow gameplay |
| Apps | `/apps/*` | 200/hr | 10min | Higher for utilities |
| Health | `/health` | Unlimited | - | Monitoring |

**Implementation**: Separate `SimpleRateLimiter` instances per app, in-memory storage (suitable for single Render instance). For multi-instance, replace with Redis backend.

---

## Database Schema

### Tables
- `users` - Core authentication (id, username, password_hash, created_at, last_login_at, created_ip, last_login_ip)
- `user_profiles` - Extended profile (user_id, display_name, bio, avatar_url, created_at, updated_at)
- `app_registry` - App catalog (id, name, route_path, description, icon, version, is_active, created_at)
- `user_app_activity` - Usage tracking (id, user_id, app_id, session_id, metadata, created_at, last_accessed)
- `game_scores` - Game leaderboards (id, user_id, game_name, score, metadata, created_at)
- `schema_version` - Tracks applied migrations

**Migrations**: Flyway-style in `flyway/sql/` (V1..V5). Auto-applied on startup via `migrator.py` (both development and production). The GitHub Actions workflow triggers Render deploys; Render runs migrations automatically when the service starts.

**Database location**: Development uses SQLite in `data/playnexus.db`. Production uses PostgreSQL via environment variables.

---

## Environment Variables

### Database
| Variable | Required | Description |
|----------|----------|-------------|
| `PGHOST` | Yes* | PostgreSQL host (e.g., abc.supabase.co) |
| `PGPORT` | Yes* | Port (usually 5432) |
| `PGUSER` | Yes* | Username (usually postgres) |
| `PGPASSWORD` | Yes* | Database password |
| `PGDATABASE` | Yes* | Database name |
| `DATABASE_URL` | Alternative | Full connection string (overrides PG*) |

### Application
| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Production | Password pepper – generate: `openssl rand -hex 32` |
| `DEBUG` | No | Enable debug mode (default: false) |
| `LOG_LEVEL` | No | DEBUG/INFO/WARNING/ERROR (default: INFO) |
| `APP_ENV` | Recommended | Environment name: `staging` or `production` (used for env-specific config from app_config table) |

*Required for PostgreSQL. If not set, falls back to SQLite (`sqlite:///./data/playnexus.db`).

---

## Environment-Specific Configuration

For staging and production environments, you can store configurable settings in the `app_config` database table. This allows you to change site behavior without redeploying.

### How It Works:

1. **Environment variables** (set in Render) determine connection and core behavior:
   - `APP_ENV` = `test` (for develop branch) or `production` (for main branch)
   - `SECRET_KEY`, `DEBUG`, database credentials

2. **Database table** `app_config` stores key-value pairs scoped to environment:
   ```sql
   SELECT key, value FROM app_config WHERE env = 'test'  -- or 'production'
   ```

3. **At startup**, after migrations run, the app loads all config for the current `APP_ENV` and updates the `settings` object.

### Predefined Config Keys:

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `site_name` | string | "PlayNexus" | Display name shown in UI |
| `maintenance_mode` | boolean | false | Enable maintenance page |
| `registration_enabled` | boolean | true | Allow new user signups |
| `debug_features_enabled` | boolean | false | Show debug/experimental features |
| `max_upload_size` | integer | 52428800 | Max file upload (bytes) |
| `rate_limit_requests` | integer | 10000 | Requests per hour per IP |
| `allow_cors` | string | "*" | CORS allowed origins |

### Adding New Config Keys:

1. Add field to `Settings` class in `src/backend/config.py`
2. Update the `load_runtime_config()` method to handle its type conversion
3. Add migration to insert default values for both `test` and `production`:
   ```sql
   INSERT INTO app_config (key, value, env, description) VALUES
   ('your_key', 'default_value', 'test', 'Description'),
   ('your_key', 'default_value', 'production', 'Description');
   ```
4. Access via `settings.your_key` anywhere in the code

### Setting Up in Render:

**Test Service** (develop branch):
- Environment Group: `TEST`
- Add `APP_ENV=test`
- GitHub Secrets needed:
  - `RENDER_API_KEY_TEST` (API key from Render account)
  - `RENDER_SERVICE_ID_TEST` (service ID: srv-xxx)
  - `RENDER_ENV_GROUP_ID_TEST` (environment group ID: evm-xxx)
- (Optional) Override any config by adding rows to `app_config` for env='test'

**Production Service** (main branch):
- Environment Group: `PROD`
- Add `APP_ENV=production`
- GitHub Secrets needed:
  - `RENDER_API_KEY` (API key from Render account)
  - `RENDER_SERVICE_ID_PROD` (service ID: srv-xxx)
  - `RENDER_ENV_GROUP_ID_PROD` (environment group ID: evm-xxx)
- Use production values in `app_config`

---

## Adding New Features

### New table (e.g., user_achievements)
1. Create migration: `flyway/sql/V6__create_user_achievements.sql`
2. Add repository in `src/backend/shared/database.py` (or new file if complex)
3. Add Pydantic models in `src/backend/shared/schemas.py` or app-specific schemas
4. Add API endpoints in appropriate router (`/api/achievements/`)
5. Update Swagger docstrings with examples
6. Update `docs/API-REFERENCE.html`
7. Push → auto-deploy with migration

### New app module (e.g., tools/calculators)
1. Create directory: `src/backend/tools/` (if separate category) or add to `apps/`
2. Create `router.py` with endpoints
3. Optionally create `service.py` for business logic
4. Register app in `app_registry` (via migration or admin API)
5. Create frontend page: `src/frontend/app/tools/calculator.html`
6. Add JavaScript: `src/frontend/js/tools/calculator.js`
7. Add to hub grid (it will auto-fetch from `/api/apps`)
8. Update docs & Swagger

---

## Deployment

GitHub Actions → Render auto-deploy on `main`:

1. **Test job** (on all pushes/PRs): Syntax check + critical lint only
2. **Deploy job** (only main branch):
   - Associate Render Environment Group (if `RENDER_ENV_GROUP_ID` set)
   - Trigger Render deploy
   - Wait for completion (max 30 min)
   - Health check on `/health` and `/api/auth/login`
3. Migrations run automatically on Render service startup via `migrator.py`

**One-time Render setup**:
1. Create Render Web Service (connect GitHub repo)
2. Create an **Environment Group** (e.g., "PROD") with:
   - `SECRET_KEY` (generate: `openssl rand -hex 32`)
   - `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`
   - `DEBUG=false`
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Disable Auto-Deploy on Render (set to Manual)
6. Add GitHub Secrets:
   - `RENDER_API_KEY` (from Render Account → API Keys)
   - `RENDER_SERVICE_ID` (from Render service URL)
   - `RENDER_ENV_GROUP_ID` (optional but recommended - your PROD group ID)
7. Associate your Render service with the Environment Group:
   - In Render service → Environment → Environment Groups
   - Select your PROD group
8. Push to `main` → auto-deploy

---

## Important Notes

### Standard Project Files

Keep these – they're expected in professional open-source projects:

- `LICENSE` – Legal license (MIT) permitting reuse
- `CODE_OF_CONDUCT.md` – Community standards
- `CONTRIBUTING.md` – How to contribute
- `.env.example` – Environment variable template

Removing these makes the project look unmaintained.

### Multi-App Architecture

This codebase is designed as a **modular platform**:
- Backend organized into feature modules (`auth/`, `games/`, `apps/`)
- Database tracks installed apps (`app_registry` table)
- Frontend dynamically loads app catalog from `/api/apps`
- Easy to add new apps without modifying core code
- Rate limiting per app category

### Rate Limiter Storage

Currently uses in-memory storage:
- ✅ Fine for single-instance Render deployments (Free/Starter)
- ❌ Does NOT share state across multiple instances
- **To scale horizontally**: Replace `SimpleRateLimiter` with Redis backend
  - Implement `RedisRateLimiter` using `redis-py`
  - Use `INCR` with expiry for distributed counting
  - Or use `redis-cell` for token bucket (more accurate)

### Frontend-Backend Integration

Frontend will:
1. Load on page → fetch `/api/apps` to show catalog
2. Auth flow: POST `/api/auth/signup` or `/api/auth/login`
3. Store session (simple: username in sessionStorage; future: JWT)
4. When launching app → POST `/apps/{id}/launch` to track usage
5. Games submit scores → POST `/api/games/{name}/scores`

Currently placeholder – implementation in progress.

---

## Project Structure

```
my-web-dashboard/
├── src/
│   ├── backend/          # Modular FastAPI application
│   │   ├── shared/       # Shared code (database, security, schemas, exceptions)
│   │   ├── auth/         # Authentication module
│   │   ├── core/         # App factory, middlewares, migrator
│   │   ├── games/        # Games module
│   │   ├── apps/         # General apps module
│   │   └── main.py       # Entry point
│   └── frontend/         # Static HTML/CSS/JS (modular structure)
├── docs/                 # Documentation (ARCHITECTURE.md, FLYWAY.md, API-REFERENCE.html)
├── flyway/               # Database migrations
│   └── sql/              # V1..V5
├── tests/                # Smoke tests (Playwright)
├── .github/workflows/    # CI/CD
├── .claude/              # Claude Code config
├── .git/hooks/           # Git hooks (pre-commit, pre-push)
├── README.md             # Quick start
├── CLAUDE.md             # This file
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── requirements.txt      # Python dependencies
├── runtime.txt           # Python version (3.12)
└── .env.example          # Environment template
```

---

## Migration History

| Version | Description | Date |
|---------|-------------|------|
| V1 | Create `users` table | 2025-03-29 |
| V2 | Create `user_profiles` table | 2025-03-30 |
| V3 | Create `app_registry` table (seed: tic-tac-toe) | 2025-03-30 |
| V4 | Create `user_app_activity` table | 2025-03-30 |
| V5 | Create `game_scores` table | 2025-03-30 |

---

## Last Updated

This document is auto-updated by git hooks when documentation changes.
Current version reflects frontend enhancements and cleanup completed on 2026-03-30.

---

## Recent Changes (2026-03-30)

### Frontend UX/UI Improvements
- Added dark/light theme toggle with localStorage persistence
- Implemented live search filtering on games page
- Created toast notification system (success, error, info, warning types)
- Mobile performance optimization (reduced Matter.js particles on small screens)

### Backend Fixes
- Fixed import paths throughout backend (correct relative imports)
- Made psycopg2 optional for SQLite-only development
- Added database auto-migration on startup via `migrator.py`
- Fixed SQLite compatibility issues in Flyway migrations (placeholder substitution, JSON → TEXT, separated INDEX statements)
- Updated deprecated FastAPI constants

### Code Cleanup
- Removed unused files: `src/backend/database.py`, `src/backend/security.py`, `src/backend/migrator.py` (recreated cleaner version), `src/backend/rate_limiter.py`
- Removed `src/shared/` empty folder
- Updated `.gitignore` to include `.claude/` and `*.db`
- Database file correctly placed in `data/` directory (`./data/playnexus.db`)

### Database
- SQLite database auto-initialized with schema (7 tables: users, user_profiles, app_registry, user_app_activity, game_scores, schema_version, sqlite_sequence)
- Migration system now fully functional for development
