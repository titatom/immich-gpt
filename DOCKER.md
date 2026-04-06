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
| **Admin Email** | `admin@yourdomain.com` |
| **Admin Password** | *(set a strong password — you will be forced to change it on first login)* |
| **Immich URL** | `http://192.168.1.x:2283` *(can also be set in the UI after first login)* |
| **Immich API Key** | *(create in Immich → Account → API Keys — can also be set in the UI)* |

### Manual Docker run

```bash
docker run -d \
  --name immich-gpt \
  --restart unless-stopped \
  -p 8000:8000 \
  -v /path/to/appdata/immich-gpt:/data \
  -e ADMIN_EMAIL=admin@example.com \
  -e ADMIN_PASSWORD=change-me-on-first-login \
  -e IMMICH_URL=http://192.168.1.x:2283 \
  -e IMMICH_API_KEY=your-key \
  -e OPENAI_API_KEY=sk-... \
  ghcr.io/titatom/immich-gpt:latest
```

### Docker Compose (single-container)

```bash
cp .env.example .env   # fill in ADMIN_EMAIL + ADMIN_PASSWORD at minimum
docker compose up -d
```

The default `docker compose up` starts only the `app` service (no Redis, no separate worker).

---

## First login

1. Open `http://your-server:8000` in a browser.
2. Sign in with the `ADMIN_EMAIL` / `ADMIN_PASSWORD` you set in the env file.
3. You will be prompted to **change your password** immediately — this is enforced for all admin-bootstrapped accounts.
4. Once logged in, go to **Settings → Immich Connection** to configure your Immich URL and API key if you did not set them via environment variables.
5. Create additional user accounts via **Users** (admin sidebar link).

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
| `/data` | SQLite database (`immich_gpt.db`), persisted app data |

**Back up `/data`.**  It contains your bucket config, prompt templates, all AI suggestions, review decisions, and user accounts.

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_EMAIL` | *(empty)* | Email for the auto-created admin account on first startup |
| `ADMIN_PASSWORD` | *(empty)* | Initial password for the admin account (forced change on first login) |
| `ADMIN_USERNAME` | `admin` | Username for the auto-created admin account |
| `SESSION_COOKIE_SECURE` | `false` | Set `true` when running behind HTTPS (internet-exposed) |
| `IMMICH_URL` | *(empty)* | Immich server URL — can also be set per-user in the UI |
| `IMMICH_API_KEY` | *(empty)* | Immich API key — can also be set per-user in the UI |
| `OPENAI_API_KEY` | *(empty)* | OpenAI key (optional — configure via UI per user) |
| `OPENAI_MODEL` | `gpt-4o` | Default model when using env-based OpenAI config |
| `WORKER_CONCURRENCY` | `2` | Background job threads (single-container only) |
| `REDIS_URL` | *(empty)* | Set to `redis://host:6379/0` to enable RQ distributed workers |
| `DATABASE_URL` | `sqlite:////data/immich_gpt.db` | SQLAlchemy DB URL (SQLite default; PostgreSQL supported) |
| `APP_PORT` | `8000` | Host port (Compose only) |

### Internet-exposed deployments

If you expose Immich GPT to the internet, set:

```env
SESSION_COOKIE_SECURE=true
```

This marks the session cookie `Secure`, ensuring it is only sent over HTTPS.

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
