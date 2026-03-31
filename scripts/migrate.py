#!/usr/bin/env python3
"""
Manual Flyway migration runner for local development (SQLite or PostgreSQL).
Use this when working locally to apply database schema changes.

Usage:
  python scripts/migrate.py                     # Auto-detect from .env
  python scripts/migrate.py --dry-run           # Show what would be applied
  python scripts/migrate.py --reset             # Apply fresh (drops schema_version)
  DATABASE_URL=sqlite:///./data/playnexus.db python scripts/migrate.py
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

# Add project root to path
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from backend.config import settings


def get_connection():
    """Get database connection based on settings."""
    db_url = settings.database.url

    if settings.database.is_postgres:
        if not POSTGRES_AVAILABLE:
            print("❌ psycopg2 not installed. Install with: pip install psycopg2-binary")
            sys.exit(1)
        conn = psycopg2.connect(db_url)
        conn.cursor_factory = RealDictCursor
        return conn, True
    else:
        # SQLite
        db_path = db_url.replace("sqlite:///", "")
        conn = sqlite3.connect(db_path)
        return conn, False


def find_migrations():
    """Find all SQL migration files in order."""
    migrations_dir = BASE_DIR / "flyway" / "sql"
    if not migrations_dir.exists():
        print(f"❌ Migrations directory not found: {migrations_dir}")
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
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                version INTEGER PRIMARY KEY,
                script TEXT NOT NULL,
                installed_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                version INTEGER PRIMARY KEY,
                script TEXT NOT NULL,
                installed_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()


def get_applied_migrations(conn, is_postgres, table_suffix=""):
    """Get list of already applied migrations."""
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
    # Replace table suffix placeholder
    sql = sql.replace("{table_suffix}", table_suffix)

    if dry_run:
        print(f"  [DRY RUN] Would apply: {script_name}")
        print(f"    SQL: {sql[:100]}...")
        return True

    cursor = conn.cursor()
    try:
        if is_postgres:
            cursor.execute(sql)
        else:
            # SQLite: split on semicolons
            for statement in sql.split(";"):
                stmt = statement.strip()
                if stmt:
                    cursor.execute(stmt)

        # Record migration in suffixed schema_version table
        schema_table = f"schema_version{table_suffix}"
        cursor.execute(
            f"INSERT INTO {schema_table} (script) VALUES (%s)" if is_postgres else f"INSERT INTO {schema_table} (script) VALUES (?)",
            (script_name,)
        )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"  ❌ Failed to apply {script_name}: {e}")
        return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Flyway migration runner for local development")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be applied without making changes")
    parser.add_argument("--reset", action="store_true", help="Reset schema_version (dangerous, only for fresh DBs)")
    parser.add_argument("--list", action="store_true", help="List available migrations")
    args = parser.parse_args()

    # Load settings from .env if available
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        from backend.config import Settings
        global settings
        settings = Settings(_env_file=env_file)

    print(f"📦 Database: {'PostgreSQL' if settings.database.is_postgres else 'SQLite'}")
    print(f"   URL: {settings.database.url.replace(settings.database.password, '***') if settings.database.password else settings.database.url}")

    migrations = find_migrations()
    if not migrations:
        print("No migrations found.")
        sys.exit(0)

    if args.list:
        print(f"\n📁 Available migrations ({len(migrations)}):")
        for m in migrations:
            print(f"   {m.name}")
        sys.exit(0)

    conn, is_postgres = get_connection()
    table_suffix = settings.database.table_suffix or ""
    create_schema_version_table(conn, is_postgres, table_suffix)
    applied = get_applied_migrations(conn, is_postgres, table_suffix)

    print(f"\n📊 Migrations status:")
    print(f"   Total: {len(migrations)}")
    print(f"   Already applied: {len([m for m in migrations if m.name in applied])}")
    print(f"   To apply: {len([m for m in migrations if m.name not in applied])}")

    if args.reset and not args.dry_run:
        if input("⚠️  This will drop schema_version table. Continue? (yes/no): ") != "yes":
            sys.exit(0)
        cursor = conn.cursor()
        schema_table = f"schema_version{table_suffix}"
        cursor.execute(f"DROP TABLE IF EXISTS {schema_table}")
        conn.commit()
        create_schema_version_table(conn, is_postgres, table_suffix)
        applied = set()
        print(f"✅ {schema_table} reset")

    if args.dry_run:
        print("\n🧪 DRY RUN - no changes will be made\n")

    applied_count = 0
    skipped_count = 0
    failed = False

    for migration in migrations:
        script_name = migration.name

        if script_name in applied:
            print(f"  ✅ Already applied: {script_name}")
            skipped_count += 1
            continue

        print(f"  ⏳ Applying: {script_name}")
        if apply_migration(conn, migration, is_postgres, dry_run=args.dry_run, table_suffix=table_suffix):
            applied_count += 1
        else:
            failed = True
            break

    print(f"\n📈 Summary:")
    print(f"   Applied: {applied_count}")
    print(f"   Skipped: {skipped_count}")
    print(f"   Failed: {1 if failed else 0}")

    conn.close()

    if failed:
        print("\n❌ Migration failed!")
        sys.exit(1)
    elif applied_count == 0 and not args.dry_run:
        print("\n✅ All migrations are already applied!")
    elif args.dry_run:
        print("\n✅ Dry run complete (no changes made)")
    else:
        print("\n✅ All migrations applied successfully!")
        print("\n💡 Next steps:")
        print("   1. Run your FastAPI app: python src/backend/main.py")
        print("   2. Test the endpoints: http://localhost:8000/docs")


if __name__ == "__main__":
    main()
