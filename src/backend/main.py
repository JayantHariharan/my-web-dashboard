"""
PlayNexus Backend - Multi-App Platform
Entry point for running the FastAPI application.
"""

import os
import logging

from fastapi.staticfiles import StaticFiles

from .core.app import create_app
from .config import settings
from .log_config import setup_logging
from .auth.router import router as auth_router

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

app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")


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
