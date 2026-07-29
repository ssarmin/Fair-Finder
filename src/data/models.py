from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Fair:
    id: str
    name: str
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    zip_code: str
    latitude: Optional[float]
    longitude: Optional[float]
    start_date: Optional[str]
    end_date: Optional[str]
    categories: List[str]

    @classmethod
    def from_dict(cls, d: dict) -> "Fair":
        return cls(
            id=str(d.get("id", "")),
            name=d.get("name", ""),
            address=d.get("address"),
            city=d.get("city"),
            state=d.get("state"),
            zip_code=str(d.get("zip_code", "")),
            latitude=d.get("latitude"),
            longitude=d.get("longitude"),
            start_date=d.get("start_date"),
            end_date=d.get("end_date"),
            categories=d.get("categories", []),
        )
