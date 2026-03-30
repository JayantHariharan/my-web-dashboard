# PlayNexus Auth

> **Authentication-Only Backend** – Secure, minimal API for user management with automated CI/CD.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791.svg)](https://postgresql.org)
[![Render](https://img.shields.io/badge/Deploy-Render-4285F4.svg)](https://render.com)

---

## ✨ Features

- 🔐 **Secure authentication** – bcrypt + pepper, rate limiting, IP audit logging
- 🚀 **Automated CI/CD** – GitHub Actions → Render deployment (staging + production)
- 🗄️ **Versioned migrations** – Flyway-style SQL scripts (auto-applied)
- 📱 **Static frontend** – Cinematic UI with Matter.js physics (served by backend)
- ⚡ **Simplified architecture** – Auth-only, no unnecessary complexity
- 🔒 **Production-ready** – Branch protection, smoke tests, health checks

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, modular architecture, security |
| [FLYWOW.md](docs/FLYWAY.md) | Database migrations guide |
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

# List apps
curl http://localhost:8000/api/apps/

# List games
curl http://localhost:8000/api/games/

# Submit score
curl -X POST "http://localhost:8000/api/games/tic-tac-toe/scores?username=test" \
  -H "Content-Type: application/json" \
  -d '{"score":1500,"metadata":{"won":true}}'

# Get leaderboard
curl "http://localhost:8000/api/games/tic-tac-toe/leaderboard?limit=10"

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
  └─ develop  – staging/Test (auto-deploys on push)
       └─ feature/<name>  – feature branches (short-lived)
```

### Workflow

1. **Development**: Create feature branches from `develop`
2. **Staging**: Push to `develop` → auto-deploys to **staging** environment
3. **Testing**: Test features in staging (https://your-app.onrender.com)
4. **Production**: Create PR from `develop` → `main`, merge → auto-deploys to **production**

> **Note**: Direct pushes to `main` are blocked by branch protection. Only PR merges trigger production deployment.

### GitHub Actions Triggers

| Event | Branches | Result |
|-------|----------|--------|
| Push to `develop` | develop | ✅ Deploy to staging |
| Merge PR to `main` | main | ✅ Deploy to production |
| Push to `main` | main | ❌ Blocked by branch protection |
| PR to `main` | any → main | ✅ Run quality checks only |

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

1. **On push to `develop`**:
   - Sets `APP_ENV=test`
   - Uses `RENDER_SERVICE_ID_TEST` (or `RENDER_SERVICE_ID` if using single service)
   - Deploys to Render staging service
   - Runs smoke tests
   - Access staging at: `https://your-staging-service.onrender.com`

2. **On merge to `main`**:
   - Sets `APP_ENV=production`
   - Uses `RENDER_SERVICE_ID_PROD` (or `RENDER_SERVICE_ID`)
   - Deploys to Render production service
   - Runs smoke tests
   - Access production at: `https://your-prod-service.onrender.com`

### Environment Groups (Optional)

Render Environment Groups allow you to:
- Share environment variables across multiple services
- Have consistent staging/production configs
- Switch services between groups easily

**If using Environment Groups**:
- Set `RENDER_ENV_GROUP_ID` (production) and `RENDER_ENV_GROUP_ID_TEST` (staging) secrets
- The workflow auto-associates your service with the correct group
- If not set, the workflow continues normally (no association)

### Render Service Setup

You need **one or two Render services**:

- **Single service** (same service for staging and production) - use environment variable `APP_ENV` to differentiate
- **Two services** (recommended for isolation) - separate staging and production services

**Recommended: Two services**

| Environment | Service Name | Branch | Render Variables |
|-------------|--------------|--------|------------------|
| Staging | `playnexus-staging` | develop | `APP_ENV=test` |
| Production | `playnexus` | main | `APP_ENV=production` |

**Configure each service**:
- Disable "Auto-Deploy" (set to Manual)
- Add environment variables (see below)
- The GitHub Actions workflow will trigger deploys via Render API

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
- `RENDER_ENV_GROUP_ID_TEST` - (Optional) Environment Group ID for staging

**Production secrets**:
- `RENDER_API_KEY` - Render API key
- `RENDER_SERVICE_ID_PROD` - Production service ID (e.g., `srv-prod-xxx`)
- `RENDER_ENV_GROUP_ID_PROD` - (Optional) Environment Group ID for production

### Option B: Single Service

If using the same Render service for both staging and production (switching only by `APP_ENV`):

**Both branches use the same service**:
- `RENDER_API_KEY` - Render API key
- `RENDER_SERVICE_ID` - Service ID (same for staging and production)
- `RENDER_ENV_GROUP_ID` - (Optional) Environment Group ID (if used)

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

See the full troubleshooting guide in `docs/CI-CD-SETUP.md`.

Common issues:
- Missing GitHub secrets → Validate in workflow step "Validate secrets"
- Environment group association failure → Not critical, will continue
- Health check failure → Check Render environment variables, database connection
- Smoke test failure → Verify frontend built correctly, Playwright dependencies
- Deployment timeout → Check Render build queue, cancel stuck deploys

---

**Last updated**: 2025-03-30

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
   - `RENDER_ENV_GROUP_ID_PROD` (from Render Environment Groups: evm-xxx)

   **For Test/Development** (develop branch):
   - `RENDER_API_KEY_TEST` (API key from a separate Render account or same account)
   - `RENDER_SERVICE_ID_TEST` (service ID for test service)
   - `RENDER_ENV_GROUP_ID_TEST` (environment group ID for TEST group)

5. **Disable Auto-Deploy on Render** (set to Manual)
   - GitHub Actions will trigger deploys manually

6. **Push to main** → First deployment starts automatically

---

## 🔧 Configuration

### Rate Limits

Rate limits are per IP address and vary by app category:

| Category | Endpoints | Limit | Block |
|----------|-----------|-------|-------|
| Auth | `/api/auth/*` | 20/hr | 15min |
| Games | `/api/games/*` | 100/hr | 10min |
| Apps | `/apps/*` | 200/hr | 10min |
| Health | `/health` | Unlimited | - |

### Database

- **Development**: SQLite (`sqlite:///./data/playnexus.db`) – no setup needed
- **Production**: PostgreSQL (recommended: Supabase or Render PostgreSQL)

Migrations are auto-applied on startup via `migrator.py` (also run in CI before deploy).

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
│   │   ├── core/         # App factory, middlewares, migrator
│   │   └── main.py       # Entry point
│   └── frontend/         # Static HTML/CSS/JS (served by backend)
├── docs/                 # Documentation
│   ├── ARCHITECTURE.md   # Architecture deep-dive
│   ├── FLYWAY.md        # Migration guide
│   └── API-REFERENCE.html  # Static API reference
├── flyway/sql/           # Database migrations (V1-V2)
├── tests/                # Smoke tests (Playwright)
├── .github/workflows/    # CI/CD pipeline
├── README.md             # This file
├── CLAUDE.md             # Claude Code guidance
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

### Adding a New App

1. **Backend**: Create module in `src/backend/apps/` or new category
   - Add `router.py` with endpoints
   - Register app in `app_registry` table (new migration or admin API)

2. **Frontend**: Create page in `src/frontend/app/`
   - `myapp.html` + `js/myapp.js`
   - Link from hub grid (auto-fetched from `/api/apps`)

3. **Documentation**: Update API docs (Swagger automatically picks up endpoints)

4. **Rate Limit**: Choose appropriate limiter (auth/games/apps) or create new

### Code Quality

Pre-commit hooks enforce:
- Python syntax check
- Flake8 linting (critical errors)
- Secret scanning (no leaked credentials)
- Auto-update doc timestamps

Pre-push hooks run full suite:
- All pre-commit checks
- MyPy type checking
- Bandit security scan
- Black code formatting check
- Smoke test (if backend running)

Run manually:
```bash
# Individual checks
flake8 src/backend/main.py --count --select=E9,F63,F7,F82 --show-source --statistics
mypy src/backend/main.py
black --check src/backend/
bandit -r src/backend/
```

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

If multi-app functionality (apps, games) is needed later, refer to `CLAUDE.md` "Extending the System" section for migration guidance.

---

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

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

**Last updated**: 2025-03-30
