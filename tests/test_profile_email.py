"""
Unit tests for:
  POST /api/profile/email         — initiate email change
  POST /api/profile/email/confirm — confirm with verification code

Covers:
  - Happy path (initiate + confirm)
  - 401 on missing / invalid / expired JWT
  - 400 on malformed email
  - 400 on same-email change attempt
  - 401 + rate-limit after 5 wrong codes
  - Old email still usable during 30-day grace window
  - Code expiry (CodeNotFound → 401)
"""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

import app.db as db_module
import app.redis_client as rc
from app.config import VERIFY_CODE_MAX_ATTEMPTS
from tests.conftest import make_token

INITIATE_URL = "/api/profile/email"
CONFIRM_URL = "/api/profile/email/confirm"


# ===========================================================================
# Helper
# ===========================================================================

def _initiate(client: TestClient, headers: dict, new_email: str) -> tuple[int, dict]:
    r = client.post(INITIATE_URL, json={"new_email": new_email}, headers=headers)
    return r.status_code, r.json()


def _confirm(
    client: TestClient, headers: dict, new_email: str, code: str
) -> tuple[int, dict]:
    r = client.post(
        CONFIRM_URL,
        json={"new_email": new_email, "code": code},
        headers=headers,
    )
    return r.status_code, r.json()


def _get_stored_code(user_id: str, new_email: str) -> str:
    """Read the code directly from the fake Redis instance."""
    import hashlib
    raw = f"{user_id}:{new_email}".encode()
    digest = hashlib.sha256(raw).hexdigest()
    return rc.get_redis().get(f"verify:{digest}")


# ===========================================================================
# POST /api/profile/email — initiate
# ===========================================================================

class TestInitiateEmailChange:

    def test_happy_path_returns_202(self, client, user, auth_headers):
        status, body = _initiate(client, auth_headers, "new@example.com")
        assert status == 202
        assert "verification code" in body["message"].lower()

    def test_code_stored_in_redis(self, client, user, auth_headers):
        _initiate(client, auth_headers, "new@example.com")
        code = _get_stored_code(user["id"], "new@example.com")
        assert code is not None
        assert len(code) == 6
        assert code.isdigit()

    def test_email_send_stub_called(self, client, user, auth_headers):
        with patch("app.routers.profile.send_verification_email") as mock_send:
            _initiate(client, auth_headers, "new@example.com")
            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            assert args[0] == "new@example.com"
            assert len(args[1]) == 6

    def test_no_auth_header_returns_401(self, client):
        status, body = _initiate(client, {}, "new@example.com")
        assert status == 401

    def test_invalid_token_returns_401(self, client):
        headers = {"Authorization": "Bearer not.a.valid.token"}
        status, body = _initiate(client, headers, "new@example.com")
        assert status == 401

    def test_expired_token_returns_401(self, client, user):
        token = make_token(user["id"], expires_delta=timedelta(seconds=-1))
        headers = {"Authorization": f"Bearer {token}"}
        status, body = _initiate(client, headers, "new@example.com")
        assert status == 401

    def test_token_for_nonexistent_user_returns_401(self, client):
        token = make_token("nonexistent-user-id")
        headers = {"Authorization": f"Bearer {token}"}
        status, body = _initiate(client, headers, "new@example.com")
        assert status == 401

    def test_malformed_email_returns_400(self, client, auth_headers):
        status, body = _initiate(client, auth_headers, "not-an-email")
        assert status == 400
        assert "detail" in body

    def test_empty_email_returns_400(self, client, auth_headers):
        r = client.post(INITIATE_URL, json={"new_email": ""}, headers=auth_headers)
        assert r.status_code == 400

    def test_same_email_returns_400(self, client, user, auth_headers):
        # user's current email is "original@example.com"
        status, body = _initiate(client, auth_headers, user["email"])
        assert status == 400
        assert "differ" in body["detail"].lower()

    def test_resend_resets_attempt_counter(self, client, user, auth_headers):
        """Re-initiating the flow should reset the attempt counter."""
        new_email = "retry@example.com"
        _initiate(client, auth_headers, new_email)

        # Exhaust attempts with wrong code
        for _ in range(VERIFY_CODE_MAX_ATTEMPTS):
            _confirm(client, auth_headers, new_email, "000000")

        # Re-initiate — should succeed and reset counter
        status, _ = _initiate(client, auth_headers, new_email)
        assert status == 202

        # Now confirm with wrong code should work again (not rate-limited yet)
        status2, body2 = _confirm(client, auth_headers, new_email, "000000")
        assert status2 == 401
        assert "incorrect" in body2["detail"].lower()


# ===========================================================================
# POST /api/profile/email/confirm
# ===========================================================================

