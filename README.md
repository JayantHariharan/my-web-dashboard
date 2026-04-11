# PlayNexus

Auth-first web app: **FastAPI** serves JSON auth APIs and static files from `src/frontend/`. After login, the hub links **Games**, **Apps**, **Community**, and **About**. Tuned for **Render** + **Supabase (PostgreSQL)** on small plans.

## Tech stack

- Backend: Python 3.12, FastAPI  
- Frontend: HTML, CSS, vanilla JS (`css/site-chrome.css`, `js/site-chrome.js` for shared header/footer)  
- DB: SQLite locally (`data/playnexus.db`); PostgreSQL in production via `DATABASE_URL`  
- Security: adaptive hashing + `SECRET_KEY` pepper, rate limits on `/api/auth/*`, security headers  
- CI/CD: GitHub Actions (quality, deploy, Flyway migrate)

## API (quick reference)

| Method | Path | Notes |
|--------|------|--------|
| POST | `/api/auth/login` | body: `username`, `password` |
| POST | `/api/auth/signup` | body: `username`, `password`, `confirm_password` |
| GET | `/api/auth/me?username=…` | Lightweight until token auth exists |
| DELETE | `/api/auth/account` | body: `username`, `password`, optional `confirm_username` |
| GET | `/health` | DB ping |
| GET | `/docs` | OpenAPI UI when the server is running |

## Local run

```bash
pip install -r requirements.txt
python -m uvicorn src.backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Open `http://127.0.0.1:8000`. Use **Chrome or Edge** (or any browser).  
Pages: `/` (sign-in + hub), `/about/about.html` (public), `/games/games.html` and `/community/community.html` (redirect to `/` if not signed in).

Optional static-only preview (API calls will fail unless you point the frontend at a running API):

```bash
cd src/frontend && python -m http.server 3000
```

## Environment variables

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string (e.g. Supabase). If unset, `PG*` vars or SQLite. |
| `SECRET_KEY` | **Required** in production-like envs. Do **not** rotate casually—existing password hashes depend on it. |
| `DEBUG` | `true` / `1` enables dev CORS list and debug logging. |
| `CORS_ORIGINS` | Comma-separated browser origins if not using the default lists in `core/app.py`. |
| `REGISTRATION_ENABLED` | `false` disables signups (`403` on `/api/auth/signup`). |
| `ENV` / `APP_ENV` | `prod` / `production` → `_prod` table suffix; `test` / `dev` / `staging` → `_test`; else default. |

## Project layout

```text
my-web-dashboard/
├── src/
│   ├── backend/          # FastAPI: auth/, core/, shared/, main.py, config.py
│   └── frontend/         # index.html, css/, js/, assets/, about/, games/, community/
├── flyway/sql/           # Versioned SQL (e.g. V1__create_users.sql)
├── scripts/              # migrate.py, run-quality-checks.sh, install-hooks.*
├── tests/                # smoke.test.js (Playwright; deploy uses this)
├── requirements.txt
└── README.md             # This file — only project doc we maintain
```

## Database migrations

- SQL lives in `flyway/sql/`.  
- Local helper: `python scripts/migrate.py` (see script `--help`).  
- Hosted: GitHub Action `.github/workflows/flyway-migrate.yml`.

## Git hooks (optional)

Install from repo root:

- macOS / Linux / Git Bash: `./scripts/install-hooks.sh`  
- Windows: `pwsh -File scripts/install-hooks.ps1`

Optional config: copy `.hooks-config.example.json` and adjust (comments inside JSON).  
CI runs `scripts/run-quality-checks.sh` on PRs.

## curl examples

```bash
curl -X POST http://127.0.0.1:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"Test1234","confirm_password":"Test1234"}'

curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"Test1234"}'
```

## Troubleshooting

- **`ImportError` on `python src/backend/main.py`:** run `python -m uvicorn src.backend.main:app` from the **repo root** instead.  
- **CORS errors from another origin:** set `CORS_ORIGINS` on Render to your exact site URL(s).  
- **Auth always 429:** auth routes are rate-limited per IP; wait or test from another network.  
- **`bcrypt` warning in logs:** fallback hashing still works; install `bcrypt` in the environment if you want the preferred backend.

## Contributing

Open PRs against `main` or `develop`. Before pushing, run `bash scripts/run-quality-checks.sh` when you can. Keep changes focused; match existing style in `src/frontend/`. Be respectful in issues and PRs.

## Product note

Session today is **client-side** (`sessionStorage` / `localStorage` mirror). `/api/auth/me` is a username lookup, not JWT yet—plan token-based auth when you outgrow this.

---

*Last updated: 2026-04-11*
