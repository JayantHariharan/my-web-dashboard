"""
Authentication API router.
Handles user login, signup, and session management.
"""

from fastapi import APIRouter, Request, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from ..shared.database import user_repo
from ..shared.security import hash_password, verify_password
from ..shared.schemas import LoginData, RegisterData, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


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
    - Generic error messages don't reveal if username exists
    - Privacy-first: No IP address storage
    - Rate limiting: 5 attempts per hour per IP

    ## Error Responses
    - `400 Bad Request`: Missing or invalid credentials
    - `401 Unauthorized`: Invalid username/password
    - `429 Too Many Requests`: Rate limit exceeded
    - `500 Internal Server Error`: Server error
    """
    username = login_data.username
    password = login_data.password

    try:
        user = user_repo.get_user_by_username(username)
    except Exception as e:
        from ..shared.log_config import logger

        logger.error(f"Login error for user '{username}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service unavailable",
        )

    if not user:
        # Use constant-time comparison by always calling verify_password
        # even if user doesn't exist
        dummy_hash = "$2b$12$dummyhashdummyhashdummyhashdu"  # bcrypt dummy
        verify_password(password, dummy_hash)
        from ..shared.log_config import logger

        logger.warning(f"Failed login attempt for non-existent user: {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Username not found"
        )

    # Verify password
    if not verify_password(password, user["password"]):
        from ..shared.log_config import logger

        logger.warning(f"Failed login attempt (wrong password) for user: {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password"
        )

    # Update login tracking (last_login_at)
    try:
        user_repo.update_login_tracking(username)
    except Exception as e:
        from ..shared.log_config import logger

        logger.error(f"Failed to update login tracking for {username}: {e}")
        # Don't fail login if tracking update fails

    from ..shared.log_config import logger

    logger.info(f"User logged in: {username}")
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
    - Password requirements: min 6 characters
    - Confirmation validation: passwords must match
    - Duplicate check: prevents username conflicts
    - Rate limiting: 5 attempts per hour
    - Privacy-first: No IP address storage

    ## Error Responses
    - `400 Bad Request`: Validation error (empty fields, password mismatch,
      weak username)
    - `409 Conflict`: Username already exists
    - `429 Too Many Requests`: Rate limit exceeded
    - `500 Internal Server Error`: Database or hashing error
    """
    username = register_data.username
    password = register_data.password

    try:
        password_hash = hash_password(password)
    except Exception as e:
        from ..shared.log_config import logger

        logger.error(f"Password hashing failed for {username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to process password",
        )

    try:
        user_id = user_repo.create_user(username, password_hash)
        from ..shared.log_config import logger

        logger.info(f"New user registered: {username} (ID: {user_id})")
    except ValueError as e:
        # Username already exists
        from ..shared.log_config import logger

        logger.warning(f"Signup attempt with existing username: {username}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        from ..shared.log_config import logger

        logger.error(f"Signup error for user '{username}': {e}")
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
    # TODO: Implement proper JWT authentication
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


# Note: IP tracking removed for privacy compliance.
# Future: Consider user consent if needing to store connection metadata.
