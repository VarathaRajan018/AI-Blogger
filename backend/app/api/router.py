"""API v1 router — aggregates all v1 route modules."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.pipeline import router as pipeline_router

api_v1_router = APIRouter(prefix="/api/v1")

# Register sub-routers
api_v1_router.include_router(pipeline_router)

# Future: add more routers here
# api_v1_router.include_router(blogs_router)
# api_v1_router.include_router(content_router)
# api_v1_router.include_router(analytics_router)
# api_v1_router.include_router(settings_router)
