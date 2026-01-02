"""Utility helpers shared across the engine."""

from __future__ import annotations

import hashlib
from typing import Iterable, List


def stable_id(*parts: str) -> str:
    """Create a deterministic identifier from a set of string parts."""
    joined = "|".join(p.strip() for p in parts if p is not None)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def uniq_preserve_order(items: Iterable[str]) -> List[str]:
    """Deduplicate while preserving first-seen order."""
    seen = set()
    out: List[str] = []
    for it in items:
        if not it:
            continue
        key = it.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out
