"""Base classes for source connectors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from ..models import JobOpportunity


class JobSource(ABC):
    """Abstract base class for a job source connector."""

    name: str

    @abstractmethod
    def fetch(self, query: Optional[str] = None, limit: int = 200) -> List[JobOpportunity]:
        """Fetch jobs and return normalized opportunities."""
        raise NotImplementedError
