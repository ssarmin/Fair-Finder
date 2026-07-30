"""Run a natural-language query using the trained intent model and repository."""
import argparse
from pathlib import Path

from src.ml.model import load_model
from src.data.repository import LocalJSONRepository


def main():
    parser = argparse.ArgumentParser(description="NL search for fairs")
    parser.add_argument("query", help="Natural-language query string")
    parser.add_argument("--model", default="models/nl_intent_model.joblib", help="Path to intent model")
    parser.add_argument("--radius", type=float, default=50.0)
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of results to show")
    args = parser.parse_args()

    model = load_model(args.model)
    res = model.predict(args.query)
    repo = LocalJSONRepository(data_dir=Path(args.data_dir) if args.data_dir else None)

    intent = res.get("intent")
    zip_code = res.get("zip")
    confidence = res.get("confidence")

    print(f"Query: '{args.query}'")
    print(f"Intent: {intent} (confidence={confidence:.2f})")
    if zip_code:
        print(f"Detected ZIP: {zip_code}")
    print("-" * 50)

    if zip_code and intent == "find_by_zip":
        fairs = repo.find_by_zip(zip_code, radius_miles=args.radius)
    else:
        fairs = repo.search(args.query, zip_code=zip_code, radius_miles=args.radius)

    if not fairs:
        print("No matching fairs found.")
        return

    for i, f in enumerate(fairs[:args.limit], 1):
        print(f"{i}. {f.name} — {f.city}, {f.state} {f.zip_code or ''}")
        if f.address:
            print(f"   {f.address}")
        if f.start_date and f.end_date:
            print(f"   Dates: {f.start_date} to {f.end_date}")
        if f.categories:
            print(f"   Categories: {', '.join(f.categories)}")
        print()


if __name__ == "__main__":
    main()