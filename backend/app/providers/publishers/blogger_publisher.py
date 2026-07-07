"""Google Blogger API v3 publisher implementation.

Publishes blog posts to Google Blogger using OAuth 2.0 credentials.
Handles token refresh, post creation, updates, and deletion.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.core.interfaces.blog_publisher import BaseBlogPublisher
from app.core.models.content import PublishResult
from app.utils.logging import get_logger
from app.utils.retry import retry_with_backoff

logger = get_logger(__name__)

# Token file path
CREDENTIALS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "credentials"
TOKEN_FILE = CREDENTIALS_DIR / "blogger_token.json"


class BloggerPublisher(BaseBlogPublisher):
    """Google Blogger API v3 publisher.

    Uses OAuth 2.0 credentials to authenticate with the Blogger API.
    The refresh token is stored in credentials/blogger_token.json.

    Args:
        blog_id: Blogger blog ID (numeric string).
        client_id: Google OAuth client ID.
        client_secret: Google OAuth client secret.
        token_file: Path to stored OAuth token file.
    """

    def __init__(
        self,
        blog_id: str,
        client_id: str,
        client_secret: str,
        token_file: Path | str = TOKEN_FILE,
    ) -> None:
        if not blog_id:
            raise ValueError("Blogger blog_id is required")

        self._blog_id = blog_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._token_file = Path(token_file)
        self._service: Any = None

        logger.info(
            "blogger publisher initialized",
            blog_id=blog_id,
            token_file=str(self._token_file),
        )

    @property
    def platform_name(self) -> str:
        """Return 'blogger'."""
        return "blogger"

    def _get_service(self) -> Any:
        """Build the Blogger API service client.

        Loads stored OAuth credentials, refreshes if needed,
        and builds the API client.

        Returns:
            Google API service object.

        Raises:
            FileNotFoundError: If token file doesn't exist.
            ValueError: If credentials are invalid.
        """
        if self._service is not None:
            return self._service

        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds: Credentials | None = None

        # Load existing token
        if self._token_file.exists():
            token_data = json.loads(self._token_file.read_text())
            creds = Credentials(
                token=token_data.get("token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self._client_id,
                client_secret=self._client_secret,
                scopes=["https://www.googleapis.com/auth/blogger"],
            )

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("refreshing expired blogger token")
                creds.refresh(Request())
                # Save refreshed token
                self._save_token(creds)
            else:
                raise FileNotFoundError(
                    f"Blogger OAuth token not found at {self._token_file}. "
                    f"Run 'python scripts/authorize_google.py' to authenticate."
                )

        self._service = build("blogger", "v3", credentials=creds)
        logger.info("blogger api service created")
        return self._service

    def _save_token(self, creds: Any) -> None:
        """Save OAuth credentials to the token file.

        Args:
            creds: Google OAuth Credentials object.
        """
        self._token_file.parent.mkdir(parents=True, exist_ok=True)
        token_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": list(creds.scopes) if creds.scopes else [],
        }
        self._token_file.write_text(json.dumps(token_data, indent=2))
        logger.info("blogger token saved", path=str(self._token_file))

    @retry_with_backoff(max_retries=3, min_wait=2.0, max_wait=30.0)
    async def publish_post(
        self,
        title: str,
        body_html: str,
        labels: Optional[list[str]] = None,
        meta_description: Optional[str] = None,
        is_draft: bool = False,
    ) -> PublishResult:
        """Publish a new post to Blogger.

        Args:
            title: Post title.
            body_html: HTML body content.
            labels: Post labels/tags.
            meta_description: SEO meta description (added to body).
            is_draft: If True, create as draft.

        Returns:
            PublishResult with post_id and URL.
        """
        service = await asyncio.get_event_loop().run_in_executor(
            None, self._get_service
        )

        # Prepend meta description as a hidden element if provided
        full_body = body_html
        if meta_description:
            full_body = (
                f'<meta name="description" content="{meta_description}" />\n'
                f"{body_html}"
            )

        post_body: dict[str, Any] = {
            "kind": "blogger#post",
            "blog": {"id": self._blog_id},
            "title": title,
            "content": full_body,
        }

        if labels:
            post_body["labels"] = labels

        logger.info(
            "publishing to blogger",
            blog_id=self._blog_id,
            title=title,
            labels=labels,
            is_draft=is_draft,
        )

        # Execute API call in executor (synchronous API client)
        def _insert() -> dict:
            return (
                service.posts()
                .insert(blogId=self._blog_id, body=post_body, isDraft=is_draft)
                .execute()
            )

        response = await asyncio.get_event_loop().run_in_executor(None, _insert)

        post_id = response.get("id", "")
        post_url = response.get("url", "")

        logger.info(
            "post published successfully",
            post_id=post_id,
            url=post_url,
            is_draft=is_draft,
        )

        return PublishResult(
            post_id=post_id,
            url=post_url,
            published_at=datetime.now(timezone.utc),
            platform="blogger",
        )

    @retry_with_backoff(max_retries=2)
    async def update_post(
        self,
        post_id: str,
        title: Optional[str] = None,
        body_html: Optional[str] = None,
        labels: Optional[list[str]] = None,
    ) -> PublishResult:
        """Update an existing Blogger post.

        Args:
            post_id: Blogger post ID.
            title: Updated title.
            body_html: Updated body.
            labels: Updated labels.

        Returns:
            PublishResult with updated post info.
        """
        service = await asyncio.get_event_loop().run_in_executor(
            None, self._get_service
        )

        update_body: dict[str, Any] = {}
        if title is not None:
            update_body["title"] = title
        if body_html is not None:
            update_body["content"] = body_html
        if labels is not None:
            update_body["labels"] = labels

        def _patch() -> dict:
            return (
                service.posts()
                .patch(blogId=self._blog_id, postId=post_id, body=update_body)
                .execute()
            )

        response = await asyncio.get_event_loop().run_in_executor(None, _patch)

        return PublishResult(
            post_id=response.get("id", post_id),
            url=response.get("url", ""),
            published_at=datetime.now(timezone.utc),
            platform="blogger",
        )

    @retry_with_backoff(max_retries=2)
    async def delete_post(self, post_id: str) -> bool:
        """Delete a Blogger post.

        Args:
            post_id: Blogger post ID.

        Returns:
            True if deleted successfully.
        """
        service = await asyncio.get_event_loop().run_in_executor(
            None, self._get_service
        )

        def _delete() -> None:
            service.posts().delete(
                blogId=self._blog_id, postId=post_id
            ).execute()

        await asyncio.get_event_loop().run_in_executor(None, _delete)

        logger.info("post deleted", post_id=post_id)
        return True
