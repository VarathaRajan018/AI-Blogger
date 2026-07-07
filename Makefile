# ============================================================
#  AI Blogger Automation Platform — Makefile
#  Usage: make <target>
# ============================================================

.PHONY: help setup up down logs migrate seed run-pipeline test lint format clean

# Default target — show help
help:
	@echo ""
	@echo "  AI Blogger Automation Platform"
	@echo "  ================================"
	@echo ""
	@echo "  Setup & Infrastructure"
	@echo "  ----------------------"
	@echo "  make setup          Copy .env.example, build images, run migrations"
	@echo "  make up             Start all Docker services (dev mode)"
	@echo "  make down           Stop all Docker services"
	@echo "  make logs           Tail logs from all services"
	@echo "  make logs-api       Tail API logs only"
	@echo "  make logs-worker    Tail Celery worker logs only"
	@echo ""
	@echo "  Database"
	@echo "  --------"
	@echo "  make migrate        Run Alembic migrations (upgrade head)"
	@echo "  make migrate-down   Rollback last migration"
	@echo "  make seed           Seed database with sample blog config"
	@echo ""
	@echo "  Pipeline"
	@echo "  --------"
	@echo "  make run-pipeline   Trigger a manual pipeline run (BLOG_ID=1)"
	@echo "  make test-pipeline  Run pipeline with dry-run mode (no publishing)"
	@echo ""
	@echo "  Development"
	@echo "  -----------"
	@echo "  make test           Run all tests with pytest"
	@echo "  make lint           Run Ruff linter"
	@echo "  make format         Format code with Black + Ruff"
	@echo "  make clean          Remove all Docker volumes and caches"
	@echo ""

# ─── Setup ──────────────────────────────────────────────────────
setup:
	@echo ">>> Setting up AI Blogger Platform..."
	@if not exist .env (copy .env.example .env && echo "Created .env from .env.example — edit it with your API keys") else (echo ".env already exists, skipping")
	docker-compose build
	$(MAKE) migrate
	@echo ">>> Setup complete! Run 'make up' to start."

# ─── Services ───────────────────────────────────────────────────
up:
	docker-compose up -d
	@echo ">>> Services started."
	@echo "    API:      http://localhost:8000"
	@echo "    API Docs: http://localhost:8000/docs"
	@echo "    Frontend: http://localhost:3000"

down:
	docker-compose down

logs:
	docker-compose logs -f

logs-api:
	docker-compose logs -f api

logs-worker:
	docker-compose logs -f celery_worker

# ─── Database ───────────────────────────────────────────────────
migrate:
	docker-compose exec api alembic upgrade head

migrate-down:
	docker-compose exec api alembic downgrade -1

seed:
	docker-compose exec api python scripts/seed_db.py

# ─── Pipeline ───────────────────────────────────────────────────
BLOG_ID ?= 1

run-pipeline:
	@echo ">>> Triggering pipeline for blog ID=$(BLOG_ID)..."
	docker-compose exec api python -m app.pipeline.orchestrator --blog-id=$(BLOG_ID)

test-pipeline:
	@echo ">>> Running pipeline in DRY-RUN mode (no publishing)..."
	docker-compose exec api python -m app.pipeline.orchestrator --blog-id=$(BLOG_ID) --dry-run

# ─── Development ────────────────────────────────────────────────
test:
	docker-compose exec api pytest backend/tests/ -v --tb=short

lint:
	docker-compose exec api ruff check backend/app/

format:
	docker-compose exec api black backend/app/
	docker-compose exec api ruff check --fix backend/app/

# ─── Cleanup ────────────────────────────────────────────────────
clean:
	docker-compose down -v --remove-orphans
	@echo ">>> All Docker volumes removed."
