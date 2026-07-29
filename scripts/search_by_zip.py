#!/usr/bin/env python3
"""Simple CLI to search fairs by ZIP or natural language query using the LocalJSONRepository."""
import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from src.data.repository import LocalJSONRepository  # noqa: E402


def _normalize_query(query: str) -> str:
    if query is None:
        return query
    query = query.strip()
    if len(query) >= 2 and query[0] == query[-1] and query[0] in {'"', "'"}:
        return query[1:-1].strip()
    return query


def _search_args(args):
    repo = LocalJSONRepository()
    if args.query is not None:
        query = _normalize_query(args.query)
        return repo.search(query, zip_code=args.zip, radius_miles=args.radius)
    return repo.find_by_zip(args.zip, radius_miles=args.radius)


def _print_no_results(args):
    if args.query and args.zip:
        print("No fairs found for query", repr(args.query), "near ZIP", args.zip)
    elif args.query:
        print("No fairs found for query", repr(args.query))
    else:
        print("No fairs found for ZIP", args.zip)


def main():
    p = argparse.ArgumentParser(description="Search fairs by ZIP code or natural language query")
    p.add_argument("--zip", help="ZIP code to search near")
    p.add_argument(
        "--query",
        help="Natural language search query, for example 'outdoor pottery markets under $50' or \"outdoor pottery markets under $50\"",
    )
    p.add_argument(
        "--radius",
        type=float,
        default=50.0,
        help="Radius in miles when searching near a ZIP code (default: 50)",
    )
    p.add_argument("--limit", type=int, default=20, help="Max results to show")
    args = p.parse_args()

    if not args.query and not args.zip:
        p.error("At least one of --zip or --query is required")

    results = _search_args(args)
    if not results:
        _print_no_results(args)
        return

    for i, f in enumerate(results[: args.limit], start=1):
        print(f"{i}. {f.name} — {f.city}, {f.state} {f.zip_code}")
        if f.address:
            print(f"   {f.address}")
        if f.start_date and f.end_date:
            print(f"   Dates: {f.start_date} to {f.end_date}")
        if f.latitude and f.longitude:
            print(f"   Location: {f.latitude}, {f.longitude}")
        if f.categories:
            print(f"   Categories: {', '.join(f.categories)}")
        print()


if __name__ == "__main__":
    main()
