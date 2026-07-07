"""Content domain models — data structures for pipeline stage outputs.

These Pydantic/dataclass models define the shape of data passed
between pipeline stages via PipelineContext.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class TrendTopic:
    """A single trending topic discovered by trend research.

    Attributes:
        title: Topic title or headline.
        source: Where this trend was found (google_trends, rss, newsapi).
        relevance_score: 0-100 relevance to configured niches.
        url: Optional URL to the source article.
        description: Brief description or summary.
        published_date: When the trend was published/detected.
        niche: Which niche this trend belongs to.
    """

    title: str
    source: str
    relevance_score: float = 50.0
    url: Optional[str] = None
    description: Optional[str] = None
    published_date: Optional[datetime] = None
    niche: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "title": self.title,
            "source": self.source,
            "relevance_score": self.relevance_score,
            "url": self.url,
            "description": self.description,
            "published_date": (
                self.published_date.isoformat() if self.published_date else None
            ),
            "niche": self.niche,
        }


@dataclass
class KeywordReport:
    """Keyword research results for a selected topic.

    Attributes:
        primary_keyword: Main target keyword.
        search_volume: Estimated monthly search volume.
        competition_score: 0-1 competition difficulty score.
        lsi_keywords: Latent semantic indexing / related keywords.
        search_intent: User intent (informational, transactional, etc.).
        suggested_titles: AI-suggested blog post title variations.
        topic_title: The original trend topic this came from.
    """

    primary_keyword: str
    lsi_keywords: list[str] = field(default_factory=list)
    search_volume: Optional[int] = None
    competition_score: Optional[float] = None
    search_intent: str = "informational"
    suggested_titles: list[str] = field(default_factory=list)
    topic_title: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "primary_keyword": self.primary_keyword,
            "lsi_keywords": self.lsi_keywords,
            "search_volume": self.search_volume,
            "competition_score": self.competition_score,
            "search_intent": self.search_intent,
            "suggested_titles": self.suggested_titles,
            "topic_title": self.topic_title,
        }


@dataclass
class ContentDraft:
    """AI-generated blog post content.

    Attributes:
        title: Blog post title.
        body_html: Full HTML body of the post.
        meta_description: SEO meta description (150-160 chars).
        tags: Post tags/labels for categorization.
        primary_keyword: Target SEO keyword.
        lsi_keywords: Related keywords used in the content.
        word_count: Total word count of the body.
    """

    title: str
    body_html: str
    meta_description: str = ""
    tags: list[str] = field(default_factory=list)
    primary_keyword: str = ""
    lsi_keywords: list[str] = field(default_factory=list)
    word_count: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "title": self.title,
            "body_html": self.body_html,
            "meta_description": self.meta_description,
            "tags": self.tags,
            "primary_keyword": self.primary_keyword,
            "lsi_keywords": self.lsi_keywords,
            "word_count": self.word_count,
        }


@dataclass
class SEOReport:
    """SEO validation report for a content draft.

    Attributes:
        score: Overall SEO score (0-100).
        passed_checks: List of checks that passed.
        failed_checks: List of checks that failed with descriptions.
        suggestions: Improvement suggestions.
    """

    score: int = 0
    passed_checks: list[dict] = field(default_factory=list)
    failed_checks: list[dict] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "score": self.score,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "suggestions": self.suggestions,
        }


@dataclass
class PublishResult:
    """Result of publishing a post to a blog platform.

    Attributes:
        post_id: Platform-assigned post ID.
        url: Public URL of the published post.
        published_at: When the post was published.
        platform: Which platform it was published to.
    """

    post_id: str
    url: str
    published_at: Optional[datetime] = None
    platform: str = "blogger"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "post_id": self.post_id,
            "url": self.url,
            "published_at": (
                self.published_at.isoformat() if self.published_at else None
            ),
            "platform": self.platform,
        }
