"""SEOValidator pipeline stage.

Rule-based SEO validation engine that checks content drafts
against 13 SEO rules and produces a score out of 100.
No LLM dependency — pure algorithmic validation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

from app.config import Settings
from app.core.models.pipeline import (
    PipelineContext,
    StageResult,
    StageStatus,
)
from app.pipeline.stages.base_stage import BaseStage
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SEOCheck:
    """Definition of a single SEO check.

    Attributes:
        name: Short identifier for the check.
        description: Human-readable description.
        max_points: Maximum points awarded if check passes.
        check_fn: Function that returns (passed: bool, message: str).
    """

    name: str
    description: str
    max_points: int
    check_fn: Callable[..., tuple[bool, str]] = field(repr=False)


class SEOValidatorStage(BaseStage):
    """Pipeline stage that validates content against SEO rules.

    Performs 13 automated SEO checks on the generated content
    and produces a score (0-100). If the score is below the
    configured threshold, the content can be sent back for
    refinement.

    Args:
        settings: Application settings.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._min_score = settings.pipeline_seo_min_score

    @property
    def name(self) -> str:
        """Return 'seo_validator'."""
        return "seo_validator"

    async def validate_input(self, context: PipelineContext) -> bool:
        """Verify that content has been generated."""
        if not context.content_draft:
            logger.warning("no content draft available for SEO validation")
            return False
        return True

    def _strip_html(self, html: str) -> str:
        """Remove HTML tags from content.

        Args:
            html: HTML string.

        Returns:
            Plain text.
        """
        text = re.sub(r"<[^>]+>", " ", html)
        return re.sub(r"\s+", " ", text).strip()

    def _extract_headings(self, html: str) -> list[tuple[str, str]]:
        """Extract all headings from HTML.

        Args:
            html: HTML content.

        Returns:
            List of (level, text) tuples. E.g., [("h2", "Introduction")].
        """
        pattern = r"<(h[1-6])[^>]*>(.*?)</\1>"
        matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
        return [(level.lower(), self._strip_html(text)) for level, text in matches]

    def _count_words(self, text: str) -> int:
        """Count words in plain text.

        Args:
            text: Plain text string.

        Returns:
            Word count.
        """
        return len(text.split())

    def _keyword_density(self, text: str, keyword: str) -> float:
        """Calculate keyword density percentage.

        Args:
            text: Plain text content.
            keyword: Target keyword.

        Returns:
            Density as percentage (e.g., 1.5 = 1.5%).
        """
        words = text.lower().split()
        total_words = len(words)
        if total_words == 0:
            return 0.0

        keyword_lower = keyword.lower()
        keyword_words = keyword_lower.split()
        keyword_len = len(keyword_words)

        count = 0
        for i in range(len(words) - keyword_len + 1):
            if words[i : i + keyword_len] == keyword_words:
                count += 1

        return round((count * keyword_len / total_words) * 100, 2)

    def _get_paragraphs(self, html: str) -> list[str]:
        """Extract paragraph text from HTML.

        Args:
            html: HTML content.

        Returns:
            List of paragraph text strings.
        """
        paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", html, re.DOTALL | re.IGNORECASE)
        return [self._strip_html(p) for p in paragraphs if self._strip_html(p)]

    def _get_sentences(self, text: str) -> list[str]:
        """Split text into sentences.

        Args:
            text: Plain text.

        Returns:
            List of sentences.
        """
        sentences = re.split(r"[.!?]+", text)
        return [s.strip() for s in sentences if s.strip()]

    def _build_checks(
        self,
        title: str,
        body_html: str,
        meta_description: str,
        primary_keyword: str,
        lsi_keywords: list[str],
    ) -> list[SEOCheck]:
        """Build all SEO check definitions.

        Args:
            title: Post title.
            body_html: HTML body content.
            meta_description: SEO meta description.
            primary_keyword: Target keyword.
            lsi_keywords: Related keywords.

        Returns:
            List of SEOCheck objects.
        """
        plain_text = self._strip_html(body_html)
        word_count = self._count_words(plain_text)
        headings = self._extract_headings(body_html)
        paragraphs = self._get_paragraphs(body_html)
        sentences = self._get_sentences(plain_text)

        keyword_lower = primary_keyword.lower()
        title_lower = title.lower()
        meta_lower = meta_description.lower()
        body_lower = plain_text.lower()

        checks = [
            # 1. Title length (50-60 chars)
            SEOCheck(
                name="title_length",
                description="Title should be 50-65 characters",
                max_points=10,
                check_fn=lambda: (
                    40 <= len(title) <= 70,
                    f"Title is {len(title)} chars (target: 50-65)",
                ),
            ),
            # 2. Title contains primary keyword
            SEOCheck(
                name="title_keyword",
                description="Title must contain the primary keyword",
                max_points=10,
                check_fn=lambda: (
                    keyword_lower in title_lower,
                    f"Primary keyword {'found' if keyword_lower in title_lower else 'missing'} in title",
                ),
            ),
            # 3. Meta description length (150-160 chars)
            SEOCheck(
                name="meta_length",
                description="Meta description should be 120-165 characters",
                max_points=10,
                check_fn=lambda: (
                    100 <= len(meta_description) <= 170,
                    f"Meta description is {len(meta_description)} chars (target: 120-165)",
                ),
            ),
            # 4. Meta contains primary keyword
            SEOCheck(
                name="meta_keyword",
                description="Meta description should contain the primary keyword",
                max_points=5,
                check_fn=lambda: (
                    keyword_lower in meta_lower,
                    f"Primary keyword {'found' if keyword_lower in meta_lower else 'missing'} in meta",
                ),
            ),
            # 5. H2/H3 headings present (≥3)
            SEOCheck(
                name="headings_present",
                description="Content should have at least 3 H2/H3 headings",
                max_points=10,
                check_fn=lambda: (
                    len([h for h in headings if h[0] in ("h2", "h3")]) >= 3,
                    f"Found {len([h for h in headings if h[0] in ('h2', 'h3')])} headings (minimum: 3)",
                ),
            ),
            # 6. Keyword density (1-3%)
            SEOCheck(
                name="keyword_density",
                description="Primary keyword density should be 1-3%",
                max_points=10,
                check_fn=lambda: (
                    0.5 <= self._keyword_density(plain_text, primary_keyword) <= 4.0,
                    f"Keyword density: {self._keyword_density(plain_text, primary_keyword)}% (target: 1-3%)",
                ),
            ),
            # 7. LSI keywords used (≥3)
            SEOCheck(
                name="lsi_keywords_used",
                description="At least 3 LSI keywords should appear in content",
                max_points=10,
                check_fn=lambda: (
                    (used := sum(1 for kw in lsi_keywords if kw.lower() in body_lower)) >= 3,
                    f"{sum(1 for kw in lsi_keywords if kw.lower() in body_lower)} of {len(lsi_keywords)} LSI keywords used (minimum: 3)",
                ),
            ),
            # 8. Word count (≥1200)
            SEOCheck(
                name="word_count",
                description=f"Content should be at least {self._settings.content_min_word_count} words",
                max_points=10,
                check_fn=lambda: (
                    word_count >= self._settings.content_min_word_count,
                    f"Word count: {word_count} (minimum: {self._settings.content_min_word_count})",
                ),
            ),
            # 9. No duplicate headings
            SEOCheck(
                name="unique_headings",
                description="All headings should be unique",
                max_points=5,
                check_fn=lambda: (
                    len(set(h[1].lower() for h in headings)) == len(headings),
                    f"{'All headings are unique' if len(set(h[1].lower() for h in headings)) == len(headings) else 'Duplicate headings found'}",
                ),
            ),
            # 10. Keyword in first paragraph
            SEOCheck(
                name="keyword_in_intro",
                description="Primary keyword should appear in the first paragraph",
                max_points=5,
                check_fn=lambda: (
                    keyword_lower in paragraphs[0].lower() if paragraphs else False,
                    f"Primary keyword {'found' if paragraphs and keyword_lower in paragraphs[0].lower() else 'missing'} in first paragraph",
                ),
            ),
            # 11. Readability — average sentence length
            SEOCheck(
                name="readability",
                description="Average sentence should be under 25 words",
                max_points=5,
                check_fn=lambda: (
                    (avg := sum(self._count_words(s) for s in sentences) / max(len(sentences), 1)) < 25,
                    f"Average sentence length: {sum(self._count_words(s) for s in sentences) / max(len(sentences), 1):.1f} words (target: <25)",
                ),
            ),
            # 12. Paragraph length — no paragraph > 150 words
            SEOCheck(
                name="paragraph_length",
                description="No paragraph should exceed 150 words",
                max_points=5,
                check_fn=lambda: (
                    all(self._count_words(p) <= 150 for p in paragraphs),
                    f"{'All paragraphs are within limit' if all(self._count_words(p) <= 150 for p in paragraphs) else 'Some paragraphs exceed 150 words'}",
                ),
            ),
            # 13. Conclusion present
            SEOCheck(
                name="conclusion_present",
                description="Content should have a conclusion section",
                max_points=5,
                check_fn=lambda: (
                    any(
                        "conclusion" in h[1].lower()
                        or "summary" in h[1].lower()
                        or "takeaway" in h[1].lower()
                        or "final" in h[1].lower()
                        or "wrap" in h[1].lower()
                        for h in headings
                    ),
                    "Conclusion section {'found' if any('conclusion' in h[1].lower() or 'summary' in h[1].lower() or 'takeaway' in h[1].lower() for h in headings) else 'missing'}",
                ),
            ),
        ]

        return checks

    async def execute(self, context: PipelineContext) -> StageResult:
        """Run SEO validation checks on the content draft.

        Args:
            context: Pipeline context with content_draft populated.

        Returns:
            StageResult with SEO score and detailed report.
        """
        draft = context.content_draft
        title = draft.get("title", "")
        body_html = draft.get("body_html", "")
        meta_description = draft.get("meta_description", "")
        primary_keyword = draft.get("primary_keyword", "")
        lsi_keywords = draft.get("lsi_keywords", [])

        logger.info(
            "validating seo",
            title=title,
            keyword=primary_keyword,
        )

        # Build and run all checks
        checks = self._build_checks(
            title=title,
            body_html=body_html,
            meta_description=meta_description,
            primary_keyword=primary_keyword,
            lsi_keywords=lsi_keywords,
        )

        total_score = 0
        max_score = 0
        passed_checks = []
        failed_checks = []
        suggestions = []

        for check in checks:
            max_score += check.max_points
            try:
                passed, message = check.check_fn()
                check_result = {
                    "name": check.name,
                    "description": check.description,
                    "points": check.max_points if passed else 0,
                    "max_points": check.max_points,
                    "passed": passed,
                    "message": message,
                }

                if passed:
                    total_score += check.max_points
                    passed_checks.append(check_result)
                else:
                    failed_checks.append(check_result)
                    suggestions.append(
                        f"[{check.name}] {check.description}: {message}"
                    )

            except Exception as exc:
                logger.warning(
                    "seo check error",
                    check=check.name,
                    error=str(exc),
                )
                failed_checks.append({
                    "name": check.name,
                    "description": check.description,
                    "points": 0,
                    "max_points": check.max_points,
                    "passed": False,
                    "message": f"Check error: {exc}",
                })

        # Normalize to 0-100 scale
        normalized_score = round((total_score / max_score) * 100) if max_score > 0 else 0

        # Store in context
        context.seo_report = {
            "score": normalized_score,
            "raw_score": total_score,
            "max_score": max_score,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "suggestions": suggestions,
            "checks_total": len(checks),
            "checks_passed": len(passed_checks),
            "checks_failed": len(failed_checks),
        }

        logger.info(
            "seo validation complete",
            score=normalized_score,
            passed=len(passed_checks),
            failed=len(failed_checks),
            min_required=self._min_score,
            verdict="PASS" if normalized_score >= self._min_score else "FAIL",
        )

        if suggestions:
            logger.info("seo suggestions", suggestions=suggestions)

        return StageResult(
            stage_name=self.name,
            status=StageStatus.SUCCESS,
            data={
                "score": normalized_score,
                "passed": len(passed_checks),
                "failed": len(failed_checks),
                "meets_threshold": normalized_score >= self._min_score,
            },
        )
