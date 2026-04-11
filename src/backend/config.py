"""
Configuration management for the PlayNexus backend.

All runtime settings are read from environment variables at process startup.
No file-based config (e.g. ``.env``) is loaded in CI or production-like
environments; a ``.env`` file is only read locally when **none** of the
recognised environment variables are set (via ``python-dotenv``).

Quick reference
---------------
See :class:`DatabaseConfig` and :class:`Settings` for the full list of
recognised environment variables and their defaults.

Production guard
----------------
``SECRET_KEY`` must be set (and not left as the default placeholder) when
``ENV=prod`` / ``APP_ENV=production``.  The application raises a
:class:`RuntimeError` at import time if this condition is not met.
"""

import logging
import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency in some environments
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
    "CORS_ORIGINS",
    "REGISTRATION_ENABLED",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
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


@dataclass
class DatabaseConfig:
    """
    Database connection configuration.

    Built from environment variables by :meth:`from_env`.

    Environment variables
    ---------------------
    .. list-table::
       :header-rows: 1
       :widths: 25 75

       * - Variable
         - Purpose
       * - ``DATABASE_URL``
         - Full PostgreSQL connection string.  Takes priority over individual
           ``PG*`` variables.
       * - ``PGHOST`` / ``PGPORT`` / ``PGUSER`` / ``PGPASSWORD`` / ``PGDATABASE``
         - Composited into a ``postgresql://`` URL when ``DATABASE_URL`` is absent.
       * - ``DB_SCHEMA``
         - PostgreSQL schema to set as ``search_path`` (default: ``public``).
       * - ``DB_POOL_SIZE``
         - Max open connections per worker (default: ``5``; Supabase free tier max is 10–20).
       * - ``ENV`` / ``APP_ENV``
         - Derives the table-name suffix: ``prod`` → ``_prod``;
           ``test``/``dev``/``staging`` → ``_test``; unset → no suffix.
    """

    url: str
    is_postgres: bool
    table_suffix: str = ""  # Suffix for table names (e.g., "_test", "_prod")
    db_schema: str = "public"  # PostgreSQL schema (default: public). Ignored for SQLite.
    pool_size: int = 5  # Recommended for Supabase free tier (max 10-20 connections total)
    max_overflow: int = 10

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
                raw_url = (
                    f"postgresql://{pg_user}:{pg_password}@{pg_host}:"
                    f"{pg_port}/{pg_database}"
                )
            else:
                # Fallback to local SQLite (place in data/ directory)
                project_root = os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )
                data_dir = os.path.join(project_root, "data")
                # Ensure data directory exists
                os.makedirs(data_dir, exist_ok=True)
                db_path = os.path.join(data_dir, "playnexus.db")
                raw_url = f"sqlite:///{db_path.replace(os.sep, '/')}"

        is_postgres = raw_url.startswith("postgresql://") or raw_url.startswith(
            "postgres://"
        )

        # Derive table suffix from ENV variable (test → _test, prod → _prod)
        # Local dev: no ENV set → empty suffix
        # Priority: ENV > APP_ENV > default
        app_env = os.environ.get("ENV", "").lower()
        if not app_env:
            app_env = os.environ.get("APP_ENV", "").lower()

        if app_env == "prod" or app_env == "production":
            table_suffix = "_prod"
        elif (
            app_env == "test"
            or app_env == "staging"
            or app_env == "dev"
            or app_env == "development"
        ):
            table_suffix = "_test"
        else:
            table_suffix = ""  # Local dev or unknown env

        # Get custom schema (PostgreSQL only). Default: 'public'
        db_schema = os.environ.get("DB_SCHEMA", "public")
        
        # Max pool size for free tier (default 5 to stay safe)
        pool_size = int(os.environ.get("DB_POOL_SIZE", "5"))

        return cls(
            url=raw_url,
            is_postgres=is_postgres,
            table_suffix=table_suffix,
            db_schema=db_schema,
            pool_size=pool_size
        )


@dataclass
class Settings:
    """
    Top-level application settings.

    Built from environment variables by :meth:`from_env`.  A singleton
    instance (``settings``) is created at module import time and imported
    by the rest of the application.

    Environment variables
    ---------------------
    .. list-table::
       :header-rows: 1
       :widths: 25 75

       * - Variable
         - Purpose
       * - ``SECRET_KEY``
         - Server-side pepper for password hashing.  **Required** in production.
           Changing this value invalidates all stored password hashes.
       * - ``DEBUG``
         - ``true`` / ``1`` enables dev CORS origins and ``DEBUG``-level logging.
       * - ``LOG_LEVEL``
         - Override the log verbosity (``DEBUG``, ``INFO``, ``WARNING``, etc.).
       * - ``REGISTRATION_ENABLED``
         - ``false`` disables new signups (returns ``403`` on ``/api/auth/signup``).
       * - ``ACCESS_TOKEN_EXPIRE_MINUTES``
         - Reserved for future JWT implementation (default: ``30``).
    """

    database: DatabaseConfig
    debug: bool = False
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 30
    log_level: int = logging.INFO

    # AI settings
    openai_api_key: str = ""
    openai_model: str = "gpt-3.5-turbo"

    # Auth-related settings
    registration_enabled: bool = True  # Allow new user signups

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

        registration_enabled = os.environ.get(
            "REGISTRATION_ENABLED", "true"
        ).lower() in ("true", "1", "yes")

        return cls(
            database=DatabaseConfig.from_env(),
            debug=debug,
            secret_key=os.environ.get("SECRET_KEY", "change-me-in-production"),
            access_token_expire_minutes=int(
                os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
            ),
            log_level=log_level,
            registration_enabled=registration_enabled,
            openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
            openai_model=os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo"),
        )


# Global settings instance
settings = Settings.from_env()

app_env = (os.environ.get("ENV") or os.environ.get("APP_ENV") or "").lower()
is_production_like = app_env in {"prod", "production"}

# Security: Ensure SECRET_KEY is set for production-like environments.
# Local SQLite development should still be able to start without extra setup.
if (
    is_production_like
    and not settings.debug
    and settings.secret_key == "change-me-in-production"
):
    raise RuntimeError(
        "SECRET_KEY environment variable must be set in production. "
        "Application startup aborted."
    )
