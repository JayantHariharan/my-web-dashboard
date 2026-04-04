"""
Configuration management for PlayNexus backend.
Handles environment-based settings with validation.
"""

import logging
import os
import re
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


ENV_KEYS = {
    "DATABASE_URL",
    "PGHOST",
    "PGPORT",
    "PGUSER",
    "PGPASSWORD",
    "PGDATABASE",
    "SECRET_KEY",
    "DEBUG",
    "LOG_LEVEL",
    "APP_ENV",
    "ENV",
    "DB_SCHEMA",
}

has_runtime_env = any(os.environ.get(key) for key in ENV_KEYS)

if (
    load_dotenv
    and not has_runtime_env
    and os.environ.get("CI", "").lower() not in {"1", "true", "yes"}
):
    env_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        ".env",
    )
    if os.path.exists(env_path):
        load_dotenv(env_path, override=False)


# ✅ Helper validation
def _is_safe_identifier(value: str) -> bool:
    return isinstance(value, str) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", value)


@dataclass
class DatabaseConfig:
    """Database configuration."""

    url: str
    is_postgres: bool
    table_suffix: str = ""
    db_schema: str = "public"
    pool_size: int = 5
    max_overflow: int = 10

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Build database config from environment variables."""

        raw_url = os.environ.get("DATABASE_URL", "")

        if not raw_url:
            pg_host = os.environ.get("PGHOST", "")
            pg_user = os.environ.get("PGUSER", "")
            pg_password = os.environ.get("PGPASSWORD", "")
            pg_database = os.environ.get("PGDATABASE", "")
            pg_port = os.environ.get("PGPORT", "5432")

            if all([pg_host, pg_user, pg_password, pg_database]):
                raw_url = (
                    f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"
                )
            else:
                project_root = os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )
                data_dir = os.path.join(project_root, "data")
                os.makedirs(data_dir, exist_ok=True)
                db_path = os.path.join(data_dir, "playnexus.db")
                raw_url = f"sqlite:///{db_path.replace(os.sep, '/')}"

        is_postgres = raw_url.startswith(("postgresql://", "postgres://"))

        # ENV detection
        app_env = (os.environ.get("ENV") or os.environ.get("APP_ENV") or "").lower()

        if app_env in ("prod", "production"):
            table_suffix = "_prod"
        elif app_env in ("test", "staging", "dev", "development"):
            table_suffix = "_test"
        else:
            table_suffix = ""

        # ✅ FIX: validate schema name
        db_schema = os.environ.get("DB_SCHEMA", "public")
        if not _is_safe_identifier(db_schema):
            raise ValueError("Invalid DB_SCHEMA value")

        # ✅ FIX: safe pool size
        try:
            pool_size = int(os.environ.get("DB_POOL_SIZE", "5"))
            pool_size = max(1, min(pool_size, 20))  # clamp 1–20
        except ValueError:
            pool_size = 5

        return cls(
            url=raw_url,
            is_postgres=is_postgres,
            table_suffix=table_suffix,
            db_schema=db_schema,
            pool_size=pool_size,
        )


@dataclass
class Settings:
    """Application settings (auth-only mode)."""

    database: DatabaseConfig
    debug: bool = False
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 30
    log_level: int = logging.INFO

    registration_enabled: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        """Build settings from environment variables."""

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

        secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")

        # ✅ FIX: enforce strong secret in production
        app_env = (os.environ.get("ENV") or os.environ.get("APP_ENV") or "").lower()
        is_production_like = app_env in {"prod", "production"}

        if is_production_like and not debug:
            if secret_key == "change-me-in-production" or len(secret_key) < 32:
                raise RuntimeError(
                    "SECRET_KEY must be set and at least 32 characters in production"
                )

        return cls(
            database=DatabaseConfig.from_env(),
            debug=debug,
            secret_key=secret_key,
            access_token_expire_minutes=int(
                os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
            ),
            log_level=log_level,
        )


# Global settings instance
settings = Settings.from_env()