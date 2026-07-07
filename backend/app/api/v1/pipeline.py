"""Pipeline API routes.

Provides endpoints for triggering and monitoring pipeline runs.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from app.config import Settings
from app.db.repositories.blog_repo import BlogRepository
from app.db.repositories.pipeline_repo import PipelineRepository
from app.dependencies import get_blog_repo, get_config, get_pipeline_repo

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])


# ── Request / Response Models ───────────────────────────────────


class TriggerPipelineRequest(BaseModel):
    """Request body for triggering a pipeline run."""

    blog_id: uuid.UUID
    dry_run: bool = False


class PipelineRunResponse(BaseModel):
    """Response for a pipeline run."""

    id: uuid.UUID
    blog_id: uuid.UUID
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    posts_generated: int = 0
    posts_published: int = 0
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}


class TriggerResponse(BaseModel):
    """Response after triggering a pipeline run."""

    run_id: uuid.UUID
    message: str


# ── Routes ──────────────────────────────────────────────────────


@router.post("/trigger", response_model=TriggerResponse, status_code=202)
async def trigger_pipeline(
    request: TriggerPipelineRequest,
    background_tasks: BackgroundTasks,
    blog_repo: BlogRepository = Depends(get_blog_repo),
    pipeline_repo: PipelineRepository = Depends(get_pipeline_repo),
    settings: Settings = Depends(get_config),
) -> TriggerResponse:
    """Trigger a manual pipeline run for a specific blog.

    Returns immediately with a run_id. The pipeline executes
    in the background.
    """
    # Validate blog exists
    blog = await blog_repo.get_by_id(request.blog_id)
    if blog is None:
        raise HTTPException(status_code=404, detail="Blog not found")

    # Create pipeline run record
    run = await pipeline_repo.create_run(
        blog_id=request.blog_id,
        config_snapshot={"dry_run": request.dry_run},
    )

    # TODO: Phase 3 — replace with Celery task dispatch
    # background_tasks.add_task(run_pipeline_task, run.id, request.dry_run)

    return TriggerResponse(
        run_id=run.id,
        message=f"Pipeline run queued for blog '{blog.name}'",
    )


@router.get("/runs", response_model=list[PipelineRunResponse])
async def list_runs(
    blog_id: Optional[uuid.UUID] = None,
    limit: int = 20,
    pipeline_repo: PipelineRepository = Depends(get_pipeline_repo),
) -> list[PipelineRunResponse]:
    """List recent pipeline runs, optionally filtered by blog."""
    runs = await pipeline_repo.get_recent_runs(blog_id=blog_id, limit=limit)
    return [
        PipelineRunResponse(
            id=run.id,
            blog_id=run.blog_id,
            status=run.status.value,
            started_at=run.started_at.isoformat() if run.started_at else None,
            completed_at=run.completed_at.isoformat() if run.completed_at else None,
            posts_generated=run.posts_generated,
            posts_published=run.posts_published,
            error_message=run.error_message,
        )
        for run in runs
    ]


@router.get("/runs/{run_id}", response_model=PipelineRunResponse)
async def get_run(
    run_id: uuid.UUID,
    pipeline_repo: PipelineRepository = Depends(get_pipeline_repo),
) -> PipelineRunResponse:
    """Get details of a specific pipeline run."""
    run = await pipeline_repo.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    return PipelineRunResponse(
        id=run.id,
        blog_id=run.blog_id,
        status=run.status.value,
        started_at=run.started_at.isoformat() if run.started_at else None,
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        posts_generated=run.posts_generated,
        posts_published=run.posts_published,
        error_message=run.error_message,
    )
