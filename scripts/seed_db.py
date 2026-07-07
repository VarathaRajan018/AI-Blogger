"""Database seeding script.

Creates the initial blog configuration in the database
so the pipeline can run against it.

Usage:
    python scripts/seed_db.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.config import get_settings
from app.db.models import Base, Blog, BlogPlatform
from app.db.session import engine, async_session_factory
from app.utils.logging import setup_logging, get_logger

logger = get_logger(__name__)


async def seed() -> None:
    """Create initial database records."""
    settings = get_settings()
    setup_logging(log_level="INFO")

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("✓ Database tables created")

    # Seed the primary blog
    async with async_session_factory() as session:
        from sqlalchemy import select

        # Check if blog already exists
        result = await session.execute(
            select(Blog).where(Blog.url == settings.primary_blog_url)
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"✓ Blog already exists: {existing.name} (ID: {existing.id})")
            print(f"  Use this ID for pipeline runs: --blog-id={existing.id}")
            return

        # Create the blog
        blog = Blog(
            name="Varatharajan's Tech Blog",
            url=settings.primary_blog_url,
            platform=BlogPlatform.BLOGGER,
            blogger_blog_id=settings.primary_blog_id or None,
            niche_config={
                "niches": [
                    "artificial intelligence",
                    "machine learning",
                    "python programming",
                    "java programming",
                    "software engineering",
                    "cloud computing",
                    "cybersecurity",
                    "technology news",
                    "interview preparation",
                    "career guidance",
                ],
                "content_guidelines": {
                    "tone": "professional yet conversational",
                    "include_code_examples": True,
                    "target_audience": "developers and tech professionals",
                },
            },
            is_active=True,
            human_approval_required=False,
        )

        session.add(blog)
        await session.commit()

        print(f"✓ Blog created: {blog.name}")
        print(f"  Blog ID: {blog.id}")
        print(f"  URL: {blog.url}")
        print(f"  Platform: {blog.platform.value}")
        print()
        print(f"  Run the pipeline with:")
        print(f"    python -m app.pipeline.orchestrator --blog-id={blog.id} --dry-run")


if __name__ == "__main__":
    asyncio.run(seed())
