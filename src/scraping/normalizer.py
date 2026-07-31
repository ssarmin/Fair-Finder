from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.data.models import Fair


def _normalize_text_for_date(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    text = re.sub(r"\s+", " ", text)
    text = text.replace("–", "-").replace("—", "-")
    # If there is a range like "2026-05-01 - 2026-05-03" prefer the first part
    if "-" in text:
        parts = re.split(r"\s*[\-–—]\s*", text)
        if len(parts) > 1:
            text = parts[0]
    return text

def _try_strptime_patterns(text: str) -> Optional[str]:
    patterns = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%B %d %Y",
        "%b %d %Y",
        "%d %B %Y",
        "%d %b %Y",
        "%A, %B %d, %Y",
        "%A, %b %d, %Y",
        "%B %d",
        "%b %d",
    ]
    for fmt in patterns:
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.date().isoformat()
        except ValueError:
            continue
    return None

def _extract_iso_from_regexes(text: str) -> Optional[str]:
    for pattern in [
        r"(\d{4}-\d{2}-\d{2})",
        r"(\d{4}/\d{2}/\d{2})",
        r"(\d{4}\.\d{2}\.\d{2})",
    ]:
        match = re.search(pattern, text)
        if match:
            return match.group(1).replace("/", "-").replace(".", "-")
    return None

def _parse_month_name_format(text: str) -> Optional[str]:
    month_pattern = (
        r"(?:january|february|march|april|may|june|july|august|"
        r"september|october|november|december|jan|feb|mar|apr|jun|jul|aug|"
        r"sep|sept|oct|nov|dec)"
    )
    if not re.search(rf"\b{month_pattern}\b", text, re.I):
        return None

    date_match = re.search(
        rf"({month_pattern})\s+(\d{{1,2}})(?:,?\s*(\d{{4}}))?", text, re.I
    )
    if not date_match:
        return None

    month_name = date_match.group(1)
    day = int(date_match.group(2))
    year = int(date_match.group(3)) if date_match.group(3) else None
    if year is None:
        return None

    month_map = {
        "jan": "January", "january": "January",
        "feb": "February", "february": "February",
        "mar": "March", "march": "March",
        "apr": "April", "april": "April",
        "may": "May",
        "jun": "June", "june": "June",
        "jul": "July", "july": "July",
        "aug": "August", "august": "August",
        "sep": "September", "sept": "September", "september": "September",
        "oct": "October", "october": "October",
        "nov": "November", "november": "November",
        "dec": "December", "december": "December",
    }
    normalized_month = month_map.get(month_name.lower())
    if normalized_month is None:
        return None

    parsed = datetime.strptime(f"{normalized_month} {day} {year}", "%B %d %Y")
    return parsed.date().isoformat()

def _parse_date(value: Optional[str]) -> Optional[str]:
    text = _normalize_text_for_date(value)
    if not text:
        return None

    # Try parse via strptime patterns
    result = _try_strptime_patterns(text)
    if result:
        return result

    # Try regex extraction for YYYY-MM-DD-like formats
    result = _extract_iso_from_regexes(text)
    if result:
        return result

    # Try month-name parsing (with explicit year)
    result = _parse_month_name_format(text)
    return result


def _parse_fee(value: Optional[str]) -> Optional[float]:
    if not value:
        return None

    text = value.strip()
    if not text:
        return None

    match = re.search(r"\$\s*(\d+(?:\.\d+)?)", text)
    if match:
        return float(match.group(1))

    return None


def _parse_zip_code(value: Optional[str]) -> str:
    if not value:
        return ""

    text = value.strip()
    if not text:
        return ""

    match = re.search(r"\b(\d{5})(?:-\d{4})?\b", text)
    if match:
        return match.group(1)

    return ""


def normalize_raw_items(raw_items: List[Dict[str, Any]]) -> List[Fair]:
    """Convert raw scraped dicts into Fair objects without guessing missing values."""
    normalized: List[Fair] = []

    for raw in raw_items:
        name = raw.get("name")
        date_text = raw.get("date_text")
        location_text = raw.get("location_text")
        fee_text = raw.get("fee_text")
        url = raw.get("url")

        fair = Fair(
            id="",
            name=(name.strip() if isinstance(name, str) and name.strip() else ""),
            address=None,
            city=None,
            state=None,
            zip_code=_parse_zip_code(location_text),
            latitude=None,
            longitude=None,
            start_date=_parse_date(date_text),
            end_date=None,
            categories=[],
            price=_parse_fee(fee_text),
            environment=None,
            description=(
                f"Source URL: {url}\n\nLocation: {location_text}\n\nFee: {fee_text}"
                if url or location_text or fee_text
                else None
            ),
        )
        normalized.append(fair)

    return normalized


def demo_normalize(raw_items: List[Dict[str, Any]], limit: int = 3) -> List[Dict[str, Any]]:
    """Return a small preview of normalized values for inspection."""
    preview = []
    for fair in normalize_raw_items(raw_items[:limit]):
        preview.append(
            {
                "name": fair.name,
                "start_date": fair.start_date,
                "price": fair.price,
                "description": fair.description,
            }
        )
    return preview
