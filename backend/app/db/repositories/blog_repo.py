"""Blog repository — data access layer for blog configurations."""

from __future__ import annotations

import uuid
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Blog, BlogPlatform


class BlogRepository:
    """Repository for Blog CRUD operations.

    All database access for the `blogs` table goes through this class.
    Pipeline stages and API routes should never touch the session directly.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, blog_id: uuid.UUID) -> Optional[Blog]:
        """Get a single blog by its UUID.

        Args:
            blog_id: The blog's UUID primary key.

        Returns:
            Blog instance or None if not found.
        """
        result = await self.session.execute(
            select(Blog).where(Blog.id == blog_id)
        )
        return result.scalar_one_or_none()

    async def get_all_active(self) -> Sequence[Blog]:
        """Get all blogs that are currently active.

        Returns:
            List of active Blog instances, ordered by creation date.
        """
        result = await self.session.execute(
            select(Blog)
            .where(Blog.is_active == True)  # noqa: E712
            .order_by(Blog.created_at)
        )
        return result.scalars().all()

    async def get_all(self) -> Sequence[Blog]:
        """Get all blogs regardless of active state.

        Returns:
            List of all Blog instances.
        """
        result = await self.session.execute(
            select(Blog).order_by(Blog.created_at)
        )
        return result.scalars().all()

    async def create(
        self,
        name: str,
        url: str,
        platform: BlogPlatform = BlogPlatform.BLOGGER,
        blogger_blog_id: Optional[str] = None,
        niche_config: Optional[dict] = None,
        human_approval_required: bool = False,
    ) -> Blog:
        """Create a new blog configuration.

        Args:
            name: Display name for the blog.
            url: Blog URL.
            platform: Blog platform type.
            blogger_blog_id: Blogger API blog ID.
            niche_config: JSON config for niches and content guidelines.
            human_approval_required: Whether posts need human approval.

        Returns:
            Newly created Blog instance.
        """
        blog = Blog(
            name=name,
            url=url,
            platform=platform,
            blogger_blog_id=blogger_blog_id,
            niche_config=niche_config or {},
            human_approval_required=human_approval_required,
        )
        self.session.add(blog)
        await self.session.flush()
        return blog

    async def update(self, blog_id: uuid.UUID, **kwargs: object) -> Optional[Blog]:
        """Update a blog's fields.

        Args:
            blog_id: The blog's UUID.
            **kwargs: Field-value pairs to update.

        Returns:
            Updated Blog instance or None if not found.
        """
        blog = await self.get_by_id(blog_id)
        if blog is None:
            return None

        for key, value in kwargs.items():
            if hasattr(blog, key):
                setattr(blog, key, value)

        await self.session.flush()
        return blog

    async def delete(self, blog_id: uuid.UUID) -> bool:
        """Delete a blog by ID.

        Args:
            blog_id: The blog's UUID.

        Returns:
            True if deleted, False if not found.
        """
        blog = await self.get_by_id(blog_id)
        if blog is None:
            return False

        await self.session.delete(blog)
        await self.session.flush()
        return True
