"""
Logging configuration for PlayNexus.
Supports console output and optional file rotation.
"""

import logging
import sys
import re
from pathlib import Path
from logging.handlers import RotatingFileHandler
from .config import settings


# ✅ Sensitive patterns to mask
SENSITIVE_PATTERNS = [
    re.compile(r"(password\s*=\s*)(\S+)", re.IGNORECASE),
    re.compile(r"(passwd\s*=\s*)(\S+)", re.IGNORECASE),
    re.compile(r"(token\s*=\s*)(\S+)", re.IGNORECASE),
    re.compile(r"(authorization\s*=\s*)(\S+)", re.IGNORECASE),
    re.compile(r"(api[_-]?key\s*=\s*)(\S+)", re.IGNORECASE),
]


class SensitiveDataFilter(logging.Filter):
    """Filter to mask sensitive data in logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            msg = record.msg

            # ✅ Mask sensitive patterns
            for pattern in SENSITIVE_PATTERNS:
                msg = pattern.sub(r"\1****", msg)

            # ✅ Prevent log injection (strip newlines)
            msg = msg.replace("\n", "\\n").replace("\r", "\\r")

            record.msg = msg

        return True


def setup_logging():
    """Configure application logging."""
    logger = logging.getLogger()
    logger.setLevel(settings.log_level)

    # Clear any existing handlers
    logger.handlers.clear()

    # Add global filter
    sensitive_filter = SensitiveDataFilter()

    # Console handler (always)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(settings.log_level)
    console_handler.addFilter(sensitive_filter)

    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (in production, rotate logs)
    if not settings.debug:
        base_dir = Path(__file__).parent.parent
        logs_dir = base_dir / "logs"
        logs_dir.mkdir(exist_ok=True)

        log_file = logs_dir / "playnexus.log"

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.INFO)
        file_handler.addFilter(sensitive_filter)

        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # ✅ Avoid exposing full path
        logger.info("File logging enabled (rotation active)")

    # Reduce noise from uvicorn access logs in production
    if not settings.debug:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    return logger