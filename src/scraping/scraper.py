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
    return bool(re.search(r"\b(raleigh|durham|chapel hill|cary|wake|orange|nc|north carolina|[0-9]{5}(?:-[0-9]{4})?)\b", text, re.I))


def _looks_like_fee(text: str) -> bool:
    if not text:
        return False
    return bool(re.search(r"\b(fee|free|donation|admission|ticket|cost|budget|compensation)\b", text, re.I) or "$" in text)


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

    body_text = "\n".join(chunk for chunk in chunks if chunk)
    if not body_text:
        return None

    record: Dict[str, Optional[str]] = {
        "name": heading_text or title_text,
        "date_text": None,
        "location_text": None,
        "fee_text": None,
        "url": url,
    }

    lower_text = body_text.lower()
    if _looks_like_date(body_text):
        record["date_text"] = body_text
    if _looks_like_location(body_text):
        record["location_text"] = body_text
    if _looks_like_fee(body_text):
        record["fee_text"] = body_text

    if not any(record.values()):
        return None

    return record


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

    session = requests.Session()
    session.trust_env = False

    try:
        response = session.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        page_html = response.text
    except requests.RequestException:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as handle:
            page_html = handle.read().decode("utf-8", "ignore")

    if delay_seconds > 0:
        time.sleep(delay_seconds)

    soup = BeautifulSoup(page_html, "html.parser")

    items: List[Dict[str, Optional[str]]] = []

    # The page uses Elementor headings for titles and text-editor widgets for
    # descriptive content. We collect the visible text from those blocks and keep
    # it in a raw form for later cleaning.
    heading_candidates = []
    for heading in soup.select("h1.elementor-heading-title, h2.elementor-heading-title, h3.elementor-heading-title"):
        text = heading.get_text(" ", strip=True)
        if text:
            heading_candidates.append(text)

    text_widgets = soup.select("div.elementor-widget-text-editor")

    for widget in text_widgets:
        widget_text = widget.get_text("\n", strip=True)
        if not widget_text:
            continue

        # Keep the raw text as-is; no normalization yet.
        record: Dict[str, Optional[str]] = {
            "name": None,
            "date_text": None,
            "location_text": None,
            "fee_text": None,
            "url": url,
        }

        # Use the first non-empty heading as the name when available.
        if heading_candidates:
            record["name"] = heading_candidates[0]

        lines = [line.strip() for line in widget_text.splitlines() if line.strip()]
        joined_text = "\n".join(lines)

        lower_text = joined_text.lower()
        if "location" in lower_text:
            record["location_text"] = joined_text
        if any(token in lower_text for token in ["date", "deadline", "call opens", "call closes", "opening", "closed"]):
            record["date_text"] = joined_text
        if any(token in lower_text for token in ["fee", "budget", "compensation", "entry fee"]):
            record["fee_text"] = joined_text

        if any(record.values()):
            items.append(record)

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
