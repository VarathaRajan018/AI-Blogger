"""KeywordResearcher pipeline stage.

Takes the top trending topic, sends it through LLM-based keyword
expansion, and produces a KeywordReport with primary keyword,
LSI keywords, and suggested blog titles.
"""

from __future__ import annotations

import json
from typing import Optional

from pydantic import BaseModel, Field

from app.config import Settings
from app.core.models.pipeline import (
    PipelineContext,
    StageResult,
    StageStatus,
)
from app.pipeline.prompts.keyword_expansion import (
    KEYWORD_EXPANSION_SYSTEM_PROMPT,
    build_keyword_expansion_prompt,
)
from app.pipeline.stages.base_stage import BaseStage
from app.providers.llm.llm_router import LLMRouter
from app.utils.logging import get_logger

logger = get_logger(__name__)


class KeywordExpansionResult(BaseModel):
    """Pydantic schema for LLM keyword expansion output."""

    primary_keyword: str = Field(description="Main target keyword (3-6 words)")
    lsi_keywords: list[str] = Field(description="8-12 semantically related keywords")
    search_intent: str = Field(default="informational", description="Search intent type")
    suggested_titles: list[str] = Field(description="5 blog title variations")
    estimated_competition: float = Field(default=0.5, ge=0.0, le=1.0)


class KeywordResearcherStage(BaseStage):
    """Pipeline stage that performs LLM-powered keyword research.

    Takes the top trending topic from context, expands it into
    a comprehensive keyword report using the LLM provider.

    Args:
        llm_router: LLM router for provider selection.
        settings: Application settings.
    """

    def __init__(self, llm_router: LLMRouter, settings: Settings) -> None:
        self._llm_router = llm_router
        self._settings = settings

    @property
    def name(self) -> str:
        """Return 'keyword_researcher'."""
        return "keyword_researcher"

    async def validate_input(self, context: PipelineContext) -> bool:
        """Verify that trends have been discovered."""
        if not context.trends:
            logger.warning("no trends available for keyword research")
            return False
        return True

    async def execute(self, context: PipelineContext) -> StageResult:
        """Perform keyword research on the top trending topic.

        Args:
            context: Pipeline context with trends populated.

        Returns:
            StageResult with keyword research data.
        """
        # Select the top trend topic
        top_trend = context.trends[0]
        topic_title = top_trend.get("title", "")
        niche = top_trend.get("niche", context.niches[0] if context.niches else "technology")
        description = top_trend.get("description", "")

        logger.info(
            "researching keywords",
            topic=topic_title,
            niche=niche,
        )

        # Get LLM provider for this module
        provider = self._llm_router.get_provider("keyword_researcher")
        cost_tracker = context.metadata.get("cost_tracker")

        # Build and send prompt
        prompt = build_keyword_expansion_prompt(
            topic_title=topic_title,
            niche=niche,
            description=description,
        )

        try:
            # Try structured JSON output first
            result = await provider.generate_json(
                prompt=prompt,
                schema=KeywordExpansionResult,
                system_prompt=KEYWORD_EXPANSION_SYSTEM_PROMPT,
            )

            # Record usage if we got a raw response
            if cost_tracker:
                # Estimate tokens since generate_json may not return LLMResponse
                from app.core.interfaces.llm_provider import LLMResponse
                estimated_response = LLMResponse(
                    content="",
                    provider=provider.get_provider_name(),
                    model=provider.get_model_name(),
                    prompt_tokens=len(prompt.split()) * 2,  # rough estimate
                    completion_tokens=200,
                    total_tokens=len(prompt.split()) * 2 + 200,
                )
                cost_tracker.record("keyword_researcher", estimated_response)

        except Exception as exc:
            logger.warning(
                "structured keyword generation failed, trying text fallback",
                error=str(exc),
            )

            # Fallback: generate as text and parse manually
            response = await provider.generate_text(
                prompt=prompt,
                system_prompt=KEYWORD_EXPANSION_SYSTEM_PROMPT,
            )

            if cost_tracker:
                cost_tracker.record("keyword_researcher", response)

            # Parse JSON from text response
            content = response.content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])

            parsed = json.loads(content)
            result = KeywordExpansionResult(**parsed)

        # Validate result quality
        if len(result.primary_keyword.split()) < 2:
            logger.warning(
                "primary keyword too short, enriching",
                keyword=result.primary_keyword,
            )
            result.primary_keyword = f"{result.primary_keyword} guide tutorial"

        if len(result.lsi_keywords) < 3:
            logger.warning(
                "too few LSI keywords",
                count=len(result.lsi_keywords),
            )

        # Store in context
        context.keywords = {
            "primary_keyword": result.primary_keyword,
            "lsi_keywords": result.lsi_keywords,
            "search_intent": result.search_intent,
            "suggested_titles": result.suggested_titles,
            "competition_score": result.estimated_competition,
            "topic_title": topic_title,
        }

        logger.info(
            "keyword research complete",
            primary_keyword=result.primary_keyword,
            lsi_count=len(result.lsi_keywords),
            titles_generated=len(result.suggested_titles),
            competition=result.estimated_competition,
        )

        return StageResult(
            stage_name=self.name,
            status=StageStatus.SUCCESS,
            data={
                "primary_keyword": result.primary_keyword,
                "lsi_keywords_count": len(result.lsi_keywords),
                "titles_count": len(result.suggested_titles),
            },
        )
