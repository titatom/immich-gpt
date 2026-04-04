# Docker Deployment Guide

Immich GPT ships as a **single Docker image** for home-server use (Unraid, Synology, Portainer, etc.) and optionally as a **multi-container stack** for higher-volume deployments.

---

## Single-container (recommended for Unraid / home servers)

One image, one container, zero extra services.  Background jobs run in-process via a Python `ThreadPoolExecutor`.  The built React UI is served directly from FastAPI.

### Unraid Community Apps

Search for **Immich GPT** in the CA plugin.  The template pre-fills all required fields.

**Minimum configuration:**

| Field | Value |
|-------|-------|
| **Data Directory** | `/mnt/user/appdata/immich-gpt` |
| **Immich URL** | `http://192.168.1.x:2283` |
| **Immich API Key** | *(create in Immich → Account → API Keys)* |
| **OpenAI API Key** | *(or leave blank and configure Ollama in the UI)* |

You can leave Immich URL / API Key blank and configure them after first launch via **Settings → Immich Connection**.

### Manual Docker run

```bash
docker run -d \
  --name immich-gpt \
  --restart unless-stopped \
  -p 8000:8000 \
  -v /path/to/appdata/immich-gpt:/data \
  -e IMMICH_URL=http://192.168.1.x:2283 \
  -e IMMICH_API_KEY=your-key \
  -e OPENAI_API_KEY=sk-... \
  ghcr.io/titatom/immich-gpt:latest
```

### Docker Compose (single-container)

```bash
cp .env.example .env   # edit with your values
docker compose up -d
```

The default `docker compose up` starts only the `app` service (no Redis, no separate worker).

---

## Multi-container stack (full stack)

Use this when classifying **1 000+ assets/day** or when you want a separate worker process (e.g., to avoid blocking the API during long classification runs).

```bash
cp .env.example .env
# edit .env — set REDIS_URL=redis://redis:6379/0
docker compose --profile full up -d
```

This starts three containers:
- `immich-gpt-api` — FastAPI + Uvicorn
- `immich-gpt-worker` — RQ worker (reads from Redis queue)
- `immich-gpt-redis` — Redis 7 (job queue + result backend)

---

## Building the image locally

The production image uses a **two-stage build**: Node.js builds the React frontend, then the Python runtime stage copies the compiled assets.

```bash
# Build the single-container image
docker build -f Dockerfile.unraid -t immich-gpt:local .

# Build the API-only image (for full-stack compose)
docker build -f backend/Dockerfile -t immich-gpt-api:local backend/
```

---

## Volumes

| Mount point | Purpose |
|-------------|---------|
| `/data` | SQLite database (`immich_gpt.db`), persisted app settings |

**Back up `/data`.**  It contains your bucket config, prompt templates, all AI suggestions, and review decisions.

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `IMMICH_URL` | *(empty)* | Immich server URL — can also be set in the UI |
| `IMMICH_API_KEY` | *(empty)* | Immich API key — can also be set in the UI |
| `OPENAI_API_KEY` | *(empty)* | OpenAI key (optional — configure via UI) |
| `OPENAI_MODEL` | `gpt-4o` | Default model when using env-based OpenAI config |
| `WORKER_CONCURRENCY` | `2` | Background job threads (single-container only) |
| `REDIS_URL` | *(empty)* | Set to `redis://host:6379/0` to enable RQ mode |
| `AUTH_ENABLED` | `false` | Set `true` to require Bearer token auth |
| `SECRET_KEY` | `change-me` | Token value when `AUTH_ENABLED=true` |
| `DATABASE_URL` | `sqlite:////data/immich_gpt.db` | SQLAlchemy DB URL |
| `APP_PORT` | `8000` | Host port (Compose only) |

---

## Upgrading

```bash
# Single-container
docker compose pull && docker compose up -d

# Full stack
docker compose --profile full pull && docker compose --profile full up -d
```

Alembic migrations run automatically on startup — no manual migration step needed.

---

## Publishing to GHCR (maintainers)

```bash
# Tag and push
docker build -f Dockerfile.unraid -t ghcr.io/titatom/immich-gpt:latest \
                                   -t ghcr.io/titatom/immich-gpt:1.0.0 .
docker push ghcr.io/titatom/immich-gpt:latest
docker push ghcr.io/titatom/immich-gpt:1.0.0
```

A GitHub Actions workflow (`.github/workflows/docker.yml`) automates this on every tagged release.
