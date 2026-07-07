"""Application configuration via Pydantic Settings.

All configuration is loaded from environment variables or .env file.
Use `get_settings()` to access the singleton settings instance.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Resolve project root (backend/..)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Main application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ─────────────────────────────────────────────
    app_name: str = "AI Blogger Automation Platform"
    app_env: str = "development"
    app_debug: bool = True
    app_secret_key: str = "change-me-in-production"
    app_log_level: str = "INFO"

    # ── Database ────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://blogger_user:blogger_pass@localhost:5432/ai_blogger"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # ── Redis ───────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ── LLM Providers ──────────────────────────────────────────
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-pro"
    gemini_temperature: float = 0.7

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_temperature: float = 0.7

    anthropic_api_key: str = ""
    claude_model: str = "claude-3-5-sonnet-20241022"

    groq_api_key: str = ""
    groq_model: str = "llama-3.1-70b-versatile"

    # LLM routing
    llm_default_provider: str = "gemini"
    llm_content_provider: str = ""
    llm_market_analysis_provider: str = ""
    llm_keyword_provider: str = ""
    llm_social_provider: str = ""
    llm_max_cost_per_run: float = 0.50

    # ── Google APIs ─────────────────────────────────────────────
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/callback"
    google_scopes: str = "https://www.googleapis.com/auth/blogger"

    search_console_site_url: str = ""
    ga4_property_id: str = ""
    ga4_credentials_path: str = ""

    # ── Trend Research ──────────────────────────────────────────
    news_api_key: str = ""
    rss_feed_urls: str = (
        "https://feeds.feedburner.com/TechCrunch,"
        "https://www.infoq.com/feed/,"
        "https://hnrss.org/frontpage"
    )
    pytrends_timeout: int = 30
    pytrends_retries: int = 3

    # ── Image Sources ───────────────────────────────────────────
    unsplash_access_key: str = ""
    pexels_api_key: str = ""
    imagen_api_key: str = ""

    # ── Blog Configuration ──────────────────────────────────────
    primary_blog_id: str = ""
    primary_blog_url: str = "https://varatharajan0180.blogspot.com/"

    # ── Pipeline ────────────────────────────────────────────────
    pipeline_cron_schedule: str = "0 0 * * *"
    pipeline_posts_per_run: int = 1
    pipeline_seo_min_score: int = 80
    pipeline_max_refinement_iterations: int = 2
    pipeline_human_approval_required: bool = False

    # ── Content ─────────────────────────────────────────────────
    content_min_word_count: int = 1200
    content_max_word_count: int = 2500
    content_language: str = "en"

    # ── Notifications ───────────────────────────────────────────
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    notification_email: str = ""
    slack_webhook_url: str = ""

    # ── Frontend / API ──────────────────────────────────────────
    api_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    cors_origins: str = "http://localhost:3000"

    # ── Derived Properties ──────────────────────────────────────

    @property
    def rss_feeds_list(self) -> list[str]:
        """Parse comma-separated RSS feed URLs into a list."""
        return [url.strip() for url in self.rss_feed_urls.split(",") if url.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env == "production"

    @field_validator("app_log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensure log level is valid."""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"Invalid log level: {v}. Must be one of {allowed}")
        return upper

    @field_validator("llm_default_provider")
    @classmethod
    def validate_llm_provider(cls, v: str) -> str:
        """Ensure default LLM provider is valid."""
        allowed = {"gemini", "openai", "claude", "groq"}
        if v.lower() not in allowed:
            raise ValueError(f"Invalid LLM provider: {v}. Must be one of {allowed}")
        return v.lower()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached singleton Settings instance.

    Uses lru_cache to ensure settings are loaded only once
    from environment / .env file.
    """
    return Settings()
