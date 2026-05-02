"""
Tests for POST /api/login.

Coverage targets
----------------
AC-1  : Valid credentials → 200 + JWT token
AC-2  : Correct email, wrong password → 401, no token
AC-3  : Unknown email → 401, identical body (no user enumeration)
AC-4  : Missing email / password / both → 400 + validation error
AC-5  : Invalid email format → 400 + validation error
AC-6  : JWT payload contains sub + exp; signed with server secret

Security rules
--------------
Rule 4  : 401 body is identical for unknown-email and wrong-password
Rule 6  : JWT expiry ≤ 3600 s; only sub + exp in payload
Rule 7  : Cookie is HttpOnly, Secure, SameSite=Strict, Path=/api
Rule 8  : Rate limiting (email failures + IP requests)
Rule 11 : Internal exceptions → 500 with generic body
"""
from __future__ import annotations

import os
import time
from unittest.mock import patch

import pytest
from jose import jwt

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
LOGIN_URL = "/api/login"
VALID_EMAIL = "alice@example.com"
VALID_PASSWORD = "CorrectHorse99!"


def post_login(client, email=None, password=None, **extra):
    body = {}
    if email is not None:
        body["email"] = email
    if password is not None:
        body["password"] = password
    body.update(extra)
    return client.post(LOGIN_URL, json=body)


# ===========================================================================
# AC-1: Successful login → 200 + JWT
# ===========================================================================
class TestSuccessfulLogin:
    def test_returns_200(self, client, registered_user):
        r = post_login(client, VALID_EMAIL, VALID_PASSWORD)
        assert r.status_code == 200

    def test_response_contains_token(self, client, registered_user):
        r = post_login(client, VALID_EMAIL, VALID_PASSWORD)
        data = r.json()
        assert "token" in data
        assert isinstance(data["token"], str)
        assert len(data["token"]) > 20  # non-trivial JWT

    def test_no_password_in_response(self, client, registered_user):
        r = post_login(client, VALID_EMAIL, VALID_PASSWORD)
        assert "password" not in r.text

    # AC-6: JWT payload
    def test_jwt_contains_sub_and_exp(self, client, registered_user):
        r = post_login(client, VALID_EMAIL, VALID_PASSWORD)
        token = r.json()["token"]
        secret = os.environ["JWT_SECRET"]
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        assert "sub" in payload, "JWT must contain 'sub' claim"
        assert "exp" in payload, "JWT must contain 'exp' claim"

    def test_jwt_sub_is_user_id(self, client, registered_user):
        r = post_login(client, VALID_EMAIL, VALID_PASSWORD)
        token = r.json()["token"]
        secret = os.environ["JWT_SECRET"]
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        assert payload["sub"] == registered_user.id

    def test_jwt_exp_within_one_hour(self, client, registered_user):
        before = int(time.time())
        r = post_login(client, VALID_EMAIL, VALID_PASSWORD)
        after = int(time.time())
        token = r.json()["token"]
        secret = os.environ["JWT_SECRET"]
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        exp = payload["exp"]
        assert exp <= after + 3600, "exp must be at most 3600 s from now"
        assert exp >= before, "exp must be in the future"

    def test_jwt_has_no_extra_claims(self, client, registered_user):
        r = post_login(client, VALID_EMAIL, VALID_PASSWORD)
        token = r.json()["token"]
        secret = os.environ["JWT_SECRET"]
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        allowed_claims = {"sub", "exp"}
        extra = set(payload.keys()) - allowed_claims
        assert not extra, f"JWT must not contain extra claims: {extra}"

    # Rule 7: secure cookie
    def test_session_cookie_is_set(self, client, registered_user):
        r = post_login(client, VALID_EMAIL, VALID_PASSWORD)
        assert "session" in r.cookies

    def test_cookie_is_httponly(self, client, registered_user):
        r = post_login(client, VALID_EMAIL, VALID_PASSWORD)
        # httpx TestClient exposes set-cookie header
        set_cookie = r.headers.get("set-cookie", "")
        assert "httponly" in set_cookie.lower()

    def test_cookie_path_is_api(self, client, registered_user):
        r = post_login(client, VALID_EMAIL, VALID_PASSWORD)
        set_cookie = r.headers.get("set-cookie", "")
        assert "path=/api" in set_cookie.lower()

    def test_cookie_samesite_strict(self, client, registered_user):
        r = post_login(client, VALID_EMAIL, VALID_PASSWORD)
        set_cookie = r.headers.get("set-cookie", "")
        assert "samesite=strict" in set_cookie.lower()


# ===========================================================================
# AC-2: Correct email, wrong password → 401
# ===========================================================================
class TestWrongPassword:
    def test_returns_401(self, client, registered_user):
        r = post_login(client, VALID_EMAIL, "WrongPassword!")
        assert r.status_code == 401

    def test_error_body(self, client, registered_user):
        r = post_login(client, VALID_EMAIL, "WrongPassword!")
        assert r.json() == {"error": "invalid_credentials"}

    def test_no_token_in_response(self, client, registered_user):
        r = post_login(client, VALID_EMAIL, "WrongPassword!")
        assert "token" not in r.json()


