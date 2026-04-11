"""
Entry point for the PlayNexus backend.

Registers the authentication router, mounts the static frontend, and
bootstraps the local SQLite schema when PostgreSQL is not configured.

The application lifecycle (startup / shutdown) is managed via FastAPI's
``lifespan`` context manager – the deprecated ``@app.on_event`` hooks have
been removed as they are scheduled for removal in a future FastAPI release.
"""

import os
import logging
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .core.app import create_app
from .config import settings
from .log_config import setup_logging
from .auth.router import router as auth_router
from .games.router import router as games_router
from .shared.database import configure_sqlite_connection

# Configure logging early (before any code that may emit log records).
setup_logging()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
PROJECT_ROOT = os.path.dirname(BASE_DIR)


# ---------------------------------------------------------------------------
# Application lifespan (replaces deprecated @app.on_event hooks)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """
    Manage the full application lifecycle for FastAPI.

    Code **before** ``yield`` runs once at startup; code **after** ``yield``
    runs once during graceful shutdown.

    Startup sequence
    ----------------
    1. Log the active environment (DEBUG / PRODUCTION) and database type.
    2. Bootstrap the local SQLite schema when PostgreSQL is not configured.
       - If the schema already exists the operation is a no-op.
       - If the database file is corrupt, :func:`recover_broken_local_sqlite_db`
         renames it aside and reattempts with a fresh file.
    3. Migrate any plain-text passwords to bcrypt hashes (idempotent; skipped
       when every password is already properly hashed).

    Shutdown sequence
    -----------------
    - Emit a graceful shutdown log line.
    """
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("Starting PlayNexus API...")
    logger.info("Environment: %s", "DEBUG" if settings.debug else "PRODUCTION")
    db_type = "PostgreSQL" if settings.database.is_postgres else "SQLite"
    logger.info("Database: %s", db_type)
    logger.info(
        "Note: Database migrations are applied via GitHub Actions (migrate workflow). "
        "Local development uses SQLite (auto-creates schema) or run migrate.py manually."
    )

    try:
        ensure_local_sqlite_schema()
    except Exception as exc:
        logger.error("Local schema initialisation failed: %s", exc)
        raise

    # Migrate any stored plain-text passwords to bcrypt (idempotent).
    try:
        from .shared.database import user_repo  # noqa: PLC0415 – deferred import

        migrated = user_repo.migrate_plain_passwords()
        if migrated > 0:
            logger.warning("Auto-migrated %d plain-text password(s).", migrated)
    except Exception as exc:
        logger.error("Password migration failed: %s", exc)
        # Non-fatal: the app can still serve requests with correctly hashed passwords.

    yield  # ── Application is now serving requests ────────────────────────

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("Shutting down PlayNexus API...")


# ---------------------------------------------------------------------------
# Application factory + router + static files
# ---------------------------------------------------------------------------

app = create_app(lifespan=_lifespan)

# Register the authentication router (/api/auth/*)
app.include_router(auth_router)

# Register the games router (/api/games/*)
app.include_router(games_router)

# Serve the static frontend (SPA-style: html=True handles directory index)
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")


# ---------------------------------------------------------------------------
# Local SQLite helpers
# ---------------------------------------------------------------------------


def ensure_local_sqlite_schema() -> None:
    """
    Bootstrap the local SQLite schema from all Flyway migration scripts.
    """
    if settings.database.is_postgres:
        return

    table_suffix = settings.database.table_suffix
    schema_version_table = f"schema_version{table_suffix}"
    db_path = settings.database.url.replace("sqlite:///", "")
    
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    for attempt in range(2):
        conn = None
        try:
            conn = configure_sqlite_connection(sqlite3.connect(db_path, timeout=30))
            cursor = conn.cursor()

            # Create the schema-version tracking table.
            cursor.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {schema_version_table} (
                    version INTEGER PRIMARY KEY AUTOINCREMENT,
                    script TEXT UNIQUE NOT NULL,
                    installed_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Discover migrations in order
            sql_dir = os.path.join(PROJECT_ROOT, "flyway", "sql")
            scripts = sorted([f for f in os.listdir(sql_dir) if f.endswith(".sql")])

            for script_name in scripts:
                cursor.execute(f"SELECT 1 FROM {schema_version_table} WHERE script = ?", (script_name,))
                if cursor.fetchone():
                    continue

                logger.info("Applying migration: %s", script_name)
                with open(os.path.join(sql_dir, script_name), "r", encoding="utf-8") as f:
                    sql = f.read()

                # Placeholders
                sql = sql.replace("{AUTOINCREMENT}", "INTEGER PRIMARY KEY AUTOINCREMENT")
                sql = sql.replace("{TEXT}", "TEXT")
                sql = sql.replace("{table_suffix}", table_suffix)

                for statement in sql.split(";"):
                    stmt = statement.strip()
                    if stmt:
                        cursor.execute(stmt)

                cursor.execute(f"INSERT INTO {schema_version_table} (script) VALUES (?)", (script_name,))
                conn.commit()
                logger.info("Successfully applied %s", script_name)
            
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
    """
    Attempt to recover from a corrupt local SQLite database.

    Renames the broken database file **and** any associated WAL / SHM /
    journal side-files by appending a ``.corrupt-<utc-timestamp>`` suffix so
    that the next startup attempt can create a fresh, valid database.

    If no files can be renamed (e.g. due to a permission error on Windows),
    a brand-new fallback path is chosen and :attr:`settings.database.url` is
    updated in-place so that the immediate retry uses a clean file.

    Args:
        db_path: Absolute path to the SQLite database that raised the error.
        exc:     The :class:`sqlite3.Error` that triggered recovery.

    Note:
        ``datetime.utcnow()`` is deprecated in Python 3.12+; this function
        uses the timezone-aware ``datetime.now(timezone.utc)`` instead.
    """
    # timezone.utc-aware timestamp avoids the DeprecationWarning from utcnow()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
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

    # Nothing could be moved – switch to an entirely new fallback file.
    fallback_path = os.path.join(os.path.dirname(db_path), "playnexus-recovered.db")
    settings.database.url = f"sqlite:///{fallback_path.replace(os.sep, '/')}"
    logger.warning(
        "SQLite recovery is using a fresh fallback database at %s", fallback_path
    )


# ---------------------------------------------------------------------------
# Direct execution (development only – prefer uvicorn CLI in production)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level,
    )
