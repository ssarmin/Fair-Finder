from __future__ import annotations
import json
import re
from pathlib import Path
from typing import List, Optional, Protocol

from .models import Fair
from .utils import haversine


class BaseRepository(Protocol):
    def find_by_zip(self, zip_code: str, radius_miles: float = 50.0) -> List[Fair]:
        ...

    def search(
        self,
        query: str,
        zip_code: Optional[str] = None,
        radius_miles: float = 50.0,
    ) -> List[Fair]:
        ...


class LocalJSONRepository:
    """Repository that reads fairs from a local JSON file under the repository's data/ folder.

    Expects two files in the project data/ directory:
    - fairs.json: list of fairs with fields including latitude and longitude
    - zips.json: mapping from ZIP code to {latitude, longitude} for ZIP centroid lookups
    """

    def __init__(self, data_dir: Optional[Path] = None):
        root = Path(__file__).resolve().parents[2]
        self.data_dir = Path(data_dir) if data_dir else root / "data"
        self._fairs: Optional[List[Fair]] = None
        self._zip_map = None

    def _load_fairs(self) -> List[Fair]:
        if self._fairs is None:
            path = self.data_dir / "fairs.json"
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            self._fairs = [Fair.from_dict(d) for d in raw]
        return self._fairs

    def _load_zip_map(self):
        if self._zip_map is None:
            path = self.data_dir / "zips.json"
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self._zip_map = json.load(f)
            except FileNotFoundError:
                self._zip_map = {}
        return self._zip_map

    def _tokenize(self, query: str) -> List[str]:
        return re.findall(r"\b[\w']+\b", query.lower())

    def _parse_price(self, query: str) -> Optional[float]:
        match = re.search(r"(?:under|below|less than)\s*\$?(\d+(?:\.\d+)?)", query.lower())
        if match:
            return float(match.group(1))
        return None

    def _parse_environment(self, query: str) -> Optional[str]:
        lower = query.lower()
        if "outdoor" in lower:
            return "outdoor"
        if "indoor" in lower:
            return "indoor"
        return None

    def _matches_query(
        self,
        fair: Fair,
        tokens: List[str],
        max_price: Optional[float],
        environment: Optional[str],
    ) -> bool:
        if max_price is not None:
            if fair.price is None or fair.price > max_price:
                return False

        if environment is not None:
            if fair.environment is None:
                return False
            if environment not in fair.environment.lower():
                return False

        if not tokens:
            return True

        searchable = " ".join(
            filter(
                None,
                [
                    fair.name,
                    fair.description,
                    fair.city,
                    fair.state,
                    fair.address,
                    fair.environment,
                ],
            )
        ).lower()
        categories = [c.lower() for c in fair.categories]

        stop_words = {
            "the",
            "and",
            "for",
            "in",
            "under",
            "below",
            "less",
            "than",
            "of",
            "a",
            "an",
            "to",
            "with",
            "near",
            "within",
            "on",
            "at",
            "by",
            "or",
            "outdoor",
            "indoor",
        }
        query_tokens = [token for token in tokens if token not in stop_words and not token.isdigit()]
        if not query_tokens:
            return True

        for token in query_tokens:
            search_terms = {token}
            if token.endswith("s"):
                search_terms.add(token[:-1])
            for term in search_terms:
                if term in searchable or term in categories:
                    break
            else:
                return False

        return True

    def _score_fair(self, fair: Fair, tokens: List[str], environment: Optional[str]) -> int:
        text = " ".join(
            filter(
                None,
                [
                    fair.name,
                    fair.description,
                    fair.city,
                    fair.state,
                    fair.address,
                    fair.environment,
                ],
            )
        ).lower()
        categories = [c.lower() for c in fair.categories]
        score = 0
        for token in tokens:
            search_terms = {token}
            if token.endswith("s"):
                search_terms.add(token[:-1])
            for term in search_terms:
                if term in text:
                    score += 3
                if term in categories:
                    score += 2
        if environment is not None and fair.environment is not None:
            if environment in fair.environment.lower():
                score += 2
        return score

    def search(
        self,
        query: str,
        zip_code: Optional[str] = None,
        radius_miles: float = 50.0,
    ) -> List[Fair]:
        """Return fairs matching a natural-language query and optional ZIP proximity."""
        fairs = self._load_fairs()
        zip_map = self._load_zip_map()

        max_price = self._parse_price(query)
        environment = self._parse_environment(query)
        tokens = self._tokenize(query)

        results = []
        distance = None
        centroid = None
        if zip_code is not None:
            z = str(zip_code)
            if z in zip_map:
                centroid = zip_map[z]
                distance = True

        for fair in fairs:
            if centroid is not None:
                if fair.latitude is None or fair.longitude is None:
                    continue
                dist = haversine(centroid["latitude"], centroid["longitude"], fair.latitude, fair.longitude)
                if dist > radius_miles:
                    continue
            if not self._matches_query(fair, tokens, max_price, environment):
                continue
            score = self._score_fair(fair, tokens, environment)
            results.append((score, dist if centroid is not None else None, fair))

        results.sort(key=lambda item: (item[0], -item[1] if item[1] is not None else 0), reverse=True)
        return [fair for _, _, fair in results]

    def find_by_zip(self, zip_code: str, radius_miles: float = 50.0) -> List[Fair]:
        """Return fairs matching a ZIP code or within radius of the ZIP centroid.

        Behavior:
        - If zips.json contains the requested ZIP, return fairs whose distance to the ZIP
          centroid is <= radius_miles (requires fair.latitude and fair.longitude).
        - Otherwise fallback to returning fairs with an exact zip_code match.
        """
        fairs = self._load_fairs()
        zip_map = self._load_zip_map()
        # normalize zip to string
        z = str(zip_code)
        if z in zip_map:
            centroid = zip_map[z]
            lat0 = centroid.get("latitude")
            lon0 = centroid.get("longitude")
            results = []
            for f in fairs:
                if f.latitude is None or f.longitude is None:
                    continue
                dist = haversine(lat0, lon0, f.latitude, f.longitude)
                if dist <= radius_miles:
                    results.append((dist, f))
            # sort by distance
            results.sort(key=lambda x: x[0])
            return [f for _, f in results]
        else:
            # fallback: exact zip match
            return [f for f in fairs if f.zip_code == z]


class ExampleExternalAPIRepository:
    """Placeholder for a repository that would call an external API (e.g., a fairs API).

    To implement: perform HTTP requests to the external service, transform results to Fair objects,
    and return them. Keep the same method signature as LocalJSONRepository to make swapping
    implementations simple.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def find_by_zip(self, zip_code: str, radius_miles: float = 50.0) -> List[Fair]:
        raise NotImplementedError("Implement an HTTP-backed repository using requests or httpx")
