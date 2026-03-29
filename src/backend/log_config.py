"""
Logging configuration for PlayNexus.
Supports console output and optional file rotation.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from .config import settings


def setup_logging():
    """Configure application logging."""
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
