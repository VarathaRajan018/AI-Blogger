# Setup & Installation Guide

## Prerequisites

Before starting, ensure you have the following installed:

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | [python.org](https://python.org) |
| Docker Desktop | Latest | [docker.com](https://docker.com) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org) |
| Git | Latest | [git-scm.com](https://git-scm.com) |

---

## Step 1: Google Cloud Setup

### 1.1 Create a Google Cloud Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (e.g., `ai-blogger-platform`)
3. Note your **Project ID**

### 1.2 Enable APIs

In your Google Cloud project, enable the following APIs:

- **Blogger API v3** — for publishing posts
- **Google Analytics Data API** — for traffic analytics
- **Google Search Console API** — for keyword data

Navigate to: **APIs & Services → Library** → search and enable each.

### 1.3 Create OAuth 2.0 Credentials

1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth 2.0 Client ID**
3. Application type: **Desktop App** (for initial setup) or **Web Application**
4. Add authorized redirect URI: `http://localhost:8000/auth/callback`
5. Download the JSON credentials file → save as `credentials/google_oauth.json`

### 1.4 Get Your Blogger Blog ID

1. Open [blogger.com](https://blogger.com)
2. Go to your blog settings
3. The **Blog ID** is in the URL: `https://www.blogger.com/blog/posts/XXXXXXXXXX`
4. Copy this number — it's your `PRIMARY_BLOG_ID` in `.env`

---

## Step 2: LLM API Keys

### Gemini (Recommended — Primary)
1. Go to [ai.google.dev](https://ai.google.dev)
2. Create an API key
3. Set `GEMINI_API_KEY` in `.env`

### OpenAI (Fallback)
1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Create a new secret key
3. Set `OPENAI_API_KEY` in `.env`

---

## Step 3: Image Source API Keys

### Unsplash
1. Go to [unsplash.com/developers](https://unsplash.com/developers)
2. Create a new application
3. Copy the **Access Key** → set `UNSPLASH_ACCESS_KEY` in `.env`

### Pexels
1. Go to [www.pexels.com/api](https://www.pexels.com/api/)
2. Request an API key
3. Set `PEXELS_API_KEY` in `.env`

---

## Step 4: NewsAPI Key

1. Go to [newsapi.org](https://newsapi.org)
2. Register for a free account
3. Copy your API key → set `NEWS_API_KEY` in `.env`

---

## Step 5: Project Installation

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/ai-blogger.git
cd ai-blogger

# 2. Run setup (creates .env, builds Docker images, runs migrations)
make setup

# 3. Edit your .env file with all API keys collected above
# Windows:
notepad .env
# Mac/Linux:
nano .env
```

---

## Step 6: First Run

```bash
# Start all services
make up

# Verify everything is running
docker-compose ps

# Test the pipeline in dry-run mode (no actual publishing)
make test-pipeline BLOG_ID=1

# Once confirmed working, run for real
make run-pipeline BLOG_ID=1
```

---

## Step 7: Access the Dashboard

| Service | URL |
|---------|-----|
| **Frontend Dashboard** | http://localhost:3000 |
| **API** | http://localhost:8000 |
| **API Documentation** | http://localhost:8000/docs |
| **API ReDoc** | http://localhost:8000/redoc |

---

## Troubleshooting

### OAuth Token Issues
If you see `invalid_grant` errors from the Blogger API:
```bash
# Re-run the OAuth authorization flow
docker-compose exec api python scripts/authorize_google.py
```

### Database Connection Issues
```bash
# Check DB is healthy
docker-compose ps db
docker-compose logs db

# Reset and remigrate (WARNING: destroys data)
make clean
make setup
```

### Celery Worker Not Processing Tasks
```bash
# Check worker is connected to Redis
docker-compose logs celery_worker

# Restart worker
docker-compose restart celery_worker
```

### LLM API Errors
- Verify API keys in `.env` are correct and active
- Check rate limits on provider dashboards
- The system will automatically fall back to the secondary LLM provider

---

## Environment Variables Reference

See [`.env.example`](../.env.example) for the complete annotated reference of all configuration options.
