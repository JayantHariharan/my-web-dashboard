"""
Security utilities for PlayNexus.
Provides password hashing with pepper, verification, and HMAC-based credential binding.
"""

import hmac
import hashlib
from typing import Optional
from passlib.context import CryptContext
from ..config import settings

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str, pepper: Optional[str] = None) -> str:
    """
    Hash a password using bcrypt with optional pepper.
    Args:
        password: Plain text password
        pepper: Additional secret (from SECRET_KEY). If None, uses settings.SECRET_KEY
    Returns:
        Hashed password string (bcrypt format)
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


def compute_user_identifier(username: str, password_hash: str) -> str:
    """
    Compute an identifier that binds username to password hash.
    This creates a deterministic fingerprint that can detect DB tampering.
    Args:
        username: User's username
        password_hash: Hashed password (bcrypt hash)
    Returns:
        Hex-encoded HMAC-SHA256 fingerprint
    """
    # Use server secret as HMAC key
    key = settings.secret_key.encode("utf-8")
    message = f"{username}:{password_hash}".encode("utf-8")
    digest = hmac.new(key, message, hashlib.sha256).hexdigest()
    return digest


def verify_user_identifier(
    username: str, password_hash: str, expected_hex: str
) -> bool:
    """
    Verify that the user identifier matches (constant-time comparison).
    Args:
        username: User's username
        password_hash: Hashed password
        expected_hex: Expected hex HMAC digest
    Returns:
        True if matches, False otherwise
    """
    computed = compute_user_identifier(username, password_hash)
    # Use hmac.compare_digest for constant-time comparison
    return hmac.compare_digest(computed, expected_hex)
