"""Middleware components for PlayNexus."""

import time
import uuid
import threading
from collections import defaultdict, deque
from typing import Dict, Tuple, Optional, List

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware


class SimpleRateLimiter:
    """Thread-safe in-memory rate limiter (dev-safe, not distributed)."""

    def __init__(
        self,
        max_requests: int = 20,
        window_seconds: int = 3600,
        block_duration_seconds: int = 900,
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.block_duration_seconds = block_duration_seconds

        self.requests: Dict[str, deque] = defaultdict(deque)
        self.blocked_ips: Dict[str, float] = {}

        # ✅ FIX: thread safety
        self.lock = threading.Lock()

    def is_allowed(self, ip: str) -> Tuple[bool, str, int]:
        """Returns (allowed, message, retry_after_seconds)."""
        now = time.time()

        with self.lock:
            # Cleanup old IPs periodically
            self._cleanup(now)

            # Check block
            if ip in self.blocked_ips:
                if now < self.blocked_ips[ip]:
                    remaining = int(self.blocked_ips[ip] - now)
                    return False, f"Too many requests. Try again in {remaining}s", remaining
                else:
                    del self.blocked_ips[ip]

            timestamps = self.requests[ip]

            # Remove old timestamps
            window_start = now - self.window_seconds
            while timestamps and timestamps[0] < window_start:
                timestamps.popleft()

            if len(timestamps) >= self.max_requests:
                block_until = now + self.block_duration_seconds
                self.blocked_ips[ip] = block_until
                return False, "Rate limit exceeded. Try later.", self.block_duration_seconds

            timestamps.append(now)
            return True, "OK", 0

    def _cleanup(self, now: float):
        """Remove stale IP data to prevent memory leaks."""
        stale_ips = [
            ip for ip, timestamps in self.requests.items()
            if not timestamps or now - timestamps[-1] > self.window_seconds * 2
        ]
        for ip in stale_ips:
            self.requests.pop(ip, None)

        expired_blocks = [
            ip for ip, unblock_time in self.blocked_ips.items()
            if now > unblock_time
        ]
        for ip in expired_blocks:
            self.blocked_ips.pop(ip, None)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with safer IP handling."""

    def __init__(
        self,
        app,
        limiter: SimpleRateLimiter,
        paths: Optional[List[str]] = None,
    ):
        super().__init__(app)
        self.limiter = limiter
        self.paths = paths or []

    def _get_client_ip(self, request: Request) -> str:
        """
        Safer IP extraction.
        Trust X-Forwarded-For ONLY if behind proxy (Render/NGINX).
        """
        x_forwarded_for = request.headers.get("X-Forwarded-For")

        # ⚠️ Trust only if present (Render sets it)
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()

        if request.client:
            return request.client.host

        return "unknown"

    async def dispatch(self, request: Request, call_next):
        if any(request.url.path.startswith(p) for p in self.paths):
            client_ip = self._get_client_ip(request)

            allowed, message, retry_after = self.limiter.is_allowed(client_ip)

            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=message,
                    headers={"Retry-After": str(retry_after)},
                )

        return await call_next(request)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach request ID to each request and response."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# Auth limiter config
auth_rate_limiter = SimpleRateLimiter(
    max_requests=20,
    window_seconds=3600,
    block_duration_seconds=900,
)