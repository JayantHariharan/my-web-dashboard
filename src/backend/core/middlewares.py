"""
Middleware components for the PlayNexus FastAPI application.

Provides:

- :class:`SimpleRateLimiter`   – in-memory sliding-window rate limiter.
- :class:`RateLimitMiddleware` – Starlette middleware that applies
  :class:`SimpleRateLimiter` to configurable URL prefixes.
- :class:`RequestIdMiddleware` – attaches a UUID ``X-Request-ID`` header
  to every response for request tracing.

Note:
    :class:`SimpleRateLimiter` is **in-process only**; rate-limit state is
    not shared across Gunicorn/uvicorn workers.  For production deployments
    with multiple workers, consider a Redis-backed limiter.
"""

import time
import uuid
from collections import defaultdict, deque
from typing import Dict, Tuple, Optional, List
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware


class SimpleRateLimiter:
    """
    In-memory sliding-window rate limiter.

    Tracks request timestamps per IP address.  When an IP exceeds
    *max_requests* within *window_seconds*, it is blocked for
    *block_duration_seconds* regardless of further requests.

    Thread safety
    -------------
    Uses plain ``dict`` / ``deque`` without locks.  asyncio's single-threaded
    event loop keeps access to these structures serialised, so no explicit
    locking is needed when used with uvicorn.
    """

    def __init__(
        self,
        max_requests: int = 20,
        window_seconds: int = 3600,
        block_duration_seconds: int = 900,
    ):
        """
        Args:
            max_requests:           Maximum number of requests allowed per IP
                                    within *window_seconds* before the IP is
                                    blocked.
            window_seconds:         Length of the sliding measurement window
                                    in seconds (default: 3600 = 1 hour).
            block_duration_seconds: How long a violating IP is blocked after
                                    exceeding the limit (default: 900 = 15 min).
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.block_duration_seconds = block_duration_seconds
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.blocked_ips: Dict[str, float] = {}  # ip -> unblock_time

    def is_allowed(self, ip: str) -> Tuple[bool, str]:
        """
        Check whether the given IP is permitted to make a request.

        Removes timestamps outside the current window, then enforces the limit.
        If the limit is exceeded the IP is added to the block-list.

        Args:
            ip: Client IP address string.

        Returns:
            A ``(allowed, message)`` tuple where *allowed* is ``True`` when
            the request should proceed, and *message* provides a human-readable
            reason when *allowed* is ``False``.
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

    def clear(self) -> None:
        """Reset all rate-limit and block-list state (intended for use in tests)."""
        self.requests.clear()
        self.blocked_ips.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware that applies :class:`SimpleRateLimiter` to a
    configurable set of URL path prefixes.

    Requests to paths that do **not** match any prefix in *paths* are passed
    through without any rate-limit check.
    """

    def __init__(
        self, app, limiter: SimpleRateLimiter, paths: Optional[List[str]] = None
    ):
        super().__init__(app)
        self.limiter = limiter
        self.paths = paths or []  # Empty list = no paths, must be explicitly set

    async def dispatch(self, request: Request, call_next):
        # Only rate limit matching route prefixes
        if any(request.url.path.startswith(path) for path in self.paths):
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
    """
    Attach a unique ``X-Request-ID`` UUID header to every response.

    Enables end-to-end request tracing across logs, monitoring tools, and
    client-side error reports.  The ID is also stored in ``request.state``
    so that downstream handlers can include it in structured log messages.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# Auth endpoints: 20 requests/hour, 15-minute block
auth_rate_limiter = SimpleRateLimiter(
    max_requests=20, window_seconds=3600, block_duration_seconds=900
)
