"""Shopping cart service backed by Redis."""

import logging
from typing import Any

from src.db.postgres_client import db
from src.db.redis_client import redis_client

logger = logging.getLogger(__name__)


class CartService:
    """Session-based shopping cart using Redis Hashes with 24-hour TTL."""

    def add_item(self, user_id: str, product_id: str, quantity: int = 1) -> dict[str, Any]:
        """Add or increase the quantity of an item in the cart."""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        with db.get_cursor() as cursor:
            cursor.execute("SELECT id, name, price, stock FROM products WHERE id = %s", (product_id,))
            product = cursor.fetchone()

        if not product:
            raise ValueError(f"Product {product_id} not found")

        redis_client.add_to_cart(user_id, product_id, quantity)
        logger.info(f"Added {quantity}x {product_id} to cart for user {user_id}")

        return {"product_id": product_id, "quantity": quantity, "unit_price": float(product["price"])}

    def remove_item(self, user_id: str, product_id: str) -> None:
        """Remove an item from the cart."""
        redis_client.remove_from_cart(user_id, product_id)

    def update_quantity(self, user_id: str, product_id: str, quantity: int) -> None:
        """Set absolute quantity. Pass 0 to remove."""
        cart = redis_client.get_cart(user_id)
        current = cart.get(product_id, 0)
        delta = quantity - current
        if delta != 0:
            redis_client.add_to_cart(user_id, product_id, delta)

    def get_cart(self, user_id: str) -> dict[str, Any]:
        """Return the cart with product details and totals."""
        raw = redis_client.get_cart(user_id)
        if not raw:
            return {"items": [], "total": 0.0, "item_count": 0}

        items = []
        total = 0.0

        with db.get_cursor() as cursor:
            for product_id, qty in raw.items():
                cursor.execute("SELECT id, name, price, stock FROM products WHERE id = %s", (product_id,))
                product = cursor.fetchone()
                if product:
                    line_total = float(product["price"]) * qty
                    total += line_total
                    items.append(
                        {
                            "product_id": product_id,
                            "name": product["name"],
                            "quantity": qty,
                            "unit_price": float(product["price"]),
                            "line_total": round(line_total, 2),
                            "in_stock": product["stock"] >= qty,
                        }
                    )

        return {
            "user_id": user_id,
            "items": items,
            "total": round(total, 2),
            "item_count": sum(i["quantity"] for i in items),
        }

    def clear_cart(self, user_id: str) -> None:
        """Remove the cart entirely."""
        redis_client.clear_cart(user_id)
