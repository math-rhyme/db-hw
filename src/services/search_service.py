"""Product search service combining PostgreSQL full-text, Redis cache, and pgvector."""

import logging
from typing import Any

from sentence_transformers import SentenceTransformer

from src.db.postgres_client import db
from src.db.redis_client import redis_client

logger = logging.getLogger(__name__)


class SearchService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def search_products(
        self,
        query: str = "",
        category: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        limit: int = 20,
        use_cache: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Full-text search with optional category and price filters.
        Results are cached in Redis for 1 hour.
        """
        cache_key = f"search:{query}:{category}:{min_price}:{max_price}:{limit}"

        if use_cache:
            cached = redis_client.get_json(cache_key)
            if cached is not None:
                logger.debug(f"Cache HIT for '{cache_key}'")
                return cached

        conditions = []
        params: list[Any] = []

        if query:
            conditions.append(
                "to_tsvector('english', p.name || ' ' || COALESCE(p.description, '')) @@ plainto_tsquery('english', %s)"
            )
            params.append(query)

        if category:
            conditions.append("p.category = %s")
            params.append(category)

        if min_price is not None:
            conditions.append("p.price >= %s")
            params.append(min_price)

        if max_price is not None:
            conditions.append("p.price <= %s")
            params.append(max_price)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        sql = f"""
            SELECT p.id, p.name, p.category, p.price, p.seller_id,
                   p.description, p.tags, p.stock,
                   s.name AS seller_name, s.rating AS seller_rating
            FROM products p
            JOIN sellers s ON p.seller_id = s.id
            {where_clause}
            ORDER BY p.name
            LIMIT %s;
        """
        params.append(limit)

        with db.get_cursor() as cursor:
            cursor.execute(sql, params)
            results = [dict(r) for r in cursor.fetchall()]

        if use_cache:
            redis_client.set_json(cache_key, results)

        return results

    def semantic_search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search products using pgvector semantic similarity."""
        query_embedding = self.model.encode(query)

        with db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT p.id, p.name, p.category, p.price, p.description, p.tags,
                       1 - (pe.description_embedding <=> %s::vector) AS similarity
                FROM products p
                JOIN product_embeddings pe ON p.id = pe.product_id
                ORDER BY pe.description_embedding <=> %s::vector
                LIMIT %s;
                """,
                (query_embedding.tolist(), query_embedding.tolist(), limit),
            )
            return [dict(r) for r in cursor.fetchall()]


if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)
    svc = SearchService()
    print("___ Full-text search: 'wood' ___")
    results = svc.search_products("wood", limit=3)
    print(json.dumps(results, indent=2, default=str))
    print("\n___ Semantic search: 'handmade ceramic for kitchen' ___")
    results = svc.semantic_search("handmade ceramic for kitchen", limit=3)
    print(json.dumps(results, indent=2, default=str))
