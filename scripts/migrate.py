#!/usr/bin/env python3
"""
Lightweight database migration runner.
Uses Supabase connection directly via environment variables.
No Java dependency - pure Python.
"""

import os
import sys
import sqlite3
from pathlib import Path
from urllib.parse import urlparse, urlunparse

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


# ✅ NEW: Mask sensitive info
def mask_db_url(db_url: str) -> str:
    try:
        parsed = urlparse(db_url)
        if parsed.password:
            netloc = parsed.netloc.replace(parsed.password, "****")
            return urlunparse(parsed._replace(netloc=netloc))
        return db_url
    except Exception:
        return "<invalid_db_url>"


def _is_safe_identifier(value: str) -> bool:
    return isinstance(value, str) and value.isidentifier()


def get_database_config():
    env_file = BASE_DIR / ".env"
    is_ci = os.getenv("CI", "").lower() in ("true", "1", "yes")

    if DOTENV_AVAILABLE and env_file.exists() and not is_ci:
        load_dotenv(env_file)

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
            data_dir = BASE_DIR / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = data_dir / "playnexus.db"
            raw_url = f"sqlite:///{db_path.as_posix()}"

    is_postgres = raw_url.startswith(("postgresql://", "postgres://"))

    app_env = os.environ.get("ENV", "").lower() or os.environ.get("APP_ENV", "").lower()

    if app_env in ("prod", "production"):
        table_suffix = "_prod"
    elif app_env in ("test", "staging", "dev", "development"):
        table_suffix = "_test"
    else:
        table_suffix = ""

    db_schema = os.environ.get("DB_SCHEMA", "public")

    return raw_url, is_postgres, table_suffix, db_schema


def get_connection(db_url, is_postgres, db_schema="public"):
    if is_postgres:
        if not POSTGRES_AVAILABLE:
            print("[ERR] psycopg2-binary not installed.")
            sys.exit(1)

        conn = psycopg2.connect(db_url)
        conn.cursor_factory = RealDictCursor

        # ✅ FIX: validate schema
        if not _is_safe_identifier(db_schema):
            raise ValueError(f"Invalid schema: {db_schema}")

        try:
            conn.cursor().execute(f"SET search_path TO {db_schema}, public")
        except Exception:
            print("[WARN] Failed to set search_path")

        return conn, True
    else:
        db_path = db_url.replace("sqlite:///", "")
        conn = sqlite3.connect(db_path)
        return conn, False


def find_migrations():
    migrations_dir = BASE_DIR / "flyway" / "sql"
    if not migrations_dir.exists():
        print(f"[ERR] Migrations directory not found: {migrations_dir}")
        return []

    return sorted(migrations_dir.glob("V*__*.sql"))


def create_schema_version_table(conn, is_postgres, table_suffix=""):
    table_name = f"schema_version{table_suffix}"

    if not _is_safe_identifier(table_name):
        raise ValueError("Invalid table name")

    cursor = conn.cursor()

    if is_postgres:
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
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                version INTEGER PRIMARY KEY,
                script TEXT NOT NULL,
                installed_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    conn.commit()


def get_applied_migrations(conn, is_postgres, table_suffix=""):
    table_name = f"schema_version{table_suffix}"

    if not _is_safe_identifier(table_name):
        raise ValueError("Invalid table name")

    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT script FROM {table_name}")
        return {row['script'] if is_postgres else row[0] for row in cursor.fetchall()}
    except Exception:
        return set()


def apply_migration(conn, migration_file, is_postgres, dry_run=False, table_suffix=""):
    script_name = migration_file.name

    with open(migration_file, "r", encoding="utf-8") as f:
        sql = f.read()

    if is_postgres:
        sql = sql.replace("{AUTOINCREMENT}", "SERIAL PRIMARY KEY")
    else:
        sql = sql.replace("{AUTOINCREMENT}", "INTEGER PRIMARY KEY AUTOINCREMENT")

    sql = sql.replace("{table_suffix}", table_suffix)

    if dry_run:
        print(f"  [DRY RUN] Would apply: {script_name}")
        return True

    cursor = conn.cursor()

    try:
        import time
        start_time = time.time()

        if is_postgres:
            cursor.execute(sql)
        else:
            for stmt in sql.split(";"):
                if stmt.strip():
                    cursor.execute(stmt)

        schema_table = f"schema_version{table_suffix}"

        if is_postgres:
            import re

            match = re.match(r'V(\d+)__(.+)\.sql', script_name)
            version = match.group(1) if match else None
            description = match.group(2).replace('_', ' ') if match else script_name

            cursor.execute("SELECT current_user")
            installed_by = cursor.fetchone()[0]

            execution_time = int((time.time() - start_time) * 1000)

            cursor.execute(
                f"""INSERT INTO {schema_table}
                (version, description, type, script, checksum, installed_by, installed_on, execution_time, success)
                VALUES (%s, %s, 'SQL', %s, NULL, %s, CURRENT_TIMESTAMP, %s, %s)""",
                (version, description, script_name, installed_by, execution_time, True)
            )
        else:
            cursor.execute(
                f"INSERT INTO {schema_table} (script) VALUES (?)",
                (script_name,)
            )

        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        print(f"  [ERR] Failed: {script_name}")
        return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Lightweight database migrations")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    db_url, is_postgres, table_suffix, db_schema = get_database_config()

    # ✅ FIX: safe logging
    print(f"[DB] Database: {'PostgreSQL' if is_postgres else 'SQLite'}")
    print(f"[DB] URL: {mask_db_url(db_url)}")

    migrations = find_migrations()
    if not migrations:
        print("No migrations found.")
        sys.exit(0)

    if args.list:
        print("\nAvailable migrations:")
        for m in migrations:
            print(m.name)
        sys.exit(0)

    conn, is_postgres = get_connection(db_url, is_postgres, db_schema)

    create_schema_version_table(conn, is_postgres, table_suffix)
    applied = get_applied_migrations(conn, is_postgres, table_suffix)

    for migration in migrations:
        if migration.name in applied:
            print(f"[OK] {migration.name}")
            continue

        print(f"[RUN] {migration.name}")
        if not apply_migration(conn, migration, is_postgres, args.dry_run, table_suffix):
            print("[ERR] Migration failed")
            sys.exit(1)

    conn.close()
    print("\n[OK] Done")


if __name__ == "__main__":
    main()