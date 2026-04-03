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
