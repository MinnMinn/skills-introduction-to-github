"""
Repository layer for the `orders` table.

Isolates all data-access logic so the API layer stays thin.
Uses an in-memory store by default; swap `_store` for a real DB session
in production without changing any API code.
"""

from __future__ import annotations

import uuid
from typing import Dict, Optional

from src.db.models import Order


class OrdersRepository:
    """
    CRUD operations against `orders`.

    The `_store` class variable acts as the persistence layer during tests
    and local development.  In production this class would be instantiated
    with a real DB session/connection.
    """

    # In-memory backing store keyed by order_id.
    # Replace with a real DB dependency (e.g. SQLAlchemy session) for production.
    _store: Dict[str, Order] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, order_id: str) -> Optional[Order]:
        """Return the Order for *order_id*, or None if not found."""
        return self._store.get(order_id)

    def create_order(self, product_id: str, quantity: int, price: str) -> Order:
        """
        Persist a new order and return the created record.

        Parameters
        ----------
        product_id : str
            UUID string identifying the product.
        quantity : int
            Number of units ordered (caller must ensure > 0).
        price : str
            Unit price as a decimal string (caller must ensure >= 0.01).

        Returns
        -------
        Order
            The newly created order record.
        """
        order_id = str(uuid.uuid4())
        order = Order(
            order_id=order_id,
            product_id=product_id,
            quantity=quantity,
            price=price,
        )
        self._store[order_id] = order
        return order

    # ------------------------------------------------------------------
    # Test / seed helpers (not part of the production interface)
    # ------------------------------------------------------------------

    def _seed(self, order: Order) -> None:
        """Insert or overwrite a record — used by tests only."""
        self._store[order.order_id] = order

    def _clear(self) -> None:
        """Remove all records — used by tests only."""
        self._store.clear()
