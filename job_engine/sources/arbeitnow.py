"""Arbeitnow jobs source connector.

Docs: https://www.arbeitnow.com/api/job-board-api

We paginate through the public job board API, normalize fields, and optionally
filter for all roles.
"""

from __future__ import annotations

from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional

import httpx

from ..models import JobOpportunity
from ..normalize import extract_function_keywords, extract_requirements, infer_seniority, is_electronics_role
from ..utils import stable_id


class ArbeitnowSource:
    """Fetch jobs from Arbeitnow and normalize them."""

    name = "arbeitnow"
    base_url = "https://www.arbeitnow.com/api/job-board-api"

    def __init__(self, timeout_s: float = 20.0, max_retries: int = 3, backoff_s: float = 2.0) -> None:
        self._timeout = timeout_s
        self._max_retries = max_retries
        self._backoff_s = backoff_s

    def _parse_date_posted(self, created_at: Any) -> Optional[str]:
        """Normalize various created_at formats to YYYY-MM-DD."""
        if created_at is None:
            return None

        if isinstance(created_at, str):
            created_at = created_at.strip()
            if not created_at:
                return None
            # Best effort for ISO-like strings; fall back to leading 10 chars.
            try:
                return datetime.fromisoformat(created_at.replace("Z", "+00:00")).date().isoformat()
            except ValueError:
                return created_at[:10] if len(created_at) >= 10 else None

        if isinstance(created_at, (int, float)):
            ts = float(created_at)
            # Arbeitnow may return epoch in ms; convert if so.
            if ts > 1e12:
                ts /= 1000.0
            try:
                return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
            except (OverflowError, OSError, ValueError):
                return None

        return None

    @staticmethod
    def _extract_salary(payload: Dict[str, Any]) -> str:
        """Return salary string or 'unknown' if missing/empty."""
        val = (
            payload.get("salary_range")
            or payload.get("salary")
            or payload.get("compensation")
        )
        if isinstance(val, (int, float)):
            return str(val)
        if isinstance(val, str):
            val = val.strip()
            if val:
                return val
        return "unknown"

    def fetch(self, query: Optional[str] = None, limit: int = 20, filter_electronics: bool = False) -> List[JobOpportunity]:
        """Fetch Arbeitnow jobs and return a list of normalized JobOpportunity."""
        out: List[JobOpportunity] = []
        page = 1
        q = (query or "").strip().lower()

        with httpx.Client(timeout=self._timeout, follow_redirects=True) as client:
            while len(out) < max(limit, 0):
                params: Dict[str, Any] = {"page": page}
                retries = 0
                while True:
                    try:
                        resp = client.get(self.base_url, params=params)
                        resp.raise_for_status()
                        break
                    except httpx.HTTPStatusError as exc:
                        if exc.response.status_code == 429 and retries < self._max_retries:
                            sleep_s = self._backoff_s * (2**retries)
                            time.sleep(sleep_s)
                            retries += 1
                            continue
                        raise
                payload = resp.json()

                jobs = payload.get("data") or payload.get("jobs") or []
                if not jobs:
                    break

                for j in jobs:
                    title = (j.get("title") or "").strip()
                    company = (j.get("company_name") or j.get("company") or "").strip()
                    url = (j.get("url") or "").strip()
                    desc = (j.get("description") or "").strip()

                    if not (title and company and url):
                        continue

                    if q and q not in f"{title.lower()} {desc.lower()}":
                        continue

                    if filter_electronics and not is_electronics_role(title, desc):
                        continue

                    date_posted = self._parse_date_posted(j.get("created_at"))

                    blob = f"{title}\n{desc}"
                    seniority = infer_seniority(title)
                    function_keywords = extract_function_keywords(blob)
                    requirements = extract_requirements(desc)
                    salary = self._extract_salary(j)

                    opp = JobOpportunity(
                        id=stable_id(self.name, url),
                        source=self.name,
                        company_name=company,
                        job_title=title,
                        job_url=url,
                        location=(j.get("location") or "Unknown"),
                        remote=bool(j.get("remote", False)),
                        date_posted=date_posted,
                        seniority=seniority,
                        function_keywords=function_keywords,
                        salary=salary,
                        description=desc,
                        requirements=requirements,
                        raw=j,
                    )
                    out.append(opp)

                    if len(out) >= max(limit, 0):
                        break

                page += 1

        return out
