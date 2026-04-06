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

### Docker Compose

```bash
cp .env.example .env   # edit with your values
docker compose up -d
```

`docker compose build` now requires Docker Buildx 0.17 or later. On older Unraid or distro-packaged Docker installs, use the published GHCR image with `docker compose up -d`, or build locally with `./build.sh` as shown below.

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
./build.sh
```

The script avoids `docker compose build`, so it still works on older Docker installations that do not ship a new enough Buildx plugin.

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
| `WORKER_CONCURRENCY` | `2` | Background job threads (ignored when `REDIS_URL` is set) |
| `REDIS_URL` | *(empty)* | Optional — set to `redis://host:6379/0` to use an existing Redis |
| `AUTH_ENABLED` | `false` | Set `true` to require Bearer token auth |
| `SECRET_KEY` | `change-me` | Token value when `AUTH_ENABLED=true` |
| `DATABASE_URL` | `sqlite:////data/immich_gpt.db` | SQLAlchemy DB URL |
| `APP_PORT` | `8000` | Host port (Compose only) |
| `IMMICH_GPT_IMAGE` | `ghcr.io/titatom/immich-gpt:latest` | Image tag used by `docker-compose.yml` |

---

## Upgrading

```bash
docker compose pull && docker compose up -d
```

Alembic migrations run automatically on startup — no manual migration step needed.

---

## Building the image locally (no GHCR required)

If the GHCR image isn't available yet (e.g. you are deploying before the first CI run completes), build the image directly from source:

```bash
# Build a local image with the same tag used by docker-compose.yml
./build.sh
docker compose up -d
```

Or build a custom local tag and tell Compose to use it:

```bash
./build.sh immich-gpt:local
IMMICH_GPT_IMAGE=immich-gpt:local docker compose up -d
```

---

## Publishing to GHCR (maintainers)

The GitHub Actions workflow (`.github/workflows/docker.yml`) publishes automatically:

| Trigger | Tags pushed |
|---------|-------------|
| Push / merge to `main` | `:latest`, `:main` |
| Version tag `v1.2.3` | `:latest`, `:1.2.3`, `:1.2`, `:1` |
| Manual dispatch | same as whichever ref was selected |

To publish manually:

```bash
docker build -f Dockerfile.unraid -t ghcr.io/titatom/immich-gpt:latest \
                                   -t ghcr.io/titatom/immich-gpt:1.0.0 .
docker push ghcr.io/titatom/immich-gpt:latest
docker push ghcr.io/titatom/immich-gpt:1.0.0
```
