"""MongoDB connection and utilities."""

import logging

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.database import Database

from src.config import MONGO_CONFIG

logger = logging.getLogger(__name__)


class MongoDBClient:
    def __init__(self):
        self.client = MongoClient(MONGO_CONFIG["uri"])
        self.db: Database = self.client[MONGO_CONFIG["database"]]

    def get_collection(self, name: str):
        """Get a MongoDB collection."""
        return self.db[name]

    def create_indexes(self):
        """Create necessary indexes for all collections."""
        reviews = self.db["reviews"]
        reviews.create_index([("product_id", ASCENDING)])
        reviews.create_index([("user_id", ASCENDING)])
        reviews.create_index([("rating", DESCENDING)])
        reviews.create_index([("created_at", DESCENDING)])
        reviews.create_index([("product_id", ASCENDING), ("user_id", ASCENDING)], unique=True)

        product_specs = self.db["product_specs"]
        product_specs.create_index([("product_id", ASCENDING)], unique=True)
        product_specs.create_index([("category", ASCENDING)])

        seller_profiles = self.db["seller_profiles"]
        seller_profiles.create_index([("seller_id", ASCENDING)], unique=True)

        user_preferences = self.db["user_preferences"]
        user_preferences.create_index([("user_id", ASCENDING)], unique=True)
        user_preferences.create_index([("last_active", DESCENDING)])

        logger.info("MongoDB indexes created successfully")

    def ping(self) -> bool:
        """Check database connectivity."""
        try:
            self.client.admin.command("ping")
            return True
        except Exception as e:
            logger.error(f"MongoDB ping failed: {e}")
            return False


# Singleton instance
mongo_client = MongoDBClient()
