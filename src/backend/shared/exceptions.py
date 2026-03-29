"""
Custom exception classes for PlayNexus.
Provides clear, specific error types for different scenarios.
"""


class PlayNexusError(Exception):
    """Base exception for PlayNexus application errors."""

    pass


class AuthenticationError(PlayNexusError):
    """Raised when authentication fails."""

    pass


class AuthorizationError(PlayNexusError):
    """Raised when user lacks permission for an action."""

    pass


class RateLimitError(PlayNexusError):
    """Raised when rate limit is exceeded."""

    pass


class ResourceNotFoundError(PlayNexusError):
    """Raised when a requested resource doesn't exist."""

    pass


class ValidationError(PlayNexusError):
    """Raised when input validation fails."""

    pass


class DatabaseError(PlayNexusError):
    """Raised when database operation fails."""

    pass
