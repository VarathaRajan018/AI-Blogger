"""Content draft repository — data access for AI-generated blog posts."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ContentDraft, ContentStatus


class ContentRepository:
    """Repository for ContentDraft CRUD operations.

    Manages the lifecycle of AI-generated content from draft
    through SEO validation to publication.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_draft(
        self,
        run_id: uuid.UUID,
        blog_id: uuid.UUID,
        title: str,
        body_html: str,
        meta_description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        primary_keyword: Optional[str] = None,
        lsi_keywords: Optional[list[str]] = None,
    ) -> ContentDraft:
        """Save a new content draft from the ContentGenerator stage.

        Args:
            run_id: Pipeline run that generated this draft.
            blog_id: Target blog for this content.
            title: Post title.
            body_html: HTML body content.
            meta_description: SEO meta description.
            tags: Post tags/labels.
            primary_keyword: Target SEO keyword.
            lsi_keywords: Latent semantic indexing keywords.

        Returns:
            Newly created ContentDraft instance.
        """
        draft = ContentDraft(
            run_id=run_id,
            blog_id=blog_id,
            title=title,
            body_html=body_html,
            meta_description=meta_description,
            tags=tags or [],
            primary_keyword=primary_keyword,
            lsi_keywords=lsi_keywords or [],
            status=ContentStatus.DRAFT,
        )
        self.session.add(draft)
        await self.session.flush()
        return draft

    async def get_draft_by_id(self, draft_id: uuid.UUID) -> Optional[ContentDraft]:
        """Get a content draft by ID.

        Args:
            draft_id: The draft's UUID.

        Returns:
            ContentDraft instance or None.
        """
        result = await self.session.execute(
            select(ContentDraft).where(ContentDraft.id == draft_id)
        )
        return result.scalar_one_or_none()

    async def get_drafts_by_run(self, run_id: uuid.UUID) -> Sequence[ContentDraft]:
        """Get all content drafts for a pipeline run.

        Args:
            run_id: Pipeline run UUID.

        Returns:
            List of ContentDraft instances.
        """
        result = await self.session.execute(
            select(ContentDraft)
            .where(ContentDraft.run_id == run_id)
            .order_by(ContentDraft.created_at)
        )
        return result.scalars().all()

    async def get_drafts_by_status(
        self,
        blog_id: uuid.UUID,
        status: ContentStatus,
        limit: int = 50,
    ) -> Sequence[ContentDraft]:
        """Get drafts filtered by status for a specific blog.

        Args:
            blog_id: Blog UUID.
            status: Content status filter.
            limit: Maximum results.

        Returns:
            List of ContentDraft instances.
        """
        result = await self.session.execute(
            select(ContentDraft)
            .where(ContentDraft.blog_id == blog_id, ContentDraft.status == status)
            .order_by(ContentDraft.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def update_seo_report(
        self,
        draft_id: uuid.UUID,
        seo_score: int,
        seo_report: dict,
    ) -> None:
        """Update SEO validation results on a draft.

        Args:
            draft_id: The draft's UUID.
            seo_score: SEO score (0-100).
            seo_report: Detailed SEO check results.
        """
        status = (
            ContentStatus.SEO_PASSED
            if seo_score >= 80
            else ContentStatus.SEO_FAILED
        )
        await self.session.execute(
            update(ContentDraft)
            .where(ContentDraft.id == draft_id)
            .values(
                seo_score=seo_score,
                seo_report=seo_report,
                status=status,
            )
        )
        await self.session.flush()

    async def update_draft(self, draft_id: uuid.UUID, **kwargs: object) -> None:
        """Update arbitrary fields on a content draft.

        Args:
            draft_id: The draft's UUID.
            **kwargs: Field-value pairs to update.
        """
        await self.session.execute(
            update(ContentDraft)
            .where(ContentDraft.id == draft_id)
            .values(**kwargs)
        )
        await self.session.flush()

    async def mark_published(
        self,
        draft_id: uuid.UUID,
        blogger_post_id: str,
        published_url: str,
    ) -> None:
        """Mark a draft as successfully published.

        Args:
            draft_id: The draft's UUID.
            blogger_post_id: ID assigned by Blogger API.
            published_url: Public URL of the published post.
        """
        await self.session.execute(
            update(ContentDraft)
            .where(ContentDraft.id == draft_id)
            .values(
                status=ContentStatus.PUBLISHED,
                blogger_post_id=blogger_post_id,
                published_url=published_url,
                published_at=datetime.now(timezone.utc),
            )
        )
        await self.session.flush()

    async def mark_pending_review(self, draft_id: uuid.UUID) -> None:
        """Queue a draft for human review.

        Args:
            draft_id: The draft's UUID.
        """
        await self.update_draft(
            draft_id, status=ContentStatus.PENDING_REVIEW
        )

    async def mark_rejected(self, draft_id: uuid.UUID) -> None:
        """Mark a draft as rejected by human reviewer.

        Args:
            draft_id: The draft's UUID.
        """
        await self.update_draft(draft_id, status=ContentStatus.REJECTED)
