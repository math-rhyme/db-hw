"""Load data into MongoDB document store."""

import logging
import random
from datetime import datetime, timedelta

from src.db.mongodb_client import mongo_client
from src.utils.data_parser import DataParser

logger = logging.getLogger(__name__)

REVIEW_TITLES = [
    "Absolutely love it!",
    "Great quality!",
    "Exceeded expectations",
    "Perfect gift",
    "Beautiful craftsmanship",
    "Very happy with purchase",
    "Exactly as described",
    "Highly recommend",
    "Worth every penny",
    "Amazing work",
]

REVIEW_BODIES = [
    "The quality is outstanding. I can tell a lot of care went into making this.",
    "Arrived quickly and packaged beautifully. Will definitely order again.",
    "This is even better in person. The photos don't do it justice.",
    "I bought this as a gift and the recipient was thrilled.",
    "Excellent workmanship and fast shipping. Very pleased.",
    "Unique and well-made. Exactly what I was looking for.",
    "The seller was very helpful and the product is gorgeous.",
    "I've ordered several times from this seller and always happy.",
]

CATEGORY_SPECS: dict[str, dict] = {
    "Home & Kitchen": {
        "material": ["acacia wood", "bamboo", "ceramic", "copper", "slate"],
        "care_instructions": ["Hand wash only", "Dishwasher safe", "Oil regularly"],
        "dimensions": {"length": 12, "width": 8, "height": 4, "unit": "inches"},
    },
    "Fashion": {
        "material": ["merino wool", "alpaca fiber", "linen", "silk", "leather"],
        "care_instructions": ["Hand wash cold", "Dry clean only", "Machine wash gentle"],
        "size_range": ["XS", "S", "M", "L", "XL"],
    },
    "Jewelry": {
        "material": ["sterling silver", "copper", "brass", "gold-filled"],
        "stone": ["turquoise", "amethyst", "moonstone", "none"],
        "finish": ["polished", "oxidized", "matte"],
    },
    "Home Decor": {
        "material": ["cotton rope", "natural grass", "reclaimed wood", "glass"],
        "dimensions": {"width": 24, "height": 36, "unit": "inches"},
        "hanging": True,
    },
    "Stationery": {
        "material": ["leather", "brass", "recycled paper", "cedar"],
        "pages": 200,
        "closure": ["brass clasp", "elastic band", "magnetic"],
    },
    "Beauty": {
        "ingredients": ["organic lavender", "activated charcoal", "essential oils", "beeswax"],
        "size": "4oz",
        "cruelty_free": True,
        "vegan": True,
    },
}


