"""Entry point for the PlayNexus backend."""

import os
import logging
import sqlite3
from datetime import datetime

from fastapi.staticfiles import StaticFiles

from .core.app import create_app
from .config import settings
from .log_config import setup_logging
from .auth.router import router as auth_router
from .shared.database import configure_sqlite_connection

# Configure logging early
setup_logging()
logger = logging.getLogger(__name__)

# Create app
app = create_app()

# Include routers from modules
app.include_router(auth_router)

# Mount static files (frontend)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
PROJECT_ROOT = os.path.dirname(BASE_DIR)

app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")


def ensure_local_sqlite_schema() -> None:
    """Bootstrap the local SQLite schema from the current migration if needed."""
    if settings.database.is_postgres:
        return

    table_suffix = settings.database.table_suffix
    users_table = f"users{table_suffix}"
    schema_version_table = f"schema_version{table_suffix}"

    for attempt in range(2):
        db_path = settings.database.url.replace("sqlite:///", "")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = None
        try:
            conn = configure_sqlite_connection(sqlite3.connect(db_path, timeout=30))
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (users_table,),
            )
            if cursor.fetchone():
                return

            cursor.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {schema_version_table} (
                    version INTEGER PRIMARY KEY,
                    script TEXT NOT NULL,
                    installed_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            migration_path = os.path.join(
                PROJECT_ROOT, "flyway", "sql", "V1__create_users.sql"
            )
            with open(migration_path, "r", encoding="utf-8") as migration_file:
                sql = migration_file.read()

            sql = sql.replace("{AUTOINCREMENT}", "INTEGER PRIMARY KEY AUTOINCREMENT")
            sql = sql.replace("{TEXT}", "TEXT")
            sql = sql.replace("{table_suffix}", table_suffix)

            for statement in sql.split(";"):
                stmt = statement.strip()
                if stmt:
                    cursor.execute(stmt)

            cursor.execute(
                f"INSERT INTO {schema_version_table} (script) VALUES (?)",
                ("V1__create_users.sql",),
            )
            conn.commit()
            logger.info("Initialized local SQLite schema from V1__create_users.sql")
            return
        except sqlite3.Error as exc:
            if conn:
                conn.close()
            if attempt == 0:
                recover_broken_local_sqlite_db(db_path, exc)
                continue
            raise
        finally:
            if conn:
                conn.close()


def recover_broken_local_sqlite_db(db_path: str, exc: Exception) -> None:
    """Move aside a broken local SQLite database so startup can recreate it cleanly."""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    candidates = [db_path, f"{db_path}-journal", f"{db_path}-wal", f"{db_path}-shm"]
    moved_any = False

    logger.warning(
        "Local SQLite bootstrap failed for %s: %s. Attempting automatic recovery.",
        db_path,
        exc,
    )

    for candidate in candidates:
        if not os.path.exists(candidate):
            continue

        recovered_path = f"{candidate}.corrupt-{timestamp}"
        try:
            os.replace(candidate, recovered_path)
            moved_any = True
            logger.warning("Moved broken SQLite artifact to %s", recovered_path)
        except PermissionError:
            logger.warning(
                "Could not move locked SQLite artifact %s. Leaving it in place.",
                candidate,
            )

    if moved_any:
        return

    fallback_path = os.path.join(os.path.dirname(db_path), "playnexus-recovered.db")
    settings.database.url = f"sqlite:///{fallback_path.replace(os.sep, '/')}"
    logger.warning(
        "SQLite recovery is using a fresh fallback database at %s",
        fallback_path,
    )


# Startup event - initialize application
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting PlayNexus API...")
    logger.info(f"Environment: {'DEBUG' if settings.debug else 'PRODUCTION'}")
    db_type = "PostgreSQL" if settings.database.is_postgres else "SQLite"
    logger.info(f"Database: {db_type}")

    logger.info("Configuration: Using environment variables only")
    logger.info(
        "Note: Database migrations are applied via GitHub Actions (migrate workflow)"
    )
    logger.info(
        "Local development: Use SQLite (auto-creates schema) or run migrate.py manually"
    )

    try:
        ensure_local_sqlite_schema()
    except Exception as e:
        logger.error(f"Local schema initialization failed: {e}")
        raise

    # Migrate any existing plain-text passwords to bcrypt (only runs if needed)
    try:
        from .shared.database import user_repo

        migrated = user_repo.migrate_plain_passwords()
        if migrated > 0:
            logger.warning(f"Auto-migrated {migrated} plain-text password(s).")
    except Exception as e:
        logger.error(f"Password migration failed: {e}")
        # Don't crash if migration fails; continue with hashed passwords


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down PlayNexus API...")



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level,
    )
