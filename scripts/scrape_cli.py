#!/usr/bin/env python3
"""CLI for scraping pages from data/list_pages.txt and printing matched results by ZIP code."""

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from src.scraping.pipeline import scrape_and_normalize  # noqa: E402


def _read_urls(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape configured pages and print matches for a ZIP code")
    parser.add_argument("zip_code", help="ZIP code to match against scraped results")
    parser.add_argument("--list-file", default=str(ROOT_DIR / "data" / "list_pages.txt"), help="Path to a file containing one URL per line")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay in seconds between requests")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of results to print")
    args = parser.parse_args()

    list_file = Path(args.list_file)
    urls = _read_urls(list_file)

    matches = []
    for url in urls:
        try:
            fairs = scrape_and_normalize(url, delay_seconds=args.delay)
        except Exception as exc:
            print(f"Skipped {url}: {exc}")
            continue

        for fair in fairs:
            if fair.zip_code == args.zip_code:
                matches.append((url, fair))

    if not matches:
        print(f"No matches found for ZIP {args.zip_code}")
        return

    for index, (url, fair) in enumerate(matches[: args.limit], start=1):
        print(f"{index}. {fair.name or 'Untitled event'}")
        print(f"   URL: {url}")
        print(f"   Date: {fair.start_date or 'not listed'}")
        print(f"   Price: {fair.price if fair.price is not None else 'not listed'}")
        print(f"   ZIP: {fair.zip_code or 'not listed'}")
        if fair.description:
            print("   Details:")
            for line in fair.description.splitlines():
                print(f"      {line}")
        print()


if __name__ == "__main__":
    main()
