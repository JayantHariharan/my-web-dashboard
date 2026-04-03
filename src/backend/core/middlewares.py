"""
Middleware components for PlayNexus.
Includes rate limiting, request ID, and other cross-cutting concerns.
"""

import time
import uuid
from collections import defaultdict, deque
from typing import Dict, Tuple, Optional, List
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware


class SimpleRateLimiter:
    """Simple in-memory rate limiter using sliding window."""

    def __init__(
        self,
        max_requests: int = 20,
        window_seconds: int = 3600,
        block_duration_seconds: int = 900,
    ):
        """
        Args:
            max_requests: Max requests per window per IP
            window_seconds: Time window in seconds
            block_duration_seconds: How long to block IP after exceeding limit
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.block_duration_seconds = block_duration_seconds
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.blocked_ips: Dict[str, float] = {}  # ip -> unblock_time

    def is_allowed(self, ip: str) -> Tuple[bool, str]:
        """
        Check if IP is allowed to make request.
        Returns: (allowed, message)
        """
        # Check if IP is blocked
        if ip in self.blocked_ips:
            if time.time() < self.blocked_ips[ip]:
                remaining = int(self.blocked_ips[ip] - time.time())
                return False, f"Too many requests. Try again in {remaining} seconds."
            else:
                del self.blocked_ips[ip]

        # Get request timestamps for this IP
        timestamps = self.requests[ip]

        # Remove old timestamps outside window
        now = time.time()
        window_start = now - self.window_seconds
        while timestamps and timestamps[0] < window_start:
            timestamps.popleft()

        # Check if limit exceeded
        if len(timestamps) >= self.max_requests:
            # Block this IP for the configured duration
            block_until = now + self.block_duration_seconds
            self.blocked_ips[ip] = block_until
            return False, "Rate limit exceeded. Please try again later."

        # Record this request
        timestamps.append(now)
        return True, "OK"

    def clear(self):
        """Clear all rate limit data (for testing)."""
        self.requests.clear()
        self.blocked_ips.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to apply rate limiting to specific routes."""

    def __init__(
        self, app, limiter: SimpleRateLimiter, paths: Optional[List[str]] = None
    ):
        super().__init__(app)
        self.limiter = limiter
        self.paths = paths or []  # Empty list = no paths, must be explicitly set

    async def dispatch(self, request: Request, call_next):
        # Only rate limit specific paths
        if request.url.path in self.paths:
            # Get client IP, considering X-Forwarded-For if behind proxy (e.g., Render)
            client_ip = "unknown"
            if request.client:
                client_ip = request.client.host
            # Check X-Forwarded-For header (use first IP if multiple)
            x_forwarded_for = request.headers.get("X-Forwarded-For")
            if x_forwarded_for:
                # Take the first IP in the list
                client_ip = x_forwarded_for.split(",")[0].strip()

            allowed, message = self.limiter.is_allowed(client_ip)

            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=message
                )

        response = await call_next(request)
        return response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware to add a unique request ID to each request."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# Pre-configured rate limiters for different app categories
# These can be imported by individual app modules

# Auth endpoints: 5 attempts/hour, 30-minute block (brute force protection)
auth_rate_limiter = SimpleRateLimiter(
    max_requests=5, window_seconds=3600, block_duration_seconds=1800
)

# Games endpoints: 100 requests/hour, 10-minute block
games_rate_limiter = SimpleRateLimiter(
    max_requests=100, window_seconds=3600, block_duration_seconds=600
)

# General apps: 200 requests/hour, 10-minute block
apps_rate_limiter = SimpleRateLimiter(
    max_requests=200, window_seconds=3600, block_duration_seconds=600
)
