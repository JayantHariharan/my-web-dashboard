# Database Migrations (Lightweight Python Runner)

This project uses versioned SQL migrations for database schema management. Migrations are applied via **GitHub Actions** using a lightweight Python script (`scripts/migrate.py`), not at application startup.

---

## How It Works

1. **Migration files** are numbered `.sql` files in `flyway/sql/`
2. **On deploy**, GitHub Actions workflow `flyway-migrate.yml` runs:
   - Sets up Python and installs `psycopg2-binary`
   - Connects to the Supabase database using secrets (DATABASE_URL or PG*)
   - Scans `flyway/sql/` for files named `V<number>__<description>.sql`
   - Applies any pending migrations using the Python script
   - Records each applied migration in the `schema_version` table (with environment suffix)
3. Migrations run in order; if one fails, the deployment fails and the error is reported

**Placeholders**: The migration script replaces these placeholders automatically:
- `{AUTOINCREMENT}` → `SERIAL PRIMARY KEY` (PostgreSQL) or `INTEGER PRIMARY KEY AUTOINCREMENT` (SQLite)
- `{TEXT}` → `TEXT` (both databases)
- `{table_suffix}` → `_prod`, `_test`, or empty based on `ENV` variable

---

## Development Workflow

## Current Migrations

| Version | Description | File |
|---------|-------------|------|
| V1 | Complete schema: users, user_profiles, all indexes | `flyway/sql/V1__create_users.sql` |

**Environment-based table suffixing**: Tables are created with a suffix based on the `ENV` variable:
- `ENV=prod` or `production` → tables: `users_prod`, `user_profiles_prod`, `schema_version_prod`
- `ENV=test` or `staging` → tables: `users_test`, `user_profiles_test`, `schema_version_test`
- No `ENV` (local dev) → tables: `users`, `user_profiles`, `schema_version` (no suffix)

The suffix is dynamically applied via the `{table_suffix}` placeholder in migrations and `TABLE_SUFFIX` config in the app.

**Note:** The original multi-app migrations (V3-V6) that created `app_registry`, `user_app_activity`, `game_scores`, and `app_config` were removed in v7.0. Those tables are now obsolete but **not automatically dropped** to preserve any existing data. If you have those tables and want to remove them, manually execute:

```sql
DROP TABLE IF EXISTS game_scores CASCADE;
DROP TABLE IF EXISTS user_app_activity CASCADE;
DROP TABLE IF EXISTS app_registry CASCADE;
DROP TABLE IF EXISTS app_config CASCADE;
```

**Migration philosophy**: We only apply forward migrations that create or modify schema. We never automatically drop tables to prevent accidental data loss. Destructive changes should be manual.

---

## Adding a New Migration

### Step 1: Create SQL File

Create a new file in `flyway/sql/` with the next version number (e.g., V2, since we have V1 only):

```
V2__create_games.sql
```

**Note**: Our initial schema is all in V1. Add new versions incrementally.

### Step 2: Write Migration SQL

### Supported Placeholders

Flyway replaces these placeholders automatically:

| Placeholder | PostgreSQL | SQLite | Purpose |
|-------------|------------|--------|---------|
| `{AUTOINCREMENT}` | `SERIAL PRIMARY KEY` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Auto-incrementing PK |
| `{TEXT}` | `TEXT` | `TEXT` | Text columns (works in both) |
| `{table_suffix}` | `_prod` or `_test` | `_prod` or `_test` | Environment-based table suffix (set via `ENV` variable) |

Example:

