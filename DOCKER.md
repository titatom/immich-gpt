# Docker Deployment Guide

Immich GPT ships as a **single Docker image**.  Background jobs run in-process via a Python `ThreadPoolExecutor`, so no extra services are needed.  If you already run Redis, you can point `REDIS_URL` at it and jobs will be dispatched through RQ instead — still the same single image.

---

## Single-container (recommended)

One image, one container, zero extra services.

### Unraid Community Apps

Search for **Immich GPT** in the CA plugin.  The template pre-fills all required fields.

**Minimum configuration:**

| Field | Value |
|-------|-------|
| **Data Directory** | `/mnt/user/appdata/immich-gpt` |
| **Immich URL** | `http://192.168.1.x:2283` |
| **Immich API Key** | *(create in Immich → Account → API Keys)* |
| **Admin Email** | `admin@example.com` |
| **Admin Password** | `change-me-now` |
| **OpenAI API Key** | *(or leave blank and configure Ollama in the UI)* |

You can leave Immich URL / API Key blank and configure them after first launch via **Settings → Immich Connection**.
Set the admin email/password before the first launch so the initial admin account can be created.

### Manual Docker run

```bash
docker run -d \
  --name immich-gpt \
  --restart unless-stopped \
  -p 8000:8000 \
  -v /path/to/appdata/immich-gpt:/data \
  -e IMMICH_URL=http://192.168.1.x:2283 \
  -e IMMICH_API_KEY=your-key \
  -e ADMIN_EMAIL=admin@example.com \
  -e ADMIN_PASSWORD=change-me-now \
  -e OPENAI_API_KEY=sk-... \
  ghcr.io/titatom/immich-gpt:latest
```

### Docker Compose

```bash
cp .env.example .env   # edit with your values
docker compose up -d
```

On a fresh database, make sure `.env` includes `ADMIN_EMAIL` and `ADMIN_PASSWORD` so the bootstrap admin can sign in.

---

## Using an existing Redis instance (optional)

If you already run Redis (e.g. for another service on the same host), you can have Immich GPT dispatch background jobs through it instead of the built-in thread pool.  No extra containers are added — it is still the same single image.

Set `REDIS_URL` in your `.env` or in the Unraid template:

```dotenv
REDIS_URL=redis://192.168.1.x:6379/0
```

When `REDIS_URL` is set, `WORKER_CONCURRENCY` is ignored because job execution moves to RQ.  You can optionally run a dedicated RQ worker in a second container of the same image:

```bash
docker run -d \
  --name immich-gpt-worker \
  --restart unless-stopped \
  -v /path/to/appdata/immich-gpt:/data \
  -e DATABASE_URL=sqlite:////data/immich_gpt.db \
  -e REDIS_URL=redis://192.168.1.x:6379/0 \
  ghcr.io/titatom/immich-gpt:latest \
  python -m app.workers.rq_worker
```

> For most home-server installs the built-in thread pool (no Redis) is the right choice.

---

## Building the image locally

The production image uses a **two-stage build**: Node.js builds the React frontend, then the Python runtime stage copies the compiled assets.

```bash
docker build -f Dockerfile.unraid -t immich-gpt:local .
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
| `ADMIN_EMAIL` | *(empty)* | Bootstrap admin email used only when no users exist yet |
| `ADMIN_PASSWORD` | *(empty)* | Bootstrap admin password used only when no users exist yet |
| `ADMIN_USERNAME` | `admin` | Bootstrap admin username |
| `WORKER_CONCURRENCY` | `2` | Background job threads (ignored when `REDIS_URL` is set) |
| `REDIS_URL` | *(empty)* | Optional — set to `redis://host:6379/0` to use an existing Redis |
| `AUTH_ENABLED` | `false` | Set `true` to require Bearer token auth |
| `SECRET_KEY` | `change-me` | Token value when `AUTH_ENABLED=true` |
| `DATABASE_URL` | `sqlite:////data/immich_gpt.db` | SQLAlchemy DB URL |
| `APP_PORT` | `8000` | Host port (Compose only) |

---

## Upgrading

```bash
docker compose pull && docker compose up -d
```

Alembic migrations run automatically on startup — no manual migration step needed.

---

## Publishing to GHCR (maintainers)

```bash
docker build -f Dockerfile.unraid -t ghcr.io/titatom/immich-gpt:latest \
                                   -t ghcr.io/titatom/immich-gpt:1.0.0 .
docker push ghcr.io/titatom/immich-gpt:latest
docker push ghcr.io/titatom/immich-gpt:1.0.0
```

A GitHub Actions workflow (`.github/workflows/docker.yml`) automates this on every tagged release.
