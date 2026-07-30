# Fair-Finder

Fair-Finder is a small Python project for searching fairs and exhibitions using local JSON data.

## What this project does

- Loads fair listings from `data/fairs.json`.
- Allows searching by ZIP code and/or natural language queries.
- Supports a hybrid search engine with hard filters and semantic ranking.
- Uses Hugging Face Sentence-Transformers when available and falls back to TF-IDF when needed.

## Project structure

- `data/` — local sample JSON data for fairs and ZIP centroids.
- `src/data/` — models and repository search logic.
- `scripts/search_by_zip.py` — simple CLI for ZIP and natural language search.
- `tests/` — unit tests for repository behavior.
- `requirements.txt` — Python dependencies required to run the code.
- `pyproject.toml` — package metadata and tooling configuration.

## Setup

1. Create and activate a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Running locally

Search fairs near a ZIP code using the CLI:

```bash
python scripts/search_by_zip.py --zip 62704
```

Search with a natural language query:

```bash
python scripts/search_by_zip.py --query 'outdoor pottery markets under $50'
```

Search near a ZIP code with a query, radius, or result limit:

```bash
python scripts/search_by_zip.py --zip 27606 --query 'outdoor pottery markets under $50' --radius 20 --limit 5
```

## How search works

`LocalJSONRepository.search(query, zip_code, radius_miles)` performs:

1. Extraction of simple constraints from the query:
   - price filters like `under $50`
   - environment filters like `outdoor` or `indoor`
2. Location filtering by ZIP code and radius.
3. Candidate filtering by price, environment, and query-related terms.
4. Semantic ranking of remaining candidates.

The ranking prefers a Sentence-Transformers model (`all-MiniLM-L6-v2`) when available. If the model cannot be loaded, the repository automatically falls back to a TF-IDF similarity search so the application still works offline or behind a blocked network.

This helps conceptually related queries like `agriculture fair` or `food market` match fairs with categories such as `Agriculture`, `Food`, or `Market`.

## Tests

Run the unit tests locally with:

```bash
python -m unittest discover -s tests
```

The tests cover:

- ZIP radius lookup with `find_by_zip()`.
- Natural language query search and filtering.
- Transformer-based semantic search behavior.
- TF-IDF fallback behavior when the transformer model is unavailable.

## Linting

Run linting with Ruff:

```bash
ruff check src scripts tests
```

## Continuous Integration

The repository includes a GitHub Actions workflow at `.github/workflows/python-ci.yml`.

The CI pipeline performs the following steps on every push and pull request to `main`:

- checks out the repository
- sets up Python 3.11 and 3.12
- installs the development dependencies from `requirements.txt`
- runs a syntax check on `src` and `scripts`
- runs the unit test suite
- runs a smoke test for `scripts/search_by_zip.py`
