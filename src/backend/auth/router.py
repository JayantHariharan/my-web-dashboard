"""
Authentication API router.
Handles user login, signup, and session management.
"""

import logging
from fastapi import APIRouter, Request, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from ..config import settings
from ..shared.database import user_repo
from ..shared.security import get_dummy_password_hash, hash_password, verify_password
from ..shared.schemas import DeleteAccountData, LoginData, RegisterData, UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class AuthSuccess(BaseModel):
    """Response for successful authentication."""

    message: str
    username: str
    user_id: int


@router.post("/login", response_model=AuthSuccess)
async def login(login_data: LoginData, request: Request):
    """
    Authenticate user and return success response.

    ## Request Example
    ```json
    {
        "username": "player123",
        "password": "SecurePass123!"
    }
    ```

    ## Response Example
    ```json
    {
        "message": "Login successful",
        "username": "player123",
        "user_id": 1
    }
    ```

    ## Security Features
    - Constant-time comparison prevents timing attacks
    - Missing users and invalid passwords are handled explicitly for the current UI flow
    - IP address logging for security auditing
    - Rate limiting: 20 requests per hour per IP

    ## Error Responses
    - `400 Bad Request`: Missing or invalid credentials
    - `401 Unauthorized`: Invalid password
    - `404 Not Found`: No user found
    - `429 Too Many Requests`: Rate limit exceeded
    - `500 Internal Server Error`: Server error
    """
    username = login_data.username
    password = login_data.password
    client_ip = get_client_ip(request)

    try:
        user = user_repo.get_user_by_username(username)
    except Exception as e:
        logger.error(f"Login error for user '{username}' from IP {client_ip}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service unavailable",
        )

    if not user:
        # Use constant-time comparison by always calling verify_password
        # even if user doesn't exist
        verify_password(password, get_dummy_password_hash())

        logger.warning(
            f"Failed login attempt for non-existent user: {username} "
            f"from IP {client_ip}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No user found",
        )

    # Verify password
    if not verify_password(password, user["password"]):
        logger.warning(
            f"Failed login attempt (wrong password) for user: {username} "
            f"from IP {client_ip}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Update login tracking (last_login_at, last_login_ip)
    try:
        user_repo.update_login_tracking(username, client_ip)
    except Exception as e:
        logger.error(f"Failed to update login tracking for {username}: {e}")
        # Don't fail login if tracking update fails

    logger.info(f"User logged in: {username} from IP {client_ip}")
    return AuthSuccess(
        message="Login successful", username=username, user_id=user["id"]
    )


@router.post("/signup", response_model=AuthSuccess)
async def signup(register_data: RegisterData, request: Request):
    """
    Register a new user account.

    ## Request Example
    ```json
    {
        "username": "newplayer123",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!"
    }
    ```

    ## Response Example
    ```json
    {
        "message": "Signup successful",
        "username": "newplayer123",
        "user_id": 5
    }
    ```

    ## Security Features
    - Password hashing: bcrypt with pepper (server secret)
    - Username validation: min 3 chars, must contain letters
    - Password requirements: min 8 characters
    - Confirmation validation: passwords must match
    - Duplicate check: prevents username conflicts
    - IP logging: tracks signup location
    - Rate limiting: 20 requests per hour per IP

    ## Error Responses
    - `400 Bad Request`: Validation error (empty fields, password mismatch,
      weak username)
    - `409 Conflict`: Username already exists
    - `429 Too Many Requests`: Rate limit exceeded
    - `500 Internal Server Error`: Database or hashing error
    """
    if not settings.registration_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration is currently disabled",
        )

    username = register_data.username
    password = register_data.password
    client_ip = get_client_ip(request)

    try:
        password_hash = hash_password(password)
    except Exception as e:
        logger.error(f"Password hashing failed for {username} from IP {client_ip}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to process password",
        )

    try:
        user_id = user_repo.create_user(username, password_hash, created_ip=client_ip)
        logger.info(
            f"New user registered: {username} (ID: {user_id}) from IP {client_ip}"
        )
    except ValueError as e:
        # Username already exists
        logger.warning(
            f"Signup attempt with existing username: {username} from IP {client_ip}"
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        logger.error(f"Signup error for user '{username}' from IP {client_ip}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration service unavailable",
        )

    return AuthSuccess(message="Signup successful", username=username, user_id=user_id)


@router.get("/me", response_model=UserResponse)
async def get_current_user(username: Optional[str] = None):
    """
    Get current user profile.

    ## Authentication
    Currently uses simple username from session (future: JWT token).

    ## Response Example
    ```json
    {
        "id": 1,
        "username": "player123",
        "created_at": "2025-03-29T10:30:00",
        "last_login_at": "2025-03-29T15:45:00",
        "profile": {}
    }
    ```

    ## Error Responses
    - `401 Unauthorized`: Not logged in
    - `404 Not Found`: User not found
    """
    # Note: Implement proper JWT authentication
    # For now, expect username in query param (demo only)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    user = user_repo.get_user_by_username(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return UserResponse(**user)


@router.delete("/account", response_model=AuthSuccess)
async def delete_account(delete_data: DeleteAccountData, request: Request):
    """
    Delete a user account after confirming username and password.

    The current frontend auth flow is client-stored username session based,
    so this endpoint uses explicit credential confirmation instead of a bearer token.
    """
    username = delete_data.username
    password = delete_data.password
    client_ip = get_client_ip(request)

    user = user_repo.get_user_by_username(username)
    if not user or not verify_password(password, user["password"]):
        logger.warning(
            f"Failed delete-account attempt for user '{username}' from IP {client_ip}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    deleted = user_repo.delete_user_by_username(username)
    if not deleted:
        logger.error(
            f"Delete-account operation could not remove user '{username}' from IP {client_ip}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to delete account",
        )

    logger.info(f"User deleted account: {username} from IP {client_ip}")
    return AuthSuccess(
        message="Account deleted successfully",
        username=username,
        user_id=user["id"],
    )


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request."""
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
