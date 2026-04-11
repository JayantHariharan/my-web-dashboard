# PlayNexus

Auth-first web app: **FastAPI** serves JSON auth APIs and static files from `src/frontend/`. After login, the hub links **Games**, **Apps**, **Community**, and **About**. Tuned for **Render** + **Supabase (PostgreSQL)** on small plans.

## Tech stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12+, FastAPI |
| Frontend | HTML, CSS, vanilla JS (Crystal Portal CSS, Sound Engine API) |
| Database | SQLite/PostgreSQL with Flyway Migrations |
| AI Agent | Minimax + Alpha-Beta Pruning (Nexus Agent Alpha) |
| Security | Adaptive bcrypt + pepper, security headers, rate limiting |

## API (quick reference)

| Method | Path | Notes |
|--------|------|--------|
| `POST` | `/api/auth/login` | Body: `username`, `password` |
| `POST` | `/api/auth/signup` | Body: `username`, `password`, `confirm_password` |
| `GET` | `/api/auth/me?username=…` | Temporary demo; JWT token auth is on the roadmap |
| `DELETE` | `/api/auth/account` | Body: `username`, `password`, optional `confirm_username` |
| `GET` | `/health` | Database connectivity ping |
| `GET` | `/docs` | OpenAPI Swagger UI (when server is running) |

## Local run

```bash
pip install -r requirements.txt
python -m uvicorn src.backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Open `http://127.0.0.1:8000` in any modern browser.

| Page | Access |
|------|--------|
| `/` | Sign-in + hub (public) |
| `/about/about.html` | Public |
| `/games/games.html` | Redirects to `/` if not signed in |
| `/community/community.html` | Redirects to `/` if not signed in |

**Static-only preview** (API calls will fail without a running backend):

```bash
cd src/frontend && python -m http.server 3000
```

## Environment variables

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string (e.g. Supabase). Falls back to individual `PG*` vars, then SQLite. |
| `SECRET_KEY` | **Required in production.** Do **not** rotate casually — existing password hashes depend on it. |
| `DEBUG` | `true` / `1` enables dev CORS origins and debug-level logging. |
| `CORS_ORIGINS` | Comma-separated origins; overrides the environment-specific default list in `core/app.py`. |
| `REGISTRATION_ENABLED` | Set to `false` to disable new signups (`403` on `/api/auth/signup`). |
| `ENV` / `APP_ENV` | `prod`/`production` → `_prod` table suffix; `test`/`dev`/`staging` → `_test`; unset → default (no suffix). |

## Project layout

```text
my-web-dashboard/
├── src/
│   ├── backend/
│   │   ├── auth/           # router.py – /api/auth/* endpoints
│   │   ├── core/           # app.py (factory), middlewares.py
│   │   ├── shared/         # database.py, schemas.py, security.py
│   │   ├── config.py       # Settings dataclass (reads env vars)
│   │   ├── log_config.py   # Console + rotating-file logging setup
│   │   └── main.py         # Entry point: lifespan, router, static mount
│   └── frontend/
│       ├── index.html      # Auth portal + signed-in hub (single page)
│       ├── css/            # style.css, crystal-portal.css, site-chrome.css
│       ├── js/             # main.js, cinematic-startup.js, site-chrome.js, toast.js
│       ├── assets/         # SVG covers, logo
│       ├── about/          # about.html
│       ├── games/          # games.html, tic-tac-toe.html
│       └── community/      # community.html
├── flyway/sql/             # Versioned SQL migrations (V1__initial_schema.sql, etc.)
├── scripts/                # migrate.py, run-quality-checks.sh, install-hooks.*
├── tests/                  # smoke.test.js (Playwright; run by deploy workflow)
├── data/                   # SQLite database (local dev only; git-ignored)
├── requirements.txt
└── README.md
```

## Application lifecycle

The backend uses FastAPI's **`lifespan` context manager** (introduced in FastAPI 0.93 / Starlette 0.27) instead of the deprecated `@app.on_event("startup")` / `@app.on_event("shutdown")` hooks.

Startup sequence (runs before the server accepts requests):

1. Log the active environment and database type.
2. Bootstrap the local SQLite schema from `flyway/sql/V1__initial_schema.sql` if needed.
3. Migrate any plain-text passwords to bcrypt (idempotent; no-op when all are already hashed).

Shutdown sequence:

- Emit a graceful shutdown log line.

## Database migrations

- SQL lives in `flyway/sql/`.
- Local helper: `python scripts/migrate.py` (see `--help`).
- Hosted: GitHub Action `.github/workflows/flyway-migrate.yml` runs Flyway against the production database on every merge to `main`.

## Deployment workflow

- GitHub Actions deploys from `.github/workflows/deploy.yml`.
- Pushes to `main` deploy production; pushes to `develop` deploy the shared test environment.
- Feature-branch pushes do not deploy to the shared Render service. Render deploys from a service's linked branch, and its manual deploy API defaults to the latest commit on that linked branch.
- For feature branches, use Render PR previews / service previews instead of trying to push feature-branch commits onto the shared test service.
- The workflow triggers a Render deploy, captures the returned deploy id, and waits for Render to report that deploy as complete before continuing.
- After Render finishes, the workflow polls `${SITE_URL}/health` until the service is ready, then runs the smoke test suite in `tests/smoke.test.js`.
- If the Render deploy fails or does not become healthy in time, the workflow stops before later verification steps run.

## Git hooks (optional)

Install from the repo root:

```bash
# macOS / Linux / Git Bash
./scripts/install-hooks.sh

# Windows PowerShell
pwsh -File scripts/install-hooks.ps1
```

Copy `.hooks-config.example.json` and adjust as needed (comments inside the file explain each option). CI runs `scripts/run-quality-checks.sh` on every PR.

## curl examples

```bash
# Register a new account
curl -X POST http://127.0.0.1:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"Test1234!","confirm_password":"Test1234!"}'

# Login
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"Test1234!"}'

# Health check
curl http://127.0.0.1:8000/health
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ImportError` when running `python src/backend/main.py` | Run from the **repo root** with `python -m uvicorn src.backend.main:app --reload` instead. |
| CORS errors from a different origin | Set `CORS_ORIGINS` on Render to your exact frontend URL(s). |
| Auth endpoints always return `429` | Rate limit is 20 requests/hour per IP; wait it out or test from a different network. |
| `bcrypt` warning in logs | The pure-Python pbkdf2 fallback is active but fully functional. Install `bcrypt` via pip for the preferred hashing backend. |
| `SECRET_KEY` warning on startup | Set the `SECRET_KEY` environment variable; the default `"change-me-in-production"` causes a hard crash when `ENV=prod`. |

## Security notes

- **`X-Frame-Options: DENY`** – clickjacking protection.
- **`Strict-Transport-Security`** – applied in production only (requires HTTPS).
- **`X-Content-Type-Options: nosniff`** – prevents MIME-sniffing attacks.
- **Constant-time password comparison** – a dummy hash is verified even when the username does not exist, preventing username enumeration via timing.
- **Logger hygiene** – passwords and sensitive values are never logged; only usernames and IP addresses appear in audit lines.

## Contributing

Open PRs against `main` or `develop`. Run `bash scripts/run-quality-checks.sh` before pushing. Keep changes focused and match the existing code style. Be respectful in issues and PRs.

## Product note

Session state today is **client-side** (`sessionStorage` / `localStorage`). `/api/auth/me` is a plain username lookup, not a JWT validation — token-based authentication is planned once the project outgrows this stage.

---

*Last updated: 2026-04-12*
