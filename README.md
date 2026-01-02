# Job Engine MVP (Python)

This is a minimal, product-friendly foundation for a **job ingestion engine** that:
- Pulls jobs from public **JSON API sources** (Remotive, Arbeitnow)
- Normalizes them into a stable **JobOpportunity** schema
- Optionally filters for **electronics/electrical engineering** roles using pragmatic keyword logic
- Outputs a **JSON list** ready for storage, downstream enrichment, or UI

## Quick start

1) Create a virtualenv (recommended) and install dependencies:

```bash
pip install -r requirements.txt
```

2) Run the fetcher and write results to `jobs.json`:

```bash
python run_fetch.py --out jobs.json
```

3) Optional flags:

```bash
python run_fetch.py --out jobs.json --limit 10
python run_fetch.py --out jobs.json --query "embedded firmware"
python run_fetch.py --out jobs.json --filter-electronics   # turn on electronics-only filtering
```

## Notes / next steps
- Add persistence (SQLite/Postgres) to keep history and dedupe across runs.
- Add more sources (Greenhouse/Lever connectors) following the `JobSource` interface.
- Replace keyword filtering with embeddings-based ranking once ingestion is stable.
