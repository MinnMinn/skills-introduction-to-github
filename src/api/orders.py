"""
REST API endpoints for Orders.

Routes:
    POST /api/v1/orders  — create a new order (validated)

Follows the repository pattern: all DB access goes through OrdersRepository.
Validation is handled by Pydantic via OrderCreateRequest; FastAPI automatically
returns HTTP 422 with field-level error details on any validation failure.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.db.repos.orders_repo import OrdersRepository
from src.schemas import OrderCreateRequest, OrderResponse

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


# ---------------------------------------------------------------------------
# Dependency — allows tests to inject a custom repository instance
# ---------------------------------------------------------------------------

_default_repo = OrdersRepository()


def get_repo() -> OrdersRepository:
    return _default_repo


# ---------------------------------------------------------------------------
# POST /api/v1/orders
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new order",
    responses={
        201: {"description": "Order created successfully"},
        422: {"description": "Validation error in request body"},
    },
)
def create_order(
    payload: OrderCreateRequest,
    repo: OrdersRepository = Depends(get_repo),
) -> OrderResponse:
    """
    Create a new order after validating the request payload.

    Pydantic enforces:
      - **product_id**: valid UUID string
      - **quantity**: integer > 0
      - **price**: decimal >= 0.01

    Any violation causes FastAPI to return **422 Unprocessable Entity**
    with field-level error details before this handler is ever called.
    """
    order = repo.create_order(
        product_id=str(payload.product_id),
        quantity=payload.quantity,
        price=str(payload.price),
    )

    return OrderResponse(
        order_id=order.order_id,
        product_id=order.product_id,
        quantity=order.quantity,
        price=order.price,
        status=order.status,
        created_at=order.created_at,
    )
