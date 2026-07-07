"""FastAPI dependency injection providers.

Provides database sessions, settings, and repository instances
for route handlers via FastAPI's Depends() system.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.repositories.blog_repo import BlogRepository
from app.db.repositories.content_repo import ContentRepository
from app.db.repositories.pipeline_repo import PipelineRepository
from app.db.session import async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for request scope.

    The session auto-commits on success and rolls back on error.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_config() -> Settings:
    """Return application settings (cached singleton)."""
    return get_settings()


async def get_blog_repo(
    session: AsyncSession = Depends(get_db),
) -> BlogRepository:
    """Provide BlogRepository instance."""
    return BlogRepository(session)


async def get_pipeline_repo(
    session: AsyncSession = Depends(get_db),
) -> PipelineRepository:
    """Provide PipelineRepository instance."""
    return PipelineRepository(session)


async def get_content_repo(
    session: AsyncSession = Depends(get_db),
) -> ContentRepository:
    """Provide ContentRepository instance."""
    return ContentRepository(session)
