# Flyway-style Database Migrations

This directory contains versioned SQL migrations for PlayNexus.

## Format

- Files must be named: `V<version>__<description>.sql`
- Example: `V1__create_users.sql`, `V2__create_games.sql`
- Version numbers must be sequential (no gaps ideal, but not required)
- Multiple statements per file are allowed (separated by semicolons)

## Placeholders

SQL files can use placeholders that are replaced based on database type:

- `{AUTOINCREMENT}` → PostgreSQL: `SERIAL PRIMARY KEY`, SQLite: `INTEGER PRIMARY KEY AUTOINCREMENT`

Other standard SQL (VARCHAR, TIMESTAMP, etc.) works as-is in both databases.

## How It Works

On application startup, `backend/migrator.py`:

1. Creates `schema_migrations` table if it doesn't exist
2. Scans this folder for `.sql` files
3. Extracts version numbers from filenames
4. Applies any migrations not yet recorded in `schema_migrations`
5. Each migration runs in a single transaction

## Adding a New Migration

1. Create a new file in this folder with the next version number:
   ```sql
   -- V3__add_user_email.sql
   ALTER TABLE users ADD COLUMN email TEXT;
   ```

2. Commit and push.
3. Render redeploys automatically.
4. Migration is applied on startup.

## Rollback

Currently, migrations are forward-only. To rollback, create a new migration that reverses the change (e.g., `V4__remove_user_email.sql` with `ALTER TABLE users DROP COLUMN email;`).

## Viewing Applied Migrations

Check the `schema_migrations` table in your database:
```sql
SELECT * FROM schema_migrations ORDER BY version;
```
