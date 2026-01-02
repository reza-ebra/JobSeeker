"""Job engine package.

The package is structured to be easily productized:
- `models.py` defines your stable schema (what your product owns).
- `sources/` contains per-source connectors that fetch jobs.
- `normalize.py` contains deterministic parsing and heuristics.
"""
