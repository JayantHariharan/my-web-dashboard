# Developer Guide (DEVELOPER.md)

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

**Git hooks** (automatic, run locally before committing/pushing):

#### `pre-commit` (fast checks on every commit)
- ✅ Python syntax validation
- ✅ Code formatting check (black)
- ✅ Critical lint errors (flake8)
- ✅ Hardcoded secret detection
- ✅ TODO/FIXME warnings
- ✅ Auto-updates documentation timestamps
- **Blocks** commits with syntax errors, formatting issues, or critical lints

#### `pre-push` (comprehensive checks before pushing to main/develop)
- ✅ All pre-commit checks (syntax, formatting, lint)
- ✅ Type checking (mypy)
- ✅ Full security scan (bandit)
- ✅ AI Security Analysis (if `OPENROUTER_API_KEY` set)
- ✅ Critical/High security issues block push
- ✅ No debug print() statements
- ✅ No large files (>1MB)
- **Runs only on `main` and `develop` branches** (skipped on feature branches for speed)
- **Blocks** pushes with Critical/High security vulnerabilities

#### `commit-msg` ( Conventional Commits )
- ✅ Enforces commit message format: `type(scope): description`
- ✅ Validates types: feat, fix, docs, style, refactor, perf, test, build, chore, ci
- ✅ Requires descriptive messages (minimum 10 chars after colon)
- ✅ Allows WIP commits: `WIP: description`
- **Blocks** invalid commit messages

#### `pre-merge-commit` (optional safety net)
- ✅ Runs when merging locally with `git merge`
- ✅ Checks: syntax, formatting, lint, secrets
- Provides extra protection before local merges

**Installation** (hooks are auto-installed when cloning):
```bash
# If hooks not working, run installer:
./scripts/install-hooks.sh

# Or manually:
cp scripts/templates/* .git/hooks/
chmod +x .git/hooks/pre-commit .git/hooks/pre-push .git/hooks/commit-msg .git/hooks/pre-merge-commit
chmod +x scripts/run-quality-checks.sh
```

**Manual quality check** (run anytime):
```bash
./scripts/run-quality-checks.sh
```
Runs all checks with detailed output: syntax, formatting, lint, type check, bandit, AI security analysis, secrets detection, migration verification, doc freshness.

**Bypass hooks** (NOT recommended):
```bash
git commit --no-verify    # Skip pre-commit & commit-msg
git push --no-verify      # Skip pre-push
```
Only bypass for emergencies (e.g., hotfix). Never bypass security checks - you risk pushing vulnerable code.

**Note**: Hooks automatically update "Last Updated" dates in `docs/DEVELOPER.md`, `docs/ARCHITECTURE.md`, `docs/FLYWAY.md`, `docs/TROUBLESHOOTING.md` and stage them. Commit these changes separately.

**Manual quality check** (run anytime):
```bash
./scripts/run-quality-checks.sh
```
This runs all the same checks as the hooks, plus:
- Database migration verification
- Documentation date freshness check
- Comprehensive JSON reports

**Note**: Hooks automatically update "Last Updated" dates in `docs/DEVELOPER.md`, `docs/ARCHITECTURE.md`, `docs/FLYWAY.md`, `docs/TROUBLESHOOTING.md` and stage them. Commit these changes separately.

### GitHub Actions CI/CD

**Workflows**:
- `quality.yml` – Code quality & security checks (lint, type, bandit, Claude AI security scan)
  - Runs on: push to `main`/`develop`, PRs to `main`/`develop`
  - Requires: `ANTHROPIC_API_KEY` secret for Claude security analysis
  - Fails on: Critical/High severity security issues
  - Artifacts: `quality-reports` (bandit-report.json, claude-security-report.json)
  - **Blocks deployment** – Deploy workflow depends on this passing

- `deploy.yml` – Deploy to Render (staging/production)
  - Triggered on: push to `main` (production) or `develop` (staging)
  - Requires quality checks to pass first
  - Includes: precheck, migration, deployment, health checks, smoke tests

- `flyway-migrate.yml` – Database migration runner
  - Called by deploy workflow

**Required Secrets** (Settings → Secrets and variables → Actions):

