"""Generate random purchase history and load into PostgreSQL and Neo4j."""

import logging
import random
from datetime import datetime, timedelta

import pandas as pd

from src.db.neo4j_client import neo4j_client
from src.db.postgres_client import db
from src.utils.data_parser import DataParser

logger = logging.getLogger(__name__)

INTEREST_TAG_MAP = {
    "sustainable living": ["sustainable", "eco", "beeswax", "natural"],
    "home decor": ["decor", "wall art", "boho", "macrame"],
    "cooking": ["kitchen", "cutting board", "spoons", "serving tray"],
    "woodworking": ["wood", "carved", "reclaimed", "walnut"],
    "crafts": ["handmade", "textile", "embroidery"],
    "minimalism": ["minimalist", "geometric", "modern"],
    "fashion": ["fashion", "scarf", "bag", "tote"],
    "jewelry": ["jewelry", "necklace", "ring", "earrings", "bracelet"],
    "art": ["art", "sculpture", "stained glass", "wire"],
    "outdoor": ["garden", "forged", "tools"],
    "rustic decor": ["rustic", "reclaimed", "wood"],
    "leather goods": ["leather", "belt", "wallet"],
    "wellness": ["aromatherapy", "lavender", "natural", "organic"],
    "natural beauty": ["beauty", "soap", "clay", "organic"],
    "yoga": ["lavender", "natural", "wellness"],
    "reading": ["bookmark", "journal", "stationery"],
    "stationery": ["stationery", "brass", "leather", "journal"],
    "vintage": ["vintage", "brass", "antique"],
    "bohemian style": ["boho", "macrame", "textile"],
    "textiles": ["textile", "embroidery", "woven", "quilt"],
    "plants": ["plant hanger", "terrarium", "planter"],
    "ceramics": ["ceramic", "pottery", "mug", "planter"],
    "eco-friendly": ["eco", "sustainable", "beeswax", "wool"],
    "zero waste": ["eco", "beeswax", "dryer balls", "sustainable"],
    "modern art": ["art", "sculpture", "abstract", "metal"],
    "design": ["geometric", "modern", "minimalist"],
    "beach lifestyle": ["coastal", "sea glass", "beach"],
    "natural materials": ["natural", "stone", "wood", "bamboo"],
    "meditation": ["lavender", "incense", "zen", "aromatherapy"],
    "aromatherapy": ["lavender", "candle", "aromatherapy", "incense"],
    "wool": ["wool", "alpaca", "knitted", "felt"],
    "winter goods": ["wool", "alpaca", "mittens", "slippers"],
    "urban gardening": ["garden", "planter", "herbs"],
    "sustainability": ["sustainable", "eco", "reclaimed"],
    "coastal decor": ["coastal", "sea glass", "beach"],
    "beach art": ["sea glass", "coastal", "beach"],
    "tea culture": ["ceramic", "mug", "pottery"],
    "asian crafts": ["ceramic", "zen", "minimalist"],
    "wood crafts": ["wood", "carved", "walnut"],
    "calligraphy": ["stationery", "journal", "brass"],
    "cultural crafts": ["textile", "embroidery", "woven"],
    "books": ["bookmark", "journal"],
    "hiking": ["natural", "stone", "sustainable"],
    "outdoor gear": ["forged", "tools", "natural"],
    "zen gardens": ["zen", "ceramic", "incense"],
    "vintage fashion": ["vintage", "beads", "antique"],
    "antiques": ["vintage", "brass", "copper"],
    "bbq": ["wood", "cutting board", "serving tray"],
    "outdoor cooking": ["cutting board", "kitchen", "wood"],
    "artisan foods": ["cutting board", "serving tray", "kitchen"],
    "desert plants": ["planter", "terrarium", "ceramic"],
    "southwestern art": ["textile", "woven", "geometric"],
    "colonial history": ["wood", "reclaimed", "brass"],
    "restoration": ["reclaimed", "wood", "rustic"],
    "community art": ["art", "textile", "handmade"],
    "modern design": ["minimalist", "geometric", "modern"],
    "mountain life": ["wool", "alpaca", "natural"],
    "outdoor adventures": ["natural", "sustainable", "stone"],
    "music": ["wood", "handmade"],
    "handmade instruments": ["wood", "handmade"],
    "scandinavian design": ["minimalist", "wool", "geometric"],
    "surfing": ["coastal", "sea glass", "sustainable"],
    "tech": ["minimalist", "modern"],
}


