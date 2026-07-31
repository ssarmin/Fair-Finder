from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.data.models import Fair
from src.scraping.normalizer import normalize_raw_items
from src.scraping.scraper import scrape_page


def scrape_and_normalize(url: str, delay_seconds: float = 0.5) -> List[Fair]:
    """Scrape a page and convert the extracted entries into Fair objects."""
    raw_items = scrape_page(url, delay_seconds=delay_seconds)
    return normalize_raw_items(raw_items)
