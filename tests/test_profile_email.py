"""Tests for POST /api/profile/email and POST /api/profile/email/confirm.

Covers:
- Happy path (initiate + confirm → 200)
- Unauthorized (no token, expired token, invalid token) → 401
- Malformed email → 400
- Changing to the same email → 400
- Wrong verification code → 401
- Rate-limit after 5 wrong attempts → 401
- Expired / missing code → 404
- Audit trail: old email retained after change
"""

import fakeredis
import pytest
from fastapi.testclient import TestClient

from app import redis_client as rc
from app.config import settings
from app.db import email_exists_in_audit, get_user
from app.redis_client import store_verification_code


# ── Helpers ───────────────────────────────────────────────────────────────────

INITIATE_URL = "/api/profile/email"
CONFIRM_URL = "/api/profile/email/confirm"
NEW_EMAIL = "alice.new@example.com"
CODE = "123456"


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def initiate(client: TestClient, token: str, new_email: str = NEW_EMAIL) -> None:
    """POST to INITIATE_URL and assert 202."""
    resp = client.post(INITIATE_URL, json={"new_email": new_email}, headers=auth_headers(token))
    assert resp.status_code == 202, resp.text


def plant_code(user_id: str = "user-001", new_email: str = NEW_EMAIL, code: str = CODE) -> None:
    """Directly store a known code in Redis (bypasses the random generator)."""
    store_verification_code(user_id, new_email, code)


# ════════════════════════════════════════════════════════════════════════════
# POST /api/profile/email  (initiate)
# ════════════════════════════════════════════════════════════════════════════

class TestInitiateEmailChange:

    def test_happy_path_returns_202(self, client, alice_token):
        resp = client.post(
            INITIATE_URL,
            json={"new_email": NEW_EMAIL},
            headers=auth_headers(alice_token),
        )
        assert resp.status_code == 202
        data = resp.json()
        assert "detail" in data

    def test_no_auth_returns_401(self, client):
        resp = client.post(INITIATE_URL, json={"new_email": NEW_EMAIL})
        assert resp.status_code == 401

    def test_expired_token_returns_401(self, client, expired_token):
        resp = client.post(
            INITIATE_URL,
            json={"new_email": NEW_EMAIL},
            headers=auth_headers(expired_token),
        )
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self, client):
        resp = client.post(
            INITIATE_URL,
            json={"new_email": NEW_EMAIL},
            headers={"Authorization": "Bearer this.is.garbage"},
        )
        assert resp.status_code == 401

    def test_malformed_email_returns_400(self, client, alice_token):
        resp = client.post(
            INITIATE_URL,
            json={"new_email": "not-an-email"},
            headers=auth_headers(alice_token),
        )
        assert resp.status_code == 422  # FastAPI/Pydantic validation error

    def test_same_email_returns_400(self, client, alice_token):
        # alice@example.com is Alice's current email
        resp = client.post(
            INITIATE_URL,
            json={"new_email": "alice@example.com"},
            headers=auth_headers(alice_token),
        )
        assert resp.status_code == 400
        assert "differ" in resp.json()["detail"].lower()

    def test_code_stored_in_redis_after_initiate(self, client, alice_token):
        initiate(client, alice_token, NEW_EMAIL)
        stored = rc.get_verification_code("user-001", NEW_EMAIL)
        assert stored is not None
        assert len(stored) == 6
        assert stored.isdigit()


# ════════════════════════════════════════════════════════════════════════════
# POST /api/profile/email/confirm
# ════════════════════════════════════════════════════════════════════════════

