"""
PlayNexus Backend - Multi-App Platform
Entry point for running the FastAPI application.
"""

import os
import logging

from .core.app import create_app
from .config import settings
from .log_config import setup_logging

# Configure logging early
setup_logging()
logger = logging.getLogger(__name__)

# Create app
app = create_app()

# Include routers from modules
from .auth.router import router as auth_router
from .games.router import router as games_router
from .apps.router import router as apps_router

app.include_router(auth_router)
app.include_router(games_router)
app.include_router(apps_router)

# Mount static files (frontend)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")


# Startup event - initialize database
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting PlayNexus API...")
    logger.info(f"Environment: {'DEBUG' if settings.debug else 'PRODUCTION'}")
    logger.info(
        f"Database: {'PostgreSQL' if settings.database.is_postgres else 'SQLite'}"
    )

    # Apply database schema migrations
    try:
        from .migrator import apply_migrations

        apply_migrations()
    except Exception as e:
        logger.error(f"Database migration failed: {e}")
        if not settings.debug:
            raise

    # Load runtime configuration from app_config table (staging/production specific)
    try:
        settings.load_runtime_config(logger)
        logger.info(f"Runtime config loaded. Site: {settings.site_name}, Maintenance: {settings.maintenance_mode}")
    except Exception as e:
        logger.warning(f"Could not load runtime config: {e}")

    # Migrate any existing plain-text passwords to bcrypt (only runs if needed)
    try:
        from .shared.database import user_repo

        migrated = user_repo.migrate_plain_passwords()
        if migrated > 0:
            logger.warning(f"Auto-migrated {migrated} plain-text password(s).")
    except Exception as e:
        logger.error(f"Password migration failed: {e}")
        # Don't crash startup if migration fails; continue with hashed passwords only


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down PlayNexus API...")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level,
    )
