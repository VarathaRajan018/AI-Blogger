# ADR-003: Google Blogger API v3 with OAuth 2.0

**Date**: 2026-07-07  
**Status**: Accepted  
**Deciders**: Platform Architect

---

## Context

The platform must publish blog posts programmatically to `varatharajan0180.blogspot.com`. We evaluated direct HTML scraping/form submission, third-party Blogger tools, and the official Blogger API v3.

## Decision

Use the **official Google Blogger API v3** with **OAuth 2.0** for all publishing operations, wrapped behind a `BaseBlogPublisher` abstraction interface.

## Rationale

| Factor | Rationale |
|--------|----------|
| **Official API** | Stable, documented, and supported by Google — no risk of breakage from UI changes |
| **Full CRUD** | Supports create, update, delete, and label management — all features we need |
| **OAuth 2.0** | Secure, revocable credentials — no need to store raw passwords |
| **Abstraction Layer** | `BaseBlogPublisher` interface means WordPress, Medium, Dev.to can be added later with zero changes to pipeline logic |
| **Rate Limits** | 10,000 requests/day (free) is sufficient for 1–50 posts/day at scale |
| **Labels/Tags** | API supports label assignment natively — critical for SEO taxonomy |

## Abstraction Design

```python
# core/interfaces/blog_publisher.py
class BaseBlogPublisher(ABC):
    async def publish_post(self, draft: ContentDraft) -> PublishResult: ...
    async def update_post(self, post_id: str, draft: ContentDraft) -> PublishResult: ...
    async def delete_post(self, post_id: str) -> bool: ...
    async def list_posts(self, blog_id: str) -> List[PostSummary]: ...
```

Concrete implementations:
- `BloggerPublisher` — Google Blogger API v3 (Phase 2)
- `WordPressPublisher` — WordPress REST API (Phase 6)

## Consequences

- **Positive**: Clean separation between pipeline logic and publishing destination; future-proof
- **Negative**: OAuth token refresh logic must be implemented and tokens securely stored
- **Mitigation**: Use Google's `google-auth` Python library for token management; store refresh tokens encrypted in DB
