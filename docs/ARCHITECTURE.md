# System Architecture

## Overview

PlayNexus currently runs as an auth-first web application.

A FastAPI backend serves both:

- JSON APIs for authentication
- Static frontend files from `src/frontend/`

The repo still contains static pages for future sections of the site, but the active backend scope is intentionally narrow while the auth foundation is being stabilized.

## Runtime Shape

```text
Browser
  |
  |-- GET /                  -> static frontend
  |-- POST /api/auth/login   -> backend auth router
  |-- POST /api/auth/signup  -> backend auth router
  |-- DELETE /api/auth/account -> backend auth router
  |-- GET /api/auth/me       -> backend auth router
  `-- GET /health            -> health endpoint

FastAPI app
  |
  |-- core/app.py            -> app factory, middleware, health, exception handling
  |-- auth/router.py         -> auth endpoints
  |-- shared/database.py     -> repository layer
  |-- shared/security.py     -> password hashing and verification
  `-- StaticFiles mount      -> serves frontend

Database
  |
  |-- users[_suffix]
  |-- user_profiles[_suffix]
  `-- schema_version[_suffix]
```

## Backend Layers

### Entry point

`src/backend/main.py` creates the app, includes the auth router, mounts the frontend, and runs a startup check for legacy plaintext-password migration.

### App factory

`src/backend/core/app.py` is responsible for:

- CORS
- request IDs
- security headers
- gzip
- cache control
- auth rate limiting
- health endpoint
- exception handling

### Auth module

`src/backend/auth/router.py` currently owns:

- login
- signup
- current-user lookup
- account deletion

### Shared layer

`src/backend/shared/` contains the reusable backend pieces:

- `database.py`: repository access and connection helpers
- `security.py`: adaptive password hashing plus pepper helpers
- `schemas.py`: request and response models

## Frontend Design

The frontend is static HTML, CSS, and JavaScript.

### Current auth behavior

- The auth portal lives in `src/frontend/index.html`.
- Login and signup call `/api/auth/...`.
- Successful auth stores the username in `sessionStorage`.
- Theme preference is stored in `localStorage`.
- The hub uses animation-heavy visuals, including canvas effects and Matter.js-based physics.

### Important limitation

The frontend session model is still lightweight. It is not yet backed by JWTs or server sessions, so `/api/auth/me` is currently a username-based lookup rather than full session validation.

## Data Model

### users

Stores core account data:

- id
- username
- password hash
- created timestamp
- last login timestamp
- created IP
- last login IP

### user_profiles

Stores optional profile data tied to a user.

### schema_version

Tracks applied SQL migrations.

## Configuration Model

Configuration is environment-driven.

### Database selection

- `DATABASE_URL` if present
- otherwise `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`
- otherwise SQLite in `data/playnexus.db`

### Environment suffixes

- `production` or `prod` -> `_prod`
- `test`, `staging`, `dev`, or `development` -> `_test`
- local default -> no suffix

## Security Model

### Current protections

- adaptive password hashing with `bcrypt` preferred and `pbkdf2_sha256` fallback
- `SECRET_KEY`-peppered adaptive password hashing with `bcrypt_sha256` preferred
- auth rate limiting by IP
- request ID tracing
- security headers
- parameterized SQL values
- strongly sanitized dynamic column and order-by mapping (SQL injection prevented)

### Current tradeoffs

- in-memory rate limiting only
- sessionStorage-based frontend state
- no JWT or refresh-token model yet
- `SECRET_KEY` is part of password verification, so each Render environment must keep a stable value

## What Is Intentionally Out of Scope Right Now

These ideas belong to the future roadmap, not the current backend scope:

- app registry APIs
- game score APIs
- social activity APIs
- runtime `app_config` loading
- distributed rate limiting

## Roadmap Direction

The planned sequence is:

1. Finish auth page flows and cleanup.
2. Improve session/auth robustness.
3. Reintroduce broader PlayNexus app experiences only after the auth layer is stable.

## Last Updated

2026-04-04
