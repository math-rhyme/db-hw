"""Load data into PostgreSQL database."""

import logging

from src.db.postgres_client import db
from src.utils.data_parser import DataParser

logger = logging.getLogger(__name__)


class RelationalLoader:
    def __init__(self):
        self.db = db
        self.parser = DataParser()

    def load_categories(self):
        """Load categories into PostgreSQL."""
        categories = self.parser.parse_categories()
        with self.db.get_cursor() as cursor:
            for _, row in categories.iterrows():
                cursor.execute(
                    """
                    INSERT INTO categories (id, name, description)
                    VALUES (%(id)s, %(name)s, %(description)s)
                    ON CONFLICT (id) DO NOTHING;
                    """,
                    row.to_dict(),
                )
        logger.info(f"Loaded {len(categories)} categories")
        print(f"Loaded {len(categories)} categories")

    def load_sellers(self):
        """Load sellers into PostgreSQL."""
        sellers = self.parser.parse_sellers()
        with self.db.get_cursor() as cursor:
            for _, row in sellers.iterrows():
                cursor.execute(
                    """
                    INSERT INTO sellers (id, name, specialty, rating, joined)
                    VALUES (%(id)s, %(name)s, %(specialty)s, %(rating)s, %(joined)s)
                    ON CONFLICT (id) DO NOTHING;
                    """,
                    {
                        "id": row["id"],
                        "name": row["name"],
                        "specialty": row["specialty"],
                        "rating": float(row["rating"]),
                        "joined": row["joined"].date(),
                    },
                )
        logger.info(f"Loaded {len(sellers)} sellers")
        print(f"Loaded {len(sellers)} sellers")

    def load_users(self):
        """Load users into PostgreSQL."""
        users = self.parser.parse_users()
        with self.db.get_cursor() as cursor:
            for _, row in users.iterrows():
                cursor.execute(
                    """
                    INSERT INTO users (id, name, email, join_date, location, interests)
                    VALUES (%(id)s, %(name)s, %(email)s, %(join_date)s, %(location)s, %(interests)s)
                    ON CONFLICT (id) DO NOTHING;
                    """,
                    {
                        "id": row["id"],
                        "name": row["name"],
                        "email": row["email"],
                        "join_date": row["join_date"].date(),
                        "location": row["location"],
                        "interests": row["interests"],
                    },
                )
        logger.info(f"Loaded {len(users)} users")
        print(f"Loaded {len(users)} users")

    def load_products(self):
        """Load products into PostgreSQL."""
        products = self.parser.parse_products()
        with self.db.get_cursor() as cursor:
            for _, row in products.iterrows():
                cursor.execute(
                    """
                    INSERT INTO products (id, name, category, price, seller_id, description, tags, stock)
                    VALUES (%(id)s, %(name)s, %(category)s, %(price)s, %(seller_id)s,
                            %(description)s, %(tags)s, %(stock)s)
                    ON CONFLICT (id) DO NOTHING;
                    """,
                    {
                        "id": row["id"],
                        "name": row["name"],
                        "category": row["category"],
                        "price": float(row["price"]),
                        "seller_id": row["seller_id"],
                        "description": row["description"],
                        "tags": row["tags"],
                        "stock": int(row["stock"]),
                    },
                )
        logger.info(f"Loaded {len(products)} products")
        print(f"Loaded {len(products)} products")

    def load_all(self):
        """Load all data into PostgreSQL."""
        print("Creating tables...")
        self.db.create_tables()

        print("Loading categories...")
        self.load_categories()

        print("Loading sellers...")
        self.load_sellers()

        print("Loading users...")
        self.load_users()

        print("Loading products...")
        self.load_products()

        print("Relational data loading complete!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    loader = RelationalLoader()
    loader.load_all()
