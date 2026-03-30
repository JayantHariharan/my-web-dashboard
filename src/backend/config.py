"""
Configuration management for PlayNexus backend.
Handles environment-based settings with validation.
"""

import logging
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DatabaseConfig:
    """Database configuration."""

    url: str
    is_postgres: bool

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Build database config from environment variables."""
        raw_url = os.environ.get("DATABASE_URL", "")

        if not raw_url:
            # Construct from individual PostgreSQL environment variables
            pg_host = os.environ.get("PGHOST", "")
            pg_user = os.environ.get("PGUSER", "")
            pg_password = os.environ.get("PGPASSWORD", "")
            pg_database = os.environ.get("PGDATABASE", "")
            pg_port = os.environ.get("PGPORT", "5432")

            if all([pg_host, pg_user, pg_password, pg_database]):
                raw_url = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"
            else:
                # Fallback to local SQLite (place in data/ directory)
                project_root = os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )
                db_path = os.path.join(project_root, "data", "playnexus.db")
                raw_url = f"sqlite:///{db_path.replace(os.sep, '/')}"

        is_postgres = raw_url.startswith("postgresql://") or raw_url.startswith(
            "postgres://"
        )

        return cls(url=raw_url, is_postgres=is_postgres)


@dataclass
class Settings:
    """Application settings."""

    database: DatabaseConfig
    debug: bool = False
    secret_key: str = "change-me-in-production"  # Used for sessions if needed
    access_token_expire_minutes: int = 30
    log_level: int = logging.INFO  # Logging level (DEBUG, INFO, etc.)

    @classmethod
    def from_env(cls) -> "Settings":
        """Build settings from environment variables."""
        debug = os.environ.get("DEBUG", "false").lower() in ("true", "1", "yes")
        log_level_str = os.environ.get(
            "LOG_LEVEL", "INFO" if not debug else "DEBUG"
        ).upper()
        # Convert string to logging level constant
        log_level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        log_level = log_level_map.get(log_level_str, logging.INFO)

        return cls(
            database=DatabaseConfig.from_env(),
            debug=debug,
            secret_key=os.environ.get("SECRET_KEY", "change-me-in-production"),
            access_token_expire_minutes=int(
                os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
            ),
            log_level=log_level,
        )


# Global settings instance
settings = Settings.from_env()

# Security: Ensure SECRET_KEY is set in production
if not settings.debug and settings.secret_key == "change-me-in-production":
    raise RuntimeError(
        "SECRET_KEY environment variable must be set in production. "
        "Application startup aborted."
    )
