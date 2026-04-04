"""Security utilities for PlayNexus authentication."""

import hashlib
import hmac
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


def _normalize_password_input(password: str, pepper: str) -> str:
    """
    Convert the password+pepper pair into a fixed-length digest.

    bcrypt rejects inputs over 72 bytes. Using an HMAC-SHA256 digest gives us
    a stable, fixed-length secret for both bcrypt and pbkdf2 while still
    binding the password to the server-side pepper.
    """
    return hmac.new(
        pepper.encode("utf-8"),
        password.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _legacy_password_input(password: str, pepper: str) -> str:
    """Legacy password format kept for backward-compatible verification."""
    return password + pepper


_dummy_password_hash = pwd_context.hash(
    _normalize_password_input("playnexus-dummy", settings.secret_key)
)


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

    normalized_secret = _normalize_password_input(password, pepper)
    return pwd_context.hash(normalized_secret)


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

    normalized_secret = _normalize_password_input(plain_password, pepper)
    if pwd_context.verify(normalized_secret, hashed_password):
        return True

    # Backward compatibility for users created before fixed-length preprocessing
    # was introduced. This lets existing accounts continue to log in.
    legacy_secret = _legacy_password_input(plain_password, pepper)
    scheme = pwd_context.identify(hashed_password)
    if scheme == "bcrypt" and len(legacy_secret.encode("utf-8")) > 72:
        return False

    try:
        return pwd_context.verify(legacy_secret, hashed_password)
    except ValueError:
        return False


def get_dummy_password_hash() -> str:
    """Return a valid hash for timing-safe dummy verification."""
    return _dummy_password_hash
