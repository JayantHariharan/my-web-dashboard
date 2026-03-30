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
   - V1: `users` table
   - V2: `user_profiles` table + username index

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
- `V1__create_users.sql`
- `V2__add_username_index.sql`
- `V2__user_profiles.sql`

**Rules:**
- Version numbers should be sequential but can have multiples (V2 can have two files - they run alphabetically)
- Description should be lowercase with underscores
- Use `IF NOT EXISTS` for CREATE statements (idempotent)
- Never use `DROP` in migrations (unless it's a very special case and documented)

---

## How Migrations Are Applied

The `migrator.py`:
1. Scans `flyway/sql/` for `V*__*.sql` files
2. Reads `schema_version` table to see which migrations already applied
3. For each migration file NOT in `schema_version`:
   - Executes the SQL
   - Records filename in `schema_version`

Once a migration is applied, its filename is recorded. Even if you later delete the file, the app won't try to re-apply it (it checks `schema_version` first).

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
- V1: create users table
- V2: create user_profiles table
- V3: add email column to users (separate)

---

## Example: Safe Migration Workflow

### Adding a new column to users:
```sql
-- V4: Add email column to users
-- Date: 2026-03-30
-- Purpose: Allow users to have optional email addresses

ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email) WHERE email IS NOT NULL;
```

### Adding a new table:
```sql
-- V5: Create user_sessions table for session management
-- Date: 2026-03-30

CREATE TABLE IF NOT EXISTS user_sessions (
    id {AUTOINCREMENT},
    user_id INTEGER NOT NULL,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions(user_id);
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

**Last Updated**: 2026-03-30
