"""
test_login.py – pytest test-suite for the POST /login endpoint.

Covers:
 - 200 + token on valid credentials
 - 401 on wrong password
 - 401 on unknown email (same shape as wrong-password)
 - 400 on missing email / password / both
 - argon2id algorithm used for hashing (not MD5, bcrypt, etc.)
 - Rate-limit: IP limit returns 429 with Retry-After
 - Rate-limit: email-failure limit returns 429 with Retry-After
 - Token is a 64-char hex string (secrets.token_hex(32))
 - Session cookie attributes: HttpOnly, SameSite=Lax, Path=/
"""

from __future__ import annotations

import importlib
import time
from unittest.mock import patch

import pytest
from argon2 import PasswordHasher

import login as login_module
from login import app, register_user, _USER_STORE, _ip_requests, _email_failures


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_EMAIL = "test@example.com"
VALID_PASSWORD = "correcthorsebatterystaple"


@pytest.fixture(autouse=True)
def reset_state():
    """Reset shared mutable state between tests."""
    _USER_STORE.clear()
    _ip_requests.clear()
    _email_failures.clear()
    register_user(VALID_EMAIL, VALID_PASSWORD)
    yield
    _USER_STORE.clear()
    _ip_requests.clear()
    _email_failures.clear()


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def post_login(client, *, email=VALID_EMAIL, password=VALID_PASSWORD, **kw):
    return client.post(
        "/login",
        json={"email": email, "password": password},
        **kw,
    )


# ---------------------------------------------------------------------------
# AC 1 – valid credentials → 200 + non-empty token
# ---------------------------------------------------------------------------

class TestValidLogin:
    def test_returns_200(self, client):
        rv = post_login(client)
        assert rv.status_code == 200

    def test_response_contains_token(self, client):
        rv = post_login(client)
        body = rv.get_json()
        assert "token" in body
        assert body["token"]  # non-empty

    def test_token_is_64_char_hex(self, client):
        rv = post_login(client)
        token = rv.get_json()["token"]
        assert len(token) == 64
        assert all(c in "0123456789abcdef" for c in token)

    def test_each_login_returns_unique_token(self, client):
        t1 = post_login(client).get_json()["token"]
        t2 = post_login(client).get_json()["token"]
        assert t1 != t2


# ---------------------------------------------------------------------------
# AC 2 – wrong password → 401, no token
# ---------------------------------------------------------------------------

class TestWrongPassword:
    def test_returns_401(self, client):
        rv = post_login(client, password="wrongpassword")
        assert rv.status_code == 401

    def test_no_token_in_body(self, client):
        rv = post_login(client, password="wrongpassword")
        body = rv.get_json()
        assert "token" not in body

    def test_body_is_invalid_credentials(self, client):
        rv = post_login(client, password="wrongpassword")
        assert rv.get_json() == {"error": "invalid_credentials"}


# ---------------------------------------------------------------------------
# AC 3 – unknown email → 401, same shape as wrong-password
# ---------------------------------------------------------------------------

class TestUnknownEmail:
    def test_returns_401(self, client):
        rv = post_login(client, email="nobody@nowhere.example")
        assert rv.status_code == 401

    def test_same_body_shape_as_wrong_password(self, client):
        rv_unknown = post_login(client, email="nobody@nowhere.example").get_json()
        rv_wrong = post_login(client, password="wrongpassword").get_json()
        assert rv_unknown == rv_wrong == {"error": "invalid_credentials"}

    def test_no_token_in_body(self, client):
        rv = post_login(client, email="nobody@nowhere.example")
        assert "token" not in rv.get_json()


# ---------------------------------------------------------------------------
# AC 4 – missing fields → 400
# ---------------------------------------------------------------------------

class TestMissingFields:
    def test_missing_email_returns_400(self, client):
        rv = client.post("/login", json={"password": VALID_PASSWORD})
        assert rv.status_code == 400

    def test_missing_password_returns_400(self, client):
        rv = client.post("/login", json={"email": VALID_EMAIL})
        assert rv.status_code == 400

    def test_missing_both_returns_400(self, client):
        rv = client.post("/login", json={})
        assert rv.status_code == 400

    def test_empty_email_returns_400(self, client):
        rv = client.post("/login", json={"email": "", "password": VALID_PASSWORD})
        assert rv.status_code == 400

    def test_empty_password_returns_400(self, client):
        rv = client.post("/login", json={"email": VALID_EMAIL, "password": ""})
        assert rv.status_code == 400

    def test_non_json_body_returns_400(self, client):
        rv = client.post("/login", data="not-json", content_type="text/plain")
        assert rv.status_code == 400

    def test_error_key_in_400_body(self, client):
        rv = client.post("/login", json={"password": VALID_PASSWORD})
        body = rv.get_json()
        assert "error" in body


