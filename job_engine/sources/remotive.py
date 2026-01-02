"""Remotive jobs source connector.

Remotive provides a public JSON endpoint (great for an MVP ingestion layer).
We fetch the data, map fields to our normalized schema, and keep the raw payload.
Optional electronics filtering can be enabled by the caller.

Docs: https://remotive.com/api/remote-jobs

Note: Free APIs can change; treat this as a pluggable connector.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from ..models import JobOpportunity
from ..normalize import extract_function_keywords, extract_requirements, infer_seniority, is_electronics_role
from ..utils import stable_id


class RemotiveSource:
    """Fetch jobs from Remotive and normalize them."""

    name = "remotive"
    base_url = "https://remotive.com/api/remote-jobs"

    def __init__(self, timeout_s: float = 20.0) -> None:
        self._timeout = timeout_s

    @staticmethod
    def _extract_salary(payload: Dict[str, Any]) -> str:
        """Return salary string or 'unknown' if missing/empty."""
        val = payload.get("salary") or payload.get("compensation")
        if isinstance(val, (int, float)):
            return str(val)
        if isinstance(val, str):
            val = val.strip()
            if val:
                return val
        return "unknown"

    def fetch(self, query: Optional[str] = None, limit: int = 200, filter_electronics: bool = False) -> List[JobOpportunity]:
        """Fetch Remotive jobs and return a list of normalized JobOpportunity.

        Args:
            query: Optional free-text query passed to Remotive (search).
            limit: Soft cap to reduce output size for development.
            filter_electronics: If True, keep only electronics-related roles.

        Returns:
            List of JobOpportunity records.
        """
        params: Dict[str, Any] = {}
        if query:
            params["search"] = query

        with httpx.Client(timeout=self._timeout, follow_redirects=True) as client:
            resp = client.get(self.base_url, params=params)
            resp.raise_for_status()
            payload = resp.json()

        jobs = payload.get("jobs", []) or []
        out: List[JobOpportunity] = []

        for j in jobs[: max(limit, 0)]:
            title = (j.get("title") or "").strip()
            company = (j.get("company_name") or "").strip()
            url = (j.get("url") or "").strip()
            desc = (j.get("description") or "").strip()

            if not (title and company and url):
                continue

            if filter_electronics and not is_electronics_role(title, desc):
                continue

            # Remotive has "publication_date" like "2024-01-01T12:34:56"
            pub_dt = (j.get("publication_date") or "").strip()
            date_posted = pub_dt[:10] if len(pub_dt) >= 10 else None

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
                location=(j.get("candidate_required_location") or "Remote"),
                remote=True,
                date_posted=date_posted,
                seniority=seniority,
                function_keywords=function_keywords,
                salary=salary,
                description=desc,
                requirements=requirements,
                raw=j,
            )
            out.append(opp)

        return out
