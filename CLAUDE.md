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
- `pre-commit` – Syntax, quality checks, updates doc timestamps
- `pre-push` – Full suite (syntax, quality checks, smoke test), updates doc timestamps

**Skip hooks**: `git commit --no-verify` or `git push --no-verify` (NOT recommended)

**Note**: Hooks automatically update "Last Updated" dates in `docs/DEVELOPER.md`, `docs/ARCHITECTURE.md`, `docs/FLYWAY.md` and stage them. Commit these changes separately.

**Claude Code slash commands**:
- `/security-scan` – Security audit (runs CodeQL analysis via GitHub)
- `/code-quality` – Comprehensive quality verification (syntax, YAML, branch checks)
- `/deploy-ready` – Verify deployment readiness (runs pre-push checks)

**Install dev tools** (for hooks & manual checks):
```bash
pip install pyyaml
npm install playwright && npx playwright install chromium --with-deps
```

**After pulling updates**: If hooks were updated, re-run `./scripts/install-hooks.sh` to refresh installed hooks.


**Manual checks**:
```bash
python -m py_compile src/backend/main.py  # syntax check
./scripts/run-quality-checks.sh           # comprehensive quality checks
SITE_URL=https://playnexus-test.onrender.com node tests/smoke.test.js  # smoke test
```

**GitHub Security Features**:
- **CodeQL** – Native static analysis for security vulnerabilities (automatically runs on PRs)
- **Dependabot** – Automatic dependency updates (opens PRs for outdated packages)
- **Secret scanning** – Alerts for hardcoded secrets (enabled by GitHub)
- **Branch protection** – Enforces reviews, status checks, and quality gates

**Smoke test environment fallback:**
If `SITE_URL` is not set, the test uses `APP_ENV` to determine the URL:
- `production` → `https://playnexus-prod.onrender.com`
- anything else → `https://playnexus-test.onrender.com`

---

## CI/CD Standards

When modifying or creating GitHub Actions workflows (`.github/workflows/*.yml`), follow these rules:

### 1. Concurrency Control
**Required**: All deployable workflows must have job-level concurrency with `cancel-in-progress: true`.

Example:
```yaml
jobs:
  deploy:
    concurrency:
      group: deploy-${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }}
      cancel-in-progress: true
```

For reusable workflows:
```yaml
jobs:
  migrate:
    concurrency:
      group: flyway-${{ inputs.environment }}
      cancel-in-progress: true
```

For quality checks:
```yaml
jobs:
  code-quality:
    concurrency:
      group: quality-${{ github.ref }}
      cancel-in-progress: true
```

### 2. Artifact Retention
**Required**: All artifact uploads must set `retention-days: 7` to limit storage costs.

Example:
```yaml
- name: Upload reports
  uses: actions/upload-artifact@v4
  with:
    name: my-reports
    path: reports/
    retention-days: 7
```

### 3. Secret Handling
**Important**: Never reference secrets directly in `if:` conditions. Use one of:
- Check inside shell script: `if [ -z "$SECRET_NAME" ]; then ...`
- Use expression syntax properly without `${{ }}` in `if:` field: `if: secrets.SECRET_NAME != ''`

### 4. Conditional Steps
Use `always()` or `success()` without `${{ }}` wrapper:
```yaml
if: always()
if: success()
```

### 5. Expression Syntax
Inside `run`, `env`, or `with` fields, use `${{ }}` for context and secret interpolation:
```yaml
env:
  API_KEY: ${{ secrets.API_KEY }}
run: echo "${{ github.sha }}"
```

### 6. Migration Strategy
Migrations are applied via Python script in `.github/workflows/flyway-migrate.yml` (uses `scripts/migrate.py`), **not** on application startup. Do NOT re-introduce auto-migration in the application.

### 7. Reusable Workflow Outputs
To pass outputs from a reusable workflow to the caller:
- Define `outputs` in the `workflow_call` section of the called workflow
- Access via `needs.<job>.outputs.<output_name>` in the caller
- Do NOT add an `outputs` block directly under the job using `uses:`

---

## Database Migrations

- Place migration files in `flyway/sql/` following naming: `V<number>__<description>.sql`
- Use placeholder `{AUTOINCREMENT}` for auto-incrementing PK (PostgreSQL: `SERIAL PRIMARY KEY`, SQLite: `INTEGER PRIMARY KEY AUTOINCREMENT`)
- Use placeholder `{TEXT}` for text fields (works in both DBs)
- Apply migrations via GitHub Actions; local dev uses SQLite (auto-creates schema)

See `docs/FLYWAY.md` for complete migration guide.

---

## Code Structure