# ---------------------------------------------------------------------------
# AC 5 – argon2id algorithm is used
# ---------------------------------------------------------------------------

class TestArgon2idAlgorithm:
    def test_stored_hash_uses_argon2id(self):
        """The hash stored for the test user must be an argon2id hash."""
        stored = _USER_STORE[VALID_EMAIL]
        # argon2id hashes start with "$argon2id$"
        assert stored.startswith("$argon2id$"), (
            f"Expected argon2id hash, got: {stored[:30]}"
        )

    def test_verify_with_argon2_cffi_succeeds(self):
        ph = PasswordHasher(
            time_cost=3, memory_cost=65_536, parallelism=1,
            hash_len=32, salt_len=16
        )
        stored = _USER_STORE[VALID_EMAIL]
        assert ph.verify(stored, VALID_PASSWORD)

    def test_not_md5(self):
        stored = _USER_STORE[VALID_EMAIL]
        assert len(stored) != 32, "Hash looks like raw MD5"

    def test_not_bcrypt(self):
        stored = _USER_STORE[VALID_EMAIL]
        assert not stored.startswith("$2b$"), "Hash looks like bcrypt"


# ---------------------------------------------------------------------------
# Security – rate limiting
# ---------------------------------------------------------------------------

class TestRateLimiting:
    def test_ip_limit_returns_429(self, client):
        """After 10 requests from the same IP, the 11th should get 429."""
        for _ in range(10):
            post_login(client)
        rv = post_login(client)
        assert rv.status_code == 429

    def test_429_has_retry_after_header(self, client):
        for _ in range(10):
            post_login(client)
        rv = post_login(client)
        assert "Retry-After" in rv.headers
        assert int(rv.headers["Retry-After"]) > 0

    def test_429_body(self, client):
        for _ in range(10):
            post_login(client)
        rv = post_login(client)
        assert rv.get_json() == {"error": "too_many_requests"}

    def test_email_failure_limit_returns_429(self, client):
        """After 5 failed attempts for the same email, the 6th should get 429."""
        for _ in range(5):
            post_login(client, password="wrongpassword")
        # Reset IP counter so IP limit doesn't interfere.
        _ip_requests.clear()
        rv = post_login(client, password="wrongpassword")
        assert rv.status_code == 429

    def test_email_failure_limit_retry_after(self, client):
        for _ in range(5):
            post_login(client, password="wrongpassword")
        _ip_requests.clear()
        rv = post_login(client, password="wrongpassword")
        assert "Retry-After" in rv.headers


# ---------------------------------------------------------------------------
# Security – cookie attributes
# ---------------------------------------------------------------------------

class TestSessionCookie:
    def test_cookie_is_httponly(self, client):
        rv = post_login(client)
        cookie_header = rv.headers.get("Set-Cookie", "")
        assert "HttpOnly" in cookie_header

    def test_cookie_is_samesite_lax(self, client):
        rv = post_login(client)
        cookie_header = rv.headers.get("Set-Cookie", "")
        assert "SameSite=Lax" in cookie_header

    def test_cookie_path_is_root(self, client):
        rv = post_login(client)
        cookie_header = rv.headers.get("Set-Cookie", "")
        assert "Path=/" in cookie_header


# ---------------------------------------------------------------------------
# Security – dummy verify timing equalisation
# ---------------------------------------------------------------------------

class TestTimingEqualisation:
    def test_dummy_verify_is_called_for_unknown_email(self, client):
        """Verify that PasswordHasher.verify is called even for unknown emails."""
        original_verify = login_module._PH.verify
        call_count = {"n": 0}

        def counting_verify(hash_, pwd):
            call_count["n"] += 1
            return original_verify(hash_, pwd)

        with patch.object(login_module._PH, "verify", side_effect=counting_verify):
            post_login(client, email="ghost@nowhere.example")

        assert call_count["n"] >= 1, "verify() should be called for unknown emails"


# ---------------------------------------------------------------------------
# Security – generic 500 on unhandled exceptions
# ---------------------------------------------------------------------------

class TestInternalErrorHandling:
    def test_unhandled_exception_returns_500(self, client):
        with patch.object(login_module._PH, "verify", side_effect=RuntimeError("boom")):
            rv = post_login(client)
        assert rv.status_code == 500
        assert rv.get_json() == {"error": "internal_error"}
