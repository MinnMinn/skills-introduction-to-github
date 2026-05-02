"""
In-process sliding-window rate limiter for the login endpoint.

Two independent limits are enforced (security policy rule 8):
  1. Per-email failure limit  : 5 failures / 60 s
  2. Per-IP request limit     : 20 requests / 60 s (successes + failures)

For production deployments with multiple workers, replace the in-process
store with a shared Redis instance; the interface (`RateLimiter`) remains
the same.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Deque

from app.config import get_settings


class _SlidingWindowCounter:
    """Thread-safe sliding-window counter backed by a deque of timestamps."""

    def __init__(self, window_seconds: int, max_events: int) -> None:
        self._window = window_seconds
        self._max = max_events
        self._buckets: dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def record_and_check(self, key: str) -> bool:
        """
        Record one event for *key* and return True iff the limit is exceeded
        (i.e. the caller should be rate-limited).
        """
        now = time.monotonic()
        cutoff = now - self._window
        with self._lock:
            bucket = self._buckets[key]
            # Evict expired entries from the left.
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            exceeded = len(bucket) >= self._max
            if not exceeded:
                bucket.append(now)
            return exceeded

    def is_limited(self, key: str) -> bool:
        """Return True iff *key* is currently over the limit (read-only)."""
        now = time.monotonic()
        cutoff = now - self._window
        with self._lock:
            bucket = self._buckets[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            return len(bucket) >= self._max


class RateLimiter:
    """
    Composite rate limiter: per-email failure + per-IP total-request windows.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._email_failures = _SlidingWindowCounter(
            window_seconds=settings.rate_limit_window_seconds,
            max_events=settings.rate_limit_failures_per_email,
        )
        self._ip_requests = _SlidingWindowCounter(
            window_seconds=settings.rate_limit_window_seconds,
            max_events=settings.rate_limit_requests_per_ip,
        )

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def check_ip(self, ip: str) -> bool:
        """
        Record one request from *ip* and return True if the IP limit is
        exceeded (caller should return HTTP 429).
        """
        return self._ip_requests.record_and_check(ip)

    def check_email_failure(self, email: str) -> bool:
        """
        Record one failure for *email* and return True if the email failure
        limit is exceeded (caller should return HTTP 429).
        """
        return self._email_failures.record_and_check(email)

    def is_email_limited(self, email: str) -> bool:
        """Return True if the email failure limit is already exceeded."""
        return self._email_failures.is_limited(email)


# Module-level singleton — shared across all requests in a single process.
rate_limiter = RateLimiter()