```
src/backend/
├── config.py          # Settings (env-based)
├── log_config.py      # Logging setup
├── main.py            # Entry point (create app, mount static, include routers)
├── core/
│   ├── app.py         # FastAPI factory, middleware
│   └── middlewares.py # RateLimitMiddleware, CORS, RequestIdMiddleware
├── shared/
│   ├── database.py    # BaseRepository, UserRepository, UserProfileRepository
│   ├── security.py    # Password hashing (bcrypt + pepper)
│   ├── schemas.py     # Pydantic models
│   └── exceptions.py  # Custom exceptions
└── auth/
    ├── router.py      # /api/auth/* endpoints
    └── service.py     # Authentication logic
```

---

## Security Checklist

Before committing/pushing:
- [ ] No hardcoded secrets (use environment variables)
- [ ] All SQL uses parameterized queries (repository pattern)
- [ ] Passwords hashed with bcrypt + pepper
- [ ] Rate limiting enabled on auth endpoints
- [ ] No TODO/FIXME in critical paths (or documented)
- [ ] Sensitive data not logged

---

## Common Tasks

### Add a new API endpoint
1. Add route in `src/backend/auth/router.py` or create new module
2. Implement logic in service layer (e.g., `auth/service.py`)
3. Add Pydantic schemas in `shared/schemas.py` if needed
4. Update documentation (`docs/API-REFERENCE.html`)
5. Run quality checks

### Add a database migration
1. Create SQL file: `flyway/sql/V<next>__<description>.sql`
2. Use `IF NOT EXISTS` for tables, `IF NOT EXISTS` for indexes
3. Commit with message: `feat(db): <description>`
4. Push → Migrations apply automatically in CI/CD
5. Verify `schema_version` table in production

### Deploy to Render

**Automatic deployments:**
- Push to `main` → Production deployment
- Push to `develop` → Staging deployment
- Feature branches do NOT trigger deployment

**Workflow steps:**
1. **Precheck** – validates secrets and database connectivity
2. **Migrate database** – applies Flyway migrations via `scripts/migrate.py`
3. **Deploy** – triggers Render deployment, monitors until completion, runs health checks and smoke test

**Environment URLs:**
- Staging: `https://playnexus-test.onrender.com`
- Production: `https://playnexus-prod.onrender.com` (configured in Render)

**Smoke test:**
- Runs automatically after successful deployment
- Uses Playwright to navigate to the deployed site
- Verifies that "PlayNexus" appears on the page
- Takes a full-page screenshot for debugging
- If `SITE_URL` is not provided or is `null`, falls back to environment-specific hardcoded URLs:
  - Staging: `https://playnexus-test.onrender.com`
  - Production: `https://playnexus-prod.onrender.com`

**Monitoring:**
- Render deployment monitored for up to 60 minutes
- Deployments in `live` or `succeeded` state → success
- Failures (`errored`, `failed`, `build_failed`, etc.) cause workflow to fail
- Health checks: `/health` and `/api/auth/login` must return 200/302/401

---

## Troubleshooting

### Workflow syntax errors
Check YAML with online validator or `python -c "import yaml; yaml.safe_load(open('file.yml'))"`

### Migration failed in CI
Check logs for SQL error, fix migration file, push fix. If partially applied, manually rollback or delete from `schema_version`.

### Local development with PostgreSQL
Set environment variables in `.env`:
```
PGHOST=localhost
PGPORT=5432
PGUSER=postgres
PGPASSWORD=yourpassword
PGDATABASE=playnexus
```
Then run: `python scripts/migrate.py` to apply migrations.

---

**Last Updated**: 2026-04-03

---

## Recent Major Changes

- **2026-04-03**: Fixed deployment workflow output propagation and error handling
  - Added `outputs` to `flyway-migrate.yml` to expose migration success status
  - Improved deploy job monitoring with robust error handling and 60-minute timeout
  - Added Playwright dependency installation before smoke test
  - Smoke test now uses environment fallback URLs when `SITE_URL` is null

- **2026-04-03**: Fixed migration constraint issue with PostgreSQL
  - `scripts/migrate.py` now correctly includes `checksum` column in `schema_version` INSERT
  - Column order matches Flyway's structure exactly to avoid constraint violations

- **2026-04-03**: Simplified security & quality scanning
  - Migrated from custom AI scanning to GitHub-native CodeQL and Dependabot
  - Removed OpenAI/Anthropic dependencies and API key requirements
  - Reduced maintenance overhead with automated dependency updates
  - Updated documentation to reflect native GitHub security features

- **2026-04-01**: Migrated from Flyway CLI to lightweight Python migration runner
