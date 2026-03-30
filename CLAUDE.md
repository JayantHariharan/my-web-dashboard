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

**Pattern**: Simplified auth-only backend with repository pattern, Flyway-style migrations, bcrypt + pepper authentication.

### Backend Structure (Auth-Only)

```
src/backend/
├── config.py              # Settings (env-based) – database, debug, secret_key
├── log_config.py          # Logging configuration
├── main.py                # Entry point – creates app, includes auth router, mounts static
├── migrator.py            # Database migration engine (auto-applies on startup)
├── core/
│   ├── app.py             # FastAPI factory, middleware, static files
│   └── middlewares.py     # RateLimitMiddleware, RequestIdMiddleware, CORS
├── shared/
│   ├── database.py        # BaseRepository + UserRepository, UserProfileRepository
│   ├── security.py        # Password hashing (bcrypt + pepper)
│   ├── schemas.py         # Shared Pydantic models
│   └── exceptions.py      # Custom exceptions
└── auth/
    ├── router.py          # /api/auth/login, /api/auth/signup, /api/auth/me
    └── service.py         # Authentication business logic
```

**Simplification (v7.0)**:
- Removed multi-app architecture (games, apps modules)
- Removed activity tracking, game scores, app registry
- Removed database-based runtime configuration (app_config table)
- All configuration now via environment variables
- Focus: Secure, minimal authentication backend

**Rate Limiting**: Implemented in `core/middlewares.py` using `SimpleRateLimiter` class. In-memory storage (suitable for single Render instance). For multi-instance scaling, replace with Redis backend.

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

## API Endpoints (Auth-Only)

### Authentication (`/api/auth/*`)
- `POST /api/auth/login` - Authenticate user (returns user_id)
- `POST /api/auth/signup` - Register new account
- `GET /api/auth/me` - Get current user profile

**Rate limit**: 20 requests/hour per IP (combined)

### Health
- `GET /health` - Service health check (no rate limit)

### Removed Endpoints (v7.0)

The following endpoints were removed with the multi-app simplification:
- ❌ `/api/apps/*` (apps catalog and launch tracking)
- ❌ `/api/games/*` (game scores and leaderboards)

The system is now focused solely on authentication.

---

## Rate Limiting Strategy

| Endpoint Category | Limit | Block | Purpose |
|-------------------|-------|-------|---------|
| Auth | 20/hr | 15min | Prevent brute force |
| Health | Unlimited | - | Monitoring |

**Note**: In v7.0, the multi-app architecture (games/apps) was removed. The system is now **authentication-only**. Only auth endpoints are rate-limited.

**Implementation**: Simple `SimpleRateLimiter` with in-memory storage (suitable for single Render instance). For multi-instance scaling, replace with Redis backend.

---

## Database Schema

### Tables (Auth-Only Mode)

**Core authentication tables:**
- `users` - Core authentication (id, username, password_hash, created_at, last_login_at, created_ip, last_login_ip)
- `user_profiles` - Extended profile (user_id, display_name, bio, preferences, avatar_url, created_at, updated_at)
- `schema_version` - Tracks applied migrations (Flyway-style)

### Removed Tables (v7.0 simplification)

The following non-authentication tables were removed to streamline the backend:
- ❌ `app_registry` (apps catalog)
- ❌ `user_app_activity` (app usage tracking)
- ❌ `game_scores` (game leaderboards)
- ❌ `app_config` (runtime configuration)

All configuration is now via environment variables only (no database-based config).

**Migrations**: Flyway-style in `flyway/sql/` (V1..V7). Auto-applied on startup via `migrator.py` (both development and production). The GitHub Actions workflow triggers Render deploys; Render runs migrations automatically when the service starts.

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

### Predefined Config Keys (initially auth-only):

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `registration_enabled` | boolean | true | Allow new user signups |

*Start small. Add more keys as needed by updating Settings and this table.*
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

## Extending the System

**Note**: v7.0 simplified the system to authentication-only. Multi-app functionality was removed. If you need to extend the system, consider these patterns:

### Extending User Profiles

To add new user profile fields:

1. Create a migration to add columns to `user_profiles`:
   ```sql
   ALTER TABLE user_profiles ADD COLUMN your_field TEXT;
   ```

2. Update `UserProfileRepository` in `src/backend/shared/database.py` with helper methods

3. Update Pydantic schemas in `src/backend/shared/schemas.py` (e.g., `UserProfileUpdate`)

4. Add endpoint in `src/backend/auth/router.py` or create a new profile router

### Re-adding Multi-App Support (Optional)

If you need apps/games functionality again, you would:

