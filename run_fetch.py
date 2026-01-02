"""CLI entry point.

This script fetches jobs, normalizes them, and writes a JSON list to disk.

Examples:
    python run_fetch.py --out jobs.json
    python run_fetch.py --out jobs.json --limit 100 --query "embedded firmware"
    python run_fetch.py --out jobs.json --no-filter

The output is a list of dicts (serialized Pydantic models).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from job_engine.sources.remotive import RemotiveSource
from job_engine.sources.arbeitnow import ArbeitnowSource


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch and normalize jobs from multiple sources.")
    p.add_argument("--out", type=str, default="jobs.json", help="Output JSON file path.")
    p.add_argument("--limit", type=int, default=20, help="Max jobs to output (soft cap).")
    p.add_argument("--query", type=str, default=None, help="Optional search query passed to source.")
    p.add_argument(
        "--filter-electronics",
        action="store_true",
        help="Enable electronics keyword filtering (default is to keep all roles).",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    remotive = RemotiveSource()
    arbeitnow = ArbeitnowSource()

    # Fetch from both sources; include both even if one source fills the limit.
    remotive_jobs = remotive.fetch(query=args.query, limit=args.limit, filter_electronics=args.filter_electronics)
    arbeitnow_jobs = arbeitnow.fetch(query=args.query, limit=args.limit, filter_electronics=args.filter_electronics)

    # Interleave sources to avoid one source crowding out the other, while deduping by id.
    seen = set()
    jobs = []
    i = 0
    max_len = args.limit
    while len(jobs) < max_len and (i < len(remotive_jobs) or i < len(arbeitnow_jobs)):
        if i < len(remotive_jobs):
            j = remotive_jobs[i]
            if j.id not in seen:
                seen.add(j.id)
                jobs.append(j)
        if len(jobs) >= max_len:
            break
        if i < len(arbeitnow_jobs):
            j = arbeitnow_jobs[i]
            if j.id not in seen:
                seen.add(j.id)
                jobs.append(j)
        i += 1

    # If still under limit, append remaining unique jobs from both lists.
    if len(jobs) < max_len:
        for j in remotive_jobs[i:] + arbeitnow_jobs[i:]:
            if j.id in seen:
                continue
            jobs.append(j)
            seen.add(j.id)
            if len(jobs) >= max_len:
                break

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Pydantic v2: model_dump() -> serializable dict
    # Use json mode to serialize types like HttpUrl to strings for json.dumps
    data = [j.model_dump(mode="json") for j in jobs]
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {len(data)} jobs to: {out_path}")


if __name__ == "__main__":
    main()
