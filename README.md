# immich-gpt

> Turn your Immich library into something you can actually browse, search, and clean up without handing the steering wheel to AI.

`immich-gpt` is a self-hosted review workflow for Immich. It syncs your assets, asks AI to suggest buckets, descriptions, and tags, then puts every suggestion in front of you before anything gets written back.

It is built for people who like smart automation, but still want veto power.

## Why this repo is useful

Immich is great at storing your photos. `immich-gpt` helps with the messy part after that:

- turning a giant camera-roll backlog into something categorized
- adding descriptions and tags without editing every asset by hand
- spotting low-value shots without auto-deleting anything
- keeping Immich credentials server-side instead of sending them to the AI provider
- giving you a human-in-the-loop review queue instead of "hope the bot got it right"

## Why it feels safe

- Nothing is written back automatically
- Every suggestion can be reviewed, edited, approved, or rejected
- `Trash` is non-destructive
- Thumbnails are fetched server-side, so raw Immich URLs and credentials stay private

This is the "AI assistant, not AI intern with production access" version of photo organization.

## What you get

- Bucket suggestions for assets like Documents, Business, Personal, and Trash
- AI-generated descriptions and tags
- A review queue built for fast approve/edit/reject workflows
- Job progress in the UI for sync and classification runs
- A simple single-container Docker deployment by default
- An optional Redis + worker setup for larger libraries and heavier workloads

## Pick your deployment style

### Single-container mode (recommended)

One container, no Redis, no worker to babysit.

- best for home servers, Unraid, Synology, Portainer, and quick trials
- background jobs run in-process via `ThreadPoolExecutor`
- started with plain `docker compose up -d`

### Full-stack mode

Separate API, worker, and Redis containers.

- better when you classify large libraries regularly
- useful when you want a dedicated worker process
- started with `docker compose --profile full up -d`

`DOCKER.md` has the deeper deployment guide, including Unraid, manual `docker run`, volumes, and upgrades.

## Quick start

### 1. Copy the starter env file

```bash
cp .env.example .env
```

### 2. Fill in the important values

Required on a fresh install:

- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`

Usually required before your first real sync:

- `IMMICH_URL`
- `IMMICH_API_KEY`

Optional, but useful if you want OpenAI working immediately:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`

On a brand-new database, the backend uses `ADMIN_EMAIL`, `ADMIN_PASSWORD`, and `ADMIN_USERNAME` to create your first admin user automatically.

### 3. Build or pull the image

Build locally:

```bash
docker build -f Dockerfile.unraid -t immich-gpt:latest .
```

Or pull the published image:

```bash
docker pull ghcr.io/titatom/immich-gpt:latest
docker tag ghcr.io/titatom/immich-gpt:latest immich-gpt:latest
```

### 4. Start it

Recommended single-container launch:

```bash
docker compose up -d
```

Higher-throughput full-stack launch:

```bash
docker compose --profile full up -d
```

### 5. Open the app and do the fun part

1. Open `http://localhost:8000`
2. Sign in with `ADMIN_EMAIL` and `ADMIN_PASSWORD`
3. Go to `Settings` if you want to finish configuring Immich or your AI provider in the UI
4. Go to `Dashboard` and run `Sync Assets`
5. Start `Run AI Classification`
6. Open `Review` and start approving, editing, or rejecting suggestions

## First-run experience

If you just want to see the app come to life quickly:

1. boot the single-container version
2. sign in with the bootstrap admin account
3. add your Immich connection
4. kick off a sync
5. let the AI make suggestions
6. keep the good ones, fix the weird ones, reject the bad ones

That is the core loop, and it is the whole point of the project.

## Environment variables

The README covers the high-value knobs. `.env.example` includes the full commented starter config.

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
| `DATABASE_URL` | `sqlite:///./data/immich_gpt.db` | Backend DB URL for local or custom runs |
| `AUTH_ENABLED` | `false` | Optional extra Bearer-token gate on API requests |
| `SECRET_KEY` | `change-me-in-production` | Secret for tokens and the optional Bearer-token gate |

## Data and storage

The Docker deployment stores app state in `/data`.

That includes:

- the SQLite database
- saved settings
- prompt templates
- review decisions
- AI suggestions

Back up `/data` if you care about your curation work.

## Local development

### Backend

Run from `backend/` so the app loads the local `.env` file correctly:

```bash
cd backend
export PATH="$HOME/.local/bin:$PATH"
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Leave `REDIS_URL` empty for simple local development. If you want Redis-backed jobs locally, start Redis and the RQ worker separately.

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

## Default buckets

| Bucket | Purpose |
|--------|---------|
| Documents | Receipts, invoices, forms, scans, and paper photos |
| Business | Work sites, tools, and project documentation |
| Personal | Family, travel, events, and daily life |
| Trash | Blurry, accidental, or low-value shots |

`Trash` is still just a suggestion bucket. Nothing is deleted automatically.

## More Docker details

See `DOCKER.md` for:

- Unraid and home-server deployment notes
- manual `docker run` examples
- full-stack Redis/worker setup
- image build details
- upgrade commands

## Roadmap

- [ ] Ollama provider
- [ ] OpenRouter provider
- [ ] SSE for real-time job updates
- [ ] Asset detail view
- [ ] Video thumbnail support
- [ ] Duplicate/junk heuristic pre-filter
- [ ] Immich face/people metadata