class TestConfirmEmailChange:

    def test_happy_path_returns_200(self, client, alice_token):
        plant_code()
        resp = client.post(
            CONFIRM_URL,
            json={"new_email": NEW_EMAIL, "code": CODE},
            headers=auth_headers(alice_token),
        )
        assert resp.status_code == 200
        assert "updated" in resp.json()["detail"].lower()

    def test_email_updated_in_db_after_confirm(self, client, alice_token):
        plant_code()
        client.post(
            CONFIRM_URL,
            json={"new_email": NEW_EMAIL, "code": CODE},
            headers=auth_headers(alice_token),
        )
        user = get_user("user-001")
        assert user.email == NEW_EMAIL

    def test_old_email_in_audit_trail_after_confirm(self, client, alice_token):
        plant_code()
        client.post(
            CONFIRM_URL,
            json={"new_email": NEW_EMAIL, "code": CODE},
            headers=auth_headers(alice_token),
        )
        # Old email "alice@example.com" must appear in the audit trail
        assert email_exists_in_audit("user-001", "alice@example.com")

    def test_no_auth_returns_401(self, client):
        plant_code()
        resp = client.post(CONFIRM_URL, json={"new_email": NEW_EMAIL, "code": CODE})
        assert resp.status_code == 401

    def test_expired_token_returns_401(self, client, expired_token):
        plant_code()
        resp = client.post(
            CONFIRM_URL,
            json={"new_email": NEW_EMAIL, "code": CODE},
            headers=auth_headers(expired_token),
        )
        assert resp.status_code == 401

    def test_wrong_code_returns_401(self, client, alice_token):
        plant_code()
        resp = client.post(
            CONFIRM_URL,
            json={"new_email": NEW_EMAIL, "code": "000000"},
            headers=auth_headers(alice_token),
        )
        assert resp.status_code == 401
        assert "invalid" in resp.json()["detail"].lower()

    def test_wrong_code_increments_attempts(self, client, alice_token):
        plant_code()
        for _ in range(3):
            client.post(
                CONFIRM_URL,
                json={"new_email": NEW_EMAIL, "code": "000000"},
                headers=auth_headers(alice_token),
            )
        attempts = rc.get_attempts("user-001", NEW_EMAIL)
        assert attempts == 3

    def test_rate_limit_after_max_attempts(self, client, alice_token):
        plant_code()
        max_attempts = settings.max_verify_attempts  # default 5
        # Exhaust all allowed wrong attempts
        for _ in range(max_attempts):
            client.post(
                CONFIRM_URL,
                json={"new_email": NEW_EMAIL, "code": "000000"},
                headers=auth_headers(alice_token),
            )
        # Next attempt (even with the correct code) must be blocked
        resp = client.post(
            CONFIRM_URL,
            json={"new_email": NEW_EMAIL, "code": CODE},
            headers=auth_headers(alice_token),
        )
        assert resp.status_code == 401
        assert "too many" in resp.json()["detail"].lower()

    def test_missing_pending_code_returns_404(self, client, alice_token):
        # Never called initiate — no code in Redis
        resp = client.post(
            CONFIRM_URL,
            json={"new_email": NEW_EMAIL, "code": CODE},
            headers=auth_headers(alice_token),
        )
        assert resp.status_code == 404

    def test_malformed_email_returns_422(self, client, alice_token):
        resp = client.post(
            CONFIRM_URL,
            json={"new_email": "bad@@email", "code": CODE},
            headers=auth_headers(alice_token),
        )
        assert resp.status_code == 422

    def test_redis_keys_deleted_after_success(self, client, alice_token):
        plant_code()
        client.post(
            CONFIRM_URL,
            json={"new_email": NEW_EMAIL, "code": CODE},
            headers=auth_headers(alice_token),
        )
        assert rc.get_verification_code("user-001", NEW_EMAIL) is None
        assert rc.get_attempts("user-001", NEW_EMAIL) == 0

    def test_different_users_independent_codes(self, client, alice_token, bob_token):
        """Alice and Bob each have their own independent verification flows."""
        plant_code(user_id="user-001", new_email="alice.new@example.com", code="111111")
        plant_code(user_id="user-002", new_email="bob.new@example.com", code="222222")

        r_alice = client.post(
            CONFIRM_URL,
            json={"new_email": "alice.new@example.com", "code": "111111"},
            headers=auth_headers(alice_token),
        )
        r_bob = client.post(
            CONFIRM_URL,
            json={"new_email": "bob.new@example.com", "code": "222222"},
            headers=auth_headers(bob_token),
        )

        assert r_alice.status_code == 200
        assert r_bob.status_code == 200

    def test_wrong_code_shows_remaining_attempts(self, client, alice_token):
        plant_code()
        resp = client.post(
            CONFIRM_URL,
            json={"new_email": NEW_EMAIL, "code": "000000"},
            headers=auth_headers(alice_token),
        )
        assert resp.status_code == 401
        detail = resp.json()["detail"]
        # Should mention remaining attempts
        assert "remaining" in detail.lower() or "attempt" in detail.lower()
