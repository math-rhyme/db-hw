"""
ArtisanMarket test suite.
"""

import json
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


@pytest.fixture
def sample_products() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": "P001",
                "name": "Hand-carved Wooden Bowl",
                "category": "Home & Kitchen",
                "price": 45.99,
                "seller_id": "S001",
                "description": "Beautiful acacia wood bowl.",
                "tags": ["wood", "handmade"],
                "stock": 15,
            },
            {
                "id": "P002",
                "name": "Ceramic Coffee Mug Set",
                "category": "Home & Kitchen",
                "price": 38.50,
                "seller_id": "S002",
                "description": "Set of 4 handmade ceramic mugs.",
                "tags": ["ceramic", "handmade"],
                "stock": 22,
            },
            {
                "id": "P003",
                "name": "Knitted Wool Scarf",
                "category": "Fashion",
                "price": 55.00,
                "seller_id": "S003",
                "description": "Soft merino wool scarf.",
                "tags": ["wool", "fashion"],
                "stock": 8,
            },
        ]
    )


@pytest.fixture
def sample_users() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": "U001",
                "name": "Emma Thompson",
                "email": "emma@email.com",
                "join_date": pd.Timestamp("2023-03-15"),
                "location": "Portland, OR",
                "interests": ["sustainable living", "home decor", "cooking"],
            },
            {
                "id": "U002",
                "name": "James Chen",
                "email": "james@email.com",
                "join_date": pd.Timestamp("2023-04-22"),
                "location": "Seattle, WA",
                "interests": ["woodworking", "crafts", "minimalism"],
            },
        ]
    )


class TestDataParser:
    def test_parse_products_columns(self, sample_products):
        """Products DataFrame has expected columns."""
        expected = {"id", "name", "category", "price", "seller_id", "description", "tags", "stock"}
        assert expected.issubset(set(sample_products.columns))

    def test_tags_are_lists(self, sample_products):
        """Tags field should be a list."""
        assert isinstance(sample_products.iloc[0]["tags"], list)

    def test_price_is_float(self, sample_products):
        """Price should be float."""
        assert isinstance(sample_products.iloc[0]["price"], float)

    def test_interests_are_lists(self, sample_users):
        """User interests should be lists."""
        assert isinstance(sample_users.iloc[0]["interests"], list)

    def test_join_date_is_timestamp(self, sample_users):
        """join_date should be a Timestamp."""
        assert isinstance(sample_users.iloc[0]["join_date"], pd.Timestamp)


class TestPurchaseGenerator:
    def test_interest_score_relevant(self, sample_products, sample_users):
        """A wood-interested user should score higher on wood products."""
        from src.utils.purchase_generator import PurchaseGenerator

        gen = PurchaseGenerator.__new__(PurchaseGenerator)
        gen.parser = MagicMock()
        gen.users = sample_users
        gen.products = sample_products

        user_interests = ["woodworking"]
        wood_score = gen._interest_score(user_interests, ["wood", "handmade"])
        ceramic_score = gen._interest_score(user_interests, ["ceramic", "handmade"])
        assert wood_score > ceramic_score

    def test_generate_purchases_returns_dataframe(self, sample_products, sample_users):
        """generate_purchases should return a non-empty DataFrame."""
        from src.utils.purchase_generator import PurchaseGenerator

        with patch.object(PurchaseGenerator, "__init__", lambda _: None):
            gen = PurchaseGenerator()
            gen.users = sample_users
            gen.products = sample_products

        purchases = gen.generate_purchases(num_purchases=10)
        assert isinstance(purchases, pd.DataFrame)
        assert len(purchases) > 0

    def test_purchase_dates_after_join(self, sample_products, sample_users):
        """All purchases should be on or after the user's join date."""
        from src.utils.purchase_generator import PurchaseGenerator

        with patch.object(PurchaseGenerator, "__init__", lambda _: None):
            gen = PurchaseGenerator()
            gen.users = sample_users
            gen.products = sample_products

        purchases = gen.generate_purchases(num_purchases=20)
        merged = purchases.merge(sample_users[["id", "join_date"]], left_on="user_id", right_on="id")
        merged["purchase_date"] = pd.to_datetime(merged["purchase_date"])
        merged["join_date"] = pd.to_datetime(merged["join_date"])
        assert (merged["purchase_date"] >= merged["join_date"]).all()

    def test_purchase_quantities_in_range(self, sample_products, sample_users):
        """Quantities should be between 1 and 3."""
        from src.utils.purchase_generator import PurchaseGenerator

        with patch.object(PurchaseGenerator, "__init__", lambda _: None):
            gen = PurchaseGenerator()
            gen.users = sample_users
            gen.products = sample_products

        purchases = gen.generate_purchases(num_purchases=30)
        assert purchases["quantity"].between(1, 3).all()

    def test_purchase_has_required_columns(self, sample_products, sample_users):
        """purchases DataFrame must have all required columns."""
        from src.utils.purchase_generator import PurchaseGenerator

        with patch.object(PurchaseGenerator, "__init__", lambda _: None):
            gen = PurchaseGenerator()
            gen.users = sample_users
            gen.products = sample_products

        purchases = gen.generate_purchases(num_purchases=5)
        required = {"purchase_id", "user_id", "product_id", "quantity", "unit_price", "purchase_date"}
        assert required.issubset(set(purchases.columns))


