# 🤖 AI Blogger Automation Platform

> A fully autonomous, AI-driven blogging platform that researches trends, generates SEO-optimized content, publishes to Google Blogger, and tracks analytics — completely on autopilot.

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![LangChain](https://img.shields.io/badge/LangChain-latest-orange)](https://langchain.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue?logo=postgresql)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7+-red?logo=redis)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📖 Table of Contents

- [Overview](#-overview)
- [Target Blog](#-target-blog)
- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Pipeline Stages](#-pipeline-stages)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Configuration](#-configuration)
- [Roadmap](#-roadmap)
- [Revenue Strategy](#-revenue-strategy)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🌟 Overview

**AI Blogger Automation Platform** is a production-grade automation system designed to run the complete blogging lifecycle without human intervention. From discovering what's trending in the tech world to publishing a fully-formatted, SEO-optimized blog post on Google Blogger — every step is automated, observable, and configurable.

The platform is built with a **modular pipeline architecture** that allows each stage to be independently upgraded, tested, and swapped. AI providers (Gemini, GPT-4, Claude, Groq) are plug-in swappable through a provider abstraction layer, ensuring no vendor lock-in.

### Why Build This?

Growing a technology blog is time-intensive. A human blogger must:

- Monitor dozens of trend sources daily
- Research keywords and competition
- Write 1,500–3,000 word SEO articles
- Source or create images
- Publish and format posts
- Promote on social media
- Analyze traffic and iterate

This platform automates **all of the above**, enabling a single person to operate a content empire that generates passive income.

---

## 🎯 Target Blog

**Blog**: [Varatharajan's Tech Blog](https://varatharajan0180.blogspot.com/)

**Niches**:
- Artificial Intelligence & Machine Learning
- Programming (Java, Python)
- Software Engineering & Architecture
- Cloud Computing (AWS, GCP, Azure)
- Cybersecurity
- Technology News & Trends
- Interview Preparation & Career Guidance

---

## ✨ Features

### Core Automation Pipeline

| Stage | Description |
|-------|-------------|
| 🔍 **Trend Research** | Discovers trending topics via Google Trends, NewsAPI, and curated RSS feeds |
| 📊 **Market Analysis** | AI-powered competitive analysis and topic ranking by opportunity score |
| 🔑 **Keyword Research** | Extracts primary + LSI keywords with search volume and competition data |
| ✍️ **Content Generation** | Generates full SEO-optimized blog posts (title, body, meta description, tags) |
| 🖼️ **Image Suggestions** | Sources relevant images from Unsplash/Pexels or generates via AI |
| ✅ **SEO Validation** | Validates posts against 20+ SEO rules with automated refinement |
| 📤 **Blogger Publishing** | Publishes directly to Google Blogger via official API v3 |
| 📱 **Social Captions** | Generates Twitter, LinkedIn, and WhatsApp-ready promotional text |
| 📈 **Analytics Reporting** | Collects traffic and performance data from Google Analytics 4 |
| ⏰ **Daily Automation** | Full pipeline runs on a configurable CRON schedule |

### Platform Features

- 🔄 **Multi-Blog Support** — Manage and automate multiple Blogger sites from one platform
- 🤖 **AI Provider Agnosticism** — Switch between Gemini, GPT-4o, Claude, or Groq per module
- 👤 **Human-in-the-Loop** — Toggle approval mode: fully auto-publish or review before publishing
- 💰 **Cost Tracking** — Per-run LLM token usage and cost breakdown
- 📊 **Management Dashboard** — React-based UI for monitoring, content management, and analytics
- 🔁 **Retry & Resilience** — Automatic retry with exponential backoff at every stage
- 📝 **Content History** — Full audit trail of every generated draft and published post

---

## 🏗️ Architecture

The platform follows a **staged pipeline architecture** with clear separation of concerns:

```
Scheduler → Orchestrator → [Pipeline Stages] → Database
                                  ↓
                         LLM Provider Abstraction
                          (Gemini | GPT | Claude | Groq)
```

Each pipeline stage:
1. Reads its required inputs from a shared `PipelineContext`
2. Executes its specialized logic (with retry support)
3. Writes outputs back to context for the next stage
4. Logs all activity for observability

For the complete architecture document, see [`docs/architecture.md`](docs/architecture.md).

### Architecture Decision Records (ADRs)

| ADR | Decision |
|-----|---------|
| [ADR-001](docs/adr/001-python-langchain.md) | Python + LangChain as AI orchestration layer |
| [ADR-002](docs/adr/002-postgresql-over-mongodb.md) | PostgreSQL for structured pipeline metadata |
| [ADR-003](docs/adr/003-blogger-api-approach.md) | Google Blogger API v3 with OAuth 2.0 |

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Language | Python 3.11+ | Core backend |
| AI Orchestration | LangChain + LangGraph | LLM abstraction & agent workflows |
| Primary LLM | Google Gemini 1.5 Pro | Content generation |
| API Framework | FastAPI | Async REST API |
| Task Queue | Celery + Redis | Async pipeline execution |
| Scheduler | Celery Beat / APScheduler | Daily CRON automation |
| Database | PostgreSQL | Persistent storage |
| ORM | SQLAlchemy 2.0 | Async database access |
| Frontend | React + Vite | Management dashboard |
| Cache | Redis | API response caching |
| Publishing | Blogger API v3 | Blog post publishing |
| Containerization | Docker + Compose | Reproducible deployment |
| Logging | Structlog | Structured observability |

---

## ⚙️ Pipeline Stages

```
01. TrendResearcher    → Discovers trending topics (Google Trends, RSS, NewsAPI)
02. MarketAnalyzer     → Ranks topics by opportunity using AI analysis
03. KeywordResearcher  → Primary keyword + LSI keywords extraction
04. ContentGenerator   → Full blog post: title, intro, body, conclusion, meta
05. ImageSuggester     → Sourcing from Unsplash/Pexels + optional AI generation
06. SEOValidator       → 20+ SEO checks: readability, density, meta, headings
07. BlogPublisher      → Publish to Google Blogger via API
08. SocialMediaGen     → Twitter thread, LinkedIn post, WhatsApp caption
09. AnalyticsReporter  → 7-day rolling traffic and engagement metrics
```

---

## 📁 Project Structure

```
ai-blogger/
├── backend/
│   └── app/
│       ├── api/            # FastAPI route handlers
│       ├── core/           # Domain models & interfaces (ABCs)
│       ├── providers/      # LLM, publisher, image, trend providers
│       ├── pipeline/       # Pipeline stages & orchestrator
│       ├── db/             # SQLAlchemy models & repositories
│       ├── tasks/          # Celery async tasks
│       └── utils/          # Logging, retry, cost tracking
├── frontend/
│   └── src/
│       ├── pages/          # Dashboard, Content, Analytics, Settings
│       ├── components/     # Reusable UI components
│       └── services/       # API client layer
├── docs/
│   ├── architecture.md     # Full architecture document
│   └── adr/                # Architecture Decision Records
├── scripts/                # Setup and utility scripts
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🚀 Getting Started

> ⚠️ **Phase 2 implementation in progress.** This section will be completed with setup instructions when the core codebase is available.

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Google Cloud project with Blogger API enabled
- Google OAuth 2.0 credentials
- An LLM API key (Gemini recommended)

### Quick Start (coming in Phase 2)

```bash
# Clone the repository
git clone https://github.com/yourusername/ai-blogger.git
cd ai-blogger

# Copy environment configuration
cp .env.example .env
# Edit .env with your API keys

# Start all services
docker-compose up -d

# Run setup migrations
make setup

# Trigger a manual pipeline run
make run-pipeline BLOG_ID=1
```

---

## ⚙️ Configuration

All configuration is managed via environment variables (`.env` file). See [`.env.example`](.env.example) for the complete reference.

Key configuration areas:
- **LLM Provider** — Select primary and fallback AI providers per module
- **Blog Targets** — Configure one or more Blogger sites
- **Schedule** — Set the daily automation time (default: 06:00 AM)
- **Approval Mode** — Toggle human review before publishing
- **Cost Limits** — Set maximum token spend per pipeline run

---

## 🗺️ Roadmap

| Phase | Status | Milestone |
|-------|--------|-----------|
| **Phase 1** | ✅ Complete | Architecture & Design |
| **Phase 2** | 🔄 Next | Core Pipeline (Trend → Publish) |
| **Phase 3** | ⏳ Planned | Images, Social Captions, Scheduler |
| **Phase 4** | ⏳ Planned | React Dashboard + Multi-Blog |
| **Phase 5** | ⏳ Planned | AI Quality + Revenue Tracking |
| **Phase 6** | ⏳ Planned | Production Hardening + WordPress |

---

## 💰 Revenue Strategy

The platform is designed to grow the blog into a revenue-generating asset through:

| Channel | Strategy |
|---------|---------|
| **Google AdSense** | High-traffic SEO content drives ad impressions |
| **Affiliate Marketing** | AI-detected affiliate opportunities embedded in relevant posts |
| **Digital Products** | Courses, eBooks, and templates promoted through blog content |
| **Sponsored Posts** | Authority blog attracts sponsored content opportunities |
| **Email Marketing** | Auto-generated newsletter drafts grow subscriber list |

---

## 🤝 Contributing

Contributions are welcome! Please read the [Contributing Guide](docs/CONTRIBUTING.md) and follow the project's [Coding Standards](docs/architecture.md#coding-standards).

### Commit Convention

```
feat: add new pipeline stage for internal linking
fix: handle Blogger API rate limit gracefully
refactor: extract LLM prompt templates to dedicated module
docs: update architecture diagram for Phase 3
test: add unit tests for SEOValidator
```

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with ❤️ to automate the future of content creation**

[Blog](https://varatharajan0180.blogspot.com/) · [Architecture Docs](docs/architecture.md) · [Report an Issue](https://github.com/VarathaRajan018/AI-Blogger/issues)

</div>
