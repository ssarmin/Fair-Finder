#!/usr/bin/env python3
"""Simple CLI to search fairs by ZIP using the LocalJSONRepository."""
import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from src.data.repository import LocalJSONRepository  # noqa: E402


def main():
    p = argparse.ArgumentParser(description="Search fairs by ZIP code")
    p.add_argument("zip", help="ZIP code to search for")
    p.add_argument("--radius", type=float, default=50.0, help="Radius in miles (default: 50)")
    p.add_argument("--limit", type=int, default=20, help="Max results to show")
    args = p.parse_args()

    repo = LocalJSONRepository()
    results = repo.find_by_zip(args.zip, radius_miles=args.radius)

    if not results:
        print("No fairs found for ZIP", args.zip)
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
