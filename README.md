# immich-gpt

> AI-assisted metadata enrichment and review for Immich.

`immich-gpt` connects to your Immich library, sends thumbnails and metadata to an AI provider, and stages the resulting bucket, description, and tag suggestions for human review before anything is written back.

## Highlights

- Sync assets from Immich without exposing your Immich credentials to the AI provider
- Classify assets into editable buckets and generate descriptions and tags
- Review every suggestion before write-back
- Track long-running sync/classification jobs in the web UI
- Run as a simple single-container app by default, or with Redis + a dedicated worker for higher throughput

## How it works

1. Sign in to the web app.
2. Add or confirm your Immich connection and AI provider settings.
3. Sync assets from Immich.
4. Run AI classification jobs.
5. Review, edit, approve, or reject suggestions.
6. Write approved metadata back to Immich.

Nothing is written automatically. Review stays in the loop.

## Deployment modes

### Single-container mode (default)

- One container
- No Redis required
- Background jobs run in-process via `ThreadPoolExecutor`
- Best fit for home servers, Unraid, Synology, and local evaluation

Start it with plain `docker compose up -d`.

### Full-stack mode

- Separate API container
- Separate worker container
- Redis-backed job queue
- Better fit for larger libraries or heavier sustained workloads

Start it with `docker compose --profile full up -d`.

More deployment examples are in `DOCKER.md`.

## Quick start

### 1. Create your env file

```bash
cp .env.example .env
```

### 2. Edit the required values

At minimum, set:

- `IMMICH_URL`
- `IMMICH_API_KEY`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`

Optional but usually useful on day one:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`

The admin bootstrap values are important on a fresh database. If no users exist yet, the backend creates that first admin account automatically on startup.

### 3. Build or pull the app image

Build locally:

```bash
docker build -f Dockerfile.unraid -t immich-gpt:latest .
```

Or use the published image:

```bash
docker pull ghcr.io/titatom/immich-gpt:latest
docker tag ghcr.io/titatom/immich-gpt:latest immich-gpt:latest
```

### 4. Start the app

Single-container mode:

```bash
docker compose up -d
```

Full-stack mode:

```bash
docker compose --profile full up -d
```

### 5. Sign in and run your first job

1. Open `http://localhost:8000`
2. Sign in with `ADMIN_EMAIL` / `ADMIN_PASSWORD`
3. Go to `Settings` if you want to finish configuring Immich or the AI provider in the UI
4. Go to `Dashboard` and run `Sync Assets`
5. Start `Run AI Classification`
6. Review results in `Review`

## Environment variables

`README` lists the most important variables; `.env.example` contains the full starter file with comments.

| Variable | Default | Description |
|----------|---------|-------------|
| `IMMICH_URL` | empty | Immich server URL |
| `IMMICH_API_KEY` | empty | Immich API key |
| `OPENAI_API_KEY` | empty | OpenAI API key when using env-based provider config |
| `OPENAI_MODEL` | `gpt-4o` | Default OpenAI model |
| `ADMIN_EMAIL` | empty | First admin account email on a fresh database |
| `ADMIN_PASSWORD` | empty | First admin account password on a fresh database |
| `ADMIN_USERNAME` | `admin` | First admin username on a fresh database |
| `APP_PORT` | `8000` | Host port published by Docker Compose |
| `WORKER_CONCURRENCY` | `2` | In-process worker threads in single-container mode |
| `REDIS_URL` | empty | Enable Redis/RQ mode for custom or multi-process deployments |
| `DATABASE_URL` | `sqlite:///./data/immich_gpt.db` | Backend DB URL for local/custom runs |
| `AUTH_ENABLED` | `false` | Optional extra Bearer-token gate on API requests |
| `SECRET_KEY` | `change-me-in-production` | Secret for tokens and optional Bearer-token gate |

## Local development

### Backend

Run from `backend/` so the app loads the local `.env` file correctly:

```bash
cd backend
export PATH="$HOME/.local/bin:$PATH"
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

For local single-process development, leave `REDIS_URL` empty. If you want Redis-backed jobs locally, start Redis and the RQ worker separately.

### Frontend

```bash
cd frontend
npm install
npx vite --host 0.0.0.0 --port 3000
```

The Vite dev server proxies `/api` to the backend on port `8000`.

## Running tests

Backend:

```bash
cd backend
python3 -m pytest tests/ -v
```

Frontend:

```bash
cd frontend
npm test
npm run lint
npx tsc --noEmit
```

## API surface

Key endpoints:

- `GET /api/health`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET/POST /api/settings/immich`
- `GET/POST /api/settings/providers`
- `POST /api/jobs/sync`
- `POST /api/jobs/classify`
- `GET /api/review/queue`
- `POST /api/review/item/{id}/approve`
- `POST /api/review/item/{id}/reject`

## Default buckets

| Bucket | Purpose |
|--------|---------|
| Documents | Receipts, invoices, forms, scans, and paper photos |
| Business | Work sites, tools, and project documentation |
| Personal | Family, travel, events, and daily life |
| Trash | Blurry, accidental, or low-value shots |

`Trash` is non-destructive. Nothing is deleted automatically.

## Roadmap

- [ ] Ollama provider
- [ ] OpenRouter provider
- [ ] SSE for real-time job updates
- [ ] Asset detail view
- [ ] Video thumbnail support
- [ ] Duplicate/junk heuristic pre-filter
- [ ] Immich face/people metadata
