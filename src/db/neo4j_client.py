"""Neo4j connection and utilities."""

import logging
from typing import Any

from neo4j import GraphDatabase

from src.config import NEO4J_CONFIG

logger = logging.getLogger(__name__)


class Neo4jClient:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_CONFIG["uri"],
            auth=(NEO4J_CONFIG["user"], NEO4J_CONFIG["password"]),
        )

    def close(self):
        self.driver.close()

    def ping(self) -> bool:
        """Check Neo4j connectivity."""
        try:
            with self.driver.session() as session:
                session.run("RETURN 1")
            return True
        except Exception as e:
            logger.error(f"Neo4j ping failed: {e}")
            return False

    def create_constraints(self):
        """Create uniqueness constraints and indexes."""
        with self.driver.session() as session:
            session.run("CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE")
            session.run("CREATE CONSTRAINT product_id IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE")
            session.run("CREATE CONSTRAINT category_id IF NOT EXISTS FOR (c:Category) REQUIRE c.id IS UNIQUE")
        logger.info("Neo4j constraints created")

    def merge_user(self, user_id: str, name: str, join_date: str):
        """Upsert a User node."""
        with self.driver.session() as session:
            session.run(
                "MERGE (u:User {id: $id}) SET u.name = $name, u.join_date = $join_date",
                id=user_id,
                name=name,
                join_date=join_date,
            )

    def merge_product(self, product_id: str, name: str, category: str, price: float):
        """Upsert a Product node."""
        with self.driver.session() as session:
            session.run(
                "MERGE (p:Product {id: $id}) SET p.name = $name, p.category = $category, p.price = $price",
                id=product_id,
                name=name,
                category=category,
                price=price,
            )

    def merge_category(self, category_id: str, name: str):
        """Upsert a Category node."""
        with self.driver.session() as session:
            session.run(
                "MERGE (c:Category {id: $id}) SET c.name = $name",
                id=category_id,
                name=name,
            )

    def link_product_to_category(self, product_id: str, category_name: str):
        """Create BELONGS_TO relationship."""
        with self.driver.session() as session:
            session.run(
                """
                MATCH (p:Product {id: $pid})
                MATCH (c:Category {name: $cat})
                MERGE (p)-[:BELONGS_TO]->(c)
                """,
                pid=product_id,
                cat=category_name,
            )

    def add_purchase(self, user_id: str, product_id: str, quantity: int, date: str):
        """Create or update a PURCHASED relationship."""
        with self.driver.session() as session:
            session.run(
                """
                MATCH (u:User {id: $uid})
                MATCH (p:Product {id: $pid})
                MERGE (u)-[r:PURCHASED {date: $date}]->(p)
                SET r.quantity = $qty
                """,
                uid=user_id,
                pid=product_id,
                qty=quantity,
                date=date,
            )

    def add_view(self, user_id: str, product_id: str, timestamp: str):
        """Record a VIEWED relationship."""
        with self.driver.session() as session:
            session.run(
                """
                MATCH (u:User {id: $uid})
                MATCH (p:Product {id: $pid})
                MERGE (u)-[r:VIEWED {timestamp: $ts}]->(p)
                """,
                uid=user_id,
                pid=product_id,
                ts=timestamp,
            )

    def get_also_bought(self, product_id: str, limit: int = 5) -> list[dict[str, Any]]:
        """'Users who bought this also bought' recommendation."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (p:Product {id: $pid})<-[:PURCHASED]-(u:User)-[:PURCHASED]->(other:Product)
                WHERE other.id <> $pid
                WITH other, COUNT(DISTINCT u) AS co_buyers
                ORDER BY co_buyers DESC
                LIMIT $limit
                RETURN other.id AS id, other.name AS name, other.price AS price,
                       other.category AS category, co_buyers
                """,
                pid=product_id,
                limit=limit,
            )
            return [dict(r) for r in result]

    def get_frequently_bought_together(self, product_id: str, limit: int = 5) -> list[dict[str, Any]]:
        """Products most frequently purchased in the same order context."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (p:Product {id: $pid})<-[:PURCHASED]-(u:User)-[:PURCHASED]->(other:Product)
                WHERE other.id <> $pid
                WITH other, COUNT(*) AS freq
                ORDER BY freq DESC
                LIMIT $limit
                RETURN other.id AS id, other.name AS name, other.price AS price,
                       other.category AS category, freq
                """,
                pid=product_id,
                limit=limit,
            )
            return [dict(r) for r in result]


# Singleton instance
neo4j_client = Neo4jClient()
