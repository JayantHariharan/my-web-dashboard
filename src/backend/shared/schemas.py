"""Shared Pydantic models for the current PlayNexus backend."""

import re
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

# ============ Base Models ============


class BaseResponse(BaseModel):
    """Base response model for successful API calls."""

    success: bool = True
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response model."""

    detail: str
    code: Optional[str] = None


# ============ User/Auth Models ============


class UserBase(BaseModel):
    """Base user model."""

    username: str = Field(..., min_length=1, max_length=100, description="Username")


class UserResponse(UserBase):
    """User data returned in API responses (no sensitive info)."""

    id: int
    created_at: datetime
    last_login_at: Optional[datetime] = None
    profile: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True  # Enable ORM mode (for SQLAlchemy later, now for dict)


class LoginData(BaseModel):
    """Login request model."""

    username: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Username",
        examples=["player123", "gamer_pro", "AliceSmith"],
    )
    password: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Password",
        examples=["SecurePass123!", "MyP@ssw0rd", "GameTime2024"],
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Username cannot be empty")
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", v):
            raise ValueError(
                "Username may only contain letters, numbers, underscores, and hyphens"
            )
        if not any(c.isalpha() for c in v):
            raise ValueError("Username must contain at least one letter")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Password cannot be empty")
        return v


class RegisterData(LoginData):
    """Registration request model."""

    password: str = Field(
        ...,
        min_length=8,
        description="Password (minimum 8 characters)",
        examples=["SecurePass123!", "MyP@ssw0rd2024", "GameTime2024"],
    )
    confirm_password: str = Field(
        ...,
        description="Password confirmation (must match password)",
        examples=["SecurePass123!", "MyP@ssw0rd2024", "GameTime2024"],
    )

    @field_validator("password")
    @classmethod
    def validate_signup_password(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Password cannot be empty")
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("confirm_password")
    @classmethod
    def validate_confirm_password(cls, v: str, info) -> str:
        v = v.strip()
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v


class DeleteAccountData(BaseModel):
    """Delete-account request model."""

    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=100)
    confirm_username: Optional[str] = Field(default=None, min_length=1, max_length=100)

    @field_validator("username", "confirm_username")
    @classmethod
    def validate_usernames(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Username cannot be empty")
        return value

    @field_validator("confirm_username")
    @classmethod
    def validate_confirm_username(cls, value: Optional[str], info) -> Optional[str]:
        if value is None:
            return value
        if "username" in info.data and value != info.data["username"]:
            raise ValueError("Usernames do not match")
        return value

    @field_validator("password")
    @classmethod
    def validate_delete_password(cls, value: str) -> str:
        return value.strip()


# ============ User Profile Models ============


class UserProfileUpdate(BaseModel):
    """Update user profile."""

    display_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    preferences: Optional[Dict[str, Any]] = None


class UserProfileResponse(BaseModel):
    """User profile data."""

    user_id: int
    username: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    preferences: Dict[str, Any] = {}
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
