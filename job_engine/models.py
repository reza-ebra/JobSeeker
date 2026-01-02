"""Data models for the job engine.

The key idea: your product should own a *stable* normalized schema regardless of the
upstream job source(s). We also keep the `raw` payload so you can re-parse later
without re-fetching.

This file uses Pydantic v2.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, HttpUrl


Seniority = Literal[
    "intern",
    "junior",
    "mid",
    "senior",
    "staff",
    "principal",
    "manager",
    "director",
    "vp",
    "cxo",
    "unknown",
]


class JobOpportunity(BaseModel):
    """A normalized job record.

    Fields are intentionally explicit and stable. Prefer adding new fields rather
    than changing existing ones once you start storing these in a database.
    """

    id: str = Field(..., description="Deterministic ID (e.g., sha256(source + url)).")
    source: str = Field(..., description="Source identifier, e.g. 'remotive'.")

    company_name: str
    job_title: str
    job_url: HttpUrl

    location: str = "Unknown"
    remote: bool = False
    date_posted: Optional[str] = Field(
        default=None,
        description="Posting date (YYYY-MM-DD) when available; may be None.",
    )

    seniority: Seniority = "unknown"
    function_keywords: List[str] = Field(default_factory=list)

    description: str = ""
    requirements: List[str] = Field(default_factory=list)
    salary: str = Field(default="unknown", description="Compensation info as-provided by source, or 'unknown'.")

    raw: Dict[str, Any] = Field(default_factory=dict, description="Original payload.")
