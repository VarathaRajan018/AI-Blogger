"""Pipeline Orchestrator — runs pipeline stages sequentially.

The Orchestrator is the entry point for all pipeline executions.
It creates a PipelineContext, runs each stage in order, handles
failures, and records the final result to the database.

Usage:
    CLI:
        python -m app.pipeline.orchestrator --blog-id=<UUID> [--dry-run]

    Programmatic:
        orchestrator = PipelineOrchestrator(settings)
        result = await orchestrator.run(blog_id)
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from typing import Optional, Sequence

from app.config import Settings, get_settings
from app.core.models.pipeline import (
    FailureStrategy,
    PipelineContext,
    StageResult,
    StageStatus,
)
from app.db.models import PipelineStatus
from app.db.session import async_session_factory
from app.db.repositories.blog_repo import BlogRepository
from app.db.repositories.content_repo import ContentRepository
from app.db.repositories.pipeline_repo import PipelineRepository
from app.pipeline.stages.base_stage import BaseStage
from app.providers.llm.llm_router import LLMRouter
from app.utils.cost_tracker import CostTracker
from app.utils.logging import get_logger, setup_logging

logger = get_logger(__name__)


# Default niches if not configured per blog
DEFAULT_NICHES = [
    "artificial intelligence",
    "machine learning",
    "python programming",
    "java programming",
    "software engineering",
    "cloud computing",
    "cybersecurity",
    "technology news",
]


class PipelineOrchestrator:
    """Runs the content automation pipeline end-to-end.

    Creates a PipelineContext, executes each stage sequentially,
    handles failures, and records results to the database.

    Args:
        settings: Application settings.
        stages: Optional custom list of stages. If not provided,
            uses the default pipeline stages.
    """

    def __init__(
        self,
        settings: Settings,
        stages: Optional[Sequence[BaseStage]] = None,
    ) -> None:
        self._settings = settings
        self._llm_router = LLMRouter(settings)
        self._stages = list(stages) if stages else self._build_default_stages()

        logger.info(
            "orchestrator initialized",
            stages=[s.name for s in self._stages],
            stage_count=len(self._stages),
        )

    def _build_default_stages(self) -> list[BaseStage]:
        """Build the default pipeline stage sequence.

        Returns:
            Ordered list of pipeline stages.
        """
        from app.pipeline.stages.trend_researcher import TrendResearcherStage
        from app.pipeline.stages.keyword_researcher import KeywordResearcherStage
        from app.pipeline.stages.content_generator import ContentGeneratorStage
        from app.pipeline.stages.seo_validator import SEOValidatorStage
        from app.pipeline.stages.blog_publisher_stage import BlogPublisherStage

        return [
            TrendResearcherStage(settings=self._settings),
            KeywordResearcherStage(
                llm_router=self._llm_router, settings=self._settings
            ),
            ContentGeneratorStage(
                llm_router=self._llm_router, settings=self._settings
            ),
            SEOValidatorStage(settings=self._settings),
            BlogPublisherStage(settings=self._settings),
        ]

    async def run(
        self,
        blog_id: uuid.UUID,
        dry_run: bool = False,
        run_stages: Optional[list[str]] = None,
    ) -> PipelineContext:
        """Execute the full pipeline for a given blog.

        Args:
            blog_id: UUID of the blog to run the pipeline for.
            dry_run: If True, skip publishing to Blogger.
            run_stages: Optional list of stage names to run.
                If provided, only these stages execute (for debugging).

        Returns:
            PipelineContext with all stage outputs and results.
        """
        async with async_session_factory() as session:
            blog_repo = BlogRepository(session)
            pipeline_repo = PipelineRepository(session)
            content_repo = ContentRepository(session)

            # ── Load blog config ────────────────────────────
            blog = await blog_repo.get_by_id(blog_id)
            if blog is None:
                raise ValueError(f"Blog not found: {blog_id}")

            # ── Create pipeline run record ──────────────────
            run = await pipeline_repo.create_run(
                blog_id=blog_id,
                config_snapshot={
                    "dry_run": dry_run,
                    "stages": run_stages or [s.name for s in self._stages],
                    "provider": self._settings.llm_default_provider,
                },
            )
            await pipeline_repo.mark_running(run.id)
            await session.commit()

            # ── Build pipeline context ──────────────────────
            niches = (blog.niche_config or {}).get("niches", DEFAULT_NICHES)

            context = PipelineContext(
                run_id=run.id,
                blog_id=blog_id,
                blog_config={
                    "name": blog.name,
                    "url": blog.url,
                    "platform": blog.platform.value,
                    "blogger_blog_id": blog.blogger_blog_id,
                    "human_approval_required": blog.human_approval_required,
                },
                dry_run=dry_run,
                niches=niches,
            )

            # ── Create cost tracker ─────────────────────────
            cost_tracker = CostTracker(
                run_id=run.id,
                max_cost_usd=self._settings.llm_max_cost_per_run,
            )
            context.metadata["cost_tracker"] = cost_tracker

            logger.info(
                "pipeline run starting",
                run_id=str(run.id),
                blog_name=blog.name,
                dry_run=dry_run,
                niches=niches,
                stage_count=len(self._stages),
            )

            # ── Execute stages ──────────────────────────────
            posts_generated = 0
            posts_published = 0

            try:
                for stage in self._stages:
                    # Skip stages not in run_stages filter
                    if run_stages and stage.name not in run_stages:
                        logger.debug(
                            "stage skipped (not in filter)",
                            stage=stage.name,
                        )
                        continue

                    try:
                        result = await stage.run(context)

                        if result.status == StageStatus.FAILED:
                            strategy = stage.on_failure(
                                context, Exception(result.error or "Unknown")
                            )
                            if strategy == FailureStrategy.ABORT:
                                logger.error(
                                    "pipeline aborted at stage",
                                    stage=stage.name,
                                    error=result.error,
                                )
                                await pipeline_repo.mark_failed(
                                    run.id,
                                    f"Stage '{stage.name}' failed: {result.error}",
                                )
                                await session.commit()
                                return context
                            # SKIP: continue to next stage

                    except Exception as exc:
                        logger.error(
                            "unhandled stage exception",
                            stage=stage.name,
                            error=str(exc),
                            exc_info=True,
                        )
                        await pipeline_repo.mark_failed(
                            run.id,
                            f"Stage '{stage.name}' raised: {exc}",
                        )
                        await session.commit()
                        return context

                # ── Count results ───────────────────────────
                if context.content_draft:
                    posts_generated = 1
                if context.publish_result:
                    posts_published = 1

                # ── Save content draft to DB ────────────────
                if context.content_draft:
                    draft_data = context.content_draft
                    draft = await content_repo.save_draft(
                        run_id=run.id,
                        blog_id=blog_id,
                        title=draft_data.get("title", "Untitled"),
                        body_html=draft_data.get("body_html", ""),
                        meta_description=draft_data.get("meta_description"),
                        tags=draft_data.get("tags", []),
                        primary_keyword=draft_data.get("primary_keyword"),
                        lsi_keywords=draft_data.get("lsi_keywords", []),
                    )

                    # Update with SEO and publish data
                    if context.seo_report:
                        await content_repo.update_seo_report(
                            draft.id,
                            seo_score=context.seo_report.get("score", 0),
                            seo_report=context.seo_report,
                        )

                    if context.publish_result:
                        await content_repo.mark_published(
                            draft.id,
                            blogger_post_id=context.publish_result.get("post_id", ""),
                            published_url=context.publish_result.get("url", ""),
                        )

                    if context.social_captions:
                        await content_repo.update_draft(
                            draft.id, social_captions=context.social_captions
                        )

                    if context.image_suggestions:
                        await content_repo.update_draft(
                            draft.id, image_suggestions=context.image_suggestions
                        )

                # ── Mark run complete ───────────────────────
                await pipeline_repo.mark_completed(
                    run.id,
                    posts_generated=posts_generated,
                    posts_published=posts_published,
                )
                await session.commit()

                # ── Log summary ─────────────────────────────
                cost_summary = cost_tracker.get_summary()
                logger.info(
                    "pipeline run completed",
                    run_id=str(run.id),
                    blog_name=blog.name,
                    posts_generated=posts_generated,
                    posts_published=posts_published,
                    elapsed_seconds=round(context.elapsed_seconds, 2),
                    total_llm_cost=f"${cost_summary['total_cost_usd']:.4f}",
                    total_tokens=cost_summary["total_tokens"],
                    stages_completed=len(context.stage_results),
                    failures=[
                        r.stage_name
                        for r in context.stage_results
                        if r.status == StageStatus.FAILED
                    ],
                )

            except Exception as exc:
                logger.error(
                    "pipeline run failed",
                    run_id=str(run.id),
                    error=str(exc),
                    exc_info=True,
                )
                await pipeline_repo.mark_failed(run.id, str(exc))
                await session.commit()

            return context


# ── CLI Entry Point ─────────────────────────────────────────────


async def main() -> None:
    """CLI entry point for manual pipeline runs."""
    parser = argparse.ArgumentParser(
        description="AI Blogger Pipeline Orchestrator"
    )
    parser.add_argument(
        "--blog-id",
        type=str,
        required=True,
        help="UUID of the blog to run the pipeline for",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Skip publishing — generate content but don't post to Blogger",
    )
    parser.add_argument(
        "--stages",
        type=str,
        nargs="*",
        default=None,
        help="Run only specific stages (space-separated stage names)",
    )

    args = parser.parse_args()

    # Initialize logging
    settings = get_settings()
    setup_logging(
        log_level=settings.app_log_level,
        json_output=settings.is_production,
    )

    logger.info(
        "cli pipeline trigger",
        blog_id=args.blog_id,
        dry_run=args.dry_run,
        stages=args.stages,
    )

    # Ensure database tables exist
    from app.db.models import Base
    from app.db.session import engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Run the pipeline
    orchestrator = PipelineOrchestrator(settings=settings)
    context = await orchestrator.run(
        blog_id=uuid.UUID(args.blog_id),
        dry_run=args.dry_run,
        run_stages=args.stages,
    )

    # Print summary
    if context.has_failures:
        print("\n❌ Pipeline completed with failures:")
        for r in context.stage_results:
            if r.status == StageStatus.FAILED:
                print(f"   FAILED: {r.stage_name} — {r.error}")
        sys.exit(1)
    else:
        print("\n✅ Pipeline completed successfully!")
        print(f"   Stages: {len(context.stage_results)}")
        print(f"   Duration: {context.elapsed_seconds:.1f}s")
        if context.publish_result:
            print(f"   Published: {context.publish_result.get('url', 'N/A')}")
        elif context.dry_run:
            print("   Mode: DRY RUN (no publishing)")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
