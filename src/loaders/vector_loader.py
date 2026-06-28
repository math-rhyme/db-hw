"""Load vector embeddings into pgvector."""

import logging

import numpy as np
from sentence_transformers import SentenceTransformer

from src.db.postgres_client import db
from src.utils.data_parser import DataParser

logger = logging.getLogger(__name__)


class VectorLoader:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.parser = DataParser()

    def generate_and_store_embeddings(self):
        """Generate embeddings for all products and store in pgvector."""
        products = self.parser.parse_products()
        count = 0

        for _, product in products.iterrows():
            text = f"{product['name']} {product['description']} {' '.join(product['tags'])}"
            embedding = self.model.encode(text)
            self._store_embedding(product["id"], embedding)
            count += 1

        logger.info(f"Generated and stored {count} embeddings")
        print(f"Generated and stored {count} embeddings")

    def _store_embedding(self, product_id: str, embedding: np.ndarray):
        """Store embedding in pgvector."""
        with db.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO product_embeddings (product_id, description_embedding)
                VALUES (%s, %s)
                ON CONFLICT (product_id) DO UPDATE
                SET description_embedding = EXCLUDED.description_embedding;
                """,
                (product_id, embedding.tolist()),
            )

    def load_all(self):
        """Run the full vector embedding pipeline."""
        print("Generating and storing product embeddings...")
        self.generate_and_store_embeddings()
        print("Vector loading complete!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    loader = VectorLoader()
    loader.load_all()
