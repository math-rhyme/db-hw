"""PostgreSQL connection and utilities."""

import logging
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.config import POSTGRES_CONFIG

logger = logging.getLogger(__name__)
Base = declarative_base()


class PostgresConnection:
    def __init__(self):
        self.config = POSTGRES_CONFIG
        self._engine = None
        self._session_factory = None

    @property
    def engine(self):
        if not self._engine:
            db_url = (
                f"postgresql://{self.config['user']}:{self.config['password']}@"
                f"{self.config['host']}:{self.config['port']}/{self.config['database']}"
            )
            self._engine = create_engine(db_url, pool_size=5, max_overflow=10)
        return self._engine

    @property
    def session_factory(self):
        if not self._session_factory:
            self._session_factory = sessionmaker(bind=self.engine)
        return self._session_factory

    @contextmanager
    def get_cursor(self):
        """Get a database cursor for raw SQL queries."""
        conn = psycopg2.connect(**self.config)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                yield cursor
                conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    def create_tables(self):
        """Create all tables in the database."""
        with self.get_cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")

            # categories
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id VARCHAR(10) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    description TEXT
                );
            """)

            # sellers
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sellers (
                    id VARCHAR(10) PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    specialty VARCHAR(200),
                    rating DECIMAL(3,1) CHECK (rating >= 0 AND rating <= 5),
                    joined DATE NOT NULL
                );
            """)

            # users
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id VARCHAR(10) PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    email VARCHAR(200) NOT NULL UNIQUE,
                    join_date DATE NOT NULL,
                    location VARCHAR(200),
                    interests TEXT[]
                );
            """)

            # products
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id VARCHAR(10) PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    category VARCHAR(100) NOT NULL REFERENCES categories(name),
                    price DECIMAL(10,2) NOT NULL CHECK (price > 0),
                    seller_id VARCHAR(10) REFERENCES sellers(id),
                    description TEXT,
                    tags TEXT[],
                    stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # orders
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(10) NOT NULL REFERENCES users(id),
                    status VARCHAR(50) DEFAULT 'pending',
                    total_amount DECIMAL(10,2) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # order items
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS order_items (
                    id SERIAL PRIMARY KEY,
                    order_id INTEGER NOT NULL REFERENCES orders(id),
                    product_id VARCHAR(10) NOT NULL REFERENCES products(id),
                    quantity INTEGER NOT NULL CHECK (quantity > 0),
                    unit_price DECIMAL(10,2) NOT NULL
                );
            """)

            # product embeddings
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS product_embeddings (
                    product_id VARCHAR(10) PRIMARY KEY REFERENCES products(id),
                    description_embedding vector(384)
                );
            """)

            # indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_seller ON products(seller_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_price ON products(price);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_id);")

            # full-text search index
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_products_fts
                ON products USING GIN(to_tsvector('english', name || ' ' || COALESCE(description, '')));
            """)

            logger.info("All PostgreSQL tables and indexes created successfully")


# Singleton instance
db = PostgresConnection()
