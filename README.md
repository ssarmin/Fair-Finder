# Fair-Finder

Fair-Finder is a small Python project for searching fairs and exhibitions by ZIP code.

## Project structure

- `data/` — sample local JSON data for fairs and ZIP centroids
- `src/data/` — data-layer implementation with models and repository logic
- `scripts/search_by_zip.py` — CLI script to search fairs by ZIP, natural language query, or both
- `tests/` — unit tests for the data layer
- `.github/workflows/python-ci.yml` — GitHub Actions workflow for CI
- `requirements.txt` — development dependency file for linting
- `pyproject.toml` — project metadata and tool configuration

## Setup

1. Create a virtual environment (recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install the development requirements:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Running locally

Search fairs by ZIP code using the CLI:

```bash
python scripts/search_by_zip.py --zip 62704
```

Search with a natural language query:

```bash
python scripts/search_by_zip.py --query 'outdoor pottery markets under $50'
python scripts/search_by_zip.py --query "outdoor pottery markets under $50"
```

The query engine now uses lightweight semantic similarity matching over fair names, descriptions, categories, and location metadata. This helps conceptually related queries like `agriculture fair` or `food market` match fairs with categories such as `Agriculture`, `Food`, or `Market`.

Search near a ZIP code and filter by query:

```bash
python scripts/search_by_zip.py --zip 27606 --query 'outdoor pottery markets under $50' --limit 5
python scripts/search_by_zip.py --zip 27606 --query "outdoor pottery markets under $50" --limit 5
```

Add a search radius or limit:

```bash
python scripts/search_by_zip.py --zip 62704 --radius 20 --limit 5
```

## Testing

Run unit tests locally with:

```bash
python -m unittest discover -s tests
```

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
