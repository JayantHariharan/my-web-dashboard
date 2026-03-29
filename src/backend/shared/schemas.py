"""
Shared Pydantic models and schemas for PlayNexus.
Common models used across multiple app modules.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
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
        if not any(c.isalpha() for c in v):
            raise ValueError("Username must contain at least one letter")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return v.strip()


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

    @field_validator("confirm_password")
    @classmethod
    def validate_confirm_password(cls, v: str, info) -> str:
        v = v.strip()
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v


class AuthResponse(BaseModel):
    """Authentication response model."""

    message: str
    username: str
    user_id: Optional[int] = None


# ============ App Registry Models ============


class AppInfo(BaseModel):
    """Information about an available app."""

    id: int
    name: str
    route_path: str
    description: str
    icon: Optional[str] = None
    is_active: bool = True

    class Config:
        from_attributes = True


class AppListResponse(BaseResponse):
    """Response for listing apps."""

    apps: List[AppInfo]


# ============ Game Models ============


class GameScoreBase(BaseModel):
    """Base score submission."""

    game_name: str
    score: int
    metadata: Optional[Dict[str, Any]] = None


class GameScoreCreate(GameScoreBase):
    """Submit a new score."""

    pass


class GameScoreResponse(GameScoreBase):
    """Returned score data."""

    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class LeaderboardEntry(BaseModel):
    """Entry in a leaderboard."""

    rank: int
    username: str
    score: int
    created_at: datetime


class LeaderboardResponse(BaseResponse):
    """Leaderboard data."""

    game_name: str
    entries: List[LeaderboardEntry]
    total_entries: int


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


# ============ Activity Models ============


class UserActivityResponse(BaseModel):
    """User app activity."""

    app_name: str
    session_id: str
    launched_at: datetime
    last_accessed: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
