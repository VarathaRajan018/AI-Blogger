"""Google Trends data source using pytrends.

Fetches trending topics and related queries from Google Trends
for the configured niches.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Sequence

from app.core.interfaces.trend_source import BaseTrendSource
from app.core.models.content import TrendTopic
from app.utils.logging import get_logger

logger = get_logger(__name__)


class GoogleTrendsSource(BaseTrendSource):
    """Fetch trending topics from Google Trends via pytrends.

    Args:
        timeout: Request timeout in seconds.
        retries: Number of retry attempts.
        geo: Geographic region (default: '' for worldwide).
    """

    def __init__(
        self,
        timeout: int = 30,
        retries: int = 3,
        geo: str = "",
    ) -> None:
        self._timeout = timeout
        self._retries = retries
        self._geo = geo

    @property
    def source_name(self) -> str:
        """Return 'google_trends'."""
        return "google_trends"

    async def fetch_trends(
        self,
        niches: list[str],
        days_back: int = 7,
        max_results: int = 20,
    ) -> Sequence[TrendTopic]:
        """Fetch trending topics from Google Trends.

        Uses pytrends to search for trending searches related
        to each niche keyword. Runs in a thread pool executor
        since pytrends is synchronous.

        Args:
            niches: List of niche keywords to search.
            days_back: Number of days to look back.
            max_results: Maximum topics to return.

        Returns:
            List of TrendTopic objects sorted by relevance.
        """
        loop = asyncio.get_event_loop()
        topics = await loop.run_in_executor(
            None, self._fetch_sync, niches, days_back, max_results
        )
        return topics

    def _fetch_sync(
        self,
        niches: list[str],
        days_back: int,
        max_results: int,
    ) -> list[TrendTopic]:
        """Synchronous Google Trends fetching (runs in executor).

        Args:
            niches: Niche keywords.
            days_back: Days to look back.
            max_results: Max topics.

        Returns:
            List of TrendTopic objects.
        """
        try:
            from pytrends.request import TrendReq
        except ImportError:
            logger.error("pytrends not installed — skipping Google Trends")
            return []

        topics: list[TrendTopic] = []

        try:
            pytrends = TrendReq(
                hl="en-US",
                tz=360,
                timeout=(self._timeout, self._timeout),
                retries=self._retries,
            )

            # Process niches in batches of 5 (pytrends limit)
            for i in range(0, len(niches), 5):
                batch = niches[i : i + 5]

                try:
                    pytrends.build_payload(
                        kw_list=batch,
                        timeframe=f"now {days_back}-d",
                        geo=self._geo,
                    )

                    # Get related queries for each keyword
                    related = pytrends.related_queries()

                    for keyword, data in related.items():
                        if data is None:
                            continue

                        # Top queries
                        top_df = data.get("top")
                        if top_df is not None and not top_df.empty:
                            for _, row in top_df.head(5).iterrows():
                                query = str(row.get("query", ""))
                                value = float(row.get("value", 50))
                                if query:
                                    topics.append(
                                        TrendTopic(
                                            title=query,
                                            source="google_trends",
                                            relevance_score=min(value, 100),
                                            niche=keyword,
                                            description=f"Trending query related to '{keyword}'",
                                        )
                                    )

                        # Rising queries (potentially viral)
                        rising_df = data.get("rising")
                        if rising_df is not None and not rising_df.empty:
                            for _, row in rising_df.head(3).iterrows():
                                query = str(row.get("query", ""))
                                if query:
                                    topics.append(
                                        TrendTopic(
                                            title=query,
                                            source="google_trends",
                                            relevance_score=90.0,  # Rising = high relevance
                                            niche=keyword,
                                            description=f"Rising query for '{keyword}'",
                                        )
                                    )

                except Exception as batch_err:
                    logger.warning(
                        "google trends batch failed",
                        batch=batch,
                        error=str(batch_err),
                    )
                    continue

        except Exception as exc:
            logger.error(
                "google trends source failed",
                error=str(exc),
                exc_info=True,
            )

        # Deduplicate by title
        seen_titles: set[str] = set()
        unique_topics: list[TrendTopic] = []
        for topic in topics:
            normalized = topic.title.lower().strip()
            if normalized not in seen_titles:
                seen_titles.add(normalized)
                unique_topics.append(topic)

        # Sort by relevance and limit
        unique_topics.sort(key=lambda t: t.relevance_score, reverse=True)

        logger.info(
            "google trends fetch complete",
            topics_found=len(unique_topics),
            niches_searched=len(niches),
        )

        return unique_topics[:max_results]
