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
3. Login with a non-existent username returns `404 No user found`.
4. Login with a wrong password returns `401 Invalid username or password`.
5. On success, the frontend stores a lightweight client session in `sessionStorage` and mirrors it in `localStorage` for restore.
6. The UI transitions from the auth portal into the hub view directly revealing the **premium 'Secure Access Granted' success overlay**, eliminating distracting intermediate ticket animations.
7. The hub view is revealed after a smooth cinematic fade-out of the login portal (`#auth-portal-section`). The frontend restores the saved session automatically upon page reload.
8. Account deletion is credential-confirmed via `DELETE /api/auth/account`.
9. **Deletion Flow**: After successful deletion, the UI shows a red alert success state with a **dynamic real-time 3-second countdown** (3... 2... 1...) before safely redirecting the user back to the login portal.
10. **Startup Sequence**: The auth portal initially stays hidden and drops in via a smooth fade-in handled by `cinematic-startup.js`, preventing harsh un-animated "pop-ins" on the first load.

## Database Notes

- Local development defaults to SQLite at `data/playnexus.db`.
- If the primary local SQLite file is unhealthy, startup now recovers to `data/playnexus-recovered.db` so auth can still boot.
- Hosted environments can use PostgreSQL via `DATABASE_URL` or `PG*` variables.
- Table names may gain `_test` or `_prod` suffixes depending on `ENV` or `APP_ENV`.
- **Performance Optimization (PostgreSQL Pooling)**: The system now uses a global connection pool for PostgreSQL (Supabase). This eliminates the expensive TCP/SSL handshake overhead of establishing a new connection for every single login/signup/delete request.
    - **Previous Latency**: Each request took ~150-300ms plus query time (new connection each time).
    - **Current Latency**: Requests now take ~20-50ms plus query time (reusing pre-warmed connections).
    - **Result**: Authentication actions (Login/Create Account) are roughly **3x - 5x faster** on free-tier infrastructure.
- **Planned Optimization**: For even faster retrieval, we have a roadmap item to use a deterministic hash of `username + password_salt` as the Primary Key (PK). This will allow for true O(1) existence checks.

## Security Notes

- Passwords are combined with `SECRET_KEY` and hashed with adaptive password schemes.
- The backend prefers `bcrypt_sha256`, then `bcrypt`, and falls back to `pbkdf2_sha256` if that backend is unavailable in the runtime.
- `bcrypt_sha256` avoids bcrypt's 72-byte input limit without custom weak pre-hashing in application code.
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
