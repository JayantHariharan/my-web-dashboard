"""FastAPI application factory for the auth-first PlayNexus backend."""

import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.status import (
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from starlette.middleware.base import BaseHTTPMiddleware
from ..config import settings
from ..log_config import setup_logging
from .middlewares import (
    RequestIdMiddleware,
    RateLimitMiddleware,
    auth_rate_limiter,
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
Backend API for the current PlayNexus auth-first phase.

## Features
- Account authentication and account lifecycle endpoints
- Secure authentication with adaptive password hashing + pepper
- Request tracing and security headers
- IP audit logging
- Versioned database migrations
- Health monitoring endpoint

## Authentication
The frontend currently stores the active username in sessionStorage.
JWT or server-backed sessions can be added later.

## Rate Limits (per IP)
- **Auth endpoints** (`/api/auth/*`): 20 requests/hour, 15min block

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
    # For security, avoid wildcard with credentials. Use specific origins.
    if settings.debug:
        allow_origins = [
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    else:
        # In production, should be your domain(s)
        allow_origins = ["https://playnexus.onrender.com"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 3. Security Headers Middleware
    class SecurityHeadersMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            response = await call_next(request)
            # Prevent MIME type sniffing
            response.headers["X-Content-Type-Options"] = "nosniff"
            # Prevent clickjacking
            response.headers["X-Frame-Options"] = "DENY"
            # XSS protection (legacy browsers)
            response.headers["X-XSS-Protection"] = "1; mode=block"
            # Referrer policy
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            # Permissions policy (restrict sensitive features)
            response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
            # HSTS (HTTPS only) - enforce in production
            if not settings.debug:
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            return response

    app.add_middleware(SecurityHeadersMiddleware)

    # 4. Gzip compression for all responses
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # 3b. Cache control for static assets (CSS, JS, images)
    class CacheControlMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            response = await call_next(request)
            path = request.url.path

            # Add cache headers for static assets
            if path.startswith("/css/") or path.startswith("/js/") or path.startswith("/assets/"):
                # Cache for 1 week (immutable assets)
                response.headers["Cache-Control"] = "public, max-age=604800, immutable"
            elif path.startswith("/") and not path.startswith("/api") and not path.startswith("/docs") and not path.startswith("/redoc") and not path.startswith("/openapi.json"):
                # HTML pages - no cache (always fresh)
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

            return response

    app.add_middleware(CacheControlMiddleware)

    # 4. Rate limiting - auth endpoints only in the current phase
    app.add_middleware(
        RateLimitMiddleware, limiter=auth_rate_limiter, paths=["/api/auth"]
    )

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