class TestConfirmEmailChange:

    def _setup_and_initiate(self, client, user, auth_headers, new_email="new@example.com"):
        """Helper: initiate flow and return the stored code."""
        _initiate(client, auth_headers, new_email)
        return _get_stored_code(user["id"], new_email)

    def test_happy_path_returns_200(self, client, user, auth_headers):
        new_email = "new@example.com"
        code = self._setup_and_initiate(client, user, auth_headers, new_email)
        status, body = _confirm(client, auth_headers, new_email, code)
        assert status == 200
        assert "successfully" in body["message"].lower()

    def test_email_updated_in_db(self, client, user, auth_headers):
        new_email = "updated@example.com"
        code = self._setup_and_initiate(client, user, auth_headers, new_email)
        _confirm(client, auth_headers, new_email, code)
        refreshed = db_module.get_user_by_id(user["id"])
        assert refreshed["email"] == new_email

    def test_old_email_still_in_audit_trail(self, client, user, auth_headers):
        old_email = user["email"]
        new_email = "updated@example.com"
        code = self._setup_and_initiate(client, user, auth_headers, new_email)
        _confirm(client, auth_headers, new_email, code)
        refreshed = db_module.get_user_by_id(user["id"])
        assert any(e["email"] == old_email for e in refreshed["previous_emails"])

    def test_old_email_valid_for_lookup_during_grace_period(
        self, client, user, auth_headers
    ):
        old_email = user["email"]
        new_email = "updated@example.com"
        code = self._setup_and_initiate(client, user, auth_headers, new_email)
        _confirm(client, auth_headers, new_email, code)
        # Old email lookup should still return the user (grace period)
        found = db_module.get_user_by_email(old_email)
        assert found is not None
        assert found["id"] == user["id"]

    def test_no_auth_header_returns_401(self, client):
        r = client.post(
            CONFIRM_URL, json={"new_email": "x@x.com", "code": "123456"}
        )
        assert r.status_code == 401

    def test_wrong_code_returns_401(self, client, user, auth_headers):
        new_email = "new@example.com"
        self._setup_and_initiate(client, user, auth_headers, new_email)
        status, body = _confirm(client, auth_headers, new_email, "000000")
        assert status == 401
        assert "incorrect" in body["detail"].lower()

    def test_rate_limit_after_five_wrong_attempts(self, client, user, auth_headers):
        new_email = "new@example.com"
        self._setup_and_initiate(client, user, auth_headers, new_email)

        for i in range(VERIFY_CODE_MAX_ATTEMPTS):
            status, body = _confirm(client, auth_headers, new_email, "000000")
            assert status == 401

        # 6th attempt — should be rate limited
        status, body = _confirm(client, auth_headers, new_email, "000000")
        assert status == 401
        assert "too many" in body["detail"].lower() or "attempts" in body["detail"].lower()

    def test_correct_code_after_partial_failures(self, client, user, auth_headers):
        """A correct code should still work if < MAX_ATTEMPTS failures occurred."""
        new_email = "new@example.com"
        code = self._setup_and_initiate(client, user, auth_headers, new_email)

        # Fail twice, then succeed
        _confirm(client, auth_headers, new_email, "000000")
        _confirm(client, auth_headers, new_email, "000000")
        status, body = _confirm(client, auth_headers, new_email, code)
        assert status == 200

    def test_expired_code_returns_401(self, client, user, auth_headers):
        """
        If the Redis key has been deleted (expired), confirm should return 401.
        """
        new_email = "new@example.com"
        self._setup_and_initiate(client, user, auth_headers, new_email)
        # Manually delete the key from Redis to simulate expiry
        rc.delete_verification_code(user["id"], new_email)
        status, body = _confirm(client, auth_headers, new_email, "123456")
        assert status == 401
        assert "pending" in body["detail"].lower() or "not found" in body["detail"].lower()

    def test_malformed_email_in_confirm_returns_400(self, client, auth_headers):
        r = client.post(
            CONFIRM_URL,
            json={"new_email": "bad-email", "code": "123456"},
            headers=auth_headers,
        )
        assert r.status_code == 400

    def test_invalid_code_format_returns_400(self, client, auth_headers):
        r = client.post(
            CONFIRM_URL,
            json={"new_email": "valid@example.com", "code": "abc"},
            headers=auth_headers,
        )
        assert r.status_code == 400


# ===========================================================================
# Redis helper unit tests
# ===========================================================================

class TestRedisHelpers:

    def test_generate_code_is_6_digits(self):
        for _ in range(20):
            code = rc.generate_code()
            assert len(code) == 6
            assert code.isdigit()

    def test_store_and_retrieve_code(self):
        rc.store_verification_code("user1", "a@b.com", "123456")
        assert rc.verify_code("user1", "a@b.com", "123456") is True

    def test_wrong_code_raises_invalid_code(self):
        rc.store_verification_code("user1", "a@b.com", "123456")
        with pytest.raises(rc.InvalidCode):
            rc.verify_code("user1", "a@b.com", "654321")

    def test_code_not_found_raises(self):
        with pytest.raises(rc.CodeNotFound):
            rc.verify_code("user1", "a@b.com", "123456")

    def test_rate_limit_raises_after_max_attempts(self):
        rc.store_verification_code("user1", "a@b.com", "123456")
        for _ in range(VERIFY_CODE_MAX_ATTEMPTS):
            with pytest.raises(rc.InvalidCode):
                rc.verify_code("user1", "a@b.com", "000000")
        with pytest.raises(rc.RateLimitExceeded):
            rc.verify_code("user1", "a@b.com", "000000")

    def test_store_resets_attempt_counter(self):
        rc.store_verification_code("user1", "a@b.com", "111111")
        for _ in range(VERIFY_CODE_MAX_ATTEMPTS):
            with pytest.raises(rc.InvalidCode):
                rc.verify_code("user1", "a@b.com", "000000")
        # Re-store resets counter
        rc.store_verification_code("user1", "a@b.com", "222222")
        with pytest.raises(rc.InvalidCode):  # should be InvalidCode not RateLimitExceeded
            rc.verify_code("user1", "a@b.com", "000000")
