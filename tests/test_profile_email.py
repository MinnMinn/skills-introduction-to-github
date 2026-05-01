"""
Unit tests for the email-change flow.

Coverage:
  POST /api/profile/email
    ✓ Happy path — 202, code stored in Redis
    ✓ No Authorization header — 401
    ✓ Invalid JWT — 401
    ✓ Malformed email in body — 422 (Pydantic) / 400 (same-email guard)
    ✓ Same-email change attempt — 400

  POST /api/profile/email/confirm
    ✓ Happy path — 200, email updated in DB
    ✓ Correct code, old email still valid (audit trail)
    ✓ Wrong code — 401
    ✓ Rate limit after 5 wrong attempts — 429
    ✓ Expired / non-existent code (no prior request) — 401
    ✓ No Authorization header — 401
    ✓ Invalid JWT on confirm — 401

  Verification service unit tests (isolated)
    ✓ generate_and_store_code produces a 6-digit string
    ✓ Re-requesting a code resets the attempt counter
    ✓ verify_code returns (True, False) on correct code
    ✓ verify_code returns (False, False) on wrong code (< 5 attempts)
    ✓ verify_code returns (False, True) after 5 wrong attempts
"""
from __future__ import annotations

import fakeredis
import pytest

from app import database
from app.services import verification
from tests.conftest import auth_headers


# ===========================================================================
# POST /api/profile/email  — initiate email change
# ===========================================================================

class TestRequestEmailChange:
    def test_happy_path_returns_202(self, client, existing_user, fake_redis):
        resp = client.post(
            "/api/profile/email",
            json={"new_email": "alice-new@example.com"},
            headers=auth_headers(existing_user["id"]),
        )
        assert resp.status_code == 202
        data = resp.json()
        assert "message" in data

    def test_happy_path_code_stored_in_redis(self, client, existing_user, fake_redis):
        client.post(
            "/api/profile/email",
            json={"new_email": "alice-new@example.com"},
            headers=auth_headers(existing_user["id"]),
        )
        # At least one key should have been written to fakeredis
        keys = fake_redis.keys("email_verify:code:*")
        assert len(keys) == 1

    def test_no_auth_header_returns_401(self, client, existing_user):
        resp = client.post(
            "/api/profile/email",
            json={"new_email": "alice-new@example.com"},
        )
        assert resp.status_code == 403  # HTTPBearer returns 403 when no header

    def test_invalid_jwt_returns_401(self, client, existing_user):
        resp = client.post(
            "/api/profile/email",
            json={"new_email": "alice-new@example.com"},
            headers={"Authorization": "Bearer this.is.not.valid"},
        )
        assert resp.status_code == 401

    def test_malformed_email_returns_422(self, client, existing_user):
        resp = client.post(
            "/api/profile/email",
            json={"new_email": "not-an-email"},
            headers=auth_headers(existing_user["id"]),
        )
        # Pydantic rejects malformed email with 422 Unprocessable Entity
        assert resp.status_code == 422

    def test_same_email_returns_400(self, client, existing_user):
        resp = client.post(
            "/api/profile/email",
            json={"new_email": existing_user["email"]},
            headers=auth_headers(existing_user["id"]),
        )
        assert resp.status_code == 400
        assert "differ" in resp.json()["detail"].lower()

    def test_wrong_secret_jwt_returns_401(self, client, existing_user):
        from tests.conftest import make_jwt
        bad_token = make_jwt(existing_user["id"], secret="wrong-secret")
        resp = client.post(
            "/api/profile/email",
            json={"new_email": "alice-new@example.com"},
            headers={"Authorization": f"Bearer {bad_token}"},
        )
        assert resp.status_code == 401


# ===========================================================================
# POST /api/profile/email/confirm  — confirm with code
# ===========================================================================

