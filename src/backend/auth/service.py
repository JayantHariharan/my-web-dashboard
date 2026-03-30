"""
Authentication business logic.
Provides reusable authentication functions.
"""

from typing import Optional, Tuple
from ...shared.database import user_repo
from ...shared.security import hash_password, verify_password
from ..shared.log_config import logger


def authenticate_user(username: str, password: str) -> Tuple[bool, Optional[dict]]:
    """
    Authenticate a user with username and password.

    Returns:
        (success, user_dict) tuple
    """
    user = user_repo.get_user_by_username(username)

    if not user:
        # Still verify with dummy hash to prevent timing attacks
        dummy_hash = "$2b$12$dummyhashdummyhashdummyhashdu"
        verify_password(password, dummy_hash)
        return False, None

    if not verify_password(password, user["password"]):
        return False, None

    # Update login tracking (fire-and-forget)
    try:
        user_repo.update_login_tracking(username)
    except Exception as e:
        logger.error(f"Failed to update login tracking for {username}: {e}")

    return True, user


def register_user(
    username: str, password: str, created_ip: Optional[str] = None
) -> int:
    """
    Register a new user.

    Returns:
        user_id

    Raises:
        ValueError: If username already exists
        Exception: On database error
    """
    # Pre-check
    if user_repo.get_user_by_username(username):
        raise ValueError(f"Username '{username}' already exists")

    password_hash = hash_password(password)
    user_id = user_repo.create_user(username, password_hash, created_ip=created_ip)
    return user_id


def change_password(user_id: int, old_password: str, new_password: str) -> bool:
    """
    Change user password after verifying old password.

    Returns:
        True if successful, False if old password incorrect
    """
    user = user_repo.get_user_by_id(user_id)
    if not user:
        return False

    if not verify_password(old_password, user["password"]):
        return False

    new_hash = hash_password(new_password)
    return user_repo.update_password(user["username"], new_hash)


def deactivate_user(username: str, password: str) -> bool:
    """
    Deactivate a user account (soft delete by flagging in future).
    For now, just deletes (placeholder for soft delete implementation).
    """
    # Future: implement soft delete (set is_active = false)
    pass
