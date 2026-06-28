"""Load data into Neo4j graph database."""

import logging

from src.db.neo4j_client import neo4j_client
from src.utils.data_parser import DataParser

logger = logging.getLogger(__name__)

CATEGORY_ID_MAP = {
    "Home & Kitchen": "C001",
    "Fashion": "C002",
    "Jewelry": "C003",
    "Home Decor": "C004",
    "Stationery": "C005",
    "Beauty": "C006",
}


class GraphLoader:
    def __init__(self):
        self.client = neo4j_client
        self.parser = DataParser()

    def load_schema(self):
        """Create constraints and indexes."""
        self.client.create_constraints()

    def load_categories(self):
        """Load Category nodes."""
        categories = self.parser.parse_categories()
        for _, row in categories.iterrows():
            self.client.merge_category(row["id"], row["name"])
        print(f"Loaded {len(categories)} category nodes")

    def load_users(self):
        """Load User nodes."""
        users = self.parser.parse_users()
        for _, row in users.iterrows():
            self.client.merge_user(row["id"], row["name"], str(row["join_date"].date()))
        print(f"Loaded {len(users)} user nodes")

    def load_products(self):
        """Load Product nodes and BELONGS_TO relationships."""
        products = self.parser.parse_products()
        for _, row in products.iterrows():
            self.client.merge_product(row["id"], row["name"], row["category"], float(row["price"]))
            self.client.link_product_to_category(row["id"], row["category"])
        print(f"Loaded {len(products)} product nodes")

    def load_all(self):
        """Load all graph data."""
        print("Creating Neo4j constraints...")
        self.load_schema()

        print("Loading categories...")
        self.load_categories()

        print("Loading users...")
        self.load_users()

        print("Loading products...")
        self.load_products()

        print("Graph data loading complete!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    loader = GraphLoader()
    loader.load_all()
