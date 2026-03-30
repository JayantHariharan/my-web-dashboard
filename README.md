# PlayNexus

> **Multi-App Platform** – A modular gaming hub with secure authentication, extensible architecture, and cinematic UI.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791.svg)](https://postgresql.org)
[![Render](https://img.shields.io/badge/Deploy-Render-4285F4.svg)](https://render.com)

---

## ✨ Features

- 🔐 **Secure authentication** – bcrypt + pepper, rate limiting, IP audit logging
- 🎮 **Multi-app platform** – Easy to add new games and utilities
- 📊 **App registry** – Centralized app catalog with activity tracking
- 🏆 **Leaderboards** – Game scores with global rankings
- 🎨 **Cinematic UI** – Matter.js physics, dark theme, responsive design
- 🚀 **Automated CI/CD** – GitHub Actions → Render deployment
- 🗄️ **Versioned migrations** – Flyway-style SQL scripts
- 📱 **Mobile-first** – Works on all devices

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

# Copy environment template
cp .env.example .env
# Edit .env: set SECRET_KEY to a random string (e.g., openssl rand -hex 32)
```

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

### 3. Configure Environment

Edit `.env`:

```env
# Database options:

# Option A: Individual PG* variables (Render/Supabase)
PGHOST=localhost
PGPORT=5432
PGUSER=postgres
PGPASSWORD=yourpassword
PGDATABASE=playnexus

# Option B: Single connection string
# DATABASE_URL=postgresql://postgres:password@localhost:5432/playnexus

# Application
SECRET_KEY=openssl rand -hex 32  # Required in production
DEBUG=true                       # Set to false in production
LOG_LEVEL=INFO                   # DEBUG, INFO, WARNING, ERROR
```

### 4. Test API

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
main        – production (auto-deploys via GitHub Actions)
  └─ develop  – integration (experimental, no auto-deploy)
       └─ feature/<name>  – feature branches (short-lived)
```

- **main**: Every push triggers deployment to Render
- **develop**: Safe for experiments (no auto-deploy)
- **feature/\***: Create from `develop`, merge back via PR

---

## 🚢 Deployment

Production deployment is **fully automated** via GitHub Actions to Render.

### One-Time Setup

1. **Create PostgreSQL database** (Supabase or Render PostgreSQL)
   - Get connection details (host, port, user, password, database name)

2. **Create Render Web Service**
   - Connect GitHub repository
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
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

See [`.env.example`](.env.example) for complete list.

### Environment-Specific Configuration

For test and production, you can define runtime-configurable settings in the `app_config` database table. Set `APP_ENV` to `test` (develop branch) or `production` (main branch), and the app will load corresponding values automatically.

**Predefined settings:**

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `site_name` | string | "PlayNexus" | Site display name |
| `maintenance_mode` | boolean | false | Enable maintenance page |
| `registration_enabled` | boolean | true | Allow new signups |
| `debug_features_enabled` | boolean | false | Show debug features |
| `max_upload_size` | integer | 52428800 (50MB) | Max file upload size |
| `rate_limit_requests` | integer | 10000 | Requests per hour per IP |
| `allow_cors` | string | "\*" | CORS allowed origins |

**How to modify:**
- Insert/update rows in `app_config` table for your environment
- Changes take effect on next app restart (or implement hot-reload)
- No redeploy needed for config changes!

---

## 📁 Project Structure

```
my-web-dashboard/
├── src/
│   ├── backend/          # Modular FastAPI application
│   │   ├── shared/       # Shared: database, security, schemas, exceptions
│   │   ├── auth/         # Authentication module
│   │   ├── core/         # App factory, middlewares, migrator
│   │   ├── games/        # Games module
│   │   ├── apps/         # General apps module
│   │   └── main.py       # Entry point
│   └── frontend/         # Static HTML/CSS/JS
│       ├── app/          # App pages (hub, games, profile)
│       ├── js/           # Modular JavaScript
│       ├── css/          # CSS components
│       └── assets/       # Images, logos
├── docs/                 # Documentation
│   ├── ARCHITECTURE.md   # Architecture deep-dive
│   ├── FLYWAY.md        # Migration guide
│   └── API-REFERENCE.html  # Static API reference
├── flyway/sql/           # Database migrations (V1..V5)
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

- [ ] JWT authentication (persistent sessions)
- [ ] Redis rate limiting (multi-instance)
- [ ] User profile pictures (DiceBear/Cloudinary)
- [ ] More games: puzzle, arcade, strategy
- [ ] Achievements & badges system
- [ ] Social features (friends, chat)
- [ ] Admin dashboard
- [ ] Email verification (SendGrid)
- [ ] Password reset flow
- [ ] Two-factor authentication (2FA)
- [ ] API analytics dashboard
- [ ] PWA offline support
- [ ] Docker containerization

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