1. Re-add `app_registry`, `user_app_activity`, `game_scores` tables via migrations
2. Recreate `AppRepository`, `UserActivityRepository`, `GameScoreRepository` in `database.py`
3. Recreate `apps/` and `games/` routers
4. Re-add `app_config` table if runtime config needed
5. Include routers in `main.py`

Consider whether this complexity is truly needed. For pure authentication backend, the current simplified architecture is **recommended**.

---

## Deployment

### Automated CI/CD (GitHub Actions → Render)

**Unified workflow** for staging and production:

1. **Quality job** (all branches/PRs):
   - Syntax check, linting (flake8), type check (mypy), security scan (bandit), format check (black)
   - Runs on every push and PR
   - Uploads quality reports as artifacts

2. **Deploy job** (only on push to `main` or `develop`):
   - Validates secrets (fails fast if missing)
   - Auto-associates Render Environment Group (if configured)
   - Triggers Render deployment via API
   - Monitors deployment progress (max 30 min)
   - Health checks (`/health`, `/api/auth/login`)
   - Runs Playwright smoke test on deployed site
   - Prints comprehensive deployment summary

**Branch strategy**:
- `develop`: Auto-deploys to **staging** on every push (uses `APP_ENV=test`)
- `main`: Auto-deploys to **production** on every push (uses `APP_ENV=production`)
  - ⚠️  **Branch protection recommended**: Prevent direct pushes, require PRs
  - PR merges to `main` trigger production deployment

**Smoke test**: `tests/smoke.test.js` runs automatically after each deployment to verify the site loads and displays "PlayNexus".

### One-Time Render Setup

**Create Render Web Service(s)**:

1. Go to Render Dashboard → Create New → Web Service
2. Connect your GitHub repository
3. **Build command**: `pip install -r requirements.txt`
4. **Start command**: `uvicorn src.backend.main:app --host 0.0.0.0 --port $PORT`
   (Alternative: `python src/backend/main.py` – both work)
5. **Disable Auto-Deploy**: Set to **Manual** (GitHub Actions will trigger deploys)
6. **Add Environment Variables** (see below)
7. Create service(s):
   - **Staging**: Name like `playnexus-staging` (for `develop` branch)
   - **Production**: Name like `playnexus` (for `main` branch)
   - Or use a single service and switch via `APP_ENV`

**Environment Variables** (set in Render service → Environment tab):

| Variable | Staging | Production | Description |
|----------|---------|------------|-------------|
| `APP_ENV` | `test` | `production` | Environment identifier (loads config from `app_config` table) |
| `SECRET_KEY` | ✅ | ✅ | Password pepper: generate with `openssl rand -hex 32` |
| `PGHOST` | ⚠️ | ⚠️ | PostgreSQL host (if using external DB) |
| `PGPORT` | ⚠️ | ⚠️ | Port (usually 5432) |
| `PGUSER` | ⚠️ | ⚠️ | Username |
| `PGPASSWORD` | ⚠️ | ⚠️ | Password |
| `PGDATABASE` | ⚠️ | ⚠️ | Database name |
| `DEBUG` | optional | optional | Default: `false` |
| `LOG_LEVEL` | optional | optional | Default: `INFO` |

> **Note**: If PostgreSQL variables are not set, the app automatically uses SQLite (`./data/playnexus.db`). This is fine for single-instance Render deployments (Free/Starter plans). For multi-instance scaling, use PostgreSQL.

### GitHub Secrets Setup

Add these in **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

#### Option A: Separate Services (Recommended)

**Staging secrets** (for `develop` branch):
- `RENDER_API_KEY_TEST` - Render API key (from Render Account → API Keys)
- `RENDER_SERVICE_ID_TEST` - Staging service ID (`srv-xxx` from service URL)
- `RENDER_ENV_GROUP_ID_TEST` - (Optional) Environment Group ID (`evm-xxx`)

**Production secrets** (for `main` branch):
- `RENDER_API_KEY` - Render API key (can be same key)
- `RENDER_SERVICE_ID_PROD` - Production service ID
- `RENDER_ENV_GROUP_ID_PROD` - (Optional) Environment Group ID

#### Option B: Single Service

If using the same service for staging and production:
- `RENDER_API_KEY` - API key
- `RENDER_SERVICE_ID` - Service ID (same for both)
- `RENDER_ENV_GROUP_ID` - (Optional) Environment Group ID

### Branch Protection (Recommended)

To enforce workflow and prevent accidental production deployments:

1. Go to repository **Settings** → **Branches**
2. **Add rule** → Branch name: `main`
3. Enable:
   - ✅ **Require a pull request before merging**
     - Require approvals: `1` (or more)
   - ✅ **Require status checks to pass before merging**
     - Select: `quality` (from GitHub Actions)
   - ✅ **Require linear history** (optional but recommended)
