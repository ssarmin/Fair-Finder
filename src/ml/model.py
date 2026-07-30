from __future__ import annotations

import calendar 
import re 
from datetime import date, timedelta 
from pathlib import Path 
from typing import Dict, List, Optional, Tuple

import joblib 
from sklearn.feature_extraction.text import TfidfVectorizer 
from sklearn.linear_model import LogisticRegression 
from sklearn.pipeline import Pipeline

ZIP_RE = re.compile(r"\b(\d{5})(?:-\d{4})?\b")
RADIUS_RE = re.compile(
    r"\b(?:within|inside|around|about|under|up to)\s+(\d+(?:\.\d+)?)\s*(?:mile|miles|mi)\b"
)
RADIUS_POST_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*(?:mile|miles|mi)\s*(?:away|from|of|around)?\b")
DATE_PATTERNS = [
    re.compile(
        r"\b(?P<month>\w+)\s+(?P<day>\d{1,2})(?:st|nd|rd|th)?(?:,\s*(?P<year>\d{4}))?\b"
    ),
    re.compile(r"\b(?P<month>\d{1,2})/(?P<day>\d{1,2})(?:/(?P<year>\d{2,4}))?\b"),
    re.compile(r"\b(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})\b"),
]
RELATIVE_DATE_KEYWORDS = {
    "today": 0,
    "tomorrow": 1,
    "this weekend": 0,
    "next weekend": 7,
    "this week": 0,
    "next month": None,
}
CATEGORY_KEYWORDS = {
    "food truck": ["food truck", "food trucks", "foodtruck", "food-truck"],
    "craft": ["craft", "crafts", "handmade", "artisan", "artisans"],
    "art": ["art", "arts", "gallery", "painting", "sculpture"],
    "music": ["music", "live music", "concert", "band", "bands"],
    "farmers market": ["farmers market", "farmers' market", "farm market"],
    "family": ["family", "family-friendly", "family friendly", "kids", "kid-friendly"],
}


def _normalize_text(text: str) -> str:
    return text.lower().strip()


def extract_zip(text: str) -> Optional[str]:
    match = ZIP_RE.search(text)
    return match.group(1) if match else None


def extract_radius(text: str) -> Optional[float]:
    normalized = _normalize_text(text)
    for pattern in (RADIUS_RE, RADIUS_POST_RE):
        match = pattern.search(normalized)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    return None


def _parse_month_name(month: str) -> Optional[int]:
    try:
        return list(calendar.month_name).index(month.capitalize())
    except ValueError:
        try:
            return list(calendar.month_abbr).index(month.capitalize())
        except ValueError:
            return None


def _parse_date_from_match(match: re.Match) -> Optional[date]:
    groups = match.groupdict()
    if "year" in groups and groups["year"] is not None:
        year_text = groups["year"]
        year = int(year_text) if len(year_text) == 4 else 2000 + int(year_text)
    else:
        year = date.today().year

    if groups.get("month") and groups.get("day"):
        month_value = groups["month"]
        day_value = int(groups["day"])
        if month_value.isdigit():
            month = int(month_value)
        else:
            month = _parse_month_name(month_value)
        if month is None:
            return None
        try:
            return date(year, month, day_value)
        except ValueError:
            return None
    return None


def extract_date_range(text: str) -> Optional[Tuple[date, date]]:
    normalized = _normalize_text(text)
    for phrase, offset in RELATIVE_DATE_KEYWORDS.items():
        if phrase in normalized:
            today = date.today()
            if phrase == "this weekend":
                saturday = today + timedelta((5 - today.weekday()) % 7)
                sunday = saturday + timedelta(days=1)
                return saturday, sunday
            if phrase == "next weekend":
                saturday = today + timedelta(((5 - today.weekday()) % 7) + 7)
                sunday = saturday + timedelta(days=1)
                return saturday, sunday
            if phrase == "this week":
                monday = today - timedelta(days=today.weekday())
                sunday = monday + timedelta(days=6)
                return monday, sunday
            if phrase == "next month":
                year = today.year + (1 if today.month == 12 else 0)
                month = 1 if today.month == 12 else today.month + 1
                first_day = date(year, month, 1)
                last_day = date(year, month, calendar.monthrange(year, month)[1])
                return first_day, last_day
            if offset is not None:
                target = today + timedelta(days=offset)
                return target, target
    for pattern in DATE_PATTERNS:
        match = pattern.search(normalized)
        if match:
            parsed = _parse_date_from_match(match)
            if parsed:
                return parsed, parsed
    return None


def extract_categories(text: str) -> List[str]:
    normalized = _normalize_text(text)
    categories: List[str] = []
    for category, phrases in CATEGORY_KEYWORDS.items():
        if any(phrase in normalized for phrase in phrases):
            categories.append(category)
    return categories


class IntentModel:
    def __init__(self, pipeline: Pipeline):
        self.pipeline = pipeline

    def predict(self, text: str) -> Dict[str, Optional[object]]:
        probs = self.pipeline.predict_proba([text])[0]
        classes = list(self.pipeline.classes_)
        best_idx = int(probs.argmax())
        intent = classes[best_idx]
        confidence = float(probs[best_idx])
        return {
            "intent": intent,
            "confidence": confidence,
            "zip": extract_zip(text),
            "radius": extract_radius(text),
            "categories": extract_categories(text),
            "date_range": extract_date_range(text),
        }


def train_intent_model(training_texts: List[str], training_labels: List[str]) -> IntentModel:
    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=5000)),
            ("clf", LogisticRegression(max_iter=1000)),
        ]
    )
    pipeline.fit(training_texts, training_labels)
    return IntentModel(pipeline)


def save_model(model: IntentModel, path: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model.pipeline, str(p))


def load_model(path: str) -> IntentModel:
    pipeline = joblib.load(str(path))
    return IntentModel(pipeline)


def predict_intent(text: str, model_path: str) -> Dict[str, Optional[object]]:
    model = load_model(model_path)
    return model.predict(text)
