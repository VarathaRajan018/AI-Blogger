"""TrendResearcher pipeline stage.

Fetches trending topics from multiple sources (Google Trends, RSS)
in parallel, deduplicates, ranks, and selects the best topic for
content generation.
"""

from __future__ import annotations

import asyncio
from typing import Sequence

from app.config import Settings
from app.core.models.content import TrendTopic
from app.core.models.pipeline import (
    FailureStrategy,
    PipelineContext,
    StageResult,
    StageStatus,
)
from app.pipeline.stages.base_stage import BaseStage
from app.providers.trend_sources.google_trends_source import GoogleTrendsSource
from app.providers.trend_sources.rss_source import RSSSource
from app.utils.logging import get_logger

logger = get_logger(__name__)


class TrendResearcherStage(BaseStage):
    """Pipeline stage that discovers trending topics.

    Fetches from Google Trends and RSS feeds in parallel,
    combines and deduplicates results, ranks by relevance,
    and stores the top topics in context.

    Args:
        settings: Application settings.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

        # Initialize trend sources
        self._sources = [
            GoogleTrendsSource(
                timeout=settings.pytrends_timeout,
                retries=settings.pytrends_retries,
            ),
            RSSSource(feed_urls=settings.rss_feeds_list),
        ]

    @property
    def name(self) -> str:
        """Return 'trend_researcher'."""
        return "trend_researcher"

    def on_failure(
        self, context: PipelineContext, error: Exception
    ) -> FailureStrategy:
        """Trend research failure is recoverable — skip and use fallback topics."""
        return FailureStrategy.SKIP

    async def execute(self, context: PipelineContext) -> StageResult:
        """Fetch trends from all sources in parallel.

        Args:
            context: Pipeline context with niches configured.

        Returns:
            StageResult with discovered topics.
        """
        niches = context.niches
        if not niches:
            logger.warning("no niches configured, using defaults")
            niches = ["artificial intelligence", "python", "software engineering"]

        logger.info(
            "researching trends",
            niches=niches,
            sources=[s.source_name for s in self._sources],
        )

        # Fetch from all sources in parallel
        tasks = [
            source.fetch_trends(niches=niches, days_back=7, max_results=15)
            for source in self._sources
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect successful results
        all_topics: list[TrendTopic] = []
        for i, result in enumerate(results):
            source_name = self._sources[i].source_name
            if isinstance(result, Exception):
                logger.warning(
                    "trend source failed",
                    source=source_name,
                    error=str(result),
                )
                continue
            all_topics.extend(result)
            logger.info(
                "trend source returned",
                source=source_name,
                topics=len(result),
            )

        # Deduplicate by normalized title
        seen: set[str] = set()
        unique_topics: list[TrendTopic] = []
        for topic in all_topics:
            key = topic.title.lower().strip()
            if key not in seen:
                seen.add(key)
                unique_topics.append(topic)

        # Sort by relevance score (highest first)
        unique_topics.sort(key=lambda t: t.relevance_score, reverse=True)

        # Take top N topics
        top_count = max(5, self._settings.pipeline_posts_per_run * 3)
        selected = unique_topics[:top_count]

        if not selected:
            logger.warning("no trends found from any source")

            # Fallback: use niches directly as topics
            selected = [
                TrendTopic(
                    title=f"Latest developments in {niche}",
                    source="fallback",
                    relevance_score=50.0,
                    niche=niche,
                    description=f"Auto-generated topic for {niche} niche",
                )
                for niche in niches[:3]
            ]
            logger.info("using fallback topics", count=len(selected))

        # Store in context
        context.trends = [t.to_dict() for t in selected]

        logger.info(
            "trend research complete",
            total_discovered=len(all_topics),
            unique_topics=len(unique_topics),
            selected=len(selected),
            top_topic=selected[0].title if selected else "none",
        )

        return StageResult(
            stage_name=self.name,
            status=StageStatus.SUCCESS,
            data={
                "topics_found": len(unique_topics),
                "topics_selected": len(selected),
                "top_topic": selected[0].title if selected else None,
            },
        )
