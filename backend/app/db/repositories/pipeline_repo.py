"""Pipeline run repository — data access for pipeline execution records."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PipelineRun, PipelineStatus


class PipelineRepository:
    """Repository for PipelineRun CRUD operations.

    Tracks pipeline execution state: creation, status updates,
    completion, and failure recording.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(
        self,
        blog_id: uuid.UUID,
        config_snapshot: Optional[dict] = None,
    ) -> PipelineRun:
        """Create a new pipeline run record.

        Args:
            blog_id: Blog this run is for.
            config_snapshot: Snapshot of pipeline config at time of run.

        Returns:
            Newly created PipelineRun with PENDING status.
        """
        run = PipelineRun(
            blog_id=blog_id,
            status=PipelineStatus.PENDING,
            config_snapshot=config_snapshot,
            started_at=datetime.now(timezone.utc),
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def get_run(self, run_id: uuid.UUID) -> Optional[PipelineRun]:
        """Get a pipeline run by ID.

        Args:
            run_id: The run's UUID.

        Returns:
            PipelineRun instance or None.
        """
        result = await self.session.execute(
            select(PipelineRun).where(PipelineRun.id == run_id)
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        run_id: uuid.UUID,
        status: PipelineStatus,
        error_message: Optional[str] = None,
    ) -> None:
        """Update the status of a pipeline run.

        Args:
            run_id: The run's UUID.
            status: New status.
            error_message: Optional error message if status is FAILED.
        """
        values: dict = {"status": status}
        if status in (PipelineStatus.COMPLETED, PipelineStatus.FAILED):
            values["completed_at"] = datetime.now(timezone.utc)
        if error_message is not None:
            values["error_message"] = error_message

        await self.session.execute(
            update(PipelineRun)
            .where(PipelineRun.id == run_id)
            .values(**values)
        )
        await self.session.flush()

    async def mark_running(self, run_id: uuid.UUID) -> None:
        """Mark a pipeline run as RUNNING.

        Args:
            run_id: The run's UUID.
        """
        await self.update_status(run_id, PipelineStatus.RUNNING)

    async def mark_completed(
        self,
        run_id: uuid.UUID,
        posts_generated: int = 0,
        posts_published: int = 0,
    ) -> None:
        """Mark a pipeline run as COMPLETED with stats.

        Args:
            run_id: The run's UUID.
            posts_generated: Number of posts generated.
            posts_published: Number of posts published.
        """
        await self.session.execute(
            update(PipelineRun)
            .where(PipelineRun.id == run_id)
            .values(
                status=PipelineStatus.COMPLETED,
                completed_at=datetime.now(timezone.utc),
                posts_generated=posts_generated,
                posts_published=posts_published,
            )
        )
        await self.session.flush()

    async def mark_failed(self, run_id: uuid.UUID, error: str) -> None:
        """Mark a pipeline run as FAILED with error message.

        Args:
            run_id: The run's UUID.
            error: Error description.
        """
        await self.update_status(run_id, PipelineStatus.FAILED, error_message=error)

    async def get_recent_runs(
        self,
        blog_id: Optional[uuid.UUID] = None,
        limit: int = 20,
    ) -> Sequence[PipelineRun]:
        """Get recent pipeline runs, optionally filtered by blog.

        Args:
            blog_id: Optional blog ID filter.
            limit: Maximum number of runs to return.

        Returns:
            List of PipelineRun instances, most recent first.
        """
        query = select(PipelineRun).order_by(PipelineRun.created_at.desc())
        if blog_id is not None:
            query = query.where(PipelineRun.blog_id == blog_id)
        query = query.limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()
