"""
FastAPI application factory.
Creates and configures the PlayNexus API application.
"""

import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.status import (
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from ..config import settings
from ..log_config import setup_logging
from .middlewares import (
    RequestIdMiddleware,
    RateLimitMiddleware,
    auth_rate_limiter,
    games_rate_limiter,
    apps_rate_limiter,
)

# Configure logging early
setup_logging()
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Factory function to create and configure the FastAPI application.

    Returns:
        Configured FastAPI app instance
    """
    app = FastAPI(
        title="PlayNexus API",
        description="""
Backend API for PlayNexus gaming hub - Multi-App Platform.

## Features
- Modular app architecture (auth, games, utilities)
- Secure authentication with bcrypt + pepper
- Rate limiting per app category
- IP audit logging
- Flyway-style database migrations
- Health monitoring endpoint

## Authentication
Currently uses stateless authentication with username in sessionStorage.
Future: JWT tokens for persistent sessions.

## Rate Limits (per IP)
- **Auth endpoints** (`/api/auth/*`): 20 requests/hour, 15min block
- **Games endpoints** (`/api/games/*`): 100 requests/hour, 10min block
- **General apps** (`/apps/*`): 200 requests/hour, 10min block

## Environment
- **Development**: DEBUG=true, SQLite database
- **Production**: DEBUG=false, PostgreSQL database
""",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Add middleware (order matters)
    # 1. Request ID - adds X-Request-ID header
    app.add_middleware(RequestIdMiddleware)

    # 2. CORS - allow cross-origin requests (configure per environment)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else ["https://your-app.onrender.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 3. Rate limiting - per app category
    # Auth endpoints (strict limit)
    app.add_middleware(
        RateLimitMiddleware, limiter=auth_rate_limiter, paths=["/api/auth"]
    )
    # Games endpoints (moderate limit)
    app.add_middleware(
        RateLimitMiddleware, limiter=games_rate_limiter, paths=["/api/games"]
    )
    # General apps (higher limit)
    app.add_middleware(RateLimitMiddleware, limiter=apps_rate_limiter, paths=["/apps"])

    # Health check endpoint (no rate limit)
    @app.get("/health", tags=["Health"])
    async def health_check():
        """
        Health check endpoint for monitoring.
        Tests database connectivity.

        ## Response Example (Healthy)
        ```json
        {
            "status": "healthy",
            "service": "PlayNexus API",
            "database": "connected",
            "environment": "production"
        }
        ```

        ## Response Example (Unhealthy)
        ```json
        {
            "status": "unhealthy",
            "service": "PlayNexus API",
            "database": "disconnected",
            "environment": "production"
        }
        ```
        """
        from ..shared.database import user_repo

        try:
            with user_repo.get_cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                db_ok = result is not None
        except Exception as e:
            logger.error(f"Health check DB test failed: {e}")
            db_ok = False

        if not db_ok:
            raise HTTPException(status_code=503, detail="Database unavailable")

        return {
            "status": "healthy",
            "service": "PlayNexus API",
            "database": "connected",
            "environment": "production" if not settings.debug else "development",
        }

    # Exception handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        logger.warning(f"Validation error: {exc.errors()}")
        return JSONResponse(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

    logger.info("FastAPI application created")
    return app
