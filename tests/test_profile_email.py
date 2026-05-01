"""Unit tests for POST /api/profile/email and POST /api/profile/email/confirm.

Covers:
- Happy path (initiate + confirm)
- Unauthenticated request → 401
- Malformed email → 400
- Same email as current → 400
- Wrong code → 401 with remaining-attempts count
- Rate limit after 5 wrong attempts → 429
- Expired / missing code → 401
- Old email still valid for login 30 days after change (audit trail)
- Successful confirm clears Redis keys
"""
import copy

import pytest

import app.models.user as user_module
from app.api.profile.email import _attempts_key, _verification_key
from app.core.config import settings
from app.core.security import create_access_token


# ── Helpers ────────────────────────────────────────────────────────────────

NEW_EMAIL = "newemail@example.com"


def _initiate(client, auth_headers, new_email=NEW_EMAIL):
    return client.post(
        "/api/profile/email",
        json={"new_email": new_email},
        headers=auth_headers,
    )


def _get_stored_code(fake_redis, user_id="u1", new_email=NEW_EMAIL) -> str | None:
    return fake_redis.get(_verification_key(user_id, new_email))


def _confirm(client, auth_headers, code, new_email=NEW_EMAIL):
    return client.post(
        "/api/profile/email/confirm",
        json={"new_email": new_email, "code": code},
        headers=auth_headers,
    )


# ══════════════════════════════════════════════════════════════════════════
# POST /api/profile/email — initiate
# ══════════════════════════════════════════════════════════════════════════

