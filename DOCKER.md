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

### Docker Compose

```bash
cp .env.example .env   # fill in ADMIN_EMAIL + ADMIN_PASSWORD at minimum
docker compose up -d
```

`docker compose build` now requires Docker Buildx 0.17 or later. On older Unraid or distro-packaged Docker installs, use the published GHCR image with `docker compose up -d`, or build locally with `./build.sh` as shown below.

---

## First login

1. Open `http://your-server:8000` in a browser.
2. Sign in with the `ADMIN_EMAIL` / `ADMIN_PASSWORD` you set in the env file.
3. You will be prompted to **change your password** immediately — this is enforced for all admin-bootstrapped accounts.
4. Once logged in, go to **Settings → Immich Connection** to configure your Immich URL and API key if you did not set them via environment variables.
5. Create additional user accounts via **Users** (admin sidebar link).

---

## Multi-container stack (full stack)

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
| `IMMICH_GPT_IMAGE` | `ghcr.io/titatom/immich-gpt:latest` | Image tag used by `docker-compose.yml` |

### Internet-exposed deployments

If you expose Immich GPT to the internet, set:

```env
SESSION_COOKIE_SECURE=true
```

This marks the session cookie `Secure`, ensuring it is only sent over HTTPS.

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
