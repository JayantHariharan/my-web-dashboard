"""
Logging configuration for the PlayNexus backend.

Call :func:`setup_logging` once at process startup (already done by both
``main.py`` and the ``create_app()`` factory so it is safe to call twice
– the second call is a no-op because it clears and re-adds handlers).

Handler summary
---------------
- **Console** (``stdout``): always active; level controlled by
  ``settings.log_level`` (``INFO`` in production, ``DEBUG`` when
  ``DEBUG=true``).
- **Rotating file** (``src/logs/playnexus.log``): production-only
  (``settings.debug = False``); rotates at 10 MB, keeps 5 archived copies.

Supports structured output by keeping the format tag-friendly
(``%(name)s`` is the dotted Python module path).
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from .config import settings


def setup_logging() -> logging.Logger:
    """
    Configure application-wide logging.

    Attaches a ``StreamHandler`` (console) to the root logger in all
    environments.  In **production** (``settings.debug = False``) an
    additional ``RotatingFileHandler`` is added that writes to
    ``src/logs/playnexus.log``.

    The uvicorn access log is demoted to ``WARNING`` level in production
    to reduce noise from health-check polls.

    Returns:
        The configured root :class:`logging.Logger` instance.
    """
    logger = logging.getLogger()
    logger.setLevel(settings.log_level)

    # Clear any existing handlers
    logger.handlers.clear()

    # Console handler (always)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(settings.log_level)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (in production, rotate logs)
    if not settings.debug:
        # Determine logs directory (relative to project root)
        base_dir = Path(__file__).parent.parent
        logs_dir = base_dir / "logs"
        logs_dir.mkdir(exist_ok=True)

        log_file = logs_dir / "playnexus.log"

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,  # Keep 5 rotated files
            encoding="utf-8",
        )
        file_handler.setLevel(
            logging.INFO
        )  # File gets INFO+ by default, can be configurable too
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        logger.info(f"Logging to file: {log_file} (rotation: 10MB x 5)")

    # Reduce noise from uvicorn access logs in production
    if not settings.debug:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    return logger
