# PlayNexus

> **Ultra-Modern Gaming Platform** – Secure authentication backend with stunning glassmorphism UI, animated backgrounds, and cinematic user experience.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791.svg)](https://postgresql.org)
[![Render](https://img.shields.io/badge/Deploy-Render-4285F4.svg)](https://render.com)

---

## ✨ Features

- 🔐 **Secure authentication** – bcrypt + pepper, rate limiting, IP audit logging
- 🚀 **Automated CI/CD** – GitHub Actions → Render deployment (staging + production)
- 🗄️ **Versioned migrations** – SQL-based migrations via Python script
- 📱 **Ultra-Modern UI** – Fortnite-inspired glassmorphism, neon glows, liquid crystal animations
- 🎮 **Gaming Aesthetic** – Dynamic background orbs, grid overlays, cinematic entrance animations
- ⚡ **Responsive Design** – Perfect on desktop, tablet, and mobile
- 🔒 **Production-ready** – Branch protection, smoke tests, health checks, concurrency control

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [DEVELOPER.md](docs/DEVELOPER.md) | Claude Code integration, development workflow, git hooks |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, modular architecture, security |
| [FLYWAY.md](docs/FLYWAY.md) | Database migrations guide (Flyway-based) |
| [MIGRATIONS.md](docs/MIGRATIONS.md) | Migration philosophy & best practices |
| [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common issues and solutions |
| [API-REFERENCE.html](docs/API-REFERENCE.html) | **Static HTML API reference** (offline-capable) |

**Interactive API docs** (when server running):
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

---

## 🚀 Quick Start (Local)

### Prerequisites
- Python 3.12+
- Node.js (optional, for tests)
- Git

### 1. Clone & Setup

```bash
git clone <your-repo>
cd my-web-dashboard

# Create virtual environment (recommended)
python -m venv venv
# On Windows: venv\Scripts\activate
# On macOS/Linux: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

### 2. Run Application

```bash
# Terminal 1: Start backend (FastAPI)
python src/backend/main.py
# → http://localhost:8000

# Terminal 2: Serve frontend (optional, backend also serves static)
cd src/frontend
python -m http.server 3000
# → http://localhost:3000
```

**Note**: Backend automatically serves frontend from `src/frontend/` at `/`. For development, you can use either.

### 3. Test API

```bash
# Signup
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"Test1234","confirm_password":"Test1234"}'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"Test1234"}'

# Get current user
curl "http://localhost:8000/api/auth/me?username=test"

# Health check
curl http://localhost:8000/health
```

### 5. Interactive API Docs

- **Swagger UI**: http://localhost:8000/docs (try API calls in browser)
- **ReDoc**: http://localhost:8000/redoc (clean documentation)

---

## 🌿 Branch Strategy

```
main        – production (auto-deploys on merge)
  └─ develop  – staging (auto-deploys on push)
       └─ feature/<name>  – feature branches (short-lived)
```

### Workflow

1. **Development**: Create feature branches from `develop`
2. **Staging**: Push to `develop` → auto-deploys to **staging** environment
3. **Testing**: Test features in staging (https://playnexus-test.onrender.com)
4. **Production**: Create PR from `develop` → `main`, merge → auto-deploys to **production**

> **Note**: Direct pushes to `main` are blocked by branch protection. Only PR merges trigger production deployment.

### GitHub Actions Triggers

| Event | Branches | Result |
|-------|----------|--------|
| Push to `develop` | develop | ✅ Deploy to staging |
| Merge PR to `main` | main | ✅ Deploy to production |
| Push to `main` | main | ❌ Blocked by branch protection |
| PR to `main` | any → main | ✅ Run quality checks only |

### CI/CD Workflows

- **`.github/workflows/quality.yml`** – Code quality, security scans, smoke tests
- **`.github/workflows/flyway-migrate.yml`** – Database migrations (reusable)
- **`.github/workflows/deploy.yml`** – Deployment orchestration with monitoring

---

## 🛡️ Branch Protection Rules (Setup Required)

To enforce the workflow above, configure branch protection on `main`:

1. Go to repository **Settings** → **Branches** → **Add rule**
2. Branch name pattern: `main`
3. Enable these protections:
   - ✅ **Require a pull request before merging**
     - Require approvals: `1` (or as needed)
   - ✅ **Require status checks to pass before merging**
     - Select: `quality` (from GitHub Actions)
   - ✅ **Require linear history**
     - Prevent merge commits (optional but recommended)
4. Click **Create** or **Save changes**

This ensures:
- No direct pushes to `main`
- All changes must go through PR review
- Quality checks must pass before merge
- Production deployments are intentional and controlled

---

## 🚢 Deployment Automation

### How It Works

The CI/CD pipeline (in `.github/workflows/deploy.yml`) automatically:

1. **Precheck** – validates secrets and database connectivity
2. **Migrate database** – applies Flyway migrations via `scripts/migrate.py` (reusable workflow)
3. **Deploy** – triggers Render deployment, monitors for up to 60 minutes, runs health checks
4. **Smoke test** – verifies frontend loads, takes screenshot for debugging

**On push to `develop`**:
- Sets `APP_ENV=test`
- Uses `RENDER_SERVICE_ID_TEST` (or `RENDER_SERVICE_ID`)
- Deploys to staging
- Smoke test falls back to `https://playnexus-test.onrender.com` if `SITE_URL` not provided

**On merge to `main`**:
- Sets `APP_ENV=production`
- Uses `RENDER_SERVICE_ID_PROD` (or `RENDER_SERVICE_ID`)
- Deploys to production
- Smoke test uses `https://playnexus.onrender.com` as fallback

### Render Service Setup

You need **one or two Render services**:

- **Single service** (same service for staging and production) - use environment variable `APP_ENV` to differentiate
- **Two services** (recommended for isolation) - separate staging and production services

**Recommended: Two services**

| Environment | Service Name | Branch | Render Variables |
|-------------|--------------|--------|------------------|
| Staging | `playnexus-test` | develop | `APP_ENV=test` |
| Production | `playnexus` | main | `APP_ENV=production` |

**Configure each service**:
- Disable "Auto-Deploy" (set to Manual) – GitHub Actions triggers deploys
- Add environment variables (see below)
- Health checks enabled (target: `/health` and `/api/auth/login`)

---

## 🏗️ Render Environment Variables

Set these in your Render service(s) → Environment tab:

| Variable | Required | Description |
|----------|----------|-------------|
| `APP_ENV` | ✅ Yes | `test` for staging, `production` for prod |
| `SECRET_KEY` | ✅ Yes | Password pepper: generate with `openssl rand -hex 32` |
| `PGHOST` | ⚠️ Conditional | PostgreSQL host (if using external DB) |
| `PGPORT` | ⚠️ Conditional | PostgreSQL port (usually 5432) |
| `PGUSER` | ⚠️ Conditional | PostgreSQL username |
| `PGPASSWORD` | ⚠️ Conditional | PostgreSQL password |
| `PGDATABASE` | ⚠️ Conditional | PostgreSQL database name |
| `DEBUG` | ❌ No | Default: `false` (keep false in production!) |
| `LOG_LEVEL` | ❌ No | Default: `INFO` |

> **Note**: If PostgreSQL variables are not set, the app uses SQLite (`./data/playnexus.db`), which is fine for single-instance Render deployments (Free/Starter plans).

---

## 🔐 GitHub Actions Secrets Setup

Add these secrets in: **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

### Option A: Separate Services (Recommended)

**Staging secrets**:
- `RENDER_API_KEY_TEST` - Render API key (same key can be used for both)
- `RENDER_SERVICE_ID_TEST` - Staging service ID (e.g., `srv-staging-xxx`)

**Production secrets**:
- `RENDER_API_KEY` - Render API key
- `RENDER_SERVICE_ID_PROD` - Production service ID (e.g., `srv-prod-xxx`)

### Option B: Single Service

If using the same Render service for both staging and production (switching only by `APP_ENV`):

**Both branches use the same service**:
- `RENDER_API_KEY` - Render API key
- `RENDER_SERVICE_ID` - Service ID (same for staging and production)

The workflow will:
- On `develop`: Use `RENDER_SERVICE_ID` and set `APP_ENV=test`
- On `main`: Use `RENDER_SERVICE_ID` and set `APP_ENV=production`

---

## 🧪 Manual Testing Workflow

1. **Develop locally**:
   ```bash
   git checkout develop
   git checkout -b feature/my-feature
   # Make changes, commit, push
   git push origin feature/my-feature
   ```

2. **Create PR** to `develop` (optional, for collaboration)

3. **Merge PR to `develop`** → triggers **staging deployment**

4. **Test staging**: Visit `https://your-staging-service.onrender.com`
   - Smoke test runs automatically via CI
   - Check Render logs if issues
   - Verify all features work

5. **When ready for production**:
   - Ensure `develop` is up-to-date and working
   - Create PR from `develop` → `main`
   - Review code, ensure all checks pass
   - Merge PR (do **not** push directly to `main`)
   - **Production deployment triggers automatically**

6. **Verify production**: Check production URL, run manual tests

---

## 📊 Monitoring Deployments

### GitHub Actions
- Go to repository **Actions** tab
- See all workflow runs with status badges
- Click any run for detailed logs
- Download artifact reports (lint, security)

### Render Dashboard
- Go to Render → Your service
- **Deployments** tab: see all deploy history, status, logs
- **Logs** tab: real-time application logs
- Set up **Alerts** → **Add Alert** for email/Slack notifications

---

## 🐛 Troubleshooting

See the full troubleshooting guide in `docs/TROUBLESHOOTING.md`.

Common issues:
- Missing GitHub secrets → Validate in workflow step "Validate secrets"
- Database connection fails → Verify PostgreSQL variables, network access
- Migration failure → Check SQL syntax, constraints (see `docs/MIGRATIONS.md`)
- Health check failure → Check Render environment variables, database
- Smoke test failure → Verify Playwright deps installed, frontend accessible
- Deployment timeout → Check Render build queue, cancel stuck deploys

---

**Last updated**: 2026-04-03

---

## 🚢 Deployment

Production deployment is **fully automated** via GitHub Actions to Render.

### One-Time Setup

1. **Create PostgreSQL database** (Supabase or Render PostgreSQL)
   - Get connection details (host, port, user, password, database name)

2. **Create Render Web Service**
   - Connect GitHub repository
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn src.backend.main:app --host 0.0.0.0 --port $PORT`
     (Alternative: `python src/backend/main.py` – both work)
   - Set environment (see below)

3. **Configure Render Environment Variables**

| Variable | Value |
|-----------|-------|
| `PGHOST` | Your PostgreSQL host |
| `PGPORT` | Usually `5432` |
| `PGUSER` | PostgreSQL username |
| `PGPASSWORD` | PostgreSQL password |
| `PGDATABASE` | Database name |
| `SECRET_KEY` | `openssl rand -hex 32` (keep this secret!) |
| `DEBUG` | `false` |
| `LOG_LEVEL` | `INFO` |
| `APP_ENV` | `test` (dev) or `production` (prod) - for env-specific config |

4. **Add GitHub Secrets** (for GitHub Actions)

   **For Production** (main branch):
   - `RENDER_API_KEY` (from Render Account → API Keys)
   - `RENDER_SERVICE_ID_PROD` (from Render service URL: srv-xxx)

   **For Test/Development** (develop branch):
   - `RENDER_API_KEY_TEST` (API key from a separate Render account or same account)
   - `RENDER_SERVICE_ID_TEST` (service ID for test service)

5. **Disable Auto-Deploy on Render** (set to Manual)
   - GitHub Actions will trigger deploys manually

6. **Initial deployment**:
   - Push to `develop` branch → triggers staging deployment
   - Create PR from `develop` → `main`, merge → triggers production deployment
   - (Direct pushes to `main` are blocked by branch protection)

---

## 🔧 Configuration

### Rate Limits

Rate limits are per IP address:

| Category | Endpoints | Limit | Block |
|----------|-----------|-------|-------|
| Auth | `/api/auth/*` | 20/hr | 15min |
| Health | `/health` | Unlimited | - |

*Note: Multi-app endpoints (games, apps) are currently disabled as the system focuses on authentication-only.*

### Database

- **Development**: SQLite (`sqlite:///./data/playnexus.db`) – no setup needed
- **Production**: PostgreSQL (recommended: Supabase or Render PostgreSQL)

Migrations are applied via GitHub Actions using Python script (see `flyway-migrate.yml` workflow). Locally, SQLite auto-creates the schema; for PostgreSQL, run `python scripts/migrate.py` manually or deploy via CI.

### Environment Variables

All configuration is via environment variables (set in Render environment groups or locally):

#### Database

| Variable | Required | Description |
|----------|----------|-------------|
| `PGHOST` | Yes* | PostgreSQL host (e.g., abc.supabase.co) |
| `PGPORT` | Yes* | Port (usually 5432) |
| `PGUSER` | Yes* | Username (usually postgres) |
| `PGPASSWORD` | Yes* | Database password |
| `PGDATABASE` | Yes* | Database name |
| `DATABASE_URL` | Alternative | Full connection string (overrides PG*) |
| `DB_SCHEMA` | No | PostgreSQL schema name (default: `public`). Useful for custom schemas like `playnexus`. |

#### Application

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Production | Password pepper – generate: `openssl rand -hex 32` |
| `DEBUG` | No | Enable debug mode (default: false) |
| `LOG_LEVEL` | No | DEBUG/INFO/WARNING/ERROR (default: INFO) |
| `APP_ENV` | Recommended | Environment name: `test` (develop) or `production` (main) for env-specific config |

*Required for PostgreSQL. If not set, falls back to SQLite (`sqlite:///./data/playnexus.db`).

---

## 📁 Project Structure

```
my-web-dashboard/
├── src/
│   ├── backend/          # Auth-only FastAPI application
│   │   ├── shared/       # Database, security, schemas, exceptions
│   │   ├── auth/         # Authentication module
│   │   ├── core/         # App factory, middlewares
│   │   └── main.py       # Entry point
│   └── frontend/         # Static HTML/CSS/JS (served by backend)
├── docs/                 # Documentation
│   ├── DEVELOPER.md      # Claude Code guidance, development workflow
│   ├── ARCHITECTURE.md   # Architecture deep-dive
│   ├── FLYWAY.md        # Migration guide
│   ├── MIGRATIONS.md    # Migration philosophy & best practices
│   └── API-REFERENCE.html  # Static API reference
├── flyway/sql/           # Database migrations (V1-V2)
├── tests/                # Smoke tests (Playwright)
├── .github/workflows/    # CI/CD pipeline
├── README.md             # This file
├── requirements.txt      # Python dependencies
├── runtime.txt          # Python version (3.12)
└── .env.example         # Environment template
```

---

## 🔒 Security

- Passwords hashed with **bcrypt** + **pepper** (`SECRET_KEY`)
- **Constant-time comparison** prevents timing attacks
- **Rate limiting** per endpoint category
- **IP audit logging** (`created_ip`, `last_login_ip`)
- **Parameterized queries** – no SQL injection
- **Generic error messages** – doesn't reveal user existence
- **CORS configured** for allowed origins
- **SECRET_KEY validation** in production (aborts if missing)

---

## 🧪 Testing

### Manual Tests

```bash
# Start backend
python src/backend/main.py

# In another terminal, run smoke test (requires SITE_URL)
export SITE_URL=http://localhost:8000
npm install playwright && npx playwright install chromium
node tests/smoke.test.js
```

### Unit Tests (To Add)

Create `tests/unit/test_auth.py`, `test_database.py`, etc.
Run with `pytest tests/`.

---

## 🛠️ Development

### Extending the System

**Note**: Multi-app features (apps, games, social) are currently on hold. The system is intentionally simplified to authentication-only. If adding multi-app support in the future, refer to `docs/DEVELOPER.md` for migration guidance.

### Code Quality

The project uses **comprehensive quality checks** via git hooks:

**Pre-commit hooks** (automatic on `git commit`):
- Python syntax check
- Hardcoded secrets detection (fast pattern match)
- Check for TODO/FIXME comments in staged files
- Workflow validation (YAML syntax, concurrency, artifact retention)
- Auto-update documentation timestamps

**Pre-push hooks** (automatic on `git push`):
- All pre-commit checks
- Branch up-to-date validation (feature branches)
- Comprehensive manual quality scan (`./scripts/run-quality-checks.sh`)
- Optional smoke test (if backend accessible)

**Manual quality checks**:
```bash
# Run comprehensive quality & security checks
./scripts/run-quality-checks.sh

# Individual Python check
python -m py_compile src/backend/main.py  # syntax check
```

See `docs/DEVELOPER.md` for complete details on git hooks and development workflow.

---

## 📈 Roadmap

**Current Focus: Authentication-Only Backend**

- [ ] JWT authentication (persistent sessions) - upgrade from session-based
- [ ] Redis rate limiting (multi-instance scaling)
- [ ] Email verification (SendGrid)
- [ ] Password reset flow
- [ ] Two-factor authentication (2FA)
- [ ] User profile pictures (DiceBear/Cloudinary)
- [ ] Admin dashboard (user management)
- [ ] API analytics dashboard
- [ ] Docker containerization
- [ ] PWA offline support

*Note: Multi-app features (games, social) are on hold. The system is intentionally simplified to authentication-only.*

---

## 🎮 Future: Re-adding Multi-App Support

If multi-app functionality (apps, games) is needed later, refer to `docs/DEVELOPER.md` "Extending the System" section for migration guidance.

---

---

## 🤝 Contributing

See [docs/DEVELOPER.md](docs/DEVELOPER.md) for development guidelines, git hooks, and Claude Code integration.

---

## 📄 License

MIT – see [LICENSE](LICENSE) file.

---

## 🙏 Acknowledgments

Built with ❤️ using:
- [FastAPI](https://fastapi.tiangolo.com) – Modern Python web framework
- [Matter.js](https://brm.io/matter-js/) – 2D physics engine
- [Render](https://render.com) – Cloud hosting
- [Supabase](https://supabase.com) – PostgreSQL database

---

**Last updated**: 2026-04-03
