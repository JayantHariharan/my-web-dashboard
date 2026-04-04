# Developer Guide

This guide reflects the current PlayNexus direction: auth first, broader app expansion later.

## Current Development Focus

Build and stabilize the account experience first:

- Login
- Signup
- Delete account
- Clean frontend/backend integration for auth
- Consistent docs and repo structure

Do not assume the older multi-app platform is active just because some static pages still exist in `src/frontend/`.

## Run Locally

### Backend

```bash
pip install -r requirements.txt
python src/backend/main.py
```

### Frontend only

```bash
cd src/frontend
python -m http.server 3000
```

## Important Routes

- `POST /api/auth/login`
- `POST /api/auth/signup`
- `GET /api/auth/me`
- `DELETE /api/auth/account`
- `GET /health`

## Current Backend Structure

```text
src/backend/
|-- auth/
|   `-- router.py
|-- core/
|   |-- app.py
|   `-- middlewares.py
|-- shared/
|   |-- database.py
|   |-- schemas.py
|   `-- security.py
|-- config.py
|-- log_config.py
`-- main.py
```

## Current Frontend Structure

```text
src/frontend/
|-- index.html
|-- css/
|-- js/
|-- assets/
|-- games/
|-- author/
|-- community/
`-- news/
```

Only the auth experience is the active engineering priority right now. The other pages are static UI surface area and should not drive backend complexity yet.

## Auth Flow Today

1. The user opens `index.html` served by FastAPI.
2. The page posts login or signup data to `/api/auth/...`.
3. On success, the frontend stores the username in `sessionStorage`.
4. The UI transitions from the auth portal into the hub view.
5. Account deletion is credential-confirmed via `DELETE /api/auth/account`.

## Database Notes

- Local development defaults to SQLite at `data/playnexus.db`.
- Hosted environments can use PostgreSQL via `DATABASE_URL` or `PG*` variables.
- Table names may gain `_test` or `_prod` suffixes depending on `ENV` or `APP_ENV`.

## Security Notes

- Passwords are first normalized with an HMAC-SHA256 digest keyed by `SECRET_KEY`, then hashed with an adaptive scheme.
- The backend prefers `bcrypt` and falls back to `pbkdf2_sha256` if that backend is unavailable in the runtime.
- The HMAC preprocessing avoids bcrypt's 72-byte input limit while keeping a server-side secret in the flow.
- Auth endpoints are rate limited in memory.
- The current auth model is transitional and not token-based yet.
- `SECRET_KEY` must be set in production-like environments such as Render.
- Keep the same `SECRET_KEY` value across deploys for an environment. Removing or changing it can stop existing users from logging in or deleting their accounts.

## Git Hooks

This project includes local git hooks for quality checks.

### Pre-commit

- Python syntax validation
- Hardcoded secret detection
- TODO and FIXME detection
- Workflow validation
- Documentation freshness updates

### Pre-push

- Pre-commit checks
- Branch freshness validation
- Quality script execution
- Optional smoke testing when configured

### Commit message

Conventional commits are enforced.

## Useful Commands

```bash
python scripts/migrate.py --list
python scripts/migrate.py --dry-run
python scripts/migrate.py
python src/backend/main.py
node tests/smoke.test.js
```

## Cleanup Guidance

When cleaning the repo:

- Prefer removing dead code instead of leaving outdated abstractions around.
- Keep docs aligned with what the code actually does today.
- Avoid reintroducing multi-app backend concepts until the auth phase is complete.
- Treat stale references in docs as bugs.

## When Adding New Auth Work

Use this checklist:

1. Update the backend route or schema.
2. Update the frontend integration.
3. Update the relevant docs.
4. Verify naming stays consistent across code and docs.
5. Keep the architecture small unless there is a real need to expand it.

## Near-Term Roadmap

- Keep the auth page polished and stable
- Keep account deletion working end to end
- Improve current-user/session handling
- Add proper session or token auth
- Expand PlayNexus apps only after auth is stable

## Last Updated

2026-04-04
