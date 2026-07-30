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
    args = parser.parse_args()

    model = load_model(args.model)
    res = model.predict(args.query)
    repo = LocalJSONRepository(data_dir=Path(args.data_dir) if args.data_dir else None)

    intent = res.get("intent")
    zip_code = res.get("zip")
    confidence = res.get("confidence")

    print(f"Intent: {intent} (confidence={confidence:.2f})")
    if zip_code and intent == "find_by_zip":
        fairs = repo.find_by_zip(zip_code, radius_miles=args.radius)
    else:
        fairs = repo.search(args.query, zip_code=zip_code, radius_miles=args.radius)

    for f in fairs[:20]:
        print(f"- {f.name} — {f.city}, {f.state} ({f.zip_code})")


if __name__ == "__main__":
    main()