| Secret | Purpose |
|--------|---------|
| `OPENROUTER_API_KEY` | **Recommended** - OpenRouter API key (free tier available). Sign up at https://openrouter.ai, get API key. OpenRouter offers many models including Claude, Llama, etc. **Free tier includes generous usage limits**. |
| *(Optional)* `OPENROUTER_MODEL` | Which AI model to use for security scanning. Default: `meta-llama/llama-3.3-70b-instruct` (free, excellent quality). Other free options: `mistralai/mixtral-8x7b-instruct`. Paid Claude models: `anthropic/claude-3-opus`, `anthropic/claude-3-sonnet`. |
| *(Alternative)* `ANTHROPIC_API_KEY` | Direct Anthropic API key (more expensive, no free tier). Only use if you prefer Anthropic directly. |
| `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` | PostgreSQL connection (required) |
| `RENDER_API_KEY` | Render deployment API access (required) |
| `RENDER_SERVICE_ID_PROD` | Production Render service ID (required for production) |
| `RENDER_SERVICE_ID_TEST` | Staging Render service ID (required for staging) |

**Claude Security Scanner** (`.github/scripts/claude_security_scan.py`):
- Uses AI (via OpenRouter or Anthropic) for deep security analysis
- Checks: hardcoded secrets, SQL injection, command injection, XSS, auth bypass, crypto failures, **secret exfiltration attempts**, etc.
- Specifically detects suspicious patterns:
  - Environment variable access + network transmission
  - Printing/logging of sensitive data
  - Reading files like `.env`, `config.json`, `secrets.json`
  - Suspicious imports (paramiko, ftplib)
  - Base64 encoding before transmission
- Produces structured JSON report with severity levels and remediation guidance
- **Blocks deployment on Critical/High findings**
- **Blocks PR merges when configured with branch protection**

### Securing Public Repos: Branch Protection

**CRITICAL**: In a public repository, malicious actors can submit PRs. You MUST enable branch protection to prevent merging code with security issues.

#### Setup Branch Protection:

1. Go to repository → **Settings** → **Branches**
2. Click **Add rule**
3. **Branch name**: `main`
4. Enable these options:
   ```
   ✅ Require a pull request before merging
      - Require approvals: 1 (or your preferred count)
   ✅ Require status checks to pass before merging
      - Search for and select: "code-quality"
        (This is the job name from quality.yml)
   ✅ Require linear history (optional but recommended)
   ```
5. Click **Create** or **Save changes**

#### Repeat for `develop` branch:
Add another rule for `develop` with same settings to protect staging.

#### What This Does:
- PRs cannot be merged until ✅ **quality.yml** passes
- Security scans (Claude, bandit, flake8, mypy) must all pass
- If any check finds Critical/High issues, merge button is disabled
- Protects against malicious code including secret exfiltration attempts

#### Before Merging a PR:
- Check GitHub Actions tab → quality.yml run
- Ensure all steps passed (green checkmarks)
- Review any security report artifacts
- **Do not bypass** failed security checks!

### GitHub's Built-in Secret Scanning

GitHub automatically scans for hardcoded secrets in **public repos**:
- Enabled by default for public repos (free)
- Detects: API keys, tokens, passwords
- Alerts you if secrets are found
- Can automatically revoke leaked secrets (if supported by provider)

No additional setup needed - just be aware it's active.


### Configuring OpenRouter (Free Tier)

