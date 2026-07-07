"""Content generation prompt template.

Used by the ContentGenerator stage to produce a full SEO-optimized
blog post from keyword research data.
"""

from __future__ import annotations


CONTENT_GENERATION_SYSTEM_PROMPT = """You are an expert technology blog writer who creates SEO-optimized, 
engaging, and informative blog posts. Your content ranks well on Google and provides genuine value to readers.

Writing style guidelines:
- Use a conversational yet professional tone
- Include practical examples and code snippets where appropriate  
- Break content into scannable sections with clear H2 and H3 headings
- Use bullet points and numbered lists for easy reading
- Include relevant statistics and data points when possible
- Write in active voice
- Avoid filler words and fluff
- Make the content actionable — readers should learn something useful

You must respond with valid JSON matching the exact schema provided."""


def build_content_generation_prompt(
    primary_keyword: str,
    lsi_keywords: list[str],
    topic_title: str,
    suggested_titles: list[str],
    niche: str,
    min_word_count: int = 1200,
    max_word_count: int = 2500,
    search_intent: str = "informational",
) -> str:
    """Build a content generation prompt for the LLM.

    Args:
        primary_keyword: Target SEO keyword.
        lsi_keywords: Related keywords to include naturally.
        topic_title: Original trending topic.
        suggested_titles: AI-suggested title variations.
        niche: Blog niche.
        min_word_count: Minimum word count for the post.
        max_word_count: Maximum word count for the post.
        search_intent: Dominant search intent.

    Returns:
        Formatted prompt string.
    """
    lsi_formatted = ", ".join(f'"{kw}"' for kw in lsi_keywords[:10])
    titles_formatted = "\n".join(f"   - {t}" for t in suggested_titles[:5])

    return f"""Write a comprehensive, SEO-optimized blog post about the following topic.

**Topic**: {topic_title}
**Primary Keyword**: {primary_keyword}
**LSI Keywords to include naturally**: [{lsi_formatted}]
**Search Intent**: {search_intent}
**Blog Niche**: {niche}

**Suggested Titles** (pick the best or create a better one):
{titles_formatted}

**Content Requirements**:
1. **Word Count**: {min_word_count}-{max_word_count} words
2. **Title**: SEO-optimized, 50-65 characters, includes primary keyword
3. **Meta Description**: Compelling, 150-160 characters, includes primary keyword
4. **Structure**:
   - Engaging introduction (hook + what the reader will learn)
   - 4-6 H2 sections, each with 2-3 paragraphs
   - At least 2 H3 sub-sections under different H2s
   - Use code examples if the topic involves programming
   - Include a "Key Takeaways" or "Quick Summary" section
   - Strong conclusion with a call-to-action
5. **SEO**:
   - Primary keyword in title, first paragraph, at least 2 H2 headings, and conclusion
   - LSI keywords distributed naturally throughout (don't force them)
   - Keyword density for primary keyword: 1-2%
6. **HTML Format**: Use semantic HTML tags (h2, h3, p, ul, ol, li, code, pre, strong, em)
7. **Tags**: 5-8 relevant tags for blog categorization

**Important**: 
- Write original, insightful content — not generic summaries
- Include real-world examples, use cases, or code snippets
- Add practical tips the reader can implement immediately
- If the topic involves code, include well-commented code examples in appropriate language

Respond ONLY with valid JSON in this exact format:
{{
    "title": "Your SEO-optimized blog title here",
    "meta_description": "Compelling 150-160 character meta description here",
    "body_html": "<p>Full HTML content here...</p>",
    "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}"""
