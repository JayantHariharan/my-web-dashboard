"""
Configuration management for PlayNexus backend.
Handles environment-based settings with validation.
- Environment variables for connection & secrets
- Database table (app_config) for runtime, environment-specific settings
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


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
    """Application settings.

    Split into:
    - Core: from environment variables (set at deploy time)
    - Runtime: from database app_config table (can change without restart)
    """

    database: DatabaseConfig
    debug: bool = False
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 30
    log_level: int = logging.INFO

    # Runtime configuration (loaded from app_config table)
    # Only include what's currently needed; add more as requirements grow
    registration_enabled: bool = True  # Auth-related: allow new user signups

    # Store any extra config keys from DB that don't have explicit fields
    extra_config: Dict[str, Any] = field(default_factory=dict)

    # Store any extra config keys from DB that don't have explicit fields
    extra_config: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "Settings":
        """Build base settings from environment variables."""
        debug = os.environ.get("DEBUG", "false").lower() in ("true", "1", "yes")
        log_level_str = os.environ.get(
            "LOG_LEVEL", "INFO" if not debug else "DEBUG"
        ).upper()
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

    def load_runtime_config(self, logger: Optional[logging.Logger] = None) -> None:
        """Load environment-specific runtime configuration from app_config table.

        Called after database connection is established (in startup).
        Updates settings with values from app_config for the current APP_ENV.

        Only known keys are set on the settings object; unknown keys go to extra_config.

        Args:
            logger: Optional logger for debug messages
        """
        if self.debug:
            if logger:
                logger.info("Skipping runtime config load in DEBUG mode (using defaults)")
            return

        try:
            from .shared.database import get_connection

            app_env = os.environ.get("APP_ENV", "")
            if not app_env:
                if logger:
                    logger.warning("APP_ENV not set, cannot load environment-specific config")
                return

            with get_connection(self.database.is_postgres, self.database.url) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT key, value FROM app_config WHERE env = ?",
                    (app_env,)
                )
                rows = cursor.fetchall()

                if logger:
                    logger.info(f"Loaded {len(rows)} runtime config values for environment: {app_env}")

                for key, value in rows:
                    # Only handle known keys explicitly
                    if key == 'registration_enabled':
                        parsed_value = value.lower() == 'true'
                    else:
                        # Future keys: add more handling here as needed
                        parsed_value = value

                    # Set on self if attribute exists, otherwise store in extra_config
                    if hasattr(self, key):
                        setattr(self, key, parsed_value)
                    else:
                        self.extra_config[key] = parsed_value

        except Exception as e:
            if logger:
                logger.warning(f"Could not load runtime config from database: {e}")


# Global settings instance
settings = Settings.from_env()

# Security: Ensure SECRET_KEY is set in production
if not settings.debug and settings.secret_key == "change-me-in-production":
    raise RuntimeError(
        "SECRET_KEY environment variable must be set in production. "
        "Application startup aborted."
    )