# ===========================================================================
# AC-3: Unknown email → 401, identical body (no user enumeration)
# ===========================================================================
class TestUnknownEmail:
    def test_returns_401(self, client):
        r = post_login(client, "nobody@example.com", "anyPassword1!")
        assert r.status_code == 401

    def test_error_body_identical_to_wrong_password(self, client, registered_user):
        """Rule 4: identical body for unknown-email and wrong-password."""
        r_unknown = post_login(client, "nobody@example.com", "anyPassword1!")
        r_wrong_pw = post_login(client, VALID_EMAIL, "WrongPassword!")
        assert r_unknown.json() == r_wrong_pw.json()

    def test_no_token_in_response(self, client):
        r = post_login(client, "nobody@example.com", "anyPassword1!")
        assert "token" not in r.json()

    def test_does_not_reveal_email_existence(self, client, registered_user):
        """Response must not differ based on whether the email is registered."""
        r_registered = post_login(client, VALID_EMAIL, "wrong!")
        r_unknown = post_login(client, "nope@example.com", "wrong!")
        assert r_registered.status_code == r_unknown.status_code
        assert r_registered.json() == r_unknown.json()


# ===========================================================================
# AC-4: Missing fields → 400
# ===========================================================================
class TestMissingFields:
    def test_missing_email_returns_400(self, client):
        r = client.post(LOGIN_URL, json={"password": "somepassword"})
        assert r.status_code == 400

    def test_missing_password_returns_400(self, client):
        r = client.post(LOGIN_URL, json={"email": "user@example.com"})
        assert r.status_code == 400

    def test_empty_body_returns_400(self, client):
        r = client.post(LOGIN_URL, json={})
        assert r.status_code == 400

    def test_null_body_returns_400(self, client):
        r = client.post(LOGIN_URL, content=b"", headers={"Content-Type": "application/json"})
        assert r.status_code in (400, 422)

    def test_missing_email_has_descriptive_error(self, client):
        r = client.post(LOGIN_URL, json={"password": "somepassword"})
        body = r.json()
        assert "error" in body

    def test_missing_password_has_descriptive_error(self, client):
        r = client.post(LOGIN_URL, json={"email": "user@example.com"})
        body = r.json()
        assert "error" in body

    def test_no_token_in_400_response(self, client):
        r = client.post(LOGIN_URL, json={"password": "somepassword"})
        assert "token" not in r.json()


# ===========================================================================
# AC-5: Invalid email format → 400
# ===========================================================================
class TestInvalidEmailFormat:
    @pytest.mark.parametrize(
        "bad_email",
        [
            "notanemail",
            "missing@",
            "@nodomain.com",
            "spaces in@email.com",
            "",
            "a" * 321 + "@example.com",  # over 320-char limit
        ],
    )
    def test_invalid_email_returns_400(self, client, bad_email):
        r = post_login(client, bad_email, "somePassword1!")
        assert r.status_code == 400

    def test_validation_error_mentions_email(self, client):
        r = post_login(client, "notanemail", "somePassword1!")
        body = r.json()
        # The error detail should reference the email field.
        body_str = str(body).lower()
        assert "email" in body_str or "validation" in body_str


# ===========================================================================
# Security Rule 8: Rate limiting
# ===========================================================================
class TestRateLimiting:
    def test_email_failure_rate_limit(self, client, registered_user):
        """After 5 failures on the same email, the next attempt returns 429."""
        for _ in range(5):
            r = post_login(client, VALID_EMAIL, "WrongPassword!")
            # First 5 should be 401 (not yet rate-limited on failures).
            assert r.status_code in (401, 429)

        # The 6th (or earlier if limit hit) should trigger 429.
        r = post_login(client, VALID_EMAIL, "WrongPassword!")
        assert r.status_code == 429

    def test_ip_rate_limit(self, client, registered_user):
        """After 20 requests from the same IP, the next attempt returns 429."""
        # Use a mix of valid/invalid passwords to avoid email limit triggering first.
        emails = [f"user{i}@example.com" for i in range(25)]
        responses = []
        for email in emails:
            r = post_login(client, email, "WrongPassword!")
            responses.append(r.status_code)

        assert 429 in responses, "Expected at least one 429 after 20 requests from same IP"

    def test_rate_limit_body(self, client, registered_user):
        """Rate-limited requests should return the too_many_requests error."""
        for _ in range(6):
            r = post_login(client, VALID_EMAIL, "WrongPassword!")
        assert r.status_code == 429
        assert r.json() == {"error": "too_many_requests"}


# ===========================================================================
# Security Rule 11: Internal server errors → generic 500
# ===========================================================================
class TestInternalServerError:
    def test_db_exception_returns_500_generic(self, client, registered_user):
        """
        If the DB raises an unexpected exception, the endpoint must return
        the generic 500 body without leaking any internal details.
        """
        from app import repositories

        with patch.object(
            repositories.UserRepository,
            "get_by_email",
            side_effect=RuntimeError("db exploded"),
        ):
            r = post_login(client, VALID_EMAIL, VALID_PASSWORD)

        assert r.status_code == 500
        body = r.json()
        assert body == {"error": "internal_server_error"}
        # Ensure no stack trace or internal message is leaked.
        assert "RuntimeError" not in r.text
        assert "db exploded" not in r.text
        assert "Traceback" not in r.text


# ===========================================================================
# Password storage
# ===========================================================================
class TestPasswordStorage:
    def test_password_not_stored_in_plaintext(self, db_session, registered_user):
        """Stored hash must not equal the plain-text password."""
        assert registered_user.hashed_password != VALID_PASSWORD

    def test_password_stored_as_argon2(self, db_session, registered_user):
        """Hash should be an Argon2 hash string."""
        assert registered_user.hashed_password.startswith("$argon2")

    def test_password_not_in_response_on_success(self, client, registered_user):
        r = post_login(client, VALID_EMAIL, VALID_PASSWORD)
        assert VALID_PASSWORD not in r.text

    def test_password_not_in_response_on_failure(self, client, registered_user):
        wrong = "WrongPassword!"
        r = post_login(client, VALID_EMAIL, wrong)
        assert wrong not in r.text
