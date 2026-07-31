import re
import time
import urllib.request
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup


def _prefer_heading(soup: BeautifulSoup) -> Optional[str]:
    for selector in ["h1", "h2", "h3"]:
        for tag in soup.select(selector):
            text = tag.get_text(" ", strip=True)
            if text:
                return text
    return None


def _get_meta_content(soup: BeautifulSoup, *names: str) -> List[str]:
    values: List[str] = []
    for meta in soup.select("meta"):
        attr_name = meta.get("name", "") or meta.get("property", "")
        content = (meta.get("content") or "").strip()
        if not content:
            continue
        if attr_name.lower() in {name.lower() for name in names}:
            values.append(content)
    return values


def _looks_like_date(text: str) -> bool:
    if not text:
        return False
    if re.search(r"\b(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\b", text, re.I):
        return True
    if re.search(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", text, re.I):
        return True
    return bool(re.search(r"\b\d{4}[-/\.]\d{2}[-/\.]\d{2}\b", text))


def _looks_like_location(text: str) -> bool:
    if not text:
        return False
    if re.search(r"\b\d{5}(?:-\d{4})?\b", text):
        return True
    if re.search(r"\b(nc|north carolina)\b", text, re.I):
        return True
    if re.search(r"\b(raleigh|durham|chapel hill|cary)\b", text, re.I):
        return bool(re.search(r"\b(at|on|near|street|road|ave|avenue|blvd|boulevard|dr|drive|lane|ln|way|parkway|pkwy|square|plaza|suite|unit|apt|po box|box)\b", text, re.I) or re.search(r"[,:]", text) or re.search(r"\b\d+\b", text))

    if re.search(r"\b(hall|drive|street|road|avenue|ave|lane|ln|way|blvd|boulevard|parkway|pkwy|square|plaza|suite|unit|apt|box)\b", text, re.I):
        return True

    return False


def _looks_like_fee(text: str) -> bool:
    if not text:
        return False
    return bool(re.search(r"\b(fee|free|donation|admission|ticket|cost|budget|compensation)\b", text, re.I) or "$" in text)


def _clean_text(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    cleaned = re.sub(r"\s+", " ", text).strip()
    cleaned = re.sub(r"^(?:location|date|fee)\s*[:\-]\s*", "", cleaned, flags=re.I)
    return cleaned or None


def _first_matching_chunk(chunks: List[str], predicate) -> Optional[str]:
    matches: List[tuple[str, int]] = []
    for index, chunk in enumerate(chunks):
        cleaned = _clean_text(chunk)
        if cleaned and predicate(cleaned):
            matches.append((cleaned, index))

    if not matches:
        return None

    def rank(item: tuple[str, int]) -> tuple[int, int, int, int, str]:
        text, order = item
        lower = text.lower()
        address_score = 0
        if re.search(r"\b\d{5}(?:-\d{4})?\b", text):
            address_score += 5
        if re.search(r"\b(raleigh|durham|chapel hill|cary|nc|north carolina)\b", text, re.I):
            address_score += 3
        if re.search(r"\b(hall|drive|street|road|avenue|ave|lane|ln|way|blvd|boulevard|parkway|pkwy|square|plaza|suite|unit|apt|box)\b", text, re.I):
            address_score += 4
        if re.search(r"\b(location|address|at|near)\b", lower):
            address_score += 2
        if re.search(r"\b(date|location)\b", lower):
            address_score += 2
        if re.search(r"\b(november|december|september|october|january|february|march|april|may|june|july)\b", lower):
            address_score += 1
        if len(text) > 220:
            address_score -= 2
        if "mailing address" in lower:
            address_score -= 6
        return (-address_score, len(text), text.count(" "), order, text)

    matches.sort(key=rank)
    return matches[0][0]


def _build_generic_record(url: str, soup: BeautifulSoup) -> Optional[Dict[str, Optional[str]]]:
    title_text = soup.title.get_text(" ", strip=True) if soup.title else None
    heading_text = _prefer_heading(soup)
    meta_texts = _get_meta_content(soup, "description", "og:description", "twitter:description")

    chunks: List[str] = []
    if title_text:
        chunks.append(title_text)
    if heading_text and heading_text not in chunks:
        chunks.append(heading_text)
    chunks.extend(meta_texts)

    for paragraph in soup.select("p, li, td, th"):
        text = paragraph.get_text(" ", strip=True)
        if text and text not in chunks:
            chunks.append(text)

    if not chunks:
        return None

    record: Dict[str, Optional[str]] = {
        "name": heading_text or title_text,
        "date_text": _first_matching_chunk(chunks, _looks_like_date),
        "location_text": _first_matching_chunk(chunks, _looks_like_location),
        "fee_text": _first_matching_chunk(chunks, _looks_like_fee),
        "url": url,
    }

    if not any(record.values()):
        return None

    return record


def _fetch_page_html(url: str, headers: Dict[str, str], timeout: int = 20) -> str:
    """Fetch page HTML using requests with urllib fallback."""
    session = requests.Session()
    session.trust_env = False
    try:
        response = session.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.text
    except requests.RequestException:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as handle:
            return handle.read().decode("utf-8", "ignore")


def _collect_heading_candidates(soup: BeautifulSoup) -> List[str]:
    """Return a list of non-empty Elementor heading candidate texts."""
    heading_candidates: List[str] = []
    for heading in soup.select("h1.elementor-heading-title, h2.elementor-heading-title, h3.elementor-heading-title"):
        text = heading.get_text(" ", strip=True)
        if text:
            heading_candidates.append(text)
    return heading_candidates


def _extract_items_from_widgets(soup: BeautifulSoup, url: str, heading_candidates: List[str]) -> List[Dict[str, Optional[str]]]:
    """Extract records from div.elementor-widget-text-editor widgets."""
    items: List[Dict[str, Optional[str]]] = []
    text_widgets = soup.select("div.elementor-widget-text-editor")

    for widget in text_widgets:
        widget_text = widget.get_text("\n", strip=True)
        if not widget_text:
            continue

        record: Dict[str, Optional[str]] = {
            "name": None,
            "date_text": None,
            "location_text": None,
            "fee_text": None,
            "url": url,
        }

        if heading_candidates:
            record["name"] = heading_candidates[0]

        lines = [line.strip() for line in widget_text.splitlines() if line.strip()]
        if lines:
            record["location_text"] = _first_matching_chunk(lines, _looks_like_location)
            record["date_text"] = _first_matching_chunk(lines, _looks_like_date)
            record["fee_text"] = _first_matching_chunk(lines, _looks_like_fee)

        # keep original behavior which used any(record.values()) (url is always present)
        if any(record.values()):
            items.append(record)

    return items


def scrape_page(url: str, delay_seconds: float = 0.5) -> List[Dict[str, Optional[str]]]:
    """Fetch a page and extract raw event-like content from the page body.

    The target page uses WordPress/Elementor widgets, so the relevant data is
    typically found in heading tags and generic text-editor widgets rather than
    custom event classes.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    page_html = _fetch_page_html(url, headers, timeout=20)

    if delay_seconds > 0:
        time.sleep(delay_seconds)

    soup = BeautifulSoup(page_html, "html.parser")

    heading_candidates = _collect_heading_candidates(soup)
    items = _extract_items_from_widgets(soup, url, heading_candidates)

    if not items and heading_candidates:
        items.append(
            {
                "name": heading_candidates[0],
                "date_text": None,
                "location_text": None,
                "fee_text": None,
                "url": url,
            }
        )

    if not items:
        generic_record = _build_generic_record(url, soup)
        if generic_record:
            items.append(generic_record)

    return items
