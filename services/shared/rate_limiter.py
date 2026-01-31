"""
Rate limiting middleware for API endpoints.

Provides simple in-memory rate limiting that can be replaced with Redis
in production for distributed deployments.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

from services.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RateLimitState:
    """State for a rate-limited client."""

    requests: list[float] = field(default_factory=list)


class InMemoryRateLimiter:
    """
    Simple in-memory rate limiter using sliding window.

    Note: For production with multiple instances, use Redis-based rate limiting.
    """

    def __init__(self) -> None:
        self._state: dict[str, RateLimitState] = defaultdict(RateLimitState)
        self._cleanup_interval = 60  # seconds
        self._last_cleanup = time.time()

    def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60,
    ) -> tuple[bool, int, int]:
        """
        Check if a request is allowed under rate limits.

        Args:
            key: Client identifier (e.g., IP address)
            limit: Maximum requests per window
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_allowed, remaining, reset_time)
        """
        now = time.time()
        state = self._state[key]

        # Clean old requests outside the window
        cutoff = now - window_seconds
        state.requests = [t for t in state.requests if t > cutoff]

        # Check limit
        if len(state.requests) >= limit:
            reset_time = int(state.requests[0] + window_seconds - now)
            return False, 0, max(reset_time, 1)

        # Add current request
        state.requests.append(now)
        remaining = limit - len(state.requests)

        # Periodic cleanup of old keys
        if now - self._last_cleanup > self._cleanup_interval:
            self._cleanup()
            self._last_cleanup = now

        return True, remaining, window_seconds

    def _cleanup(self) -> None:
        """Remove stale entries to prevent memory growth."""
        now = time.time()
        stale_keys = []
        for key, state in self._state.items():
            if not state.requests or (now - max(state.requests)) > 300:
                stale_keys.append(key)
        for key in stale_keys:
            del self._state[key]


# Global rate limiter instance
_rate_limiter = InMemoryRateLimiter()


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies."""
    # Check for forwarded headers (behind load balancer/proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take first IP in chain (original client)
        return forwarded.split(",")[0].strip()

    # Check for real IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fall back to direct connection
    if request.client:
        return request.client.host

    return "unknown"


def rate_limit(
    limit: int = 100,
    window_seconds: int = 60,
    key_func: Callable[[Request], str] | None = None,
) -> Callable:
    """
    Rate limit decorator for FastAPI endpoints.

    Args:
        limit: Maximum requests per window
        window_seconds: Time window in seconds
        key_func: Function to extract rate limit key from request

    Returns:
        Dependency function for FastAPI
    """

    async def rate_limit_dependency(request: Request) -> None:
        if key_func:
            key = key_func(request)
        else:
            key = get_client_ip(request)

        # Add endpoint path to key for per-endpoint limits
        key = f"{key}:{request.url.path}"

        allowed, remaining, reset = _rate_limiter.is_allowed(
            key=key,
            limit=limit,
            window_seconds=window_seconds,
        )

        # Add rate limit headers to response
        request.state.rate_limit_remaining = remaining
        request.state.rate_limit_reset = reset

        if not allowed:
            logger.warning(
                "rate_limit_exceeded",
                client_ip=get_client_ip(request),
                endpoint=request.url.path,
                limit=limit,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {reset} seconds.",
                headers={
                    "Retry-After": str(reset),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset),
                },
            )

    return rate_limit_dependency


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add rate limit headers to all responses.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Add rate limit headers if set by endpoint
        if hasattr(request.state, "rate_limit_remaining"):
            response.headers["X-RateLimit-Remaining"] = str(
                request.state.rate_limit_remaining
            )
        if hasattr(request.state, "rate_limit_reset"):
            response.headers["X-RateLimit-Reset"] = str(request.state.rate_limit_reset)

        return response
