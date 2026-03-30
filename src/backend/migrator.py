"""
Database migration engine.
Applies Flyway-style versioned SQL migrations on startup.
"""

import logging
import os
from pathlib import Path
from typing import List

from .config import settings
from .shared.database import get_connection

logger = logging.getLogger(__name__)


def find_migrations() -> List[str]:
    """Find all SQL migration files in order."""
    # Project root flyway/sql directory
    migrations_dir = (
        Path(__file__).parent.parent.parent / "flyway" / "sql"
    )
    if not migrations_dir.exists():
        logger.warning(f"Migrations directory not found: {migrations_dir}")
        return []

    migrations = []
    for file in sorted(migrations_dir.glob("V*__*.sql")):
        migrations.append(str(file))

    return migrations


def apply_migrations():
    """Apply all pending migrations to the database."""
    if settings.database.is_postgres:
        logger.info("Skipping auto-migrations for PostgreSQL (use psql/cli)")
        return

    migrations = find_migrations()
    if not migrations:
        logger.info("No migrations to apply")
        return

    logger.info(f"Found {len(migrations)} migration(s) to apply")

    with get_connection(
        settings.database.is_postgres,
        settings.database.url
    ) as conn:
        cursor = conn.cursor()

        # Create migrations table if it doesn't exist (SQLite)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                script TEXT NOT NULL,
                installed_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        # Get already applied migrations
        cursor.execute("SELECT script FROM schema_version")
        applied = {row[0] for row in cursor.fetchall()}

        for migration in migrations:
            script_name = os.path.basename(migration)

            if script_name in applied:
                logger.debug(f"Already applied: {script_name}")
                continue

            logger.info(f"Applying migration: {script_name}")

            try:
                with open(migration, "r", encoding="utf-8") as f:
                    sql = f.read()

                # Replace placeholders based on database type
                if settings.database.is_postgres:
                    sql = sql.replace("{AUTOINCREMENT}", "SERIAL PRIMARY KEY")
                    sql = sql.replace("{TEXT}", "TEXT")
                else:
                    sql = sql.replace(
                        "{AUTOINCREMENT}", "INTEGER PRIMARY KEY AUTOINCREMENT"
                    )
                    sql = sql.replace("{TEXT}", "TEXT")

                # Execute each statement separately (SQLite lacks multi-statement exec)
                if settings.database.is_postgres:
                    cursor.execute(sql)
                else:
                    # SQLite: split on semicolons
                    for statement in sql.split(";"):
                        stmt = statement.strip()
                        if stmt:
                            cursor.execute(stmt)

                # Record migration
                cursor.execute(
                    "INSERT INTO schema_version (script) VALUES (?)", (script_name,)
                )
                conn.commit()
                logger.info(f"Applied: {script_name}")

            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to apply {script_name}: {e}")
                raise

    logger.info("All migrations applied successfully")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    apply_migrations()