4. Click **Create** or **Save changes**

This ensures:
- No direct pushes to `main`
- All changes must be reviewed via PR
- Quality checks must pass before merge
- Production deploys are intentional (PR merges only)

### Render Environment Groups (Optional)

Environment Groups let you share environment variables across services and have consistent staging/production configs.

**Setup**:
1. In Render Dashboard: Environment Groups → Create Group (e.g., "PROD", "STAGING")
2. Add environment variables to the group
3. Add `RENDER_ENV_GROUP_ID` secrets to GitHub (one for each branch)
4. The workflow auto-associates services with the correct group

If you **don't** use Environment Groups, just leave `RENDER_ENV_GROUP_ID` unset. The workflow will skip association and proceed normally.

---

## 🚀 Quick Start

1. **Setup Render**:
   - Create staging and/or production services
   - Configure environment variables (at least `SECRET_KEY` and `APP_ENV`)
   - Disable auto-deploy (set to Manual)

2. **Add GitHub Secrets**:
   - Go to repository Settings → Actions → New repository secret
   - Add `RENDER_API_KEY`, `RENDER_SERVICE_ID_*` (and optionally `*_ENV_GROUP_ID_*`)

3. **Configure Branch Protection** (optional but recommended):
   - Settings → Branches → Add rule for `main`
   - Require PR reviews and status checks

4. **Push to develop**:
   ```bash
   git push origin develop
   ```
   - Triggers staging deployment automatically
   - Watch in GitHub → Actions

5. **When ready for production**:
   - Create PR from `develop` → `main`
   - Merge after review
   - Production deployment triggers automatically

---

## 📦 Local Development

### `.env` File

Copy `.env.example` to `.env` and fill in values:

```bash
cp .env.example .env
# Edit .env with your local settings
```

Local development uses SQLite by default (no PostgreSQL needed). Set `DEBUG=true` for development mode.

### Running

```bash
# Backend
python src/backend/main.py

# Frontend only (optional - backend also serves static)
cd src/frontend && python -m http.server 3000

# Access: http://localhost:8000
```

### Git Hooks

Pre-commit and pre-push hooks automatically:
- Run syntax, linting, security checks
- Update documentation timestamps
- Run smoke tests (pre-push)

Install hooks: See `.git/hooks/` (auto-installed if using standard git setup)

To skip: `git commit --no-verify` or `git push --no-verify` (not recommended)

---

## 🧪 Quality Checks

Manual checks (before pushing):

```bash
# Install dev tools
pip install flake8 mypy black bandit

# Syntax
python -m py_compile src/backend/main.py

# Lint (critical errors)
flake8 src/backend/ --count --select=E9,F63,F7,F82 --show-source --statistics

# Full lint
flake8 src/backend/

# Type check
mypy src/backend/main.py --ignore-missing-imports

# Security scan
bandit -r src/backend/

# Format check
black --check src/backend/
```

---

## 🎯 Production Readiness Checklist

Before going live:

- [ ] Branch protection enabled on `main`
- [ ] GitHub Secrets added for both environments
- [ ] Render services created (staging + production)
- [ ] Environment variables set (at least `SECRET_KEY`, `APP_ENV`)
- [ ] Database provisioned (PostgreSQL for production)
- [ ] Smoke tests passing on staging
- [ ] Render logs monitored for errors
- [ ] Domain/DNS configured (if using custom domain)
- [ ] Backup strategy in place (PostgreSQL backups)
- [ ] Monitoring alerts configured (Render alerts)

---

## 📚 Documentation

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System design, modular architecture
- [FLYWAY.md](docs/FLYWAY.md) - Database migrations guide
- [API-REFERENCE.html](docs/API-REFERENCE.html) - API reference (offline-capable)
- [CI-CD-SETUP.md](docs/CI-CD-SETUP.md) - Detailed CI/CD setup and troubleshooting

---

**Last Updated**: 2026-03-30

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
| V2 | Add username index & create `user_profiles` | 2025-03-30 |

**v7.0 Simplification (2026-03-30):**
- Removed obsolete migrations V3-V6 that created multi-app tables
- Those tables (`app_registry`, `user_app_activity`, `game_scores`, `app_config`) are no longer used by the code
- They are **not automatically dropped** to preserve any existing data
- If you need to remove them, manually execute DROP TABLE statements (see `docs/FLYWAY.md`)

**Migration philosophy:** We only apply non-destructive migrations automatically. Table drops should be manual to prevent accidental data loss.

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
