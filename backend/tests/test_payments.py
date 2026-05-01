"""
Unit and integration tests for the payments API.

Coverage:
  - POST /api/payments/create-intent — happy path, idempotency, validation
  - POST /api/payments/webhook — valid event, invalid signature, unhandled type
  - GET  /api/payments/{payment_id} — found, not found, wrong user
  - Rate-limit middleware
  - PaymentRecord.mask_customer_id
  - Webhook signature rejection
"""
import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import stripe

from app.models.payment import PaymentRecord, PaymentStatus


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_stripe_intent(
    intent_id: str = "pi_test_fake",
    status: str = "requires_payment_method",
    amount: int = 1000,
    currency: str = "usd",
    client_secret: str = "pi_test_fake_secret_fake",
) -> MagicMock:
    """Return a mock Stripe PaymentIntent."""
    intent = MagicMock()
    intent.id = intent_id
    intent.status = status
    intent.amount = amount
    intent.currency = currency
    intent.client_secret = client_secret
    intent.metadata = {}
    return intent


def _stripe_webhook_signature(payload: bytes, secret: str) -> str:
    """Compute a valid Stripe-Signature header value."""
    timestamp = str(int(time.time()))
    signed_payload = f"{timestamp}.{payload.decode()}"
    sig = hmac.new(secret.encode(), signed_payload.encode(), hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={sig}"


# ── Model tests ───────────────────────────────────────────────────────────────

class TestPaymentRecord:
    def test_mask_customer_id_long(self):
        assert PaymentRecord.mask_customer_id("cust_abc123") == "cust****"

    def test_mask_customer_id_short(self):
        assert PaymentRecord.mask_customer_id("ab") == "****"

    def test_mask_customer_id_exactly_four(self):
        assert PaymentRecord.mask_customer_id("abcd") == "abcd****"


# ── create-intent ─────────────────────────────────────────────────────────────

class TestCreatePaymentIntent:
    @patch("app.services.stripe_service.stripe.PaymentIntent.create")
    @patch("app.services.cloudwatch_service._put_log_event")
    def test_create_intent_success(
        self, mock_cw, mock_stripe_create, test_client, valid_create_intent_payload, user_headers
    ):
        mock_stripe_create.return_value = _make_stripe_intent()

        resp = test_client.post(
            "/api/payments/create-intent",
            json=valid_create_intent_payload,
            headers=user_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"
        assert data["client_secret"] == "pi_test_fake_secret_fake"
        assert data["idempotent"] is False
        assert data["amount"] == 1000
        mock_stripe_create.assert_called_once()

    @patch("app.services.stripe_service.stripe.PaymentIntent.create")
    @patch("app.services.stripe_service.stripe.PaymentIntent.retrieve")
    @patch("app.services.cloudwatch_service._put_log_event")
    def test_idempotency_returns_existing(
        self,
        mock_cw,
        mock_retrieve,
        mock_create,
        test_client,
        valid_create_intent_payload,
        user_headers,
    ):
        """Second request with same idempotency_key returns the original intent."""
        intent = _make_stripe_intent()
        mock_create.return_value = intent
        mock_retrieve.return_value = intent

        # First request
        resp1 = test_client.post(
            "/api/payments/create-intent",
            json=valid_create_intent_payload,
            headers=user_headers,
        )
        assert resp1.status_code == 201
        assert resp1.json()["idempotent"] is False

        # Second request — same idempotency_key
        resp2 = test_client.post(
            "/api/payments/create-intent",
            json=valid_create_intent_payload,
            headers=user_headers,
        )
        assert resp2.status_code == 201
        assert resp2.json()["idempotent"] is True
        # Stripe create must only have been called once
        assert mock_create.call_count == 1

    def test_create_intent_unauthenticated(self, test_client, valid_create_intent_payload):
        resp = test_client.post("/api/payments/create-intent", json=valid_create_intent_payload)
        assert resp.status_code == 401

    def test_create_intent_zero_amount_rejected(self, test_client, user_headers):
        resp = test_client.post(
            "/api/payments/create-intent",
            json={
                "amount": 0,
                "currency": "USD",
                "customer_id": "cust_abc",
                "idempotency_key": str(uuid.uuid4()),
            },
            headers=user_headers,
        )
        assert resp.status_code == 422

    def test_create_intent_raw_card_data_rejected(self, test_client, user_headers):
        resp = test_client.post(
            "/api/payments/create-intent",
            json={
                "amount": 500,
                "currency": "USD",
                "customer_id": "cust_abc",
                "idempotency_key": str(uuid.uuid4()),
                "metadata": {"card_number": "4111111111111111"},
            },
            headers=user_headers,
        )
        assert resp.status_code == 422

    @patch("app.services.stripe_service.stripe.PaymentIntent.create")
    @patch("app.services.cloudwatch_service._put_log_event")
    def test_stripe_error_returns_502(
        self, mock_cw, mock_create, test_client, valid_create_intent_payload, user_headers
    ):
        mock_create.side_effect = stripe.error.CardError(
            message="Your card was declined.",
            param="card",
            code="card_declined",
        )
        resp = test_client.post(
            "/api/payments/create-intent",
            json=valid_create_intent_payload,
            headers=user_headers,
        )
        assert resp.status_code == 502


# ── Webhook ───────────────────────────────────────────────────────────────────

class TestWebhook:
    def _build_event(self, event_type: str, intent_id: str) -> dict:
        return {
            "id": "evt_test",
            "type": event_type,
            "data": {
                "object": {
                    "id": intent_id,
                    "amount": 1000,
                    "currency": "usd",
                    "status": "succeeded",
                }
            },
        }

    def test_invalid_signature_returns_401(self, test_client):
        resp = test_client.post(
            "/api/payments/webhook",
            content=b'{"type":"payment_intent.succeeded"}',
            headers={
                "Content-Type": "application/json",
                "Stripe-Signature": "t=0,v1=badsig",
            },
        )
        assert resp.status_code == 401

    @patch("app.services.stripe_service.stripe.Webhook.construct_event")
    @patch("app.services.cloudwatch_service._put_log_event")
    def test_webhook_no_matching_record(self, mock_cw, mock_construct, test_client):
        """Webhook for unknown intent_id returns processed=False, not 500."""
        mock_construct.return_value = self._build_event(
            "payment_intent.succeeded", "pi_unknown"
        )
        resp = test_client.post(
            "/api/payments/webhook",
            content=b"{}",
            headers={
                "Content-Type": "application/json",
                "Stripe-Signature": "t=1,v1=valid",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["processed"] is False

    @patch("app.services.stripe_service.stripe.PaymentIntent.create")
    @patch("app.services.stripe_service.stripe.Webhook.construct_event")
    @patch("app.services.cloudwatch_service._put_log_event")
    def test_webhook_updates_status_to_succeeded(
        self, mock_cw, mock_construct, mock_stripe_create, test_client, user_headers
    ):
        """Full flow: create payment → webhook succeeded → status updated."""
        intent_id = "pi_test_e2e"
        intent = _make_stripe_intent(intent_id=intent_id)
        mock_stripe_create.return_value = intent

        # Create the payment
        create_resp = test_client.post(
            "/api/payments/create-intent",
            json={
                "amount": 1000,
                "currency": "USD",
                "customer_id": "cust_e2e",
                "idempotency_key": str(uuid.uuid4()),
                "payment_method_id": "pm_test",
            },
            headers=user_headers,
        )
        assert create_resp.status_code == 201
        payment_id = create_resp.json()["payment_id"]

        # Simulate webhook
        mock_construct.return_value = self._build_event(
            "payment_intent.succeeded", intent_id
        )
        wh_resp = test_client.post(
            "/api/payments/webhook",
            content=b"{}",
            headers={
                "Content-Type": "application/json",
                "Stripe-Signature": "t=1,v1=valid",
            },
        )
        assert wh_resp.status_code == 200
        wh_data = wh_resp.json()
        assert wh_data["processed"] is True
        assert wh_data["payment_id"] == payment_id

        # Verify status updated
        status_resp = test_client.get(
            f"/api/payments/{payment_id}",
            headers=user_headers,
        )
        assert status_resp.status_code == 200
        assert status_resp.json()["status"] == "succeeded"

    @patch("app.services.stripe_service.stripe.Webhook.construct_event")
    @patch("app.services.cloudwatch_service._put_log_event")
    def test_unhandled_event_type(self, mock_cw, mock_construct, test_client):
        event = {"id": "evt_test", "type": "customer.created", "data": {"object": {}}}
        mock_construct.return_value = event
        resp = test_client.post(
            "/api/payments/webhook",
            content=b"{}",
            headers={
                "Content-Type": "application/json",
                "Stripe-Signature": "t=1,v1=valid",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["processed"] is False


# ── GET /{payment_id} ─────────────────────────────────────────────────────────

class TestGetPaymentStatus:
    @patch("app.services.stripe_service.stripe.PaymentIntent.create")
    @patch("app.services.cloudwatch_service._put_log_event")
    def test_get_payment_success(
        self, mock_cw, mock_create, test_client, user_headers
    ):
        mock_create.return_value = _make_stripe_intent()
        create_resp = test_client.post(
            "/api/payments/create-intent",
            json={
                "amount": 500,
                "currency": "EUR",
                "customer_id": "cust_xyz",
                "idempotency_key": str(uuid.uuid4()),
            },
            headers=user_headers,
        )
        payment_id = create_resp.json()["payment_id"]

        resp = test_client.get(f"/api/payments/{payment_id}", headers=user_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["payment_id"] == payment_id
        assert data["amount"] == 500
        assert "card_number" not in json.dumps(data)

    @patch("app.services.cloudwatch_service._put_log_event")
    def test_get_payment_not_found(self, mock_cw, test_client, user_headers):
        resp = test_client.get(f"/api/payments/{uuid.uuid4()}", headers=user_headers)
        assert resp.status_code == 404

    @patch("app.services.stripe_service.stripe.PaymentIntent.create")
    @patch("app.services.cloudwatch_service._put_log_event")
    def test_get_payment_wrong_user_returns_404(
        self, mock_cw, mock_create, test_client
    ):
        """User B cannot see User A's payment — 404 not 403 (no leaking existence)."""
        mock_create.return_value = _make_stripe_intent()
        create_resp = test_client.post(
            "/api/payments/create-intent",
            json={
                "amount": 700,
                "currency": "GBP",
                "customer_id": "cust_user_a",
                "idempotency_key": str(uuid.uuid4()),
            },
            headers={"X-User-ID": "user_a"},
        )
        payment_id = create_resp.json()["payment_id"]

        resp = test_client.get(
            f"/api/payments/{payment_id}",
            headers={"X-User-ID": "user_b"},  # different user
        )
        assert resp.status_code == 404


# ── Rate limit ────────────────────────────────────────────────────────────────

class TestRateLimit:
    @patch("app.services.stripe_service.stripe.PaymentIntent.create")
    @patch("app.services.cloudwatch_service._put_log_event")
    def test_rate_limit_enforced(self, mock_cw, mock_create, test_client):
        """11th request within the window should return 429."""
        mock_create.return_value = _make_stripe_intent()

        # Reset in-memory bucket for this test user
        from app.middleware.rate_limit import _request_log
        _request_log.clear()

        headers = {"X-User-ID": "user_rate_test"}
        for i in range(10):
            resp = test_client.post(
                "/api/payments/create-intent",
                json={
                    "amount": 100,
                    "currency": "USD",
                    "customer_id": "cust_rate",
                    "idempotency_key": str(uuid.uuid4()),
                },
                headers=headers,
            )
            # All 10 should succeed (or 502 from Stripe — either way not 429)
            assert resp.status_code != 429

        # 11th request must be rate-limited
        resp = test_client.post(
            "/api/payments/create-intent",
            json={
                "amount": 100,
                "currency": "USD",
                "customer_id": "cust_rate",
                "idempotency_key": str(uuid.uuid4()),
            },
            headers=headers,
        )
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers
