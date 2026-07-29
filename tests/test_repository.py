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


if __name__ == "__main__":
    unittest.main()
