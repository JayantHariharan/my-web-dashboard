"""Security utilities for PlayNexus authentication."""

import logging
from typing import Optional
from passlib.context import CryptContext
from ..config import settings

logger = logging.getLogger(__name__)

try:
    import bcrypt  # noqa: F401

    PASSWORD_SCHEMES = ["bcrypt", "pbkdf2_sha256"]
except ImportError:  # pragma: no cover - depends on installed environment
    PASSWORD_SCHEMES = ["pbkdf2_sha256"]
    logger.warning(
        "bcrypt backend not available; falling back to pbkdf2_sha256 for password hashing"
    )

pwd_context = CryptContext(schemes=PASSWORD_SCHEMES, deprecated="auto")
_dummy_password_hash = pwd_context.hash(f"playnexus-dummy::{settings.secret_key}")


def hash_password(password: str, pepper: Optional[str] = None) -> str:
    """
    Hash a password using the configured adaptive scheme with optional pepper.
    Args:
        password: Plain text password
        pepper: Additional secret (from SECRET_KEY). If None, uses settings.SECRET_KEY
    Returns:
        Hashed password string
    """
    if pepper is None:
        pepper = settings.secret_key

    # Combine password with pepper before hashing
    # This ensures that even if the pepper is known, old hashes remain secure
    peppered_password = password + pepper
    return pwd_context.hash(peppered_password)


def verify_password(
    plain_password: str, hashed_password: str, pepper: Optional[str] = None
) -> bool:
    """
    Verify a password against its hash using the same pepper.
    Args:
        plain_password: Plain text password to verify
        hashed_password: Stored password hash
        pepper: Additional secret (from SECRET_KEY). If None, uses settings.SECRET_KEY
    Returns:
        True if password matches, False otherwise
    """
    if pepper is None:
        pepper = settings.secret_key

    peppered_password = plain_password + pepper
    return pwd_context.verify(peppered_password, hashed_password)


def get_dummy_password_hash() -> str:
    """Return a valid hash for timing-safe dummy verification."""
    return _dummy_password_hash
