"""Recommendation service using Neo4j graph queries and pgvector similarity."""

import logging
from typing import Any

from src.db.neo4j_client import neo4j_client
from src.db.redis_client import redis_client

logger = logging.getLogger(__name__)
REC_TTL = 1800


class RecommendationService:
    """Combines graph-based collaborative filtering with vector similarity."""

    def also_bought(self, product_id: str, limit: int = 5) -> list[dict[str, Any]]:
        """'Customers who bought this also bought' via Neo4j."""
        cache_key = f"rec:also_bought:{product_id}:{limit}"
        cached = redis_client.get_json(cache_key)
        if cached:
            return cached

        results = neo4j_client.get_also_bought(product_id, limit)
        redis_client.set_json(cache_key, results, ttl=REC_TTL)
        return results

    def frequently_bought_together(self, product_id: str, limit: int = 5) -> list[dict[str, Any]]:
        """Products most often bought together with this product."""
        cache_key = f"rec:fbt:{product_id}:{limit}"
        cached = redis_client.get_json(cache_key)
        if cached:
            return cached

        results = neo4j_client.get_frequently_bought_together(product_id, limit)
        redis_client.set_json(cache_key, results, ttl=REC_TTL)
        return results
