"""Unit tests for app.rate_limiter sliding-window counter."""
import os

os.environ.setdefault("JWT_SECRET", "d" * 64)
os.environ.setdefault("RATE_LIMIT_EMAIL_FAILURES", "5")
os.environ.setdefault("RATE_LIMIT_IP_REQUESTS", "20")
os.environ.setdefault("RATE_LIMIT_WINDOW_SECONDS", "60")

from app.rate_limiter import _SlidingWindowCounter, RateLimiter  # noqa: E402


def test_counter_not_exceeded_under_limit():
    c = _SlidingWindowCounter(60, 5)
    for _ in range(4):
        assert c.record_and_check("key") is False


def test_counter_exceeded_when_at_limit():
    c = _SlidingWindowCounter(60, 3)
    for _ in range(3):
        c.record_and_check("key")
    assert c.record_and_check("key") is True


def test_counter_independent_keys():
    c = _SlidingWindowCounter(60, 2)
    c.record_and_check("a")
    c.record_and_check("a")
    assert c.record_and_check("b") is False


def test_counter_is_limited_readonly():
    c = _SlidingWindowCounter(60, 2)
    assert c.is_limited("x") is False
    c.record_and_check("x")
    c.record_and_check("x")
    assert c.is_limited("x") is True


def _make_limiter():
    rl = RateLimiter.__new__(RateLimiter)
    rl._email_failures = _SlidingWindowCounter(60, 5)
    rl._ip_requests = _SlidingWindowCounter(60, 20)
    return rl


def test_ip_not_limited_initially():
    assert _make_limiter().check_ip("1.2.3.4") is False


def test_ip_limited_after_max():
    rl = _make_limiter()
    for _ in range(20):
        rl.check_ip("1.2.3.4")
    assert rl.check_ip("1.2.3.4") is True


def test_email_failure_not_limited_initially():
    assert _make_limiter().check_email_failure("u@example.com") is False


def test_email_failure_limited_after_max():
    rl = _make_limiter()
    for _ in range(5):
        rl.check_email_failure("u@example.com")
    assert rl.check_email_failure("u@example.com") is True


def test_is_email_limited_before_limit():
    rl = _make_limiter()
    rl.check_email_failure("u@example.com")
    assert rl.is_email_limited("u@example.com") is False


def test_is_email_limited_after_limit():
    rl = _make_limiter()
    for _ in range(5):
        rl.check_email_failure("u@example.com")
    assert rl.is_email_limited("u@example.com") is True
