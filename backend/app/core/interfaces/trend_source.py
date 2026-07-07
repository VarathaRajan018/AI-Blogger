"""Abstract base class for trend data sources.

All trend sources (Google Trends, NewsAPI, RSS) implement this
interface for uniform trend discovery.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from app.core.models.content import TrendTopic


class BaseTrendSource(ABC):
    """Abstract interface for trend research data sources.

    Concrete implementations fetch trending topics from
    different sources and normalize them into TrendTopic objects.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the name of this trend source.

        Returns:
            Source identifier (e.g., 'google_trends', 'rss', 'newsapi').
        """
        ...

    @abstractmethod
    async def fetch_trends(
        self,
        niches: list[str],
        days_back: int = 7,
        max_results: int = 20,
    ) -> Sequence[TrendTopic]:
        """Fetch trending topics related to the given niches.

        Args:
            niches: List of niche keywords to search for.
            days_back: How many days of history to search.
            max_results: Maximum number of topics to return.

        Returns:
            Sequence of TrendTopic objects, sorted by relevance.
        """
        ...
