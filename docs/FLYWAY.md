# Database Migrations (Flyway Style)

This project uses Flyway-style versioned SQL migrations for database schema management.

---

## How It Works

1. **Migration files** are numbered `.sql` files in `flyway/sql/`
2. **On application startup**, `src/backend/migrator.py`:
   - Creates `schema_version` table if it doesn't exist
   - Scans `flyway/sql/` for files named `V<number>__<description>.sql`
   - Applies any migrations not yet recorded in `schema_version`
   - Records each applied migration (by filename) in `schema_version`
3. Migrations run in order; if one fails, the transaction rolls back and application startup fails (in production) or logs error (in development)

---

## Current Migrations

| Version | Description | File |
|---------|-------------|------|
| V1 | Create `users` table with audit fields | `flyway/sql/V1__create_users.sql` |
| V2 | Add username index & create `user_profiles` table | `flyway/sql/V2__add_username_index.sql`, `flyway/sql/V2__user_profiles.sql` |

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

Create a new file in `flyway/sql/` with the next version number:

```
V2__create_games.sql
```

### Step 2: Write Migration SQL

Supported placeholders (automatically replaced by `migrator.py` based on database type):

| Placeholder | PostgreSQL | SQLite |
|-------------|------------|--------|
| `{AUTOINCREMENT}` | `SERIAL PRIMARY KEY` | `INTEGER PRIMARY KEY AUTOINCREMENT` |
| `{TEXT}` | `TEXT` | `TEXT` |

Example:

```sql
-- V2: Create games table
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
git add flyway/sql/V2__create_games.sql
git commit -m "Add V2: create games table"
git push origin main
```

### Step 4: Automatic Deployment

GitHub Actions deploys to Render → app starts → migration is applied automatically.

**Check Render logs** to confirm:
```
migrator - INFO - Applying migration V2: V2__create_games.sql
migrator - INFO - Migration V2 applied successfully
```

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
| 2 | V2__user_profiles.sql | 2025-03-29 21:05:23 |

---

## Rollback Strategy

Migrations are **forward-only**. To undo a change:

1. Create a **new migration** that reverses it:
   ```sql
   -- V3: Drop games table (undo V2)
   DROP TABLE IF EXISTS games;
   ```
2. Deploy → V3 applies → table removed

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

### Placeholders Not Replaced

Check `src/backend/migrator.py` has substitution logic for both PostgreSQL and SQLite.

### Migrations Not Running

- Ensure `src/backend/migrator.py` exists and is imported by `main.py`
- Verify `apply_migrations()` is called in `@app.on_event("startup")` in `main.py`
- Check that `flyway/sql/` directory exists at project root (not inside `src/`)
- Look for log line: `Found X migration(s) to apply`

---

## Advanced: Custom Placeholders

The migrator automatically replaces these placeholders:

- `{AUTOINCREMENT}` → `SERIAL PRIMARY KEY` (PostgreSQL) / `INTEGER PRIMARY KEY AUTOINCREMENT` (SQLite)
- `{TEXT}` → `TEXT` (both databases)

If you need additional placeholders, edit `src/backend/migrator.py` in the `apply_migrations()` function where replacements are made:

```python
# Replace placeholders based on database type
if settings.database.is_postgres:
    sql = sql.replace('{AUTOINCREMENT}', 'SERIAL PRIMARY KEY')
    sql = sql.replace('{TEXT}', 'TEXT')
else:
    sql = sql.replace('{AUTOINCREMENT}', 'INTEGER PRIMARY KEY AUTOINCREMENT')
    sql = sql.replace('{TEXT}', 'TEXT')
```

Then use your custom placeholder in migration SQL: `column_name {YOUR_PLACEHOLDER}`

---

## Comparison with Python Migrations

We previously used Python-based migrations (`.py` files with `upgrade(repo)` functions). We switched to **SQL-only** because:

- **DBA-friendly**: SQL is universal; DBAs can review/modify without Python
- **Standard**: Flyway is a well-known industry pattern
- **Simple**: No Python code to write; just SQL
- **Portable**: Migration files work with any language/tool that understands Flyway format

If you need complex logic (data transformations), you can still write Python in migrations, but for schema changes, SQL is sufficient and cleaner.

---

**See Also**:
- [SETUP.md](../SETUP.md) – How to set up and deploy
- [DEPLOYMENT.md](../DEPLOYMENT.md) – CI/CD pipeline details
