# Migration Philosophy & Best Practices

## Core Principle: Non-Destructive Migrations

**Never delete data automatically.** Migrations should only:
- ✅ Create new tables
- ✅ Add new columns
- ✅ Create indexes
- ✅ Modify schema (add constraints, etc.)

**Never** (in automated migrations):
- ❌ DROP tables
- ❌ DELETE data
- ❌ TRUNCATE tables

Destructive operations should be **manual** (run by DBA/developer after explicit consent).

---

## Our Migration Strategy (v7.0)

### What We Did

1. **Removed obsolete migration files** (V3-V6) that created tables no longer in use:
   - `app_registry`
   - `user_app_activity`
   - `game_scores`
   - `app_config`

2. **Did NOT create a migration to drop these tables**

3. **Kept only essential migrations**:
   - V1: Complete schema (users + user_profiles + all indexes) in a single file

**Further simplification (v7.1)**: Merged V1, V2, V3 into single V1 migration for atomicity and simplicity.

### Why This Approach?

| Scenario | What Happens |
|----------|--------------|
| **Fresh install** | Only `users` and `user_profiles` get created. Old tables never exist. ✅ |
| **Existing install** | Old tables remain (they're not in current migrations, so migrator skips them). They're just unused. ✅ |
| **Data preservation** | Any data in old tables is preserved (if someone wants to keep historical game scores, they can). ✅ |
| **Future re-add** | If we bring back games/apps, old data might still be there. ✅ |
| **Clean DB** | No destructive operations that could lose data accidentally. ✅ |

---

## Migration File Naming Convention

```
V<version>__<description>.sql
```

Examples:
- `V1__create_users.sql` (contains full schema)
- `V2__create_user_sessions.sql` (next new feature)
- `V3__add_user_email_column.sql` (next change)

**Rules:**
- Version numbers **must be unique** (no two files with same V<number>)
- Use sequential numbers: V1, V2, V3, etc.
- Description should be lowercase with underscores
- Use `IF NOT EXISTS` for CREATE statements (idempotent)
- Never use `DROP` in migrations (unless it's a very special case and documented)

---

## How Migrations Are Applied

Migrations are applied via GitHub Actions using Flyway CLI:

1. On push to `main` or `develop`, the `flyway-migrate` workflow runs
2. Flyway CLI is installed and configured with `flyway/conf/flyway.conf`
3. Flyway connects to the database using secrets (`PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`)
4. Flyway scans `flyway/sql/` for `V*__*.sql` files
5. For each unapplied migration, Flyway:
   - Executes the SQL (with placeholder replacement)
   - Records the migration in the `schema_version` table automatically
6. If all migrations succeed, deployment continues; otherwise it fails

**Note**: The application does not run migrations on startup. Local development uses SQLite which auto-creates the schema from the migration files on first run, or you can run Flyway manually.

Flyway ensures migrations are applied exactly once and tracks their history in `schema_version`.

---

## Handling Obsolete Tables

If you have tables from old migrations that are no longer needed:

### Option 1: Leave them (Recommended)
- No action needed
- They don't hurt anything
- Data is preserved if you ever need it
- Just ignore them in your codebase

### Option 2: Manual cleanup (if you're sure)
Connect to your database and manually drop:

```sql
-- Development (SQLite)
DROP TABLE IF EXISTS game_scores;
DROP TABLE IF EXISTS user_app_activity;
DROP TABLE IF EXISTS app_registry;
DROP TABLE IF EXISTS app_config;

-- Production (PostgreSQL)
DROP TABLE IF EXISTS game_scores CASCADE;
DROP TABLE IF EXISTS user_app_activity CASCADE;
DROP TABLE IF EXISTS app_registry CASCADE;
DROP TABLE IF EXISTS app_config CASCADE;
```

**Only do this if:**
- You're absolutely sure you don't need the data
- You have a backup
- You understand this is irreversible

---

## Data Preservation in Simplification

When we removed the multi-app features in v7.0:

1. **We did NOT add a migration to drop the old tables**
2. **We kept the old migration files out of the active folder** (so new installs don't create them)
3. **Existing databases keep the tables** (harmless, just unused)
4. **No data loss occurs automatically**

This is the **safest** approach for production systems.

---

## Best Practices for Adding New Migrations

### 1. Make migrations idempotent
```sql
-- Good ✅
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL
);

-- Bad ❌ (fails if table exists)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL
);
```

### 2. Never drop tables in migrations
Instead:
- Add a new column: `ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255);`
- Create new indexes: `CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);`

If you must drop a table:
- Do it manually with explicit consent
- Backup first
- Document the action in the migration file header

### 3. Test migrations locally
```bash
# For SQLite development
rm data/playnexus.db
python src/backend/main.py  # Should apply all migrations cleanly
```

### 4. Version numbers should increase monotonically
- V1, V2, V3... (or V1, V2, V2-alphabetical if needed)
- Don't reuse version numbers
- Don't skip numbers unnecessarily (though it's okay if you do)

### 5. Keep migrations small and focused
One logical change per file:
- V1: initial schema (users + user_profiles + indexes) - combined because they're interdependent
- V2: add email column to users (separate version for future extension)
- V3: create user_sessions table for JWT revocation (separate feature)

**Exception**: The initial schema can be a single V1 migration if tables have foreign key dependencies (e.g., user_profiles references users). Group tightly coupled changes together.

---

## Example: Safe Migration Workflow

### Adding a new column to users:
```sql
-- V2: Add email column to users
-- Date: 2026-04-01
-- Purpose: Allow users to have optional email addresses

-- Note: {table_suffix} is automatically replaced based on ENV (test/prod)
ALTER TABLE users{table_suffix} ADD COLUMN IF NOT EXISTS email VARCHAR(255);
CREATE INDEX IF NOT EXISTS idx_users_email{table_suffix} ON users{table_suffix}(email) WHERE email IS NOT NULL;
```

### Adding a new table:
```sql
-- V3: Create user_sessions table for session management
-- Date: 2026-04-01

CREATE TABLE IF NOT EXISTS user_sessions{table_suffix} (
    id {AUTOINCREMENT},
    user_id INTEGER NOT NULL,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users{table_suffix}(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_user_sessions_token{table_suffix} ON user_sessions{table_suffix}(session_token);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user{table_suffix} ON user_sessions{table_suffix}(user_id);
```

---

## The Danger of Destructive Migrations

### ❌ **Bad Example** (what we avoided):

```sql
-- V3: Drop old tables (DESTRUCTIVE - DON'T DO THIS)
DROP TABLE IF EXISTS game_scores;
DROP TABLE IF EXISTS user_app_activity;
-- This permanently deletes all game scores and activity logs!
```

**Why this is bad:**
- Someone might have valuable data (e.g., high scores they want to keep)
- Migration runs automatically on startup without warning
- Data loss is irreversible
- Makes upgrading from old versions risky

### ✅ **Our approach** (safe):

```sql
-- V3: (no migration file - we just don't create old tables anymore)
-- Old tables remain if they exist, but are unused
-- No automatic data loss
```

---

## Rollback Strategy

If you apply a migration and it's wrong:

1. **Fix the migration file** (if not yet applied in production)
2. **Create a compensating migration** (if already applied):

```sql
-- V6: Remove email column from users (undo V4)
ALTER TABLE users DROP COLUMN IF EXISTS email;
```

3. **Manual database fix** (emergency):
   - Connect to DB
   - Execute correction SQL manually
   - Insert record into `schema_version` to mark broken migration as "applied" (or delete record to re-run fixed migration)

---

## Summary

- ✅ Migrations are **forward-only** and **non-destructive**
- ✅ We preserve all existing data automatically
- ✅ New installations get clean schema with only needed tables
- ✅ Existing installations keep old tables (unused but not dropped)
- ✅ Manual action required for destructive changes
- ✅ Simple, safe, production-friendly

**This is the professional approach to database migrations.** 🎯

---

**Last Updated**: 2026-04-01
