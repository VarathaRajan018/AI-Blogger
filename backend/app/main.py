"""AI Blogger Automation Platform — FastAPI Application Entry Point.

This module creates and configures the FastAPI application with:
- CORS middleware
- Structured logging
- Database lifecycle management
- API route mounting
- Health check endpoint
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_v1_router
from app.config import get_settings
from app.db.models import Base
from app.db.session import engine
from app.utils.logging import get_logger, setup_logging

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager.

    Handles startup (DB table creation, logging init) and
    shutdown (engine disposal) events.
    """
    # ── Startup ─────────────────────────────────────────────
    setup_logging(
        log_level=settings.app_log_level,
        json_output=settings.is_production,
    )
    logger.info(
        "starting application",
        app_name=settings.app_name,
        env=settings.app_env,
        debug=settings.app_debug,
    )

    # Create tables if they don't exist (dev convenience)
    # In production, use Alembic migrations instead
    if settings.app_debug:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("database tables ensured (debug mode)")

    yield

    # ── Shutdown ────────────────────────────────────────────
    logger.info("shutting down application")
    await engine.dispose()


# ── Application Factory ─────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    description=(
        "AI-powered autonomous blogging platform that researches trends, "
        "generates SEO-optimized content, and publishes to Google Blogger."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware ───────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ───────────────────────────────────────────────────────

app.include_router(api_v1_router)


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    """Application health check endpoint.

    Returns:
        Status and version information.
    """
    return {
        "status": "ok",
        "version": "0.1.0",
        "app": settings.app_name,
        "env": settings.app_env,
    }
