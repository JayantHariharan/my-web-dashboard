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
- `pre-commit` – Syntax, AI-powered quality check, updates doc timestamps
- `pre-push` – Full suite (syntax, AI quality scan, smoke test), updates doc timestamps

**Skip hooks**: `git commit --no-verify` or `git push --no-verify` (NOT recommended)

**Note**: Hooks automatically update "Last Updated" dates in `docs/DEVELOPER.md`, `docs/ARCHITECTURE.md`, `docs/FLYWAY.md` and stage them. Commit these changes separately.

**Claude Code slash commands**:
- `/security-scan` – Security audit (AI-powered Claude security analysis)
- `/code-quality` – AI-powered comprehensive quality scan (replaces flake8/mypy/black/bandit)
- `/deploy-ready` – Verify deployment readiness

**Install dev tools** (for hooks & manual checks):
```bash
pip install openai pyyaml
npm install playwright && npx playwright install chromium --with-deps
```

**After pulling updates**: If hooks were updated, re-run `./scripts/install-hooks.sh` to refresh installed hooks.


**Manual checks**:
```bash
python -m py_compile src/backend/main.py  # syntax check
python .github/scripts/ai_quality_scan.py   # AI quality scan (replaces flake8, mypy, black, bandit)
python .github/scripts/claude_security_scan.py  # AI security-only scan
node tests/smoke.test.js  # with SITE_URL set
```

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
Migrations are applied via Python script in `.github/workflows/flyway-migrate.yml` (now uses `scripts/migrate.py`), **not** on application startup. Do NOT re-introduce auto-migration in the application.

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
- Push to `main` or `develop` branch
- GitHub Actions runs: precheck → flyway migrate → deploy
- Quality checks run automatically on PRs before merge
- Monitor workflow status in GitHub Actions tab
- Health checks run automatically after deploy

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

**Last Updated**: 2026-04-01