class DocumentLoader:
    def __init__(self):
        self.parser = DataParser()
        self.db = mongo_client.db

    def load_reviews(self):
        """Generate and load realistic product reviews."""
        collection = self.db["reviews"]
        collection.drop()

        products = self.parser.parse_products()
        users = self.parser.parse_users()
        docs = []

        for _, product in products.iterrows():
            num_reviews = random.randint(2, 5)
            reviewers = users.sample(min(num_reviews, len(users)))

            for _, user in reviewers.iterrows():
                created = datetime.now() - timedelta(days=random.randint(1, 400))
                rating = random.choices([3, 4, 5], weights=[1, 3, 6])[0]
                doc = {
                    "product_id": product["id"],
                    "user_id": user["id"],
                    "rating": rating,
                    "title": random.choice(REVIEW_TITLES),
                    "content": random.choice(REVIEW_BODIES),
                    "images": [],
                    "helpful_votes": random.randint(0, 30),
                    "verified_purchase": random.random() > 0.2,
                    "created_at": created,
                    "comments": self._generate_comments(users, created),
                }
                docs.append(doc)

        collection.insert_many(docs)
        logger.info(f"Loaded {len(docs)} reviews")
        print(f"Loaded {len(docs)} reviews")

    def _generate_comments(self, users, base_date: datetime) -> list[dict]:
        """Generate 0–2 comments on a review."""
        if random.random() > 0.4:
            return []
        commenter = users.sample(1).iloc[0]
        return [
            {
                "user_id": commenter["id"],
                "content": random.choice(
                    [
                        "I agree completely!",
                        "Thanks for the honest review.",
                        "Same experience here.",
                        "Good to know!",
                    ]
                ),
                "created_at": base_date + timedelta(days=random.randint(1, 30)),
            }
        ]

    def load_product_specs(self):
        """Load variable product specifications by category."""
        collection = self.db["product_specs"]
        collection.drop()

        products = self.parser.parse_products()
        docs = []

        for _, product in products.iterrows():
            base_specs = CATEGORY_SPECS.get(product["category"], {})
            resolved: dict = {}
            for k, v in base_specs.items():
                resolved[k] = random.choice(v) if isinstance(v, list) else v

            docs.append(
                {
                    "product_id": product["id"],
                    "category": product["category"],
                    "specs": resolved,
                }
            )

        collection.insert_many(docs)
        logger.info(f"Loaded {len(docs)} product specs")
        print(f"Loaded {len(docs)} product specs")

    def load_seller_profiles(self):
        """Load rich seller profiles with portfolio info."""
        collection = self.db["seller_profiles"]
        collection.drop()

        sellers = self.parser.parse_sellers()
        products = self.parser.parse_products()
        docs = []

        for _, seller in sellers.iterrows():
            seller_products = products[products["seller_id"] == seller["id"]]
            docs.append(
                {
                    "seller_id": seller["id"],
                    "name": seller["name"],
                    "specialty": seller["specialty"],
                    "bio": f"Passionate artisan specializing in {seller['specialty'].lower()}. "
                    f"Creating handmade goods with care and attention to detail since "
                    f"{seller['joined'].year}.",
                    "location": random.choice(["Portland, OR", "Austin, TX", "Brooklyn, NY", "Asheville, NC"]),
                    "portfolio": [
                        {"product_id": pid, "featured": i == 0}
                        for i, pid in enumerate(seller_products["id"].tolist()[:5])
                    ],
                    "social_links": {
                        "instagram": f"@{seller['name'].lower().replace(' ', '_')}",
                    },
                    "response_time_hours": random.choice([1, 2, 4, 8, 24]),
                    "ships_from": random.choice(["US", "CA"]),
                    "accepts_custom_orders": random.random() > 0.3,
                }
            )

        collection.insert_many(docs)
        logger.info(f"Loaded {len(docs)} seller profiles")
        print(f"Loaded {len(docs)} seller profiles")

    def load_user_preferences(self):
        """Load user behavior and preference tracking documents."""
        collection = self.db["user_preferences"]
        collection.drop()

        users = self.parser.parse_users()
        products = self.parser.parse_products()
        docs = []

        for _, user in users.iterrows():
            viewed_sample = products.sample(min(random.randint(3, 10), len(products)))
            docs.append(
                {
                    "user_id": user["id"],
                    "preferred_categories": random.sample(
                        ["Home & Kitchen", "Fashion", "Jewelry", "Home Decor", "Stationery", "Beauty"],
                        k=random.randint(1, 3),
                    ),
                    "price_range": {
                        "min": round(random.uniform(15, 40), 2),
                        "max": round(random.uniform(80, 200), 2),
                    },
                    "recently_viewed": viewed_sample["id"].tolist(),
                    "saved_items": products.sample(min(random.randint(0, 5), len(products)))["id"].tolist(),
                    "interests": user["interests"],
                    "last_active": datetime.now() - timedelta(days=random.randint(0, 30)),
                    "notification_preferences": {
                        "email": True,
                        "sale_alerts": random.random() > 0.5,
                        "new_arrivals": random.random() > 0.5,
                    },
                }
            )

        collection.insert_many(docs)
        logger.info(f"Loaded {len(docs)} user preference documents")
        print(f"Loaded {len(docs)} user preference documents")

    def load_all(self):
        """Load all MongoDB collections."""
        print("Creating MongoDB indexes...")
        mongo_client.create_indexes()

        print("Loading reviews...")
        self.load_reviews()

        print("Loading product specs...")
        self.load_product_specs()

        print("Loading seller profiles...")
        self.load_seller_profiles()

        print("Loading user preferences...")
        self.load_user_preferences()

        print("Document data loading complete!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    loader = DocumentLoader()
    loader.load_all()
