# Architecture

This guide explains how immich-gpt is put together and how data moves through the system.

## High-level design

immich-gpt is a web application with:

- a Python FastAPI backend
- a React and TypeScript frontend
- a SQLite database
- an optional Redis plus RQ worker path for background jobs

In production, the frontend is built into static assets and served by FastAPI from the same container.

## System diagram

```text
┌─────────────┐    ┌──────────────────────┐    ┌────────────┐
│   Browser   │───▶│   FastAPI backend    │───▶│   Immich   │
│  React SPA  │    │                      │    │   Server   │
└─────────────┘    │  auth                │    └────────────┘
                   │  settings            │
                   │  routing tree        │
                   │  sync jobs           │
                   │  AI classification   │───▶ AI provider
                   │  plans + write-back  │     (OpenAI /
                   │  audit logs          │      OpenRouter /
                   └──────────────────────┘      Ollama)
                          │
                          ▼
                     SQLite database
```

## Main components

### Frontend

The frontend provides:

- first-run setup and login
- dashboard workflows
- assets, routing plans, and jobs
- routing tree and prompt management
- logs and settings
- admin user management

The main navigation includes:

- Dashboard
- Assets
- Routing
- Routing plans
- Jobs
- Logs
- Settings
- Users for admins

### Backend

The FastAPI backend handles:

- authentication and sessions
- first-user bootstrap
- user and admin APIs
- Immich connectivity and album access
- routing tree, prompt, and provider configuration
- sync and classification jobs
- routing plan decisions and write-back
- audit logging

### Database

SQLite stores:

- users and sessions
- password reset tokens
- application settings
- provider definitions
- routing nodes, examples, and plans
- synced assets and AI routing output
- job runs and job logs
- audit trail records

## Deployment model

### Default mode

The normal deployment is a single container:

- FastAPI serves the API
- FastAPI serves the built frontend
- SQLite lives under `/data`
- background jobs run in-process via a `ThreadPoolExecutor`

This keeps the operational model simple for home labs and small servers.

### Optional Redis mode

If `REDIS_URL` is set:

- new jobs are dispatched through RQ
- the FastAPI process automatically starts an in-process RQ worker
  thread on lifespan startup (one thread per `WORKER_CONCURRENCY`
  slot) so the same single container that enqueues jobs also drains
  the queue
- you can additionally run one or more separate worker containers
  (`python -m app.workers.rq_worker`) for horizontal scaling

This is useful only if you already operate Redis and want a more
distributed worker model.

## Request and data flow

## 1. First-run setup

When no users exist:

1. the frontend checks setup status
2. the setup page is shown
3. the first admin is created
4. the user is logged in immediately with a session cookie

After the first account exists, setup is locked and new users must be created through admin flows.

## 2. Sync flow

When a user starts a sync job:

1. the backend reads that user's effective Immich credentials
2. Immich assets are fetched for the requested scope
3. asset metadata is normalized and stored in SQLite
4. the job status and logs are updated as work progresses

Supported sync scopes:

- all assets
- favorites only
- selected albums

## 3. Classification flow

When a user starts AI classification:

1. the routing service loads enabled routing-tree leaves and their prompt guidance
2. behavior settings are resolved, such as whether new tags or albums are allowed
3. the backend prepares a thumbnail and metadata context for each asset
4. the selected provider is called
5. the structured response is validated against routing schemas
6. routing plan items are stored in the database
7. progress updates are streamed to the UI

Important safety property:

- providers receive prepared image data and metadata, not raw private Immich URLs

## 4. Routing plan and write-back flow

immich-gpt is intentionally review-first.

1. AI output enters a routing plan
2. the plan groups items into auto-applied, ready-to-approve, needs-review, trash-candidate, rejected, and failed states
3. the user approves or rejects plan items
4. Immich receives approved metadata or album changes
5. audit logs capture important actions and errors

Nothing is written back until a plan item is approved and the approved items are applied.

## Routing tree and destination modes

The routing tree is central to how immich-gpt thinks about organization. Parent nodes provide structure; leaf nodes define selectable destinations and write-back behavior.

Supported modes:

| Mode | Meaning |
|------|---------|
| `virtual` | Keep the classification inside immich-gpt only |
| `immich_album` | Map approved assets into a specific Immich album |
| `review_only` | Require review without writing to Immich |
| `immich_trash` | Send approved assets into Immich trash as part of a review-first cleanup flow |

Each routing leaf can also influence:

- priority
- confidence and review thresholds
- prompt instructions and preview text
- positive and negative examples
- metadata suggestions and write-back options
- auto-apply rules

## Prompting model

Prompt assembly combines:

- routing-tree structure
- per-leaf prompt guidance
- positive and negative examples
- effective behavior settings
- known tags and album constraints when the user disallows new ones

This keeps routing prompts flexible without requiring source-code changes for normal tuning.

## Job lifecycle

The UI exposes live job progress and logs. Status values can include:

- `queued`
- `starting`
- `syncing_assets`
- `preparing_image`
- `classifying_ai`
- `validating_result`
- `saving_suggestion`
- `writing_results`
- `completed`
- `failed`
- `cancelled`
- `paused`

The job stream endpoint uses Server-Sent Events, so reverse proxies must not buffer that response.

## Frontend serving

During development:

- Vite runs on port `3000`
- the backend usually runs on port `8000`
- the frontend proxies `/api` requests to the backend

In production:

- `npx vite build` writes static assets into `backend/static`
- FastAPI serves those assets and falls back to `index.html` for SPA routes

## Security and operational notes

- session cookies default to `SameSite=strict`
- `SESSION_COOKIE_SECURE` must match whether the browser uses HTTP or HTTPS
- `SECRET_KEY` must be strong and persistent
- expired sessions and reset tokens are cleaned up on startup
- rate limiting is enabled by default

## Related guides

- End-user setup: [`getting-started.md`](getting-started.md)
- Runtime settings: [`configuration.md`](configuration.md)
- Deployment details: [`../DOCKER.md`](../DOCKER.md)
- Troubleshooting: [`troubleshooting.md`](troubleshooting.md)
