"""Pipeline domain models — shared context and stage results.

PipelineContext is the state bag passed between pipeline stages.
Each stage reads its inputs and writes its outputs to the context.
"""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


class StageStatus(str, enum.Enum):
    """Result status of a pipeline stage execution."""

    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"


class FailureStrategy(str, enum.Enum):
    """What to do when a stage fails."""

    RETRY = "retry"
    SKIP = "skip"
    ABORT = "abort"


@dataclass
class StageResult:
    """Result of a single pipeline stage execution.

    Attributes:
        stage_name: Name of the stage that produced this result.
        status: Success, skipped, or failed.
        data: Arbitrary output data from the stage.
        error: Error message if failed.
        duration_seconds: How long the stage took to execute.
    """

    stage_name: str
    status: StageStatus
    data: Any = None
    error: Optional[str] = None
    duration_seconds: float = 0.0


@dataclass
class PipelineContext:
    """Shared state bag passed between pipeline stages.

    Each pipeline stage reads its required inputs from this context
    and writes its outputs back. The Orchestrator creates this at
    the start of a run and passes it to each stage sequentially.

    Attributes:
        run_id: UUID of the current pipeline run.
        blog_id: UUID of the target blog.
        blog_config: Blog configuration dict (niches, settings).
        dry_run: If True, skip publishing to Blogger.
        niches: List of niche keywords for trend research.
        trends: List of discovered trending topics.
        market_analysis: Ranked topics with opportunity scores.
        keywords: Keyword research results.
        content_draft: Generated blog post content.
        image_suggestions: Suggested images for the post.
        seo_report: SEO validation results.
        publish_result: Publishing outcome (post_id, url).
        social_captions: Generated social media captions.
        analytics: Analytics data collected.
        stage_results: Results from each completed stage.
        metadata: Arbitrary metadata for extensions.
    """

    run_id: uuid.UUID
    blog_id: uuid.UUID
    blog_config: dict = field(default_factory=dict)
    dry_run: bool = False

    # Stage data — populated as pipeline progresses
    niches: list[str] = field(default_factory=list)
    trends: list[dict] = field(default_factory=list)
    market_analysis: Optional[dict] = None
    keywords: Optional[dict] = None
    content_draft: Optional[dict] = None
    image_suggestions: list[dict] = field(default_factory=list)
    seo_report: Optional[dict] = None
    publish_result: Optional[dict] = None
    social_captions: Optional[dict] = None
    analytics: Optional[dict] = None

    # Execution tracking
    stage_results: list[StageResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_stage_result(self, result: StageResult) -> None:
        """Record a stage's execution result.

        Args:
            result: The StageResult to record.
        """
        self.stage_results.append(result)

    def get_stage_result(self, stage_name: str) -> Optional[StageResult]:
        """Look up a previous stage's result by name.

        Args:
            stage_name: Name of the stage to look up.

        Returns:
            StageResult if found, None otherwise.
        """
        for result in self.stage_results:
            if result.stage_name == stage_name:
                return result
        return None

    @property
    def has_failures(self) -> bool:
        """Check if any stage has failed."""
        return any(r.status == StageStatus.FAILED for r in self.stage_results)

    @property
    def elapsed_seconds(self) -> float:
        """Seconds elapsed since pipeline started."""
        return (datetime.now(timezone.utc) - self.started_at).total_seconds()