**1. Get Your OpenRouter API Key**:
  - Go to https://openrouter.ai
  - Sign up / Log in
  - Navigate to **Account** → **API Keys** (or https://openrouter.ai/account/api-keys)
  - Click **Create Key**
  - Copy your API key (starts with `sk-or-`)
  - **Free credits**: OpenRouter provides generous free tier usage (likely $1+ credit to start, no time expiration)

**2. Choose a Free Model** (Recommended: `meta-llama/llama-3.3-70b-instruct`):
  - Excellent quality, completely free on OpenRouter
  - Visit: https://openrouter.ai/models
  - Search: `meta-llama/llama-3.3-70b-instruct`
  - **Alternative free models**:
    - `mistralai/mixtral-8x7b-instruct` (good quality, fast)
    - `google/gemma-7b-it` (lighter weight)
  - **Claude models** (if you want actual Claude): `anthropic/claude-3-haiku` (paid but cheap), `anthropic/claude-3-sonnet`, `anthropic/claude-3-opus` (paid)

**3. Add GitHub Secrets**:
  - Repository → Settings → Secrets and variables → Actions → New repository secret
  - **Name**: `OPENROUTER_API_KEY`
  - **Value**: Your OpenRouter API key
  - Optional: Add `OPENROUTER_MODEL` with model name (default: `meta-llama/llama-3.3-70b-instruct`)

**4. Verify Setup**:
  - Push to `develop` branch
  - GitHub Actions → quality.yml should run
  - Look for "Claude Security Analysis (OpenRouter Free Tier)" step
  - Check artifacts for `claude-security-report.json`

**Note**: The scanner will automatically use OpenRouter if `OPENROUTER_API_KEY` is set. If you also set `ANTHROPIC_API_KEY`, OpenRouter takes priority. Leave `ANTHROPIC_API_KEY` unset to ensure free tier usage.

**Install dev tools** (for hooks & manual checks):
- `/security-scan` – Security audit (bandit, auth patterns, secrets)
- `/code-quality` – Lint, type check, formatting review
- `/deploy-ready` – Verify deployment readiness

**Install dev tools** (for hooks & manual checks):
```bash
pip install flake8 mypy black bandit anthropic openai
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

**Migrations**: Flyway-style in `flyway/sql/` (V1..V2). Applied via GitHub Actions using Flyway CLI during deployment (not on application startup). Locally, use SQLite which auto-creates schema, or run Flyway manually if needed.

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
- (Optional) Override any config by adding rows to `app_config` for env='test'

**Production Service** (main branch):
- Environment Group: `PROD`
- Add `APP_ENV=production`
- GitHub Secrets needed:
  - `RENDER_API_KEY` (API key from Render account)
  - `RENDER_SERVICE_ID_PROD` (service ID: srv-xxx)
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

**Simple deployment workflow** - quality checks not automated:

1. **Deploy-staging job** (on push to `develop`):
   - Validates staging secrets (fails fast if missing)
   - Verifies Render service accessibility
   - Auto-associates Render Environment Group (if configured)
   - Triggers staging deployment via Render API
   - Monitors deployment progress (max 30 min)
   - Health checks (`/health`, `/api/auth/login`)
   - Runs Playwright smoke test on deployed site
   - Prints comprehensive deployment summary

3. **Deploy-production job** (only on push to `main`):
   - Validates production secrets (fails fast if missing)
   - Verifies Render service accessibility
   - Auto-associates Render Environment Group (if configured)
   - Triggers production deployment via Render API
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

**Required Secrets:**

| Secret Name | Description | Notes |
|-------------|-------------|-------|
| `RENDER_API_KEY` | Your Render API key | **Same key for both staging & production** |
| `RENDER_SERVICE_ID` | Production service ID (`srv-xxx`) | For `main` branch |
| `RENDER_SERVICE_ID_TEST` | Staging service ID (`srv-xxx`) | For `develop` branch |

**Note:** You need **one Render service for staging** and **one for production** (or the same service with different `APP_ENV`). The service IDs will be different. But you can reuse the same API key for both.

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

### Deployment Troubleshooting

Experiencing deployment issues? See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for:
- Quick diagnostic commands
- Common issues & solutions (Auto-Deploy, Service ID, API key)
- Manual API testing guide
- Expected workflow output
- Step-by-step debugging

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

**Last Updated**: 2026-04-01

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
│   │   ├── core/         # App factory, middlewares
│   │   └── main.py       # Entry point
│   └── frontend/         # Static HTML/CSS/JS (modular structure)
├── docs/                 # Documentation (ARCHITECTURE.md, FLYWAY.md, API-REFERENCE.html)
├── flyway/               # Database migrations
│   └── sql/              # V1..V5
├── tests/                # Smoke tests (Playwright)
├── .github/workflows/    # CI/CD
├── .claude/              # Claude Code config
├── .git/hooks/           # Git hooks (pre-commit, pre-push)
├── docs/                 # Documentation
│   ├── DEVELOPER.md      # This file
│   ├── ARCHITECTURE.md
│   ├── FLYWAY.md
│   ├── MIGRATIONS.md
│   └── API-REFERENCE.html
├── README.md             # Quick start
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
- Fixed SQLite compatibility issues in Flyway migrations (placeholder substitution, JSON → TEXT, separated INDEX statements)
- Updated deprecated FastAPI constants

### Code Cleanup
- Removed unused files: `src/backend/database.py`, `src/backend/security.py`, `src/backend/rate_limiter.py` (moved functionality to `shared/`)
- Removed `src/shared/` empty folder
- Updated `.gitignore` to include `.claude/` and `*.db`
- Database file correctly placed in `data/` directory (`./data/playnexus.db`)

### Database
- SQLite database auto-initialized with schema (3 tables: users, user_profiles, schema_version). Table names include environment-based suffixes in production (e.g., users_test, users_prod).
- Migration system now fully functional for development
