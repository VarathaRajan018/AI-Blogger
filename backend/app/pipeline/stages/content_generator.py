"""ContentGenerator pipeline stage.

Takes keyword research data and generates a full SEO-optimized
blog post using the configured LLM provider.
"""

from __future__ import annotations

import json
import re

from pydantic import BaseModel, Field

from app.config import Settings
from app.core.models.pipeline import (
    PipelineContext,
    StageResult,
    StageStatus,
)
from app.pipeline.prompts.content_generation import (
    CONTENT_GENERATION_SYSTEM_PROMPT,
    build_content_generation_prompt,
)
from app.pipeline.stages.base_stage import BaseStage
from app.providers.llm.llm_router import LLMRouter
from app.utils.logging import get_logger

logger = get_logger(__name__)


class GeneratedContent(BaseModel):
    """Pydantic schema for LLM content generation output."""

    title: str = Field(description="SEO-optimized blog title")
    meta_description: str = Field(description="150-160 char meta description")
    body_html: str = Field(description="Full HTML body of the blog post")
    tags: list[str] = Field(default_factory=list, description="Blog post tags")


class ContentGeneratorStage(BaseStage):
    """Pipeline stage that generates full blog post content.

    Uses the LLM provider to generate a complete, SEO-optimized
    blog post based on keyword research data from the previous stage.

    Args:
        llm_router: LLM router for provider selection.
        settings: Application settings.
    """

    def __init__(self, llm_router: LLMRouter, settings: Settings) -> None:
        self._llm_router = llm_router
        self._settings = settings

    @property
    def name(self) -> str:
        """Return 'content_generator'."""
        return "content_generator"

    async def validate_input(self, context: PipelineContext) -> bool:
        """Verify that keyword research has been completed."""
        if not context.keywords:
            logger.warning("no keywords available for content generation")
            return False
        if not context.keywords.get("primary_keyword"):
            logger.warning("primary keyword is empty")
            return False
        return True

    def _count_words(self, html_content: str) -> int:
        """Count words in HTML content (strips tags).

        Args:
            html_content: HTML string.

        Returns:
            Word count.
        """
        # Strip HTML tags
        text = re.sub(r"<[^>]+>", " ", html_content)
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return len(text.split())

    def _clean_html(self, html: str) -> str:
        """Clean and normalize generated HTML.

        Args:
            html: Raw HTML from LLM.

        Returns:
            Cleaned HTML string.
        """
        # Remove markdown artifacts that might leak through
        html = html.replace("```html", "").replace("```", "")

        # Ensure consistent heading format
        html = re.sub(r"<h1[^>]*>", "<h2>", html)
        html = re.sub(r"</h1>", "</h2>", html)

        return html.strip()

    async def execute(self, context: PipelineContext) -> StageResult:
        """Generate blog post content.

        Args:
            context: Pipeline context with keywords populated.

        Returns:
            StageResult with generated content data.
        """
        keywords = context.keywords
        primary_keyword = keywords["primary_keyword"]
        lsi_keywords = keywords.get("lsi_keywords", [])
        topic_title = keywords.get("topic_title", primary_keyword)
        suggested_titles = keywords.get("suggested_titles", [])
        niche = (
            context.niches[0]
            if context.niches
            else "technology"
        )

        logger.info(
            "generating content",
            primary_keyword=primary_keyword,
            topic=topic_title,
            niche=niche,
        )

        # Get LLM provider
        provider = self._llm_router.get_provider("content_generator")
        cost_tracker = context.metadata.get("cost_tracker")

        # Build prompt
        prompt = build_content_generation_prompt(
            primary_keyword=primary_keyword,
            lsi_keywords=lsi_keywords,
            topic_title=topic_title,
            suggested_titles=suggested_titles,
            niche=niche,
            min_word_count=self._settings.content_min_word_count,
            max_word_count=self._settings.content_max_word_count,
        )

        # Generate content via LLM
        try:
            result = await provider.generate_json(
                prompt=prompt,
                schema=GeneratedContent,
                system_prompt=CONTENT_GENERATION_SYSTEM_PROMPT,
            )

            if cost_tracker:
                from app.core.interfaces.llm_provider import LLMResponse
                estimated = LLMResponse(
                    content="",
                    provider=provider.get_provider_name(),
                    model=provider.get_model_name(),
                    prompt_tokens=len(prompt.split()) * 2,
                    completion_tokens=2000,
                    total_tokens=len(prompt.split()) * 2 + 2000,
                )
                cost_tracker.record("content_generator", estimated)

        except Exception as exc:
            logger.warning(
                "structured content generation failed, using text fallback",
                error=str(exc),
            )

            response = await provider.generate_text(
                prompt=prompt,
                system_prompt=CONTENT_GENERATION_SYSTEM_PROMPT,
            )

            if cost_tracker:
                cost_tracker.record("content_generator", response)

            # Parse JSON from text
            content_text = response.content.strip()
            if content_text.startswith("```"):
                lines = content_text.split("\n")
                content_text = "\n".join(lines[1:-1])

            parsed = json.loads(content_text)
            result = GeneratedContent(**parsed)

        # Clean and validate
        body_html = self._clean_html(result.body_html)
        word_count = self._count_words(body_html)

        logger.info(
            "content generated",
            title=result.title,
            word_count=word_count,
            tags=result.tags,
            meta_length=len(result.meta_description),
        )

        if word_count < self._settings.content_min_word_count:
            logger.warning(
                "content below minimum word count",
                word_count=word_count,
                minimum=self._settings.content_min_word_count,
            )

        # Store in context
        context.content_draft = {
            "title": result.title,
            "body_html": body_html,
            "meta_description": result.meta_description,
            "tags": result.tags,
            "primary_keyword": primary_keyword,
            "lsi_keywords": lsi_keywords,
            "word_count": word_count,
        }

        return StageResult(
            stage_name=self.name,
            status=StageStatus.SUCCESS,
            data={
                "title": result.title,
                "word_count": word_count,
                "tags_count": len(result.tags),
            },
        )
