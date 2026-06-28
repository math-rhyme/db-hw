"""Utilities for parsing CSV data."""

from typing import override

import pandas as pd

from src.config import DATA_DIR


class DataParser:
    @staticmethod
    def parse_products() -> pd.DataFrame:
        """Parse products CSV file."""
        df = pd.read_csv(DATA_DIR / "products.csv")
        df.columns = df.columns.str.lower()
        df["price"] = df["price"].astype(float)
        df["tags"] = df["tags"].apply(lambda x: x.split(","))
        return df

    @staticmethod
    def parse_users() -> pd.DataFrame:
        """Parse users CSV file."""
        df = pd.read_csv(DATA_DIR / "users.csv")
        df.columns = df.columns.str.lower()
        df["interests"] = df["interests"].apply(lambda x: x.split(","))
        df["join_date"] = pd.to_datetime(df["join_date"])
        return df

    @staticmethod
    def parse_categories() -> pd.DataFrame:
        """Parse categories CSV file."""
        df = pd.read_csv(DATA_DIR / "categories.csv")
        df.columns = df.columns.str.lower()
        return df

    @staticmethod
    def parse_sellers() -> pd.DataFrame:
        """Parse sellers CSV file."""
        df = pd.read_csv(DATA_DIR / "sellers.csv")
        df.columns = df.columns.str.lower()
        df["rating"] = df["rating"].astype(float)
        df["joined"] = pd.to_datetime(df["joined"])
        return df


class CachedDataParser(DataParser):
    """Data parser with caching capability."""

    def __init__(self):
        self._cache: dict[str, pd.DataFrame] = {}

    @override
    def parse_products(self) -> pd.DataFrame:
        """Parse products with caching."""
        if "products" not in self._cache:
            self._cache["products"] = super().parse_products()
        return self._cache["products"]

    def get_data(self, data_type: str) -> pd.DataFrame:
        """Get data by type using pattern matching."""
        match data_type:
            case "products":
                return self.parse_products()
            case "users":
                return self.parse_users()
            case "categories":
                return self.parse_categories()
            case "sellers":
                return self.parse_sellers()
            case _:
                raise ValueError(f"Unknown data type: {data_type}")
