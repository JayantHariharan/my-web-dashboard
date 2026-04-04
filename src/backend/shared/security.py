"""Security utilities for PlayNexus authentication."""

import logging
from typing import Optional
from passlib.context import CryptContext
from ..config import settings

logger = logging.getLogger(__name__)

try:
    import bcrypt  # noqa: F401

    PASSWORD_SCHEMES = ["bcrypt_sha256", "bcrypt", "pbkdf2_sha256"]
except ImportError:  # pragma: no cover - depends on installed environment
    PASSWORD_SCHEMES = ["pbkdf2_sha256"]
    logger.warning(
        "bcrypt backend not available; falling back to pbkdf2_sha256 for password hashing"
    )

def _peppered_password_input(password: str, pepper: str) -> str:
    """
    Bind the password to the server-side secret before adaptive hashing.

    `bcrypt_sha256` safely handles long inputs internally, avoiding bcrypt's
    72-byte limit without requiring custom hashing logic in application code.
    """
    return password + pepper


def _build_password_context() -> CryptContext:
    """
    Build the adaptive hashing context and actively verify the preferred scheme.

    Some Render/Python environments expose a partially working bcrypt backend:
    passlib can import it, but the first real hash call fails during backend
    self-checks. If that happens, fall back to pbkdf2_sha256 so the app can
    still start and authentication keeps working.
    """
    preferred_context = CryptContext(schemes=PASSWORD_SCHEMES, deprecated="auto")

    try:
        preferred_context.hash(_peppered_password_input("playnexus-self-test", "init"))
        return preferred_context
    except Exception as exc:  # pragma: no cover - environment dependent
        logger.warning(
            "bcrypt backend failed runtime self-test; falling back to pbkdf2_sha256 only: %s",
            exc,
        )
        return CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


pwd_context = _build_password_context()
_dummy_password_hash: Optional[str] = None


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

    peppered_password = _peppered_password_input(password, pepper)
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

    try:
        peppered_password = _peppered_password_input(plain_password, pepper)
        return pwd_context.verify(peppered_password, hashed_password)
    except ValueError:
        return False


def get_dummy_password_hash() -> str:
    """Return a valid hash for timing-safe dummy verification."""
    global _dummy_password_hash

    if _dummy_password_hash is None:
        _dummy_password_hash = pwd_context.hash(
            _peppered_password_input("playnexus-dummy", settings.secret_key)
        )

    return _dummy_password_hash
