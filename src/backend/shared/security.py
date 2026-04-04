"""Security utilities for PlayNexus authentication."""

import logging
from typing import Optional
from passlib.context import CryptContext
from ..config import settings

logger = logging.getLogger(__name__)

try:
    import bcrypt  # noqa: F401

    PASSWORD_SCHEMES = ["bcrypt_sha256", "bcrypt", "pbkdf2_sha256"]
except ImportError:  # pragma: no cover
    PASSWORD_SCHEMES = ["pbkdf2_sha256"]
    logger.warning(
        "bcrypt backend not available; falling back to pbkdf2_sha256"
    )


# ✅ Limits to prevent abuse
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128


def _peppered_password_input(password: str, pepper: str) -> str:
    """Bind password with server-side secret."""
    return password + pepper


def _validate_password(password: str) -> None:
    """Basic password validation (can be extended later)."""
    if not isinstance(password, str):
        raise ValueError("Password must be a string")

    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError("Password must be at least 8 characters")

    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError("Password too long")


def _validate_pepper(pepper: str) -> None:
    """Ensure pepper (secret key) is strong enough."""
    if not pepper or len(pepper) < 16:
        raise ValueError("Invalid SECRET_KEY for password hashing")


def _build_password_context() -> CryptContext:
    """Build hashing context with safe fallback."""
    preferred_context = CryptContext(schemes=PASSWORD_SCHEMES, deprecated="auto")

    try:
        preferred_context.hash(_peppered_password_input("self-test", "init"))
        return preferred_context
    except Exception:
        # ✅ FIX: do not log raw exception
        logger.warning(
            "bcrypt backend failed self-test; using pbkdf2_sha256"
        )
        return CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


pwd_context = _build_password_context()
_dummy_password_hash: Optional[str] = None


def hash_password(password: str, pepper: Optional[str] = None) -> str:
    """Hash password securely."""

    _validate_password(password)

    if pepper is None:
        pepper = settings.secret_key

    _validate_pepper(pepper)

    peppered_password = _peppered_password_input(password, pepper)
    return pwd_context.hash(peppered_password)


def verify_password(
    plain_password: str, hashed_password: str, pepper: Optional[str] = None
) -> bool:
    """Verify password securely with timing-safe behavior."""

    if pepper is None:
        pepper = settings.secret_key

    try:
        _validate_pepper(pepper)

        # Even if password is invalid, still process to avoid timing leaks
        if not isinstance(plain_password, str):
            plain_password = ""

        peppered_password = _peppered_password_input(plain_password, pepper)

        return pwd_context.verify(peppered_password, hashed_password)

    except Exception:
        # ✅ FIX: always do dummy verify to prevent timing attacks
        pwd_context.verify(
            _peppered_password_input("dummy", pepper),
            get_dummy_password_hash(),
        )
        return False


def get_dummy_password_hash() -> str:
    """Return a valid hash for timing-safe verification."""
    global _dummy_password_hash

    if _dummy_password_hash is None:
        _dummy_password_hash = pwd_context.hash(
            _peppered_password_input("playnexus-dummy", settings.secret_key)
        )

    return _dummy_password_hash