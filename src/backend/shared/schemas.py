"""Shared Pydantic models for the current PlayNexus backend."""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


# ============ Constants ============
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 50
PASSWORD_MAX_LENGTH = 128


# ============ Base Models ============


class BaseResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None


# ============ User/Auth Models ============


class UserBase(BaseModel):
    username: str = Field(
        ...,
        min_length=USERNAME_MIN_LENGTH,
        max_length=USERNAME_MAX_LENGTH,
        description="Username",
    )

    @field_validator("username")
    @classmethod
    def normalize_username(cls, v: str) -> str:
        v = v.strip()

        if not v:
            raise ValueError("Username cannot be empty")

        # Normalize to lowercase (optional but recommended)
        v = v.lower()

        # Allow only safe characters
        if not all(c.isalnum() or c in ("_", ".") for c in v):
            raise ValueError("Username contains invalid characters")

        return v


class UserResponse(UserBase):
    id: int
    created_at: datetime
    last_login_at: Optional[datetime] = None
    profile: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class LoginData(BaseModel):
    username: str = Field(
        ...,
        min_length=USERNAME_MIN_LENGTH,
        max_length=USERNAME_MAX_LENGTH,
        description="Username",
    )
    password: str = Field(
        ...,
        min_length=1,
        max_length=PASSWORD_MAX_LENGTH,
        description="Password",
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip().lower()

        if not v:
            raise ValueError("Username cannot be empty")

        if not all(c.isalnum() or c in ("_", ".") for c in v):
            raise ValueError("Username contains invalid characters")

        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Invalid password")

        # ❗ DO NOT strip password (intentional)
        if len(v) > PASSWORD_MAX_LENGTH:
            raise ValueError("Password too long")

        return v


class RegisterData(LoginData):
    password: str = Field(
        ...,
        min_length=8,
        max_length=PASSWORD_MAX_LENGTH,
        description="Password (minimum 8 characters)",
    )
    confirm_password: str = Field(...)

    @field_validator("confirm_password")
    @classmethod
    def validate_confirm_password(cls, v: str, info) -> str:
        if not isinstance(v, str):
            raise ValueError("Invalid confirmation password")

        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")

        return v


class DeleteAccountData(BaseModel):
    username: str = Field(
        ..., min_length=USERNAME_MIN_LENGTH, max_length=USERNAME_MAX_LENGTH
    )
    password: str = Field(..., min_length=1, max_length=PASSWORD_MAX_LENGTH)
    confirm_username: Optional[str] = Field(
        default=None,
        min_length=USERNAME_MIN_LENGTH,
        max_length=USERNAME_MAX_LENGTH,
    )

    @field_validator("username", "confirm_username")
    @classmethod
    def validate_usernames(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value

        value = value.strip().lower()

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
        if not isinstance(value, str):
            raise ValueError("Invalid password")

        return value


# ============ User Profile Models ============


class UserProfileUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    preferences: Optional[Dict[str, Any]] = None

    @field_validator("display_name", "bio")
    @classmethod
    def sanitize_text(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return v.strip()


class UserProfileResponse(BaseModel):
    user_id: int
    username: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    preferences: Dict[str, Any] = Field(default_factory=dict)  # ✅ FIXED
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True