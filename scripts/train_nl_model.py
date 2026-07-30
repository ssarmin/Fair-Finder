"""Train a small intent classifier for natural-language commands."""
import json
from pathlib import Path

from src.ml.model import train_intent_model, save_model


def main():
    repo_root = Path(__file__).resolve().parents[1]
    data_path = repo_root / "data" / "nl_training.json"
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    texts = [d["text"] for d in data]
    labels = [d["intent"] for d in data]

    model = train_intent_model(texts, labels)
    out = repo_root / "models" / "nl_intent_model.joblib"
    save_model(model, str(out))
    print(f"Saved intent model to {out}")


if __name__ == "__main__":
    main()
