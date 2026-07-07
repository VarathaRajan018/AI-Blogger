# API Reference

> **Note**: This document will be auto-generated from FastAPI's OpenAPI schema in Phase 2.  
> The full interactive API documentation will be available at `http://localhost:8000/docs` once the backend is implemented.

---

## API Version

All endpoints are prefixed with `/api/v1/`

---

## Planned Endpoints

### Blogs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/blogs` | List all configured blogs |
| `POST` | `/api/v1/blogs` | Add a new blog configuration |
| `GET` | `/api/v1/blogs/{blog_id}` | Get blog details |
| `PUT` | `/api/v1/blogs/{blog_id}` | Update blog configuration |
| `DELETE` | `/api/v1/blogs/{blog_id}` | Remove a blog |

### Pipeline

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/pipeline/trigger` | Manually trigger a pipeline run |
| `GET` | `/api/v1/pipeline/runs` | List all pipeline runs |
| `GET` | `/api/v1/pipeline/runs/{run_id}` | Get detailed run status |
| `POST` | `/api/v1/pipeline/runs/{run_id}/cancel` | Cancel a running pipeline |

### Content

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/content/drafts` | List all content drafts |
| `GET` | `/api/v1/content/drafts/{draft_id}` | Get a specific draft |
| `PUT` | `/api/v1/content/drafts/{draft_id}` | Edit a draft |
| `POST` | `/api/v1/content/drafts/{draft_id}/approve` | Approve and publish a draft |
| `POST` | `/api/v1/content/drafts/{draft_id}/reject` | Reject a draft with notes |

### Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/analytics/summary` | Get 7-day analytics summary |
| `GET` | `/api/v1/analytics/posts` | Get per-post analytics |
| `GET` | `/api/v1/analytics/trends` | Get traffic trend data |

### Settings

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/settings` | Get current platform settings |
| `PUT` | `/api/v1/settings` | Update platform settings |
| `GET` | `/api/v1/settings/llm-providers` | List available LLM providers |

---

## Authentication

The API uses **Bearer token authentication** for the dashboard.  
Google OAuth is handled via the `/auth/` endpoints.

---

## Error Responses

All errors follow the RFC 7807 Problem Details format:

```json
{
  "type": "https://api.aiblogger.local/errors/pipeline-failed",
  "title": "Pipeline Execution Failed",
  "status": 500,
  "detail": "TrendResearcher stage failed after 3 retries: Google Trends rate limited",
  "instance": "/api/v1/pipeline/runs/abc-123",
  "run_id": "abc-123",
  "stage": "trend_researcher"
}
```
