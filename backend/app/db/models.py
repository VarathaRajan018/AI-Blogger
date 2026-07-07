"""SQLAlchemy ORM models for the AI Blogger platform.

All tables are defined here using SQLAlchemy 2.0 Mapped Column style.
UUIDs are used as primary keys for all tables.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


# ── Enums ───────────────────────────────────────────────────────


class PipelineStatus(str, enum.Enum):
    """Status of a pipeline run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ContentStatus(str, enum.Enum):
    """Status of a content draft."""

    DRAFT = "draft"
    SEO_PASSED = "seo_passed"
    SEO_FAILED = "seo_failed"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    FAILED = "failed"


class BlogPlatform(str, enum.Enum):
    """Supported blog platforms."""

    BLOGGER = "blogger"
    WORDPRESS = "wordpress"


# ── Models ──────────────────────────────────────────────────────


class Blog(Base):
    """Blog configuration — one row per managed blog site."""

    __tablename__ = "blogs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    platform: Mapped[BlogPlatform] = mapped_column(
        Enum(BlogPlatform), default=BlogPlatform.BLOGGER
    )
    blogger_blog_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    niche_config: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    human_approval_required: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    pipeline_runs: Mapped[list["PipelineRun"]] = relationship(
        back_populates="blog", cascade="all, delete-orphan"
    )
    analytics_snapshots: Mapped[list["AnalyticsSnapshot"]] = relationship(
        back_populates="blog", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Blog(id={self.id}, name={self.name!r}, platform={self.platform})>"


class PipelineRun(Base):
    """Record of a single pipeline execution."""

    __tablename__ = "pipeline_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    blog_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blogs.id"), nullable=False
    )
    status: Mapped[PipelineStatus] = mapped_column(
        Enum(PipelineStatus), default=PipelineStatus.PENDING
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    config_snapshot: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    posts_generated: Mapped[int] = mapped_column(Integer, default=0)
    posts_published: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    blog: Mapped["Blog"] = relationship(back_populates="pipeline_runs")
    content_drafts: Mapped[list["ContentDraft"]] = relationship(
        back_populates="pipeline_run", cascade="all, delete-orphan"
    )
    trend_reports: Mapped[list["TrendReport"]] = relationship(
        back_populates="pipeline_run", cascade="all, delete-orphan"
    )
    llm_usage_logs: Mapped[list["LLMUsageLog"]] = relationship(
        back_populates="pipeline_run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_pipeline_runs_blog_status", "blog_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<PipelineRun(id={self.id}, status={self.status})>"


class TrendReport(Base):
    """Snapshot of trending topics discovered during a pipeline run."""

    __tablename__ = "trend_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id"), nullable=False
    )
    blog_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blogs.id"), nullable=False
    )
    topics: Mapped[dict] = mapped_column(JSONB, nullable=False)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    researched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    pipeline_run: Mapped["PipelineRun"] = relationship(back_populates="trend_reports")

    def __repr__(self) -> str:
        return f"<TrendReport(id={self.id}, run_id={self.run_id})>"


class ContentDraft(Base):
    """AI-generated blog post draft with SEO data and publish state."""

    __tablename__ = "content_drafts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id"), nullable=False
    )
    blog_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blogs.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    meta_description: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    primary_keyword: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    lsi_keywords: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus), default=ContentStatus.DRAFT
    )
    seo_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    seo_report: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    image_suggestions: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    social_captions: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    blogger_post_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    published_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    pipeline_run: Mapped["PipelineRun"] = relationship(
        back_populates="content_drafts"
    )
    keyword_reports: Mapped[list["KeywordReport"]] = relationship(
        back_populates="content_draft", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_content_drafts_blog_status", "blog_id", "status"),
        Index("ix_content_drafts_run_id", "run_id"),
    )

    def __repr__(self) -> str:
        return f"<ContentDraft(id={self.id}, title={self.title!r}, status={self.status})>"


class KeywordReport(Base):
    """Keyword research data associated with a content draft."""

    __tablename__ = "keyword_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_drafts.id"), nullable=False
    )
    primary_keyword: Mapped[str] = mapped_column(String(200), nullable=False)
    search_volume: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    competition_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lsi_keywords: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    serp_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    content_draft: Mapped["ContentDraft"] = relationship(
        back_populates="keyword_reports"
    )

    def __repr__(self) -> str:
        return f"<KeywordReport(id={self.id}, keyword={self.primary_keyword!r})>"


class AnalyticsSnapshot(Base):
    """Daily analytics snapshot for a blog."""

    __tablename__ = "analytics_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    blog_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blogs.id"), nullable=False
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_pageviews: Mapped[int] = mapped_column(Integer, default=0)
    unique_visitors: Mapped[int] = mapped_column(Integer, default=0)
    avg_session_duration: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    top_posts: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    traffic_sources: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    adsense_revenue: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, default=0.0
    )

    # Relationships
    blog: Mapped["Blog"] = relationship(back_populates="analytics_snapshots")

    __table_args__ = (
        Index("ix_analytics_blog_date", "blog_id", "snapshot_date", unique=True),
    )

    def __repr__(self) -> str:
        return f"<AnalyticsSnapshot(blog_id={self.blog_id}, date={self.snapshot_date})>"


class LLMUsageLog(Base):
    """Token usage and cost tracking for LLM API calls."""

    __tablename__ = "llm_usage_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id"), nullable=False
    )
    module_name: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    pipeline_run: Mapped["PipelineRun"] = relationship(
        back_populates="llm_usage_logs"
    )

    __table_args__ = (
        Index("ix_llm_usage_run_id", "run_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<LLMUsageLog(module={self.module_name!r}, "
            f"provider={self.provider!r}, cost=${self.cost_usd:.4f})>"
        )
