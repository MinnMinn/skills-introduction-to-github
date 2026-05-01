"""
Unit tests for POST /api/profile/email and POST /api/profile/email/confirm.

Coverage targets:
  - Happy path (request + confirm)
  - Unauthorized request (missing / expired / malformed token) → 401
  - Malformed email → 400
  - Wrong code → 401 with remaining-attempts hint
  - Rate limit after 5 wrong attempts → 401
  - Expired / missing pending request → 401
  - Old email still present in audit record after change
  - Code not leaked in HTTP response
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import app.audit as audit
from app.routers.profile import _verification_key
from tests.conftest import (
    TEST_USER_EMAIL,
    TEST_USER_ID,
    auth_headers,
    make_token,
)

NEW_EMAIL = "new@example.com"
VALID_CODE = "123456"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _plant_code(fake_redis, code: str = VALID_CODE, email: str = NEW_EMAIL) -> None:
    """Manually plant a verification code in Redis (bypasses random generation)."""
    key = _verification_key(TEST_USER_ID, email.lower())
    fake_redis.set(key, code, ex=900)


# ---------------------------------------------------------------------------
# POST /api/profile/email — happy path
# ---------------------------------------------------------------------------


class TestRequestEmailChange:
    def test_happy_path_returns_202(self, client: TestClient, fake_redis):
        resp = client.post(
            "/api/profile/email",
            json={"new_email": NEW_EMAIL},
            headers=auth_headers(),
        )
        assert resp.status_code == 202

    def test_happy_path_response_body(self, client: TestClient, fake_redis):
        resp = client.post(
            "/api/profile/email",
            json={"new_email": NEW_EMAIL},
            headers=auth_headers(),
        )
        data = resp.json()
        assert "message" in data

    def test_code_stored_in_redis(self, client: TestClient, fake_redis):
        """After a successful request, a 6-digit code must exist in Redis."""
        client.post(
            "/api/profile/email",
            json={"new_email": NEW_EMAIL},
            headers=auth_headers(),
        )
        key = _verification_key(TEST_USER_ID, NEW_EMAIL.lower())
        stored = fake_redis.get(key)
        assert stored is not None
        assert stored.isdigit()
        assert len(stored) == 6

    def test_code_has_ttl(self, client: TestClient, fake_redis):
        """The stored code must have a TTL ≤ 900 seconds."""
        client.post(
            "/api/profile/email",
            json={"new_email": NEW_EMAIL},
            headers=auth_headers(),
        )
        key = _verification_key(TEST_USER_ID, NEW_EMAIL.lower())
        ttl = fake_redis.ttl(key)
        assert 0 < ttl <= 900

    def test_code_not_in_response(self, client: TestClient, fake_redis):
        """The verification code must NOT appear anywhere in the HTTP response."""
        resp = client.post(
            "/api/profile/email",
            json={"new_email": NEW_EMAIL},
            headers=auth_headers(),
        )
        key = _verification_key(TEST_USER_ID, NEW_EMAIL.lower())
        stored_code = fake_redis.get(key)
        assert stored_code not in resp.text

    def test_email_send_stub_called(self, client: TestClient, fake_redis):
        with patch("app.routers.profile.send_verification_code") as mock_send:
            client.post(
                "/api/profile/email",
                json={"new_email": NEW_EMAIL},
                headers=auth_headers(),
            )
            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args
            assert call_kwargs[1]["to_email"] == NEW_EMAIL.lower() or call_kwargs[0][0] == NEW_EMAIL.lower()


# ---------------------------------------------------------------------------
# POST /api/profile/email — auth errors
# ---------------------------------------------------------------------------


class TestRequestEmailChangeAuth:
    def test_missing_auth_header_returns_403(self, client: TestClient):
        # HTTPBearer returns 403 when the header is absent (FastAPI default)
        resp = client.post("/api/profile/email", json={"new_email": NEW_EMAIL})
        assert resp.status_code in (401, 403)

    def test_expired_token_returns_401(self, client: TestClient):
        resp = client.post(
            "/api/profile/email",
            json={"new_email": NEW_EMAIL},
            headers=auth_headers(make_token(expired=True)),
        )
        assert resp.status_code == 401

    def test_invalid_token_string_returns_401(self, client: TestClient):
        resp = client.post(
            "/api/profile/email",
            json={"new_email": NEW_EMAIL},
            headers={"Authorization": "Bearer not-a-real-jwt"},
        )
        assert resp.status_code == 401

    def test_token_missing_sub_returns_401(self, client: TestClient):
        resp = client.post(
            "/api/profile/email",
            json={"new_email": NEW_EMAIL},
            headers=auth_headers(make_token(missing_sub=True)),
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/profile/email — validation errors
# ---------------------------------------------------------------------------


class TestRequestEmailChangeValidation:
    @pytest.mark.parametrize(
        "bad_email",
        [
            "not-an-email",
            "missing@",
            "@nodomain.com",
            "",
            "spaces in@email.com",
            "plainstring",
        ],
    )
    def test_malformed_email_returns_422(self, client: TestClient, bad_email: str):
        resp = client.post(
            "/api/profile/email",
            json={"new_email": bad_email},
            headers=auth_headers(),
        )
        # Pydantic validation error → FastAPI returns 422 Unprocessable Entity
        assert resp.status_code == 422

    def test_missing_body_returns_422(self, client: TestClient):
        resp = client.post(
            "/api/profile/email",
            headers=auth_headers(),
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/profile/email/confirm — happy path
# ---------------------------------------------------------------------------


class TestConfirmEmailChange:
    def test_happy_path_returns_200(self, client: TestClient, fake_redis):
        _plant_code(fake_redis)
        resp = client.post(
            "/api/profile/email/confirm",
            json={"new_email": NEW_EMAIL, "code": VALID_CODE},
            headers=auth_headers(),
        )
        assert resp.status_code == 200

    def test_happy_path_updates_user_email(self, client: TestClient, fake_redis):
        _plant_code(fake_redis)
        client.post(
            "/api/profile/email/confirm",
            json={"new_email": NEW_EMAIL, "code": VALID_CODE},
            headers=auth_headers(),
        )
        user = audit.get_user(TEST_USER_ID)
        assert user is not None
        assert user["email"] == NEW_EMAIL.lower()

    def test_happy_path_preserves_old_email_in_audit(
        self, client: TestClient, fake_redis
    ):
        _plant_code(fake_redis)
        client.post(
            "/api/profile/email/confirm",
            json={"new_email": NEW_EMAIL, "code": VALID_CODE},
            headers=auth_headers(),
        )
        user = audit.get_user(TEST_USER_ID)
        assert user is not None
        assert user.get("old_email") == TEST_USER_EMAIL
        assert "old_email_valid_until" in user

    def test_happy_path_clears_redis_code(self, client: TestClient, fake_redis):
        _plant_code(fake_redis)
        client.post(
            "/api/profile/email/confirm",
            json={"new_email": NEW_EMAIL, "code": VALID_CODE},
            headers=auth_headers(),
        )
        key = _verification_key(TEST_USER_ID, NEW_EMAIL.lower())
        assert fake_redis.get(key) is None


# ---------------------------------------------------------------------------
# POST /api/profile/email/confirm — auth errors
# ---------------------------------------------------------------------------


class TestConfirmEmailChangeAuth:
    def test_missing_auth_header(self, client: TestClient, fake_redis):
        _plant_code(fake_redis)
        resp = client.post(
            "/api/profile/email/confirm",
            json={"new_email": NEW_EMAIL, "code": VALID_CODE},
        )
        assert resp.status_code in (401, 403)

    def test_expired_token(self, client: TestClient, fake_redis):
        _plant_code(fake_redis)
        resp = client.post(
            "/api/profile/email/confirm",
            json={"new_email": NEW_EMAIL, "code": VALID_CODE},
            headers=auth_headers(make_token(expired=True)),
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/profile/email/confirm — wrong code
# ---------------------------------------------------------------------------


class TestConfirmEmailChangeWrongCode:
    def test_wrong_code_returns_401(self, client: TestClient, fake_redis):
        _plant_code(fake_redis)
        resp = client.post(
            "/api/profile/email/confirm",
            json={"new_email": NEW_EMAIL, "code": "000000"},
            headers=auth_headers(),
        )
        assert resp.status_code == 401

    def test_wrong_code_shows_remaining_attempts(self, client: TestClient, fake_redis):
        _plant_code(fake_redis)
        resp = client.post(
            "/api/profile/email/confirm",
            json={"new_email": NEW_EMAIL, "code": "000000"},
            headers=auth_headers(),
        )
        assert "remaining" in resp.json()["detail"].lower()

    def test_rate_limit_after_five_wrong_attempts(
        self, client: TestClient, fake_redis
    ):
        _plant_code(fake_redis)
        for _ in range(5):
            client.post(
                "/api/profile/email/confirm",
                json={"new_email": NEW_EMAIL, "code": "000000"},
                headers=auth_headers(),
            )
        # 6th attempt — should now be rate-limited even with the correct code.
        resp = client.post(
            "/api/profile/email/confirm",
            json={"new_email": NEW_EMAIL, "code": VALID_CODE},
            headers=auth_headers(),
        )
        assert resp.status_code == 401

    def test_rate_limit_error_message(self, client: TestClient, fake_redis):
        _plant_code(fake_redis)
        for _ in range(5):
            client.post(
                "/api/profile/email/confirm",
                json={"new_email": NEW_EMAIL, "code": "000000"},
                headers=auth_headers(),
            )
        resp = client.post(
            "/api/profile/email/confirm",
            json={"new_email": NEW_EMAIL, "code": "000000"},
            headers=auth_headers(),
        )
        detail = resp.json()["detail"].lower()
        assert "too many" in detail or "rate limit" in detail or "attempt" in detail

    def test_no_pending_request_returns_401(self, client: TestClient, fake_redis):
        """No code in Redis (never requested or expired)."""
        resp = client.post(
            "/api/profile/email/confirm",
            json={"new_email": NEW_EMAIL, "code": VALID_CODE},
            headers=auth_headers(),
        )
        assert resp.status_code == 401

    def test_wrong_email_on_confirm_returns_401(self, client: TestClient, fake_redis):
        """Correct code but wrong email → Redis key miss → 401."""
        _plant_code(fake_redis, email=NEW_EMAIL)
        resp = client.post(
            "/api/profile/email/confirm",
            json={"new_email": "different@example.com", "code": VALID_CODE},
            headers=auth_headers(),
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/profile/email/confirm — validation errors
# ---------------------------------------------------------------------------


class TestConfirmEmailChangeValidation:
    def test_invalid_code_format_returns_422(self, client: TestClient, fake_redis):
        _plant_code(fake_redis)
        resp = client.post(
            "/api/profile/email/confirm",
            json={"new_email": NEW_EMAIL, "code": "abc"},
            headers=auth_headers(),
        )
        assert resp.status_code == 422

    def test_code_too_short_returns_422(self, client: TestClient, fake_redis):
        _plant_code(fake_redis)
        resp = client.post(
            "/api/profile/email/confirm",
            json={"new_email": NEW_EMAIL, "code": "12345"},
            headers=auth_headers(),
        )
        assert resp.status_code == 422

    def test_code_too_long_returns_422(self, client: TestClient, fake_redis):
        _plant_code(fake_redis)
        resp = client.post(
            "/api/profile/email/confirm",
            json={"new_email": NEW_EMAIL, "code": "1234567"},
            headers=auth_headers(),
        )
        assert resp.status_code == 422

    def test_malformed_email_on_confirm_returns_422(
        self, client: TestClient, fake_redis
    ):
        resp = client.post(
            "/api/profile/email/confirm",
            json={"new_email": "not-valid", "code": VALID_CODE},
            headers=auth_headers(),
        )
        assert resp.status_code == 422
