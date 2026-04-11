"""
Security utilities for PlayNexus authentication.

Password hashing strategy
--------------------------
Passwords are stored as adaptive hashes produced by one of these schemes
(tried in priority order):

1. ``bcrypt_sha256`` – bcrypt wrapped in SHA-256, which eliminates bcrypt's
   72-byte input limit and allows arbitrarily long passwords.
2. ``bcrypt``        – plain bcrypt (fallback when bcrypt_sha256 is absent).
3. ``pbkdf2_sha256`` – pure-Python fallback for environments where the
   compiled bcrypt C extension is unavailable (e.g. restricted Render
   buildpacks).

A **server-side pepper** (``settings.secret_key``) is appended to every
password before hashing.  This means a leaked database dump is useless
without also stealing the server secret.

Note:
    ``passlib`` handles algorithm agility automatically via its
    ``deprecated="auto"`` setting: hashes produced by an older scheme are
    re-hashed on the next successful login without any extra application code.
"""

import logging
from typing import Optional
from passlib.context import CryptContext
from ..config import settings

logger = logging.getLogger(__name__)

try:
    import bcrypt  # noqa: F401

    # Prefer bcrypt_sha256 (removes the 72-byte bcrypt input limit), then plain
    # bcrypt as a direct fallback, then pbkdf2_sha256 as a pure-Python escape hatch.
    PASSWORD_SCHEMES = ["bcrypt_sha256", "bcrypt", "pbkdf2_sha256"]
except ImportError:  # pragma: no cover – bcrypt C extension not installed
    PASSWORD_SCHEMES = ["pbkdf2_sha256"]
    logger.warning(
        "bcrypt C extension not available; using pbkdf2_sha256 for password hashing. "
        "Install 'bcrypt' for stronger security."
    )

def _peppered_password_input(password: str, pepper: str) -> str:
    """
    Concatenate the password with the server-side pepper before hashing.

    The combined string is passed to the adaptive hasher.  Using
    ``bcrypt_sha256`` (the preferred scheme) means the 72-byte bcrypt input
    limit is never hit, even for very long passwords.

    Args:
        password: The plain-text password supplied by the user.
        pepper:   The server-side secret (``settings.secret_key``).

    Returns:
        The peppered string to be hashed.
    """
    return password + pepper


def _build_password_context() -> CryptContext:
    """
    Build and validate the adaptive password-hashing context.

    Performs a live self-test hash on startup to detect broken bcrypt
    installations (common on some Render buildpacks where the C extension
    imports successfully but raises on the first real call).  Falls back
    gracefully to ``pbkdf2_sha256`` when the preferred scheme fails.

    Returns:
        A validated :class:`passlib.context.CryptContext` instance ready
        for production use.
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
    Hash a password using the configured adaptive scheme.

    The pepper is appended to the password before hashing so that a stolen
    database cannot be brute-forced without also knowing the server secret.

    Args:
        password: Plain-text password supplied by the user.
        pepper:   Server-side secret to bind the hash to this deployment.
                  Defaults to ``settings.secret_key`` when ``None``.

    Returns:
        An encoded hash string (e.g. ``$2b$12$...``) safe to store in the DB.
    """
    if pepper is None:
        pepper = settings.secret_key

    peppered_password = _peppered_password_input(password, pepper)
    return pwd_context.hash(peppered_password)


def verify_password(
    plain_password: str, hashed_password: str, pepper: Optional[str] = None
) -> bool:
    """
    Verify a plain-text password against a stored hash.

    Applies the same pepper used during hashing before comparison.  Returns
    ``False`` (never raises) if the hash is malformed or from an unknown
    scheme, which keeps the caller's error-handling simple.

    Args:
        plain_password:  Password entered by the user.
        hashed_password: Hash retrieved from the database.
        pepper:          Server-side secret; defaults to ``settings.secret_key``.

    Returns:
        ``True`` if the password matches the hash, ``False`` otherwise.
    """
    if pepper is None:
        pepper = settings.secret_key

    try:
        peppered_password = _peppered_password_input(plain_password, pepper)
        return pwd_context.verify(peppered_password, hashed_password)
    except ValueError:
        return False


def get_dummy_password_hash() -> str:
    """
    Return a pre-computed hash for constant-time dummy verification.

    Used in the login endpoint when the requested username does not exist:
    calling :func:`verify_password` against this hash ensures the response
    time is indistinguishable from a real failed login, preventing
    username-enumeration via timing attacks.

    The hash is generated once and cached for the lifetime of the process.

    Returns:
        A valid bcrypt hash of a known dummy string.
    """
    global _dummy_password_hash

    if _dummy_password_hash is None:
        _dummy_password_hash = pwd_context.hash(
            _peppered_password_input("playnexus-dummy", settings.secret_key)
        )

    return _dummy_password_hash
