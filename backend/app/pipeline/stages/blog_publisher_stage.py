"""BlogPublisher pipeline stage.

Publishes SEO-validated content to the configured blog platform.
Supports dry-run mode and human-in-the-loop approval.
"""

from __future__ import annotations

from app.config import Settings
from app.core.models.pipeline import (
    FailureStrategy,
    PipelineContext,
    StageResult,
    StageStatus,
)
from app.pipeline.stages.base_stage import BaseStage
from app.providers.publishers.blogger_publisher import BloggerPublisher
from app.utils.logging import get_logger

logger = get_logger(__name__)


class BlogPublisherStage(BaseStage):
    """Pipeline stage that publishes content to the blog platform.

    Checks SEO score, respects dry-run mode and human approval
    settings, then publishes via the configured publisher.

    Args:
        settings: Application settings.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def name(self) -> str:
        """Return 'blog_publisher'."""
        return "blog_publisher"

    def on_failure(
        self, context: PipelineContext, error: Exception
    ) -> FailureStrategy:
        """Publishing failure should not crash the pipeline — skip gracefully."""
        return FailureStrategy.SKIP

    async def validate_input(self, context: PipelineContext) -> bool:
        """Verify content and SEO report are available."""
        if not context.content_draft:
            logger.warning("no content draft available for publishing")
            return False
        if not context.seo_report:
            logger.warning("no seo report available — skipping publish")
            return False
        return True

    async def execute(self, context: PipelineContext) -> StageResult:
        """Publish content to the blog or skip based on conditions.

        Conditions for skipping:
        - Dry run mode is active
        - SEO score is below threshold
        - Human approval is required (queued for review)
        - Missing Blogger credentials

        Args:
            context: Pipeline context with content_draft and seo_report.

        Returns:
            StageResult with publish outcome.
        """
        draft = context.content_draft
        seo_report = context.seo_report
        seo_score = seo_report.get("score", 0)
        blog_config = context.blog_config

        title = draft.get("title", "Untitled")
        body_html = draft.get("body_html", "")
        tags = draft.get("tags", [])
        meta_description = draft.get("meta_description", "")

        # ── Check: Dry Run ──────────────────────────────────
        if context.dry_run:
            logger.info(
                "dry run — skipping publish",
                title=title,
                seo_score=seo_score,
            )
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                data={"reason": "dry_run", "title": title, "seo_score": seo_score},
            )

        # ── Check: SEO Threshold ────────────────────────────
        if seo_score < self._settings.pipeline_seo_min_score:
            logger.warning(
                "seo score below threshold — skipping publish",
                score=seo_score,
                threshold=self._settings.pipeline_seo_min_score,
            )
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                data={
                    "reason": "seo_score_low",
                    "score": seo_score,
                    "threshold": self._settings.pipeline_seo_min_score,
                },
            )

        # ── Check: Human Approval ───────────────────────────
        if blog_config.get("human_approval_required", False):
            logger.info(
                "human approval required — queuing for review",
                title=title,
                seo_score=seo_score,
            )
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                data={"reason": "pending_human_approval", "title": title},
            )

        # ── Check: Credentials ──────────────────────────────
        blogger_blog_id = blog_config.get("blogger_blog_id", "") or self._settings.primary_blog_id
        if not blogger_blog_id:
            logger.error("no blogger_blog_id configured")
            return StageResult(
                stage_name=self.name,
                status=StageStatus.FAILED,
                error="No blogger_blog_id configured. Set PRIMARY_BLOG_ID in .env",
            )

        # ── Publish ─────────────────────────────────────────
        logger.info(
            "publishing to blogger",
            title=title,
            blog_id=blogger_blog_id,
            seo_score=seo_score,
            tags=tags,
        )

        try:
            publisher = BloggerPublisher(
                blog_id=blogger_blog_id,
                client_id=self._settings.google_client_id,
                client_secret=self._settings.google_client_secret,
            )

            result = await publisher.publish_post(
                title=title,
                body_html=body_html,
                labels=tags,
                meta_description=meta_description,
            )

            # Store in context
            context.publish_result = result.to_dict()

            logger.info(
                "post published successfully",
                post_id=result.post_id,
                url=result.url,
                title=title,
            )

            return StageResult(
                stage_name=self.name,
                status=StageStatus.SUCCESS,
                data={
                    "post_id": result.post_id,
                    "url": result.url,
                    "title": title,
                },
            )

        except FileNotFoundError as exc:
            logger.error(
                "blogger auth token not found",
                error=str(exc),
            )
            return StageResult(
                stage_name=self.name,
                status=StageStatus.FAILED,
                error=(
                    "Blogger OAuth token not found. "
                    "Run 'python scripts/authorize_google.py' to authenticate."
                ),
            )

        except Exception as exc:
            logger.error(
                "publishing failed",
                error=str(exc),
                exc_info=True,
            )
            raise
