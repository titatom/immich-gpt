# immich-gpt

<p align="center">
  <img src="frontend/public/logo.svg" alt="immich-gpt logo" width="320" />
</p>

**AI metadata enrichment and review-first organization for Immich.**

immich-gpt is a self-hosted web app that connects to your Immich library, pulls thumbnails and metadata, asks an AI model for descriptions, tags, and bucket placement, and lets you approve every change before it is written back.

## Key highlights

- Review-first workflow: nothing is written back automatically
- Built for Immich: sync your library, classify assets, and organize albums
- Flexible providers: OpenAI, OpenRouter, and self-hosted Ollama
- Safe image handling: private Immich URLs are not sent to external providers
- Simple deployment: one Docker image, one container, optional Redis only if you want it
- Multi-user support: first-run setup, admin-managed users, per-user settings

## Table of contents

- [What immich-gpt does](#what-immich-gpt-does)
- [Documentation map](#documentation-map)
- [Quick start](#quick-start)
- [Typical workflow](#typical-workflow)
- [Features](#features)
- [Deployment options](#deployment-options)
- [Configuration overview](#configuration-overview)
- [API and health endpoints](#api-and-health-endpoints)
- [Architecture](#architecture)
- [Development](#development)
- [Roadmap](#roadmap)
- [License](#license)

## What immich-gpt does

immich-gpt helps you enrich and organize large photo libraries without giving up control.

### Better metadata

For each synced asset, immich-gpt can suggest:

- a bucket or category
- a natural-language description
- search-friendly tags
- an album or sub-album name when your bucket rules allow it

### Smarter organization

Buckets let you control what approval means for each kind of asset:

- **Virtual**: keep the classification inside immich-gpt only
- **Immich Album**: map approved assets into a specific Immich album
- **Parent Group**: let AI suggest sub-albums under a broader bucket
- **Immich Trash**: build a review-first cleanup workflow

### Review before write-back

The review queue lets you:

- approve as-is
- edit the bucket, description, tags, or album suggestion
- reject the suggestion
- re-run AI analysis when you want another pass

## Documentation map

Start here, then jump to the guide that matches your job.

| Guide | What it covers |
|------|-----------------|
| [`docs/getting-started.md`](docs/getting-started.md) | First install, first login, and a safe first workflow |
| [`DOCKER.md`](DOCKER.md) | Docker Compose, `docker run`, Unraid, Redis workers, upgrades |
| [`docs/reverse-proxy.md`](docs/reverse-proxy.md) | Nginx, Caddy, Traefik, HTTPS, and SSE buffering |
| [`docs/configuration.md`](docs/configuration.md) | Environment variables, provider settings, cookies, workers, CORS |
| [`docs/architecture.md`](docs/architecture.md) | System design, data flow, jobs, storage, and write-back |
| [`docs/troubleshooting.md`](docs/troubleshooting.md) | Startup, login, Immich connectivity, SSE, providers, password reset |
| [`docs/development.md`](docs/development.md) | Local development, tests, frontend build, and Alembic |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | How to contribute changes to the project |

## Quick start

The fastest path is Docker Compose.

1. Copy the sample environment file:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and set at minimum:

   - `IMMICH_URL`
   - `IMMICH_API_KEY`
   - `DATA_DIR`

   `SECRET_KEY` can be left blank in Docker deployments. The container will generate one on first boot and persist it under `/data/.secret_key`.

3. Start the app:

   ```bash
   docker compose up -d
   ```

4. Open `http://localhost:8000`.

5. Complete the first-run setup wizard to create the initial admin account.

6. Open **Settings** and configure:

   - your Immich connection
   - your preferred AI provider
   - whether new tags and new album names may be created

7. Go to **Dashboard** and run **Sync + AI**.

8. Open **Review** and approve, edit, or reject each suggestion.

If you are serving the app behind HTTPS, set `SESSION_COOKIE_SECURE=true`. If you are running on a plain HTTP LAN, leave it `false`.

For full install details, read [`docs/getting-started.md`](docs/getting-started.md) and [`DOCKER.md`](DOCKER.md).

## Typical workflow

### 1. Connect Immich and your provider

In **Settings**, save your Immich URL and API key, then add an AI provider:

- **OpenAI**
- **OpenRouter**
- **Ollama**

Immich settings saved in the UI are stored in the database and override `IMMICH_URL` and `IMMICH_API_KEY` environment values for that user.

### 2. Create a few buckets

A simple starter set is:

- **Family** -> Parent Group
- **Travel** -> Parent Group
- **Receipts** -> Virtual
- **Favourites Archive** -> Immich Album
- **Trash** -> Immich Trash

Each bucket can define its own prompt guidance, priority, and confidence threshold.

### 3. Pick a sync scope

From **Dashboard**, choose:

- **All Photos & Videos**
- **Favourites Only**
- **Specific Albums**

Then choose a workflow:

- **Sync Only**
- **Sync + AI**
- **AI Only**

For a first run, **Sync + AI** is usually the easiest option.

### 4. Review and approve

In **Review**, you can:

- change the bucket
- rewrite the description
- add or remove tags
- accept or replace the album suggestion
- approve or reject the result

### 5. Roll out gradually

A safe rollout looks like this:

1. start with a few clear buckets
2. run on favourites or specific albums first
3. review the early results closely
4. refine prompts and bucket rules
5. expand to more of the library

## Features

### AI-first pipeline

- one AI call per asset with image plus metadata context
- structured JSON responses with schema validation
- bad provider responses are surfaced as errors instead of silently ignored

### Image handling

- thumbnails are fetched server-side from Immich
- images are converted to base64 data URLs before being sent to providers
- private Immich URLs are never passed directly to external AI services

### Prompt system

- global prompts for classification, descriptions, and tags
- per-bucket prompts for tighter control
- prompts are stored in the database and editable in the UI

### Review workflow

- thumbnails for each item
- edit-before-approve controls
- bulk approve and reject actions
- large preview on thumbnail click

### Jobs and progress

- live progress tracking
- job logs in the UI
- job states such as `queued`, `syncing_assets`, `preparing_image`, `classifying_ai`, `writing_results`, and `completed`
- pause, resume, and cancel support

### Write-back safeguards

- explicit approval before write-back
- audit logging for important actions
- failures are visible instead of swallowed
- external library limitations are detected and warned

## Deployment options

| Option | Best for |
|--------|----------|
| Docker Compose | Most users and home labs |
| Unraid Community Apps | Unraid users who want a template-driven install |
| `docker run` | Small manual deployments |
| Redis + RQ worker | Advanced setups that already run Redis |
| Local development | Contributors working on backend or frontend changes |

immich-gpt runs as a single container by default. Background jobs use an in-process `ThreadPoolExecutor`, so Redis is optional rather than required.

## Configuration overview

The project supports both environment-based defaults and per-user settings in the UI.

### Most important settings

| Setting | Purpose |
|--------|---------|
| `IMMICH_URL` | Base URL of your Immich instance |
| `IMMICH_API_KEY` | Immich API key |
| `SECRET_KEY` | Session-signing secret; auto-generated in Docker if blank |
| `SESSION_COOKIE_SECURE` | Must be `true` behind HTTPS, `false` for plain HTTP |
| `OPENAI_API_KEY` | Optional default OpenAI key |
| `OPENAI_MODEL` | Default OpenAI model |
| `REDIS_URL` | Optional Redis for RQ worker mode |
| `WORKER_CONCURRENCY` | Thread count for built-in background jobs |
| `LOG_LEVEL` | Logging verbosity |

UI settings take precedence for:

- Immich connection details
- provider definitions
- behaviour toggles such as allowing new tags and new albums

The full configuration reference lives in [`docs/configuration.md`](docs/configuration.md).

## API and health endpoints

Useful built-in endpoints:

| Endpoint | Purpose |
|---------|---------|
| `/health` | Basic health check |
| `/api/health` | Health check under the API namespace |
| `/docs` | Interactive OpenAPI docs |
| `/redoc` | Alternative API reference UI |

Core API areas include:

- `/api/auth`
- `/api/settings`
- `/api/buckets`
- `/api/prompts`
- `/api/assets`
- `/api/jobs`
- `/api/review`
- `/api/albums`
- `/api/thumbnails`

## Architecture

```text
┌─────────────┐    ┌──────────────────────┐    ┌────────────┐
│   Browser   │───▶│   FastAPI (Python)   │───▶│   Immich   │
│  React SPA  │    │                      │    │   Server   │
└─────────────┘    │  auth + settings     │    └────────────┘
                   │  sync + job control  │
                   │  prompt assembly     │
                   │  review + write-back │───▶ AI provider
                   └──────────────────────┘     (OpenAI /
                          │                     OpenRouter /
                          ▼                     Ollama)
                     SQLite DB
                (persistent volume)
```

FastAPI serves the API and, in production, the built React frontend from `backend/static`. SQLite stores users, settings, prompts, synced assets, suggestions, jobs, and audit logs. Optional Redis can be added when you want RQ workers.

For a deeper architecture walkthrough, see [`docs/architecture.md`](docs/architecture.md).

## Development

### Backend

```bash
cd backend
python3 -m pytest tests/ -v
```

### Frontend

```bash
cd frontend
npm test
npm run lint
npx tsc --noEmit
```

### Frontend production build

```bash
cd frontend
npx vite build
```

That build writes static assets into `backend/static` so FastAPI can serve the SPA in production.

See [`docs/development.md`](docs/development.md) for local run commands, migrations, and contributor workflow details.

## Roadmap

- [ ] Asset detail view
- [ ] Video thumbnail support
- [ ] Duplicate and junk heuristic pre-filter
- [ ] Immich face and people metadata
- [ ] SMTP or email delivery for password resets

## License

This project is licensed under the GNU Affero General Public License v3.0. See [`LICENSE`](LICENSE) for the full text.

If you modify immich-gpt and let users interact with that modified version over a network, AGPL-3.0 requires you to make the corresponding source code of that version available to those users.
