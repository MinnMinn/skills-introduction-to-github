"""
In-process sliding-window rate limiter middleware.

Limits: RATE_LIMIT_REQUESTS requests per RATE_LIMIT_WINDOW_SECONDS per user.
Default: 10 requests / 60 seconds (create-intent endpoint).

In production replace the in-memory store with a shared Redis instance
so the limit works across multiple API replicas.
"""
import time
from collections import defaultdict, deque
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings

# In-memory store: user_id → deque of request timestamps
_request_log: dict[str, deque] = defaultdict(deque)

# Paths that should be rate-limited
_RATE_LIMITED_PATHS = {"/api/payments/create-intent"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter applied to payment creation."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path not in _RATE_LIMITED_PATHS:
            return await call_next(request)

        settings = get_settings()
        user_id = _extract_user_id(request)
        window = settings.RATE_LIMIT_WINDOW_SECONDS
        max_requests = settings.RATE_LIMIT_REQUESTS
        now = time.monotonic()

        bucket = _request_log[user_id]

        # Evict timestamps outside the window
        while bucket and bucket[0] < now - window:
            bucket.popleft()

        if len(bucket) >= max_requests:
            retry_after = int(window - (now - bucket[0])) + 1
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Maximum 10 requests per minute.",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        bucket.append(now)
        return await call_next(request)


def _extract_user_id(request: Request) -> str:
    """
    Extract user identifier from the request for rate-limit bucketing.

    Uses the authenticated user ID from the request state (set by auth middleware),
    falling back to the client IP address for unauthenticated requests.
    """
    user = getattr(request.state, "user_id", None)
    if user:
        return str(user)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
