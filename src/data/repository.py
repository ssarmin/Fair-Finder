from __future__ import annotations
from typing import List, Optional, Protocol
from pathlib import Path
import json

from .models import Fair
from .utils import haversine


class BaseRepository(Protocol):
    def find_by_zip(self, zip_code: str, radius_miles: float = 50.0) -> List[Fair]:
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
