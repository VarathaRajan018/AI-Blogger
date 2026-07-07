"""RSS feed data source for trend research.

Parses configured RSS feeds and extracts recent articles
relevant to the configured niches.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Sequence
from time import mktime

from app.core.interfaces.trend_source import BaseTrendSource
from app.core.models.content import TrendTopic
from app.utils.logging import get_logger

logger = get_logger(__name__)


class RSSSource(BaseTrendSource):
    """Fetch trending topics from RSS feeds.

    Parses a list of RSS feed URLs and extracts recent articles
    that match the configured niches.

    Args:
        feed_urls: List of RSS feed URLs to parse.
    """

    def __init__(self, feed_urls: list[str]) -> None:
        self._feed_urls = feed_urls

    @property
    def source_name(self) -> str:
        """Return 'rss'."""
        return "rss"

    async def fetch_trends(
        self,
        niches: list[str],
        days_back: int = 7,
        max_results: int = 20,
    ) -> Sequence[TrendTopic]:
        """Fetch trending topics from RSS feeds.

        Runs feedparser in a thread pool since it's synchronous.

        Args:
            niches: Niche keywords to filter by.
            days_back: Only include articles from last N days.
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
        """Synchronous RSS feed parsing (runs in executor).

        Args:
            niches: Niche keywords for relevance filtering.
            days_back: Days to look back.
            max_results: Maximum results.

        Returns:
            Filtered and scored TrendTopic list.
        """
        try:
            import feedparser
        except ImportError:
            logger.error("feedparser not installed — skipping RSS source")
            return []

        topics: list[TrendTopic] = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
        niche_lower = [n.lower() for n in niches]

        for feed_url in self._feed_urls:
            try:
                feed = feedparser.parse(feed_url)

                if feed.bozo and not feed.entries:
                    logger.warning("rss feed parse error", url=feed_url)
                    continue

                for entry in feed.entries[:30]:  # Cap per feed
                    title = entry.get("title", "")
                    link = entry.get("link", "")
                    summary = entry.get("summary", "")
                    published = entry.get("published_parsed")

                    # Parse publish date
                    pub_date: datetime | None = None
                    if published:
                        try:
                            pub_date = datetime.fromtimestamp(
                                mktime(published), tz=timezone.utc
                            )
                        except (ValueError, OverflowError):
                            pub_date = None

                    # Skip old articles
                    if pub_date and pub_date < cutoff:
                        continue

                    # Calculate relevance based on niche keyword matching
                    text_lower = f"{title} {summary}".lower()
                    matching_niches = [
                        n for n in niche_lower if n in text_lower
                    ]
                    if not matching_niches:
                        continue

                    relevance = min(
                        40.0 + (len(matching_niches) * 20.0), 100.0
                    )

                    topics.append(
                        TrendTopic(
                            title=title.strip(),
                            source="rss",
                            relevance_score=relevance,
                            url=link,
                            description=summary[:300] if summary else None,
                            published_date=pub_date,
                            niche=matching_niches[0] if matching_niches else None,
                        )
                    )

            except Exception as exc:
                logger.warning(
                    "rss feed failed",
                    url=feed_url,
                    error=str(exc),
                )
                continue

        # Deduplicate by title
        seen: set[str] = set()
        unique: list[TrendTopic] = []
        for t in topics:
            key = t.title.lower().strip()
            if key not in seen:
                seen.add(key)
                unique.append(t)

        # Sort by relevance
        unique.sort(key=lambda t: t.relevance_score, reverse=True)

        logger.info(
            "rss fetch complete",
            feeds_parsed=len(self._feed_urls),
            topics_found=len(unique),
        )

        return unique[:max_results]
