# Database Migrations

PlayNexus uses a lightweight Python migration runner instead of Java Flyway.

Migration files live in `flyway/sql/` and are applied by `scripts/migrate.py`.

## Current Schema Scope

The current project scope only needs these tables:

- `users`
- `user_profiles`
- `schema_version`

Environment suffixes may be added at runtime, for example `_test` or `_prod`.

## Commands

```bash
python scripts/migrate.py --list
python scripts/migrate.py --dry-run
python scripts/migrate.py
```

## How the Runner Works

1. Loads database configuration from environment variables.
2. Falls back to SQLite when PostgreSQL settings are not present.
3. Creates the `schema_version` table if needed.
4. Finds files matching `V*__*.sql`.
5. Applies unapplied migrations in order.
6. Records each successful migration.

## Supported Placeholders

- `{AUTOINCREMENT}`
- `{TEXT}`
- `{table_suffix}`

These placeholders are replaced by the migration runner for SQLite or PostgreSQL.

## Current Migration Inventory

- `V1__create_users.sql`: creates the current auth-first schema

## Environment Inputs

- `DATABASE_URL`
- `PGHOST`
- `PGPORT`
- `PGUSER`
- `PGPASSWORD`
- `PGDATABASE`
- `ENV` or `APP_ENV`
- `DB_SCHEMA` for PostgreSQL schema selection

## Guidance

- Keep migrations additive and clear.
- Do not add future multi-app tables until the auth-first phase actually needs them.
- Prefer a new migration over editing an applied migration.

## Last Updated

2026-04-04
