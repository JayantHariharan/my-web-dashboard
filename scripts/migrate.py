#!/usr/bin/env python3
"""
Lightweight database migration runner.
Uses Supabase connection directly via environment variables.
No Java dependency - pure Python.

Usage:
  python scripts/migrate.py                     # Apply migrations
  python scripts/migrate.py --dry-run           # Show what would be applied
  python scripts/migrate.py --reset             # Reset schema_version table
  python scripts/migrate.py --list              # List available migrations
"""

import os
import sys
import sqlite3
from pathlib import Path

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))


def get_database_config():
    """Load database configuration from environment variables."""
    # Load .env file if present (only for local dev, CI sets env vars directly)
    env_file = BASE_DIR / ".env"
    is_ci = os.getenv("CI", "").lower() in ("true", "1", "yes")
    if DOTENV_AVAILABLE and env_file.exists() and not is_ci:
        load_dotenv(env_file)

    # Get DATABASE_URL or construct from PG* variables
    raw_url = os.environ.get("DATABASE_URL", "")

    if not raw_url:
        pg_host = os.environ.get("PGHOST", "")
        pg_user = os.environ.get("PGUSER", "")
        pg_password = os.environ.get("PGPASSWORD", "")
        pg_database = os.environ.get("PGDATABASE", "")
        pg_port = os.environ.get("PGPORT", "5432")

        if all([pg_host, pg_user, pg_password, pg_database]):
            raw_url = (
                f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"
            )
        else:
            # Fallback to local SQLite
            data_dir = BASE_DIR / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = data_dir / "playnexus.db"
            raw_url = f"sqlite:///{db_path.as_posix()}"

    is_postgres = raw_url.startswith("postgresql://") or raw_url.startswith("postgres://")

    # Determine table suffix from ENV/APP_ENV
    app_env = os.environ.get("ENV", "").lower()
    if not app_env:
        app_env = os.environ.get("APP_ENV", "").lower()

    if app_env in ("prod", "production"):
        table_suffix = "_prod"
    elif app_env in ("test", "staging", "dev", "development"):
        table_suffix = "_test"
    else:
        table_suffix = ""

    # Get custom schema (PostgreSQL only). Default: 'public'
    db_schema = os.environ.get("DB_SCHEMA", "public")

    return raw_url, is_postgres, table_suffix, db_schema


def get_connection(db_url, is_postgres, db_schema="public"):
    """Create database connection."""
    if is_postgres:
        if not POSTGRES_AVAILABLE:
            print("[ERR]  psycopg2-binary not installed. Install with: pip install psycopg2-binary")
            sys.exit(1)
        conn = psycopg2.connect(db_url)
        conn.cursor_factory = RealDictCursor
        # Set search_path to use custom schema (falls back to public)
        try:
            conn.cursor().execute(f"SET search_path TO {db_schema}, public")
        except Exception as e:
            print(f"[WARN] Failed to set search_path to '{db_schema}': {e}")
        return conn, True
    else:
        db_path = db_url.replace("sqlite:///", "")
        conn = sqlite3.connect(db_path)
        return conn, False


def find_migrations():
    """Find all SQL migration files in order."""
    migrations_dir = BASE_DIR / "flyway" / "sql"
    if not migrations_dir.exists():
        print(f"[ERR]  Migrations directory not found: {migrations_dir}")
        return []

    migrations = []
    for file in sorted(migrations_dir.glob("V*__*.sql")):
        migrations.append(file)

    return migrations