```sql
-- V3: Create games table
-- Placeholder {AUTOINCREMENT} expands to SERIAL (PostgreSQL) or INTEGER AUTOINCREMENT (SQLite)

CREATE TABLE IF NOT EXISTS games (
    id {AUTOINCREMENT},
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Rules**:
- Use `IF NOT EXISTS` to make migrations idempotent (safe to re-run)
- Use `{AUTOINCREMENT}` for auto-incrementing primary key
- Standard SQL types (VARCHAR, TIMESTAMP, etc.) work in both databases
- For `JSON` columns, use `{TEXT}` to store JSON as text in SQLite (PostgreSQL supports native JSON)
- Separate multiple statements with semicolons, or use separate `CREATE INDEX` statements after table creation

### Step 3: Commit and Push

```bash
git add flyway/sql/V3__create_games.sql
git commit -m "feat(db): add games table (V3)"
git push origin main
```

### Step 4: Automatic Deployment

GitHub Actions runs the `flyway-migrate` workflow → Python script applies migration → deployment proceeds.

**Check GitHub Actions logs** to confirm:
```
[DB] Database: PostgreSQL
...
[OK]  All migrations applied successfully!
```

---

---

## Viewing Applied Migrations

Connect to your database and query:

```sql
SELECT * FROM schema_version ORDER BY installed_on;
```

Example output:

| id | version | script | installed_on |
|----|---------|--------|--------------|
| 1 | V1__create_users.sql | 2025-03-29 21:00:01 |
| 2 | V2__create_user_profiles.sql | 2025-03-29 21:05:23 |

---

## Rollback Strategy

Migrations are **forward-only**. To undo a change:

1. Create a **new migration** that reverses it:
   ```sql
   -- V4: Drop games table (undo V3)
   DROP TABLE IF EXISTS games;
   ```
2. Deploy → V4 applies → table removed

Or manually revert via database console if needed (not recommended for production).

---

## Best Practices

1. **Never modify** an already-applied migration file. Create a new one instead.
2. **Use sequential version numbers**: 1, 2, 3... No gaps required but keep order.
3. **Test migrations locally** before pushing:
   ```bash
   # Delete local database and let app recreate with all migrations
   rm data/playnexus.db  # if using SQLite
   python -m backend.main
   ```
4. **Make migrations idempotent** with `IF NOT EXISTS` / `DROP IF EXISTS`.
5. **Keep migrations small** – one logical change per file.
6. **Add descriptive comments** at the top of each migration file.
7. **Never commit sensitive data** in migrations (no seed data with real info).

---

## Migration File Naming Convention

```
V<version>__<description>.sql
```

Examples:
- `V1__create_users.sql`
- `V2__create_games.sql`
- `V3__add_user_email_column.sql`

**Format**:
- `V` + integer version (required)
- Double underscore `__` separator
- Lowercase description with underscores
- `.sql` extension

---

## Troubleshooting

### Migration Failed

**Symptom**: App fails to start, logs show `Migration Vx failed`.

**Fix**:
1. Check logs for the exact SQL error (look for "Failed to apply Vx")
2. Fix the SQL syntax in the migration file
3. If migration partially applied, manually clean up:
   - Connect to DB (using `sqlite3` CLI or DB Browser)
   - Drop partially created table: `DROP TABLE IF EXISTS table_name;`
   - Remove record from `schema_version`:
     ```sql
     DELETE FROM schema_version WHERE script = 'Vx__filename.sql';
     ```
4. Restart app → migration will retry
5. Push fix → redeploy if in production

### Migrations Failed

**Symptom**: GitHub Actions workflow fails during the "Run Python migrations" step.

**Fix**:
1. Check logs for the exact SQL error (look for "Failed to apply Vx")
2. Fix the SQL syntax in the migration file
3. If migration partially applied, manually clean up:
   - Connect to DB
   - Rollback manually or delete from `schema_version` and drop objects
4. Push fix → redeploy

### Migrations Not Running

- Verify `flyway-migrate.yml` workflow exists and is triggered
- Check that `flyway/sql/` directory exists at project root
- Ensure database secrets (`PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`) are set in GitHub repository secrets
- Look for output showing migration status (e.g., `[..] Migrations status:`)

---

**See Also**:
- [SETUP.md](../SETUP.md) – How to set up and deploy
- [DEPLOYMENT.md](../DEPLOYMENT.md) – CI/CD pipeline details