class TestInitiateEmailChange:

    def test_happy_path_returns_202(self, client, auth_headers, fake_redis):
        resp = _initiate(client, auth_headers)
        assert resp.status_code == 202
        assert "Verification code sent" in resp.json()["detail"]

    def test_code_stored_in_redis(self, client, auth_headers, fake_redis):
        _initiate(client, auth_headers)
        code = _get_stored_code(fake_redis)
        assert code is not None
        assert len(code) == 6
        assert code.isdigit()

    def test_unauthenticated_returns_401(self, client):
        resp = client.post("/api/profile/email", json={"new_email": NEW_EMAIL})
        assert resp.status_code == 401

    def test_invalid_bearer_token_returns_401(self, client):
        resp = client.post(
            "/api/profile/email",
            json={"new_email": NEW_EMAIL},
            headers={"Authorization": "Bearer not.a.real.token"},
        )
        assert resp.status_code == 401

    def test_malformed_email_returns_400(self, client, auth_headers):
        resp = client.post(
            "/api/profile/email",
            json={"new_email": "not-an-email"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "detail" in resp.json()

    def test_missing_new_email_field_returns_400(self, client, auth_headers):
        resp = client.post("/api/profile/email", json={}, headers=auth_headers)
        assert resp.status_code == 400

    def test_same_email_as_current_returns_400(self, client, auth_headers):
        resp = client.post(
            "/api/profile/email",
            json={"new_email": "user@example.com"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "differ" in resp.json()["detail"].lower()

    def test_initiate_resets_previous_attempt_counter(
        self, client, auth_headers, fake_redis
    ):
        # Simulate leftover attempt counter
        akey = _attempts_key("u1", NEW_EMAIL)
        fake_redis.set(akey, 3)

        _initiate(client, auth_headers)

        assert fake_redis.get(akey) is None


# ══════════════════════════════════════════════════════════════════════════
# POST /api/profile/email/confirm
# ══════════════════════════════════════════════════════════════════════════

class TestConfirmEmailChange:

    def test_happy_path_returns_200(self, client, auth_headers, fake_redis):
        _initiate(client, auth_headers)
        code = _get_stored_code(fake_redis)
        resp = _confirm(client, auth_headers, code)
        assert resp.status_code == 200
        assert "updated successfully" in resp.json()["detail"].lower()

    def test_email_updated_in_user_store(self, client, auth_headers, fake_redis):
        _initiate(client, auth_headers)
        code = _get_stored_code(fake_redis)
        _confirm(client, auth_headers, code)
        assert user_module._users["u1"]["email"] == NEW_EMAIL

    def test_redis_keys_cleared_after_success(self, client, auth_headers, fake_redis):
        _initiate(client, auth_headers)
        code = _get_stored_code(fake_redis)
        _confirm(client, auth_headers, code)

        assert _get_stored_code(fake_redis) is None
        assert fake_redis.get(_attempts_key("u1", NEW_EMAIL)) is None

    def test_unauthenticated_confirm_returns_401(self, client, auth_headers, fake_redis):
        _initiate(client, auth_headers)
        code = _get_stored_code(fake_redis)
        resp = client.post(
            "/api/profile/email/confirm",
            json={"new_email": NEW_EMAIL, "code": code},
        )
        assert resp.status_code == 401

    def test_wrong_code_returns_401(self, client, auth_headers, fake_redis):
        _initiate(client, auth_headers)
        resp = _confirm(client, auth_headers, "000000")
        assert resp.status_code == 401
        assert "Incorrect" in resp.json()["detail"]

    def test_wrong_code_decrements_remaining_attempts(
        self, client, auth_headers, fake_redis
    ):
        _initiate(client, auth_headers)
        resp = _confirm(client, auth_headers, "000000")
        assert resp.status_code == 401
        # 5 max − 1 used = 4 remaining
        assert "4 attempt(s) remaining" in resp.json()["detail"]

    def test_rate_limit_after_max_attempts(self, client, auth_headers, fake_redis):
        _initiate(client, auth_headers)
        for _ in range(settings.EMAIL_CHANGE_MAX_ATTEMPTS - 1):
            resp = _confirm(client, auth_headers, "000000")
            assert resp.status_code == 401

        # The 5th wrong attempt should trigger 429
        resp = _confirm(client, auth_headers, "000000")
        assert resp.status_code == 429
        assert "Too many failed attempts" in resp.json()["detail"]

    def test_already_rate_limited_returns_429_immediately(
        self, client, auth_headers, fake_redis
    ):
        """If the attempt counter is already at the limit, return 429 upfront."""
        _initiate(client, auth_headers)
        akey = _attempts_key("u1", NEW_EMAIL)
        fake_redis.set(akey, settings.EMAIL_CHANGE_MAX_ATTEMPTS)

        resp = _confirm(client, auth_headers, "123456")
        assert resp.status_code == 429

    def test_missing_or_expired_code_returns_401(self, client, auth_headers):
        # No initiate — no Redis key
        resp = _confirm(client, auth_headers, "123456")
        assert resp.status_code == 401
        assert "expired" in resp.json()["detail"].lower()

    def test_malformed_email_in_confirm_returns_400(self, client, auth_headers):
        resp = client.post(
            "/api/profile/email/confirm",
            json={"new_email": "bad-email", "code": "123456"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_non_digit_code_returns_400(self, client, auth_headers):
        resp = client.post(
            "/api/profile/email/confirm",
            json={"new_email": NEW_EMAIL, "code": "abc123"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_short_code_returns_400(self, client, auth_headers):
        resp = client.post(
            "/api/profile/email/confirm",
            json={"new_email": NEW_EMAIL, "code": "12345"},
            headers=auth_headers,
        )
        assert resp.status_code == 400


# ══════════════════════════════════════════════════════════════════════════
# Audit trail: old email still valid for login for 30 days
# ══════════════════════════════════════════════════════════════════════════

class TestAuditTrail:

    def test_old_email_retained_in_audit_log(self, client, auth_headers, fake_redis):
        old_email = user_module._users["u1"]["email"]
        _initiate(client, auth_headers)
        code = _get_stored_code(fake_redis)
        _confirm(client, auth_headers, code)

        audit = user_module._users["u1"]["email_audit"]
        assert len(audit) == 1
        assert audit[0]["old_email"] == old_email

    def test_old_email_valid_for_login_after_change(
        self, client, auth_headers, fake_redis
    ):
        from app.models.user import email_valid_for_login

        old_email = user_module._users["u1"]["email"]
        _initiate(client, auth_headers)
        code = _get_stored_code(fake_redis)
        _confirm(client, auth_headers, code)

        assert email_valid_for_login("u1", old_email) is True

    def test_new_email_valid_for_login_after_change(
        self, client, auth_headers, fake_redis
    ):
        from app.models.user import email_valid_for_login

        _initiate(client, auth_headers)
        code = _get_stored_code(fake_redis)
        _confirm(client, auth_headers, code)

        assert email_valid_for_login("u1", NEW_EMAIL) is True

    def test_expired_old_email_not_valid_for_login(self):
        """An audit entry past its expiry date must not allow login."""
        from datetime import datetime, timedelta, timezone

        from app.models.user import email_valid_for_login

        past = datetime.now(tz=timezone.utc) - timedelta(days=1)
        user_module._users["u1"]["email_audit"] = [
            {
                "old_email": "old@example.com",
                "changed_at": past - timedelta(days=30),
                "expires_at": past,
            }
        ]
        assert email_valid_for_login("u1", "old@example.com") is False


# ══════════════════════════════════════════════════════════════════════════
# Security helpers
# ══════════════════════════════════════════════════════════════════════════

class TestSecurityHelpers:

    def test_decode_invalid_token_returns_none(self):
        from app.core.security import decode_access_token

        assert decode_access_token("garbage") is None

    def test_decode_valid_token_returns_subject(self):
        from app.core.security import decode_access_token

        token = create_access_token("u1")
        assert decode_access_token(token) == "u1"

    def test_expired_token_returns_none(self):
        from datetime import timedelta

        from app.core.security import decode_access_token

        token = create_access_token("u1", expires_delta=timedelta(seconds=-1))
        assert decode_access_token(token) is None
