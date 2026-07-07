"""Abstract base class for blog publishers.

All blog publishers (Blogger, WordPress) implement this interface,
enabling platform-agnostic publishing from the pipeline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.core.models.content import ContentDraft, PublishResult


class BaseBlogPublisher(ABC):
    """Abstract interface for blog platform publishers.

    Concrete implementations handle authentication, API calls,
    and post creation for specific platforms.
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform identifier.

        Returns:
            Platform name (e.g., 'blogger', 'wordpress').
        """
        ...

    @abstractmethod
    async def publish_post(
        self,
        title: str,
        body_html: str,
        labels: Optional[list[str]] = None,
        meta_description: Optional[str] = None,
        is_draft: bool = False,
    ) -> PublishResult:
        """Publish a new blog post.

        Args:
            title: Post title.
            body_html: HTML body content.
            labels: Post labels/tags.
            meta_description: SEO meta description.
            is_draft: If True, create as draft (not live).

        Returns:
            PublishResult with post_id and URL.
        """
        ...

    @abstractmethod
    async def update_post(
        self,
        post_id: str,
        title: Optional[str] = None,
        body_html: Optional[str] = None,
        labels: Optional[list[str]] = None,
    ) -> PublishResult:
        """Update an existing blog post.

        Args:
            post_id: Platform-specific post ID.
            title: Updated title (None = keep current).
            body_html: Updated body (None = keep current).
            labels: Updated labels (None = keep current).

        Returns:
            PublishResult with updated post info.
        """
        ...

    @abstractmethod
    async def delete_post(self, post_id: str) -> bool:
        """Delete a blog post.

        Args:
            post_id: Platform-specific post ID.

        Returns:
            True if deleted successfully.
        """
        ...