class TestRedisClient:
    def test_cart_add_and_get(self):
        """Cart add/get round-trip (mocked Redis)."""
        from src.db.redis_client import RedisClient

        mock_redis = MagicMock()
        mock_redis.hget.return_value = None
        mock_redis.hgetall.return_value = {"P001": b"2"}

        client = RedisClient.__new__(RedisClient)
        client.client = mock_redis

        client.add_to_cart("U001", "P001", 2)
        mock_redis.hset.assert_called_once_with("cart:U001", "P001", 2)

        cart = client.get_cart("U001")
        assert cart == {"P001": 2}

    def test_hot_products_tracking(self):
        """Hot products sorted set should receive increments."""
        from src.db.redis_client import RedisClient

        mock_redis = MagicMock()
        mock_redis.zrevrange.return_value = [("P001", 5.0), ("P002", 3.0)]

        client = RedisClient.__new__(RedisClient)
        client.client = mock_redis

        client.increment_product_views("P001", "2024-01-15")
        mock_redis.zincrby.assert_called_once_with("hot_products:2024-01-15", 1, "P001")

        results = client.get_hot_products("2024-01-15", limit=2)
        assert len(results) == 2
        assert results[0] == ("P001", 5.0)

    def test_json_cache_roundtrip(self):
        """set_json/get_json should round-trip correctly."""
        from src.db.redis_client import RedisClient

        data = {"id": "P001", "name": "Test"}
        encoded = json.dumps(data)

        mock_redis = MagicMock()
        mock_redis.get.return_value = encoded.encode()

        client = RedisClient.__new__(RedisClient)
        client.client = mock_redis

        client.set_json("product:P001", data)
        mock_redis.setex.assert_called_once()

        result = client.get_json("product:P001")
        assert result == data


class TestNeo4jClient:
    def _make_client(self):
        from src.db.neo4j_client import Neo4jClient

        client = Neo4jClient.__new__(Neo4jClient)
        client.driver = MagicMock()
        return client

    def test_merge_user(self):
        client = self._make_client()
        mock_session = MagicMock()
        client.driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        client.driver.session.return_value.__exit__ = MagicMock(return_value=False)
        client.merge_user("U001", "Emma Thompson", "2023-03-15")
        mock_session.run.assert_called_once()

    def test_add_purchase(self):
        client = self._make_client()
        mock_session = MagicMock()
        client.driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        client.driver.session.return_value.__exit__ = MagicMock(return_value=False)
        client.add_purchase("U001", "P001", 2, "2024-01-15")
        mock_session.run.assert_called_once()
        call_args = mock_session.run.call_args
        assert "PURCHASED" in call_args[0][0]

    def test_get_also_bought_returns_list(self):
        client = self._make_client()
        mock_result = [{"id": "P002", "name": "Mug", "price": 38.5, "category": "Home & Kitchen", "co_buyers": 3}]
        mock_session = MagicMock()
        mock_session.run.return_value = mock_result
        client.driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        client.driver.session.return_value.__exit__ = MagicMock(return_value=False)

        results = client.get_also_bought("P001")
        assert isinstance(results, list)


class TestCartService:
    def test_get_empty_cart(self):
        from src.services.cart_service import CartService

        with patch("src.services.cart_service.redis_client") as mock_redis:
            mock_redis.get_cart.return_value = {}
            svc = CartService()
            result = svc.get_cart("U001")
            assert result["total"] == 0.0
            assert result["items"] == []


class TestSearchService:
    """SearchService tests — sentence_transformers is optional in the test environment."""

    def _import_service(self):
        """Import SearchService with sentence_transformers mocked if unavailable."""
        st_mock = MagicMock()
        st_mock.SentenceTransformer = MagicMock
        with patch.dict("sys.modules", {"sentence_transformers": st_mock}):
            import importlib

            import src.services.search_service as mod

            importlib.reload(mod)
            return mod.SearchService

    def test_cache_hit_returned_directly(self):
        cached_data = [{"id": "P001", "name": "Bowl"}]

        with patch("src.db.redis_client.redis_client") as mock_redis:
            mock_redis.get_json.return_value = cached_data
            SearchService = self._import_service()
            svc = SearchService.__new__(SearchService)
            results = svc.search_products("bowl", use_cache=True)
            assert results == cached_data

    def test_search_no_cache(self):
        """search_products with use_cache=False should skip Redis lookup."""
        SearchService = self._import_service()

        with (
            patch("src.services.search_service.redis_client") as mock_redis,
            patch("src.services.search_service.db") as mock_db,
        ):
            mock_db.get_cursor.return_value.__enter__ = MagicMock(
                return_value=MagicMock(fetchall=MagicMock(return_value=[]))
            )
            mock_db.get_cursor.return_value.__exit__ = MagicMock(return_value=False)
            svc = SearchService.__new__(SearchService)
            svc.search_products("bowl", use_cache=False)
            mock_redis.get_json.assert_not_called()