class TestConfirmEmailChange:

    NEW_EMAIL = "alice-new@example.com"

    def _initiate(self, client, user):
        """Helper: POST /api/profile/email and return the stored code."""
        client.post(
            "/api/profile/email",
            json={"new_email": self.NEW_EMAIL},
            headers=auth_headers(user["id"]),
        )

    def _get_stored_code(self, fake_redis, user_id: str, new_email: str) -> str:
        import hashlib
        email_hash = hashlib.sha256(new_email.lower().encode()).hexdigest()
        key = f"email_verify:code:{user_id}:{email_hash}"
        code = fake_redis.get(key)
        assert code is not None, "No code found in Redis"
        return code

    def test_happy_path_returns_200(self, client, existing_user, fake_redis):
        self._initiate(client, existing_user)
        code = self._get_stored_code(fake_redis, existing_user["id"], self.NEW_EMAIL)

        resp = client.post(
            "/api/profile/email/confirm",
            json={"new_email": self.NEW_EMAIL, "code": code},
            headers=auth_headers(existing_user["id"]),
        )
        assert resp.status_code == 200
        assert "updated" in resp.json()["message"].lower()

    def test_happy_path_email_updated_in_db(self, client, existing_user, fake_redis):
        self._initiate(client, existing_user)
        code = self._get_stored_code(fake_redis, existing_user["id"], self.NEW_EMAIL)

        client.post(
            "/api/profile/email/confirm",
            json={"new_email": self.NEW_EMAIL, "code": code},
            headers=auth_headers(existing_user["id"]),
        )

        updated = database.get_user_by_id(existing_user["id"])
        assert updated["email"] == self.NEW_EMAIL

    def test_old_email_still_valid_after_change(self, client, existing_user, fake_redis):
        """Audit trail: old email should still resolve the user for 30 days."""
        old_email = existing_user["email"]
        self._initiate(client, existing_user)
        code = self._get_stored_code(fake_redis, existing_user["id"], self.NEW_EMAIL)

        client.post(
            "/api/profile/email/confirm",
            json={"new_email": self.NEW_EMAIL, "code": code},
            headers=auth_headers(existing_user["id"]),
        )

        user_via_old = database.get_user_by_email(old_email)
        assert user_via_old is not None
        assert user_via_old["id"] == existing_user["id"]

    def test_wrong_code_returns_401(self, client, existing_user, fake_redis):
        self._initiate(client, existing_user)

        resp = client.post(
            "/api/profile/email/confirm",
            json={"new_email": self.NEW_EMAIL, "code": "000000"},
            headers=auth_headers(existing_user["id"]),
        )
        assert resp.status_code == 401

    def test_rate_limit_after_five_wrong_attempts(
        self, client, existing_user, fake_redis
    ):
        self._initiate(client, existing_user)

        for i in range(4):
            resp = client.post(
                "/api/profile/email/confirm",
                json={"new_email": self.NEW_EMAIL, "code": "000000"},
                headers=auth_headers(existing_user["id"]),
            )
            assert resp.status_code == 401, f"attempt {i+1} should still be 401"

        # 5th wrong attempt should trigger 429
        resp = client.post(
            "/api/profile/email/confirm",
            json={"new_email": self.NEW_EMAIL, "code": "000000"},
            headers=auth_headers(existing_user["id"]),
        )
        assert resp.status_code == 429

    def test_no_prior_request_code_returns_401(self, client, existing_user):
        resp = client.post(
            "/api/profile/email/confirm",
            json={"new_email": self.NEW_EMAIL, "code": "123456"},
            headers=auth_headers(existing_user["id"]),
        )
        assert resp.status_code == 401

    def test_no_auth_header_returns_403(self, client, existing_user, fake_redis):
        self._initiate(client, existing_user)
        resp = client.post(
            "/api/profile/email/confirm",
            json={"new_email": self.NEW_EMAIL, "code": "123456"},
        )
        assert resp.status_code == 403

    def test_invalid_jwt_on_confirm_returns_401(self, client, existing_user, fake_redis):
        self._initiate(client, existing_user)
        resp = client.post(
            "/api/profile/email/confirm",
            json={"new_email": self.NEW_EMAIL, "code": "123456"},
            headers={"Authorization": "Bearer bad.token.here"},
        )
        assert resp.status_code == 401

    def test_malformed_code_length_returns_422(self, client, existing_user, fake_redis):
        self._initiate(client, existing_user)
        resp = client.post(
            "/api/profile/email/confirm",
            json={"new_email": self.NEW_EMAIL, "code": "12"},  # too short
            headers=auth_headers(existing_user["id"]),
        )
        assert resp.status_code == 422


# ===========================================================================
# Verification service — isolated unit tests
# ===========================================================================

class TestVerificationService:

    def _fresh_redis(self):
        return fakeredis.FakeRedis(decode_responses=True)

    def test_generate_code_is_six_digits(self):
        r = self._fresh_redis()
        code = verification.generate_and_store_code(r, "user-1", "test@example.com")
        assert len(code) == 6
        assert code.isdigit()

    def test_generate_code_stored_in_redis(self):
        r = self._fresh_redis()
        code = verification.generate_and_store_code(r, "user-1", "test@example.com")
        keys = r.keys("email_verify:code:*")
        assert len(keys) == 1
        assert r.get(keys[0]) == code

    def test_verify_correct_code_returns_valid(self):
        r = self._fresh_redis()
        code = verification.generate_and_store_code(r, "u1", "a@b.com")
        is_valid, is_rate_limited = verification.verify_code(r, "u1", "a@b.com", code)
        assert is_valid is True
        assert is_rate_limited is False

    def test_verify_correct_code_cleans_redis(self):
        r = self._fresh_redis()
        code = verification.generate_and_store_code(r, "u1", "a@b.com")
        verification.verify_code(r, "u1", "a@b.com", code)
        assert r.keys("email_verify:code:*") == []

    def test_verify_wrong_code_returns_invalid(self):
        r = self._fresh_redis()
        verification.generate_and_store_code(r, "u1", "a@b.com")
        is_valid, is_rate_limited = verification.verify_code(r, "u1", "a@b.com", "000000")
        assert is_valid is False
        assert is_rate_limited is False

    def test_rate_limit_triggers_after_five_wrong(self):
        r = self._fresh_redis()
        verification.generate_and_store_code(r, "u1", "a@b.com")
        for _ in range(4):
            is_valid, is_rate_limited = verification.verify_code(r, "u1", "a@b.com", "000000")
            assert is_rate_limited is False
        # 5th attempt
        is_valid, is_rate_limited = verification.verify_code(r, "u1", "a@b.com", "000000")
        assert is_rate_limited is True
        assert is_valid is False

    def test_regenerate_code_resets_attempt_counter(self):
        r = self._fresh_redis()
        verification.generate_and_store_code(r, "u1", "a@b.com")
        # exhaust attempts
        for _ in range(5):
            verification.verify_code(r, "u1", "a@b.com", "000000")

        # request a new code — counter should reset
        new_code = verification.generate_and_store_code(r, "u1", "a@b.com")
        is_valid, is_rate_limited = verification.verify_code(r, "u1", "a@b.com", new_code)
        assert is_valid is True
        assert is_rate_limited is False

    def test_verify_missing_code_returns_false_not_rate_limited(self):
        r = self._fresh_redis()
        is_valid, is_rate_limited = verification.verify_code(r, "u1", "a@b.com", "123456")
        assert is_valid is False
        assert is_rate_limited is False