def create_schema_version_table(conn, is_postgres, table_suffix=""):
    """Create schema_version table if it doesn't exist."""
    table_name = f"schema_version{table_suffix}"
    cursor = conn.cursor()
    if is_postgres:
        # Use Flyway-compatible schema for PostgreSQL
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                installed_rank SERIAL PRIMARY KEY,
                version VARCHAR(50),
                description VARCHAR(200) NOT NULL,
                type VARCHAR(20) NOT NULL,
                script VARCHAR(1000) NOT NULL,
                checksum INT,
                installed_by VARCHAR(100) NOT NULL,
                installed_on TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                execution_time INT NOT NULL,
                success BOOLEAN NOT NULL
            )
        """)
    else:
        # Simple schema for SQLite
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                version INTEGER PRIMARY KEY,
                script TEXT NOT NULL,
                installed_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()


def get_applied_migrations(conn, is_postgres, table_suffix=""):
    """Get set of already applied migration script names."""
    table_name = f"schema_version{table_suffix}"
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT script FROM {table_name}")
        if is_postgres:
            return {row['script'] for row in cursor.fetchall()}
        else:
            return {row[0] for row in cursor.fetchall()}
    except Exception:
        return set()


def apply_migration(conn, migration_file, is_postgres, dry_run=False, table_suffix=""):
    """Apply a single migration file."""
    script_name = migration_file.name

    with open(migration_file, "r", encoding="utf-8") as f:
        sql = f.read()

    # Replace placeholders
    if is_postgres:
        sql = sql.replace("{AUTOINCREMENT}", "SERIAL PRIMARY KEY")
        sql = sql.replace("{TEXT}", "TEXT")
    else:
        sql = sql.replace("{AUTOINCREMENT}", "INTEGER PRIMARY KEY AUTOINCREMENT")
        sql = sql.replace("{TEXT}", "TEXT")
    sql = sql.replace("{table_suffix}", table_suffix)

    if dry_run:
        print(f"  [DRY RUN] Would apply: {script_name}")
        print(f"    SQL: {sql[:100]}...")
        return True

    cursor = conn.cursor()
    try:
        import time
        start_time = time.time()

        if is_postgres:
            cursor.execute(sql)
        else:
            # SQLite: split on semicolons
            for statement in sql.split(";"):
                stmt = statement.strip()
                if stmt:
                    cursor.execute(stmt)

        # Record migration - use Flyway-compatible schema for PostgreSQL
        schema_table = f"schema_version{table_suffix}"

        if is_postgres:
            # Parse version and description from filename: V1__create_users.sql -> version='1', description='create users'
            import re
            match = re.match(r'V(\d+)__(.+)\.sql', script_name)
            if match:
                version = match.group(1)
                # Replace underscores with spaces for description
                description = match.group(2).replace('_', ' ')
            else:
                version = None
                description = script_name

            # Get the database user who executed the migration
            cursor.execute("SELECT current_user")
            row = cursor.fetchone()
            installed_by = row[0] if isinstance(row, (list, tuple)) else row['current_user']

            end_time = time.time()
            execution_time = int((end_time - start_time) * 1000)  # milliseconds

            # Insert in the exact column order of Flyway's schema_version table
            # Columns: installed_rank (auto), version, description, type, script, checksum (can be NULL), installed_by, installed_on, execution_time, success
            cursor.execute(
                f"""INSERT INTO {schema_table}
                    (version, description, type, script, checksum, installed_by, installed_on, execution_time, success)
                    VALUES (%s, %s, 'SQL', %s, NULL, %s, CURRENT_TIMESTAMP, %s, %s)""",
                (version, description, script_name, installed_by, execution_time, True)
            )
        else:
            # SQLite: simple schema
            cursor.execute(
                f"INSERT INTO {schema_table} (script) VALUES (?)",
                (script_name,)
            )

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"  [ERR]  Failed to apply {script_name}: {e}")
        return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Lightweight database migrations")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be applied")
    parser.add_argument("--reset", action="store_true", help="Reset schema_version table (fresh DB)")
    parser.add_argument("--list", action="store_true", help="List available migrations")
    args = parser.parse_args()

    # Get database config
    db_url, is_postgres, table_suffix, db_schema = get_database_config()

    print(f"[DB] Database: {'PostgreSQL' if is_postgres else 'SQLite'}")
    # Mask password in URL for logging
    if '://' in db_url and '@' in db_url:
        parts = db_url.split('://', 1)
        auth_part, rest = parts[1].split('@', 1) if '@' in parts[1] else (parts[1], '')
        if ':' in auth_part:
            user, pwd = auth_part.split(':', 1)
            display_url = f"{parts[0]}://{user}:***@{rest}" if rest else f"{parts[0]}://{user}:***"
        else:
            display_url = db_url
    else:
        display_url = db_url
    print(f"   URL: {display_url}")
    print(f"   Table suffix: '{table_suffix}'" if table_suffix else "   Table suffix: (none)")
    if is_postgres and db_schema != "public":
        print(f"   Schema: '{db_schema}'")

    migrations = find_migrations()
    if not migrations:
        print("No migrations found.")
        sys.exit(0)

    if args.list:
        print(f"\n[..] Available migrations ({len(migrations)}):")
        for m in migrations:
            print(f"   {m.name}")
        sys.exit(0)

    conn, is_postgres = get_connection(db_url, is_postgres, db_schema)
    create_schema_version_table(conn, is_postgres, table_suffix)
    applied = get_applied_migrations(conn, is_postgres, table_suffix)

    print(f"\n[..] Migrations status:")
    print(f"   Total: {len(migrations)}")
    print(f"   Already applied: {len([m for m in migrations if m.name in applied])}")
    print(f"   To apply: {len([m for m in migrations if m.name not in applied])}")

    if args.reset and not args.dry_run:
        if input("[WARN]   This will drop schema_version table. Continue? (yes/no): ") != "yes":
            sys.exit(0)
        cursor = conn.cursor()
        schema_table = f"schema_version{table_suffix}"
        cursor.execute(f"DROP TABLE IF EXISTS {schema_table}")
        conn.commit()
        create_schema_version_table(conn, is_postgres, table_suffix)
        applied = set()
        print(f"[OK]  {schema_table} reset")

    if args.dry_run:
        print("\n[TEST] DRY RUN - no changes will be made\n")

    applied_count = 0
    skipped_count = 0
    failed = False

    for migration in migrations:
        script_name = migration.name

        if script_name in applied:
            print(f"  [OK]  Already applied: {script_name}")
            skipped_count += 1
            continue

        print(f"  [..]  Applying: {script_name}")
        if apply_migration(conn, migration, is_postgres, dry_run=args.dry_run, table_suffix=table_suffix):
            applied_count += 1
        else:
            failed = True
            break

    print(f"\n[..] Summary:")
    print(f"   Applied: {applied_count}")
    print(f"   Skipped: {skipped_count}")
    print(f"   Failed: {1 if failed else 0}")

    conn.close()

    if failed:
        print("\n[ERR]  Migration failed!")
        sys.exit(1)
    elif applied_count == 0 and not args.dry_run:
        print("\n[OK]  All migrations are already applied!")
    elif args.dry_run:
        print("\n[OK]  Dry run complete (no changes made)")
    else:
        print("\n[OK]  All migrations applied successfully!")
        print("\n[..] Next steps:")
        print("   1. Run your FastAPI app: python src/backend/main.py")
        print("   2. Test the endpoints: http://localhost:8000/docs")


if __name__ == "__main__":
    main()
