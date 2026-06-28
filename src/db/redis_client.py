"""Redis connection and utilities."""

import json
import logging
from decimal import Decimal
from typing import Any

import redis

from src.config import CACHE_TTL, CART_TTL, REDIS_CONFIG

logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(self):
        self.client = redis.Redis(**REDIS_CONFIG)

    def ping(self) -> bool:
        """Check Redis connectivity."""
        try:
            return self.client.ping()
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False

    # json

    def get_json(self, key: str) -> Any | None:
        """Get JSON data from Redis."""
        data = self.client.get(key)
        return json.loads(data) if data else None

    def set_json(self, key: str, value: Any, ttl: int = CACHE_TTL) -> bool:
        """Set JSON data in Redis with TTL."""

        def _default(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

        return self.client.setex(key, ttl, json.dumps(value, default=_default))

    def delete(self, key: str) -> int:
        """Delete a key from Redis."""
        return self.client.delete(key)

    # cart

    def add_to_cart(self, user_id: str, product_id: str, quantity: int) -> None:
        """Add or update item quantity in the user's cart."""
        cart_key = f"cart:{user_id}"
        current = self.client.hget(cart_key, product_id)
        new_qty = (int(current) if current else 0) + quantity
        if new_qty <= 0:
            self.client.hdel(cart_key, product_id)
        else:
            self.client.hset(cart_key, product_id, new_qty)
        self.client.expire(cart_key, CART_TTL)

    def get_cart(self, user_id: str) -> dict[str, int]:
        """Return the full cart as {product_id: quantity}."""
        cart_key = f"cart:{user_id}"
        raw = self.client.hgetall(cart_key)
        return {k: int(v) for k, v in raw.items()}

    def remove_from_cart(self, user_id: str, product_id: str) -> None:
        """Remove an item entirely from the cart."""
        self.client.hdel(f"cart:{user_id}", product_id)

    def clear_cart(self, user_id: str) -> None:
        """Remove the entire cart."""
        self.client.delete(f"cart:{user_id}")

    # hot ptoducts

    def increment_product_views(self, product_id: str, date_str: str) -> None:
        """Record a view for hot-products tracking."""
        key = f"hot_products:{date_str}"
        self.client.zincrby(key, 1, product_id)
        self.client.expire(key, 60 * 60 * 24 * 7)

    def get_hot_products(self, date_str: str, limit: int = 10) -> list[tuple[str, float]]:
        """Return top-N products by view count for a given date."""
        key = f"hot_products:{date_str}"
        results = self.client.zrevrange(key, 0, limit - 1, withscores=True)
        return [(pid, score) for pid, score in results]


# Singleton instance
redis_client = RedisClient()
