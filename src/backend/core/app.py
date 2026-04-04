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

setup_logging()
logger = logging.getLogger(__name__)


def _sanitize_error(exc: Exception) -> str:
    msg = str(exc)
    if any(k in msg.lower() for k in ["password", "secret", "token"]):
        return "Sensitive error hidden"
    return msg


def create_app() -> FastAPI:
    app = FastAPI(
        title="PlayNexus API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # 1. Request ID
    app.add_middleware(RequestIdMiddleware)

    # 2. CORS
    if settings.debug:
        allow_origins = [
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    else:
        allow_origins = [
            "https://playnexus-prod.onrender.com",
            "https://playnexus-test.onrender.com",
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 3. Security Headers
    class SecurityHeadersMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            response = await call_next(request)

            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
            response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

            # 🔥 Important: CSP
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "connect-src 'self';"
            )

            if not settings.debug:
                response.headers["Strict-Transport-Security"] = (
                    "max-age=31536000; includeSubDomains"
                )

            return response

    app.add_middleware(SecurityHeadersMiddleware)

    # 4. Cache Control
    class CacheControlMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            response = await call_next(request)
            path = request.url.path

            if path.startswith(("/css/", "/js/", "/assets/")):
                response.headers["Cache-Control"] = "public, max-age=604800, immutable"
            elif not path.startswith(("/api", "/docs", "/redoc", "/openapi.json")):
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

            return response

    app.add_middleware(CacheControlMiddleware)

    # 5. Gzip
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # 6. Rate Limiting (FIXED path)
    app.add_middleware(
        RateLimitMiddleware,
        limiter=auth_rate_limiter,
        paths=["/api/auth/"],  # ✅ FIX
    )

    # Health Check
    @app.get("/health", tags=["Health"])
    async def health_check():
        from ..shared.database import user_repo

        try:
            with user_repo.get_cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                db_ok = result is not None
        except Exception as e:
            logger.error(f"Health check failed: {_sanitize_error(e)}")
            db_ok = False

        if not db_ok:
            raise HTTPException(status_code=503, detail="Database unavailable")

        return {
            "status": "healthy",
            "service": "PlayNexus API",
            "database": "connected",
            "environment": "production" if not settings.debug else "development",
        }

    # Exception Handlers

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.warning(
            f"{request.method} {request.url.path} -> {exc.status_code}: {exc.detail}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(
            f"Validation error at {request.url.path}: {exc.errors()}"
        )
        return JSONResponse(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(
            f"Unhandled error at {request.method} {request.url.path}: {_sanitize_error(exc)}"
        )
        return JSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

    logger.info("FastAPI application created")
    return app