class PurchaseGenerator:
    def __init__(self):
        self.parser = DataParser()
        self.users = self.parser.parse_users()
        self.products = self.parser.parse_products()

    def _interest_score(self, user_interests: list[str], product_tags: list[str]) -> float:
        """Score product relevance to a user based on interest-to-tag mapping."""
        score = 0.0
        product_tags_lower = [t.strip().lower() for t in product_tags]
        for interest in user_interests:
            interest = interest.strip().lower()
            mapped_tags = INTEREST_TAG_MAP.get(interest, [interest])
            for mt in mapped_tags:
                if any(mt in pt for pt in product_tags_lower):
                    score += 1.0
        return score

    def _weighted_product_sample(self, user_interests: list[str], n: int = 3) -> pd.DataFrame:
        """Sample products weighted by relevance to user interests."""
        scores = self.products["tags"].apply(lambda tags: self._interest_score(user_interests, tags))
        scores = scores + 0.5
        weights = (scores / scores.sum()).tolist()
        indices = random.choices(range(len(self.products)), weights=weights, k=n)
        seen, unique = set(), []
        for i in indices:
            if i not in seen:
                seen.add(i)
                unique.append(i)
        return self.products.iloc[unique]

    def generate_purchases(self, num_purchases: int = 100) -> pd.DataFrame:
        """Generate realistic purchases respecting user interests and join dates."""
        purchases = []
        purchase_id = 1

        for _i in range(num_purchases):
            user = self.users.sample(1).iloc[0]

            earliest = user["join_date"].to_pydatetime()
            latest = datetime.now()
            if earliest >= latest:
                latest = earliest + timedelta(days=30)

            days_available = (latest - earliest).days
            purchase_date = earliest + timedelta(days=random.randint(0, max(days_available, 1)))

            num_items = random.randint(1, 3)
            selected_products = self._weighted_product_sample(user["interests"], num_items)

            for _, product in selected_products.iterrows():
                quantity = random.randint(1, 3)
                purchases.append(
                    {
                        "purchase_id": f"PUR{purchase_id:04d}",
                        "user_id": user["id"],
                        "product_id": product["id"],
                        "quantity": quantity,
                        "unit_price": float(product["price"]),
                        "total_price": round(float(product["price"]) * quantity, 2),
                        "purchase_date": purchase_date.strftime("%Y-%m-%d"),
                    }
                )
                purchase_id += 1

        df = pd.DataFrame(purchases)
        logger.info(f"Generated {len(df)} purchase line items")
        return df

    def save_purchases(self, purchases: pd.DataFrame, filename: str = "purchases.csv"):
        """Save generated purchases to CSV."""
        from src.config import DATA_DIR

        path = DATA_DIR / filename
        purchases.to_csv(path, index=False)
        print(f"Saved {len(purchases)} purchases to {path}")

    def load_into_postgres(self, purchases: pd.DataFrame):
        """Persist purchases as orders + order_items in PostgreSQL."""
        grouped = purchases.groupby(["user_id", "purchase_date"])

        with db.get_cursor() as cursor:
            for (user_id, purchase_date), group in grouped:
                total = float(round(group["total_price"].sum(), 2))
                cursor.execute(
                    """
                    INSERT INTO orders (user_id, status, total_amount, created_at)
                    VALUES (%s, 'completed', %s, %s)
                    RETURNING id;
                    """,
                    (user_id, total, purchase_date),
                )
                row = cursor.fetchone()
                order_id = row["id"]

                for _, item in group.iterrows():
                    cursor.execute(
                        """
                        INSERT INTO order_items (order_id, product_id, quantity, unit_price)
                        VALUES (%s, %s, %s, %s);
                        """,
                        (order_id, item["product_id"], int(item["quantity"]), float(item["unit_price"])),
                    )

        print(f"Loaded {len(grouped)} orders into PostgreSQL")

    def load_into_neo4j(self, purchases: pd.DataFrame):
        """Persist purchase relationships in Neo4j."""
        count = 0
        for _, row in purchases.iterrows():
            neo4j_client.add_purchase(
                user_id=row["user_id"],
                product_id=row["product_id"],
                quantity=int(row["quantity"]),
                date=row["purchase_date"],
            )
            count += 1
        print(f"Loaded {count} PURCHASED relationships into Neo4j")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    generator = PurchaseGenerator()
    purchases = generator.generate_purchases(100)
    generator.save_purchases(purchases)
    generator.load_into_postgres(purchases)
    generator.load_into_neo4j(purchases)
    print(f"Generated and loaded {len(purchases)} purchase line items")
