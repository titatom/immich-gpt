# Docker Deployment Guide

Immich GPT ships as a **single Docker image**.  Background jobs run in-process via a Python `ThreadPoolExecutor` — no extra services needed.  If you already run Redis on your home lab, you can point `REDIS_URL` at it and jobs will be dispatched through RQ instead — still the same single image.

---

## Single-container (recommended)

One image, one container, zero extra services.

### Unraid Community Apps

Search for **Immich GPT** in the CA plugin.  The template pre-fills all required fields.

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
cp .env.example .env   # fill in DATA_DIR, IMMICH_URL, IMMICH_API_KEY at minimum
docker compose up -d
```

`DATA_DIR` in `.env` controls where persistent data lives on the host.  For Unraid it defaults to `/mnt/user/appdata/immich-gpt`; change it to any path you prefer.

`docker compose build` now requires Docker Buildx 0.17 or later. On older Unraid or distro-packaged Docker installs, use the published GHCR image with `docker compose up -d`, or build locally with `./build.sh` as shown below.

---

## First login

1. Open `http://your-server:8000` in a browser.
2. The **setup wizard** appears on first visit (when no users exist yet).  Create the initial admin account with your chosen email, username, and password.
3. Once logged in, go to **Settings → Immich Connection** to configure your Immich URL and API key if you did not set them via environment variables.
4. Create additional user accounts via **Users** (admin sidebar link).

---

## Optional: Redis for background workers

If you already run Redis on your home lab and want to dispatch jobs through it instead of the built-in thread pool, set `REDIS_URL` in your `.env` or in the Unraid template:

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

| Host path (default) | Container path | Purpose |
|---------------------|----------------|---------|
| `DATA_DIR` → `/mnt/user/appdata/immich-gpt` | `/data` | SQLite database (`immich_gpt.db`), settings, job history, user accounts |
| *(optional)* | `/logs` | Rotating log files — mount a host path to persist logs across restarts |

The Compose file uses a **bind-mount** (not a named Docker volume) so the data directory is directly browsable on the host — ideal for Unraid, where `/mnt/user/appdata` is the standard location for container data.

To use a different path, set `DATA_DIR` in your `.env`:

```dotenv
DATA_DIR=/mnt/user/appdata/immich-gpt   # Unraid default
# DATA_DIR=/opt/immich-gpt/data         # Linux example
```

**Back up `DATA_DIR`.**  It contains your bucket config, prompt templates, all AI suggestions, review decisions, and user accounts.

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_DIR` | `/mnt/user/appdata/immich-gpt` | Host path bind-mounted to `/data` (Compose only) |
| `SECRET_KEY` | *(auto-generated)* | Cryptographic key for session cookies — auto-generated on first boot and saved to `/data/.secret_key` |
| `SESSION_COOKIE_SECURE` | `false` | Set `true` when running behind HTTPS |
| `IMMICH_URL` | *(empty)* | Immich server URL — can also be set per-user in the UI |
| `IMMICH_API_KEY` | *(empty)* | Immich API key — can also be set per-user in the UI |
| `OPENAI_API_KEY` | *(empty)* | OpenAI key (optional — configure via UI per user) |
| `OPENAI_MODEL` | `gpt-4o` | Default model when using env-based OpenAI config |
| `WORKER_CONCURRENCY` | `2` | Background job threads (built-in thread pool only) |
| `REDIS_URL` | *(empty)* | Optional — set to `redis://host:6379/0` to enable RQ workers |
| `DATABASE_URL` | `sqlite:////data/immich_gpt.db` | SQLite database path |
| `LOG_LEVEL` | `INFO` | Logging verbosity: DEBUG, INFO, WARNING, ERROR |
| `APP_PORT` | `8000` | Host port (Compose only) |
| `IMMICH_GPT_IMAGE` | `ghcr.io/titatom/immich-gpt:latest` | Image tag used by `docker-compose.yml` |

### Internet-exposed deployments

If you expose Immich GPT to the internet (e.g. through a reverse proxy), set:

```env
SESSION_COOKIE_SECURE=true
```

This marks the session cookie `Secure`, ensuring it is only sent over HTTPS.  See [`docs/reverse-proxy.md`](docs/reverse-proxy.md) for Nginx and Caddy configuration examples.

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
