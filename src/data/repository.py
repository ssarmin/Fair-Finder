from __future__ import annotations
import json
import re
from pathlib import Path
from typing import List, Optional, Protocol

try:
    from sentence_transformers import SentenceTransformer, util
except ImportError:  # pragma: no cover
    SentenceTransformer = None
    util = None

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

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
        self._model: Optional[SentenceTransformer] = None
        self._embeddings = None
        self._vectorizer: Optional[TfidfVectorizer] = None
        self._search_matrix = None
        self._use_transformer = SentenceTransformer is not None

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

    def _get_search_text(self, fair: Fair) -> str:
        return " ".join(
            filter(
                None,
                [
                    fair.name,
                    fair.description,
                    fair.city,
                    fair.state,
                    fair.address,
                    fair.environment,
                    " ".join(fair.categories),
                ],
            )
        ).lower()

    def _initialize_search_index(self) -> None:
        if self._use_transformer and self._model is not None and self._embeddings is not None:
            return
        if not self._use_transformer and self._vectorizer is not None and self._search_matrix is not None:
            return

        fairs = self._load_fairs()
        texts = [self._get_search_text(fair) for fair in fairs]

        if self._use_transformer and SentenceTransformer is not None:
            try:
                self._model = SentenceTransformer("all-MiniLM-L6-v2")
                self._embeddings = self._model.encode(texts, convert_to_tensor=True, show_progress_bar=False)
                return
            except Exception:
                self._use_transformer = False

        self._vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", max_features=5000)
        self._search_matrix = self._vectorizer.fit_transform(texts)

    def _tokenize(self, query: str) -> List[str]:
        return re.findall(r"\b[\w']+\b", query.lower())

    def _parse_price(self, query: str) -> Optional[float]:
        price = query.lower()
        if "free" in price:
            return 0.0

        match = re.search(r"(?:under|below|less than)\s*\$?(\d+(?:\.\d+)?)", price)
        if match:
            return float(match.group(1))
        return None

    def _parse_environment(self, query: str) -> Optional[str]:
        environment = query.lower()
        if "outdoor" in environment:
            return "outdoor"
        if "indoor" in environment:
            return "indoor"
        return None

    def _matches_query(
        self,
        fair: Fair,
        max_price: Optional[float],
        environment: Optional[str],
        query_terms: List[str],
    ) -> bool:
        if max_price is not None:
            if max_price == 0.0:
                if fair.price is not None and fair.price > 0.0:
                    return False
            else:
                if fair.price is None or fair.price >= max_price:
                    return False

        if environment is not None:
            if fair.environment is None:
                return False
            if environment not in fair.environment.lower():
                return False

        artist_friendly_keywords = ["art", "arts", "craft", "crafts", "pottery", "maker", "artists", "exhibition", "market", "walk"]
        specific_focus = [t for t in query_terms if t in ["art", "arts", "craft", "crafts", "pottery", "maker", "artists"]]

        if specific_focus:
            fair_text = f"{fair.name} {' '.join(fair.categories)} {fair.description or ''}".lower()
            unwanted_keywords = ["book", "books", "science", "toy", "toys", "culinary"]
            if any(unwanted in fair_text for unwanted in unwanted_keywords):
                if not any(friendly in fair_text for friendly in ["art", "craft", "pottery", "maker"]):
                    return False

            if not any(keyword in fair_text for keyword in artist_friendly_keywords):
                return False

        return True

    def _score_fair(self, fair: Fair, similarity: float, environment: Optional[str], query_terms: List[str]) -> float:
        score = similarity
        
        fair_text = f"{fair.name} {' '.join(fair.categories)}".lower()
        matching_terms = sum(1 for term in query_terms if term in fair_text)
        if matching_terms > 0:
            score += 0.15 * matching_terms

        if environment is not None and environment in (fair.environment or "").lower():
            score += 0.05
            
        return score

    def search(
        self,
        query: str,
        zip_code: Optional[str] = None,
        radius_miles: float = 50.0,
    ) -> List[Fair]:
        """Return fairs matching a natural-language query using a hybrid approach:
        1. Hard filter by extracted constraints (price, environment, ZIP radius, artist relevance).
        2. Soft rank the filtered candidates using semantic similarity and keyword matching.
        """
        fairs = self._load_fairs()
        zip_map = self._load_zip_map()

        max_price = self._parse_price(query)
        environment = self._parse_environment(query)
        query_terms = self._tokenize(query)

        centroid = None
        if zip_code is not None:
            z = str(zip_code)
            if z in zip_map:
                centroid = zip_map[z]

        # 1. Hard Filter Candidates
        candidates = []
        distances = []
        for fair in fairs:
            dist = None
            if centroid is not None:
                if fair.latitude is None or fair.longitude is None:
                    continue
                dist = haversine(centroid["latitude"], centroid["longitude"], fair.latitude, fair.longitude)
                if dist > radius_miles:
                    continue

            if not self._matches_query(fair, max_price, environment, query_terms):
                continue

            candidates.append(fair)
            distances.append(dist)

        if not candidates:
            return []

        # 2. Semantic Scoring on Filtered Candidates
        texts = [self._get_search_text(fair) for fair in candidates]
        self._initialize_search_index()

        if self._use_transformer and self._model is not None and util is not None:
            query_vector = self._model.encode([query], convert_to_tensor=True, show_progress_bar=False)
            candidate_embeddings = self._model.encode(texts, convert_to_tensor=True, show_progress_bar=False)
            similarity_tensor = util.cos_sim(query_vector, candidate_embeddings)
            similarities = similarity_tensor.cpu().numpy().flatten()
        elif self._vectorizer is not None and self._search_matrix is not None:
            query_vector = self._vectorizer.transform([query])
            candidate_matrix = self._vectorizer.transform(texts)
            similarities = cosine_similarity(query_vector, candidate_matrix).flatten()
        else:
            similarities = [1.0] * len(candidates)

        results = []
        min_similarity = 0.30 if self._use_transformer else 0.0

        for index, fair in enumerate(candidates):
            similarity = float(similarities[index]) if index < len(similarities) else 0.0
            if similarity < min_similarity:
                continue
            score = self._score_fair(fair, similarity, environment, query_terms)
            dist = distances[index]
            results.append((score, dist if dist is not None else 0, fair))

        results.sort(key=lambda item: (item[0], -item[1] if item[1] is not None else 0), reverse=True)
        return [fair for _, _, fair in results]

    def find_by_zip(self, zip_code: str, radius_miles: float = 50.0) -> List[Fair]:
        """Return fairs matching a ZIP code or within radius of the ZIP centroid."""
        fairs = self._load_fairs()
        zip_map = self._load_zip_map()
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
            results.sort(key=lambda x: x[0])
            return [f for _, f in results]
        else:
            return [f for f in fairs if f.zip_code == z]


class ExampleExternalAPIRepository:
    """Placeholder for a repository that would call an external API (e.g., a fairs API)."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def find_by_zip(self, zip_code: str, radius_miles: float = 50.0) -> List[Fair]:
        raise NotImplementedError("Implement an HTTP-backed repository using requests or httpx")