import unittest
from pathlib import Path

from src.data.repository import LocalJSONRepository


class TestLocalJSONRepository(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base_dir = Path(__file__).resolve().parents[1]
        cls.repo = LocalJSONRepository(data_dir=base_dir / "data")

    def test_find_by_exact_zip(self):
        results = self.repo.find_by_zip("27606")
        self.assertTrue(results, "Expected results for ZIP 27606")
        self.assertTrue(any(f.zip_code == "27606" for f in results))

    def test_find_by_radius(self):
        results = self.repo.find_by_zip("62704", radius_miles=20)
        self.assertTrue(results, "Expected results for ZIP 62704 within 20 miles")
        self.assertTrue(any(f.zip_code == "62704" for f in results))

    def test_search_by_natural_language(self):
        query = "outdoor pottery markets under $50"
        results = self.repo.search(query, zip_code="27606", radius_miles=50)
        self.assertTrue(results, f"Expected results for query '{query}'")
        self.assertTrue(
            any(
                f.zip_code == "27606" and f.environment == "outdoor" and f.price is not None and f.price <= 50
                for f in results
            ),
            "Expected at least one outdoor, affordable pottery market near ZIP 27606",
        )

    def test_search_semantic_similarity(self):
        query = "agriculture fair"
        results = self.repo.search(query, zip_code="62704", radius_miles=50)
        self.assertTrue(results, f"Expected results for semantic query '{query}'")
        self.assertTrue(
            any("Agriculture" in f.categories or "Food" in f.categories for f in results),
            "Expected at least one fair with Agriculture or Food category for semantic query",
        )

    def test_search_semantic_food_market(self):
        query = "food market"
        results = self.repo.search(query, zip_code="62704", radius_miles=50)
        self.assertTrue(results, f"Expected results for semantic query '{query}'")
        self.assertTrue(
            any("Food" in f.categories or "Market" in f.categories for f in results),
            "Expected at least one fair with Food or Market category for semantic query",
        )


if __name__ == "__main__":
    unittest.main()
