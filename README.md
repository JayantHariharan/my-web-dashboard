# PlayNexus

PlayNexus is currently in an auth-first phase: a FastAPI backend serves a static frontend, and the active product work is centered on account flows before the broader app hub expands.

## Current Scope

- Login
- Signup
- Delete account
- Basic profile lookup
- Static frontend served by the backend
- SQLite for local development, PostgreSQL for deployment

## Tech Stack

- Backend: FastAPI, Python 3.12
- Frontend: HTML, CSS, vanilla JavaScript
- Database: SQLite locally, PostgreSQL in hosted environments
- Security: adaptive password hashing plus `SECRET_KEY`-based peppering, request IDs, security headers, auth rate limiting
- Deployment: Render + GitHub Actions

## Current API

- `POST /api/auth/login`
- `POST /api/auth/signup`
- `GET /api/auth/me?username=<name>`
- `DELETE /api/auth/account`
- `GET /health`

## Local Development

### Prerequisites

- Python 3.12+
- Git
- Node.js only if you want to run the Playwright smoke test

### Start the app

```bash
pip install -r requirements.txt
python src/backend/main.py
```

Open `http://localhost:8000`.

The backend serves the frontend directly from `src/frontend/`.

### Environment notes

- Local development can run with the default SQLite database and a local `.env` file if you want one.
- Render should provide environment variables directly to the backend process.
- Keep `SECRET_KEY` set on Render for both test and production.
- Do not remove or rotate `SECRET_KEY` casually: it is part of the current password hashing flow, so changing it can break login and delete-account verification for existing users.

### Optional frontend-only static server

```bash
cd src/frontend
python -m http.server 3000
```

### Quick API checks

```bash
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"Test1234","confirm_password":"Test1234"}'

curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"Test1234"}'

curl "http://localhost:8000/api/auth/me?username=testuser"

curl -X DELETE http://localhost:8000/api/auth/account \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"Test1234"}'
```

## Project Layout

```text
my-web-dashboard/
|-- src/
|   |-- backend/
|   |   |-- auth/            # Auth endpoints
|   |   |-- core/            # App factory and middleware
|   |   |-- shared/          # Database, security, schemas
|   |   `-- main.py          # Entry point
|   `-- frontend/            # Static site assets and pages
|-- docs/                    # Project documentation
|-- flyway/sql/              # SQL migrations
|-- scripts/                 # Migration and quality scripts
|-- tests/                   # Smoke test
|-- README.md
`-- requirements.txt
```

## Documentation

- `docs/DEVELOPER.md`: day-to-day workflow and coding guidance
- `docs/ARCHITECTURE.md`: current runtime design
- `docs/FLYWAY.md`: migration runner usage
- `docs/MIGRATIONS.md`: migration philosophy
- `docs/TROUBLESHOOTING.md`: debugging help

## Product Direction

The current priority is to keep authentication stable, clean, and easy to extend:

- Keep the login, signup, and delete-account flows production-ready
- Keep the backend small and easy to reason about
- Remove stale multi-app assumptions from code and docs

After the auth foundation is stable, PlayNexus can grow back into a larger app hub with games and additional experiences.

## Notes

- The frontend currently keeps the active username in `sessionStorage`.
- `GET /api/auth/me` is still a simple username-based lookup, not full token auth yet.
- Passwords are normalized with an HMAC-SHA256 step keyed by `SECRET_KEY`, then hashed with `bcrypt` when available or `pbkdf2_sha256` as a fallback.
- The static `docs/API-REFERENCE.html` file may lag behind the code and should be treated as secondary to the source code and the docs above.
