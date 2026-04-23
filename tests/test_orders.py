"""
Tests for POST /api/v1/orders

Coverage:
  - Happy path: valid payload                         → 201 with correct response shape
  - Happy path: minimum valid values (qty=1, price=0.01)
  - Happy path: large quantity and price
  - Validation: missing product_id                   → 422
  - Validation: missing quantity                     → 422
  - Validation: missing price                        → 422
  - Validation: quantity = 0                         → 422
  - Validation: negative quantity                    → 422
  - Validation: price = 0.00 (below minimum)         → 422
  - Validation: negative price                       → 422
  - Validation: product_id not a valid UUID          → 422
  - Validation: product_id is an integer             → 422
  - Validation: 422 response contains field-level details
  - Repository unit tests (isolated, no HTTP layer)
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from src.api.orders import get_repo
from src.db.models import Order
from src.db.repos.orders_repo import OrdersRepository
from src.main import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_PRODUCT_ID = str(uuid.uuid4())
VALID_PAYLOAD = {
    "product_id": VALID_PRODUCT_ID,
    "quantity": 3,
    "price": "9.99",
}


@pytest.fixture()
def repo() -> OrdersRepository:
    """Fresh repository for each test."""
    r = OrdersRepository()
    r._clear()
    return r


@pytest.fixture()
def client(repo: OrdersRepository) -> TestClient:
    """TestClient with the repo dependency overridden."""
    app.dependency_overrides[get_repo] = lambda: repo
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST — happy path
# ---------------------------------------------------------------------------


class TestCreateOrderHappyPath:
    def test_returns_201_for_valid_payload(self, client: TestClient) -> None:
        response = client.post("/api/v1/orders", json=VALID_PAYLOAD)

        assert response.status_code == 201

    def test_response_contains_all_expected_keys(self, client: TestClient) -> None:
        response = client.post("/api/v1/orders", json=VALID_PAYLOAD)

        body = response.json()
        expected_keys = {"order_id", "product_id", "quantity", "price", "status", "created_at"}
        assert expected_keys == set(body.keys())

    def test_response_reflects_submitted_values(self, client: TestClient) -> None:
        response = client.post("/api/v1/orders", json=VALID_PAYLOAD)

        body = response.json()
        assert body["product_id"] == VALID_PRODUCT_ID
        assert body["quantity"] == 3
        # Price is stored/returned as a string; numeric value must match
        assert float(body["price"]) == pytest.approx(9.99)

    def test_response_order_id_is_a_valid_uuid(self, client: TestClient) -> None:
        response = client.post("/api/v1/orders", json=VALID_PAYLOAD)

        order_id = response.json()["order_id"]
        # Should not raise
        uuid.UUID(order_id)

    def test_response_status_is_pending(self, client: TestClient) -> None:
        response = client.post("/api/v1/orders", json=VALID_PAYLOAD)

        assert response.json()["status"] == "pending"

    def test_response_created_at_is_non_empty_string(self, client: TestClient) -> None:
        response = client.post("/api/v1/orders", json=VALID_PAYLOAD)

        created_at = response.json()["created_at"]
        assert isinstance(created_at, str) and len(created_at) > 0

    def test_minimum_valid_quantity_and_price(self, client: TestClient) -> None:
        """quantity=1 and price=0.01 are the lowest allowed values."""
        payload = {
            "product_id": str(uuid.uuid4()),
            "quantity": 1,
            "price": "0.01",
        }
        response = client.post("/api/v1/orders", json=payload)

        assert response.status_code == 201
        body = response.json()
        assert body["quantity"] == 1
        assert float(body["price"]) == pytest.approx(0.01)

    def test_large_quantity_and_price_accepted(self, client: TestClient) -> None:
        payload = {
            "product_id": str(uuid.uuid4()),
            "quantity": 1_000_000,
            "price": "99999.99",
        }
        response = client.post("/api/v1/orders", json=payload)

        assert response.status_code == 201


# ---------------------------------------------------------------------------
# POST — missing required fields → 422
# ---------------------------------------------------------------------------


class TestCreateOrderMissingFields:
    def test_missing_product_id_returns_422(self, client: TestClient) -> None:
        payload = {"quantity": 2, "price": "5.00"}
        response = client.post("/api/v1/orders", json=payload)

        assert response.status_code == 422

    def test_missing_quantity_returns_422(self, client: TestClient) -> None:
        payload = {"product_id": str(uuid.uuid4()), "price": "5.00"}
        response = client.post("/api/v1/orders", json=payload)

        assert response.status_code == 422

    def test_missing_price_returns_422(self, client: TestClient) -> None:
        payload = {"product_id": str(uuid.uuid4()), "quantity": 2}
        response = client.post("/api/v1/orders", json=payload)

        assert response.status_code == 422

    def test_empty_body_returns_422(self, client: TestClient) -> None:
        response = client.post("/api/v1/orders", json={})

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST — invalid quantity → 422
# ---------------------------------------------------------------------------


class TestCreateOrderInvalidQuantity:
    def test_quantity_zero_returns_422(self, client: TestClient) -> None:
        payload = {**VALID_PAYLOAD, "quantity": 0}
        response = client.post("/api/v1/orders", json=payload)

        assert response.status_code == 422

    def test_negative_quantity_returns_422(self, client: TestClient) -> None:
        payload = {**VALID_PAYLOAD, "quantity": -1}
        response = client.post("/api/v1/orders", json=payload)

        assert response.status_code == 422

    def test_large_negative_quantity_returns_422(self, client: TestClient) -> None:
        payload = {**VALID_PAYLOAD, "quantity": -9999}
        response = client.post("/api/v1/orders", json=payload)

        assert response.status_code == 422

    def test_float_quantity_returns_422(self, client: TestClient) -> None:
        """quantity must be an integer."""
        payload = {**VALID_PAYLOAD, "quantity": 1.5}
        response = client.post("/api/v1/orders", json=payload)

        assert response.status_code == 422

    def test_string_quantity_returns_422(self, client: TestClient) -> None:
        payload = {**VALID_PAYLOAD, "quantity": "two"}
        response = client.post("/api/v1/orders", json=payload)

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST — invalid price → 422
# ---------------------------------------------------------------------------


class TestCreateOrderInvalidPrice:
    def test_price_zero_returns_422(self, client: TestClient) -> None:
        payload = {**VALID_PAYLOAD, "price": "0.00"}
        response = client.post("/api/v1/orders", json=payload)

        assert response.status_code == 422

    def test_price_below_minimum_returns_422(self, client: TestClient) -> None:
        """0.009 is just below the 0.01 floor."""
        payload = {**VALID_PAYLOAD, "price": "0.009"}
        response = client.post("/api/v1/orders", json=payload)

        assert response.status_code == 422

    def test_negative_price_returns_422(self, client: TestClient) -> None:
        payload = {**VALID_PAYLOAD, "price": "-1.00"}
        response = client.post("/api/v1/orders", json=payload)

        assert response.status_code == 422

    def test_string_price_returns_422(self, client: TestClient) -> None:
        payload = {**VALID_PAYLOAD, "price": "free"}
        response = client.post("/api/v1/orders", json=payload)

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST — invalid product_id → 422
# ---------------------------------------------------------------------------


class TestCreateOrderInvalidProductId:
    def test_non_uuid_string_returns_422(self, client: TestClient) -> None:
        payload = {**VALID_PAYLOAD, "product_id": "not-a-uuid"}
        response = client.post("/api/v1/orders", json=payload)

        assert response.status_code == 422

    def test_integer_product_id_returns_422(self, client: TestClient) -> None:
        payload = {**VALID_PAYLOAD, "product_id": 12345}
        response = client.post("/api/v1/orders", json=payload)

        assert response.status_code == 422

    def test_empty_string_product_id_returns_422(self, client: TestClient) -> None:
        payload = {**VALID_PAYLOAD, "product_id": ""}
        response = client.post("/api/v1/orders", json=payload)

        assert response.status_code == 422

    def test_partial_uuid_returns_422(self, client: TestClient) -> None:
        payload = {**VALID_PAYLOAD, "product_id": "12345678-1234-1234"}
        response = client.post("/api/v1/orders", json=payload)

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST — 422 response structure contains field-level details
# ---------------------------------------------------------------------------


class TestCreateOrderValidationErrorShape:
    def test_422_body_contains_detail_key(self, client: TestClient) -> None:
        payload = {**VALID_PAYLOAD, "quantity": -1}
        response = client.post("/api/v1/orders", json=payload)

        assert response.status_code == 422
        assert "detail" in response.json()

    def test_422_detail_is_a_list(self, client: TestClient) -> None:
        payload = {**VALID_PAYLOAD, "quantity": 0}
        response = client.post("/api/v1/orders", json=payload)

        detail = response.json()["detail"]
        assert isinstance(detail, list)

    def test_422_detail_identifies_quantity_field(self, client: TestClient) -> None:
        payload = {**VALID_PAYLOAD, "quantity": -5}
        response = client.post("/api/v1/orders", json=payload)

        detail = response.json()["detail"]
        fields_mentioned = [
            str(err.get("loc", "")) for err in detail
        ]
        assert any("quantity" in loc for loc in fields_mentioned)

    def test_422_detail_identifies_price_field(self, client: TestClient) -> None:
        payload = {**VALID_PAYLOAD, "price": "0.00"}
        response = client.post("/api/v1/orders", json=payload)

        detail = response.json()["detail"]
        fields_mentioned = [str(err.get("loc", "")) for err in detail]
        assert any("price" in loc for loc in fields_mentioned)

    def test_422_detail_identifies_product_id_field(self, client: TestClient) -> None:
        payload = {**VALID_PAYLOAD, "product_id": "bad-uuid"}
        response = client.post("/api/v1/orders", json=payload)

        detail = response.json()["detail"]
        fields_mentioned = [str(err.get("loc", "")) for err in detail]
        assert any("product_id" in loc for loc in fields_mentioned)


# ---------------------------------------------------------------------------
# Repository unit tests (isolated, no HTTP layer)
# ---------------------------------------------------------------------------


class TestOrdersRepository:
    def test_get_returns_none_for_missing_order(self) -> None:
        repo = OrdersRepository()
        repo._clear()
        assert repo.get("nonexistent-id") is None

    def test_create_order_returns_order_with_correct_fields(self) -> None:
        repo = OrdersRepository()
        repo._clear()
        product_id = str(uuid.uuid4())

        order = repo.create_order(
            product_id=product_id,
            quantity=5,
            price="12.50",
        )

        assert order.product_id == product_id
        assert order.quantity == 5
        assert order.price == "12.50"
        assert order.status == "pending"

    def test_create_order_generates_unique_order_ids(self) -> None:
        repo = OrdersRepository()
        repo._clear()
        product_id = str(uuid.uuid4())

        order_a = repo.create_order(product_id=product_id, quantity=1, price="1.00")
        order_b = repo.create_order(product_id=product_id, quantity=1, price="1.00")

        assert order_a.order_id != order_b.order_id

    def test_create_order_persists_to_store(self) -> None:
        repo = OrdersRepository()
        repo._clear()

        order = repo.create_order(
            product_id=str(uuid.uuid4()),
            quantity=2,
            price="3.00",
        )

        assert repo.get(order.order_id) is order

    def test_seed_and_get_roundtrip(self) -> None:
        repo = OrdersRepository()
        repo._clear()
        order = Order(
            order_id=str(uuid.uuid4()),
            product_id=str(uuid.uuid4()),
            quantity=10,
            price="5.99",
        )
        repo._seed(order)

        assert repo.get(order.order_id) is order

    def test_clear_removes_all_records(self) -> None:
        repo = OrdersRepository()
        repo._seed(
            Order(
                order_id=str(uuid.uuid4()),
                product_id=str(uuid.uuid4()),
                quantity=1,
                price="1.00",
            )
        )
        repo._clear()

        assert len(repo._store) == 0
