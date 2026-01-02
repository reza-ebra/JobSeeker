"""Normalization & heuristics.

This module contains deterministic parsing logic:
- electronics-focused keyword filtering (MVP)
- seniority inference
- function keyword extraction
- requirements extraction (lightweight heuristic)

You can later replace these with learned models or embeddings, but keeping these
heuristics centralized makes the system predictable and testable.
"""

from __future__ import annotations

import re
from typing import List, Tuple

from .utils import uniq_preserve_order


# Practical include keywords for electronics/electrical/hardware roles.
INCLUDE_KEYWORDS = [
    "electronics",
    "electronic",
    "electrical",
    "hardware",
    "embedded",
    "firmware",
    "pcb",
    "schematic",
    "analog",
    "mixed-signal",
    "mixed signal",
    "power electronics",
    "power supply",
    "dc-dc",
    "buck",
    "boost",
    "rf",
    "antenna",
    "signal integrity",
    "emi",
    "emc",
    "verification",
    "validation",
    "test engineer",
    "lab engineer",
    "board bring-up",
    "board bring up",
    "fpga",
    "microcontroller",
    "stm32",
    "esp32",
    "FAE",
    "Field Application Engineer",
]

# Obvious exclusions to reduce noise (you can tune later).
EXCLUDE_KEYWORDS = [
    "marketing",
    "sales",
    "account executive",
    "recruiter",
    "talent acquisition",
    "hr",
    "human resources",
    "product marketing",
]


SENIORITY_PATTERNS: List[Tuple[str, str]] = [
    (r"\bintern\b", "intern"),
    (r"\b(entry\s*level|junior|jr\.?|associate)\b", "junior"),
    (r"\b(mid\s*level|intermediate)\b", "mid"),
    (r"\b(senior|sr\.?|lead)\b", "senior"),
    (r"\b(staff)\b", "staff"),
    (r"\b(principal|architect)\b", "principal"),
    (r"\b(manager|engineering manager)\b", "manager"),
    (r"\b(director)\b", "director"),
    (r"\b(vice president|vp)\b", "vp"),
    (r"\b(chief|cxo|cto|ceo|cpo|cfo)\b", "cxo"),
]


def infer_seniority(title: str) -> str:
    """Infer seniority from the job title using conservative regex patterns."""
    t = (title or "").lower()
    for pat, label in SENIORITY_PATTERNS:
        if re.search(pat, t):
            return label
    return "unknown"


def extract_function_keywords(text: str) -> List[str]:
    """Extract a small set of function keywords from combined title+description."""
    t = (text or "").lower()
    hits: List[str] = []
    for kw in INCLUDE_KEYWORDS:
        if kw in t:
            # Normalize some variants for consistency in downstream processing
            normalized = (
                kw.replace("mixed signal", "mixed-signal")
                .replace("board bring up", "board bring-up")
            )
            hits.append(normalized)
    return uniq_preserve_order(hits)


def is_electronics_role(title: str, description: str) -> bool:
    """Heuristic filter: include electronics-related roles, exclude obvious noise."""
    blob = f"{title or ''}\n{description or ''}".lower()

    # Exclusions first (fast fail)
    for kw in EXCLUDE_KEYWORDS:
        if kw in blob:
            return False

    # Require at least one include keyword.
    return any(kw in blob for kw in INCLUDE_KEYWORDS)


REQ_BULLET_RE = re.compile(
    r"(?:^|\n)\s*(?:[-*•]|\d+\.)\s+(.+?)(?=\n\s*(?:[-*•]|\d+\.)\s+|\Z)",
    flags=re.DOTALL,
)


def extract_requirements(description: str, max_items: int = 12) -> List[str]:
    """Extract bullet-like lines from description as a naive 'requirements' list.

    This works reasonably well for many job posts that include bullet lists.
    For real products, you might do section detection (\"Requirements\", \"What you'll do\")
    or LLM-assisted parsing, but this is a good deterministic baseline.
    """
    if not description:
        return []

    cleaned = re.sub(r"\r", "", description).strip()
    items = [m.group(1).strip() for m in REQ_BULLET_RE.finditer(cleaned)]
    # Keep items short and readable
    items = [re.sub(r"\s+", " ", it) for it in items]
    items = [it for it in items if 3 <= len(it) <= 220]
    return uniq_preserve_order(items)[:max_items]
