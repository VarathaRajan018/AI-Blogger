"""Keyword expansion prompt template.

Used by the KeywordResearcher stage to expand a trending topic
into a primary keyword, LSI keywords, and title suggestions.
"""

from __future__ import annotations

KEYWORD_EXPANSION_SYSTEM_PROMPT = """You are an expert SEO keyword researcher specializing in technology blogs. 
Your job is to analyze a trending topic and produce keyword research data that will help 
create a high-ranking blog post.

You must respond with valid JSON matching the exact schema provided."""


def build_keyword_expansion_prompt(
    topic_title: str,
    niche: str,
    description: str = "",
) -> str:
    """Build a keyword expansion prompt for the LLM.

    Args:
        topic_title: The trending topic to research.
        niche: The blog niche (e.g., "artificial intelligence").
        description: Optional description of the topic.

    Returns:
        Formatted prompt string.
    """
    return f"""Analyze this trending topic and generate comprehensive keyword research data.

**Trending Topic**: {topic_title}
**Blog Niche**: {niche}
{f"**Topic Description**: {description}" if description else ""}

Provide the following:

1. **primary_keyword**: A specific, long-tail keyword (3-6 words) that a blog post should target. 
   It must be search-friendly and relevant to the topic. Example: "machine learning model deployment best practices"

2. **lsi_keywords**: A list of 8-12 semantically related keywords that should appear naturally 
   in the blog post. Include a mix of:
   - Related long-tail phrases
   - Short-tail variants
   - Question-based keywords (how to, what is, why)
   - Action-based keywords (tutorial, guide, example)

3. **search_intent**: The dominant search intent for this keyword.
   One of: "informational", "transactional", "navigational", "commercial"

4. **suggested_titles**: 5 compelling blog post title variations that:
   - Include the primary keyword naturally
   - Follow proven title patterns (How-to, X Ways, Complete Guide, etc.)
   - Are 50-65 characters long for optimal SEO
   - Would achieve high click-through rates

5. **estimated_competition**: A score from 0.0 (low) to 1.0 (very high) estimating 
   how competitive this keyword is.

Respond ONLY with valid JSON in this exact format:
{{
    "primary_keyword": "your primary keyword here",
    "lsi_keywords": ["keyword1", "keyword2", ...],
    "search_intent": "informational",
    "suggested_titles": ["Title 1", "Title 2", ...],
    "estimated_competition": 0.5
}}"""
