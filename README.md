# immich-gpt

<p align="center">
  <img src="frontend/public/logo.png" alt="immich-gpt logo" width="320" />
</p>

**AI metadata enrichment and album organization for Immich.**

immich-gpt is a self-hosted app that connects to your Immich library, uses AI to suggest descriptions, tags, and album placement, and lets you review every result before anything is written back.

## Why use it

- Make large photo libraries easier to search
- Add useful descriptions and tags with AI assistance
- Organize assets into albums or sub-albums with bucket rules
- Keep a human review step before write-back
- Use OpenAI, OpenRouter, or local Ollama models

## What it helps with

### Better metadata

immich-gpt analyzes each synced asset and suggests:

- a bucket/category
- a description
- search-friendly tags
- an album or sub-album name when relevant

### Smarter album organization

Buckets let you control what approval means for each kind of asset:

- **Virtual** keeps the result inside immich-gpt only
- **Immich Album** sends approved assets to a specific existing album
- **Parent Group** lets AI suggest sub-albums under a broader bucket
- **Immich Trash** supports review-first clean-up workflows

### Review before write-back

Nothing is written back automatically. In the review queue you can:

- approve as-is
- edit the bucket, description, tags, or album
- reject the suggestion
- re-run AI analysis on an asset

## How to use it

### 1. Connect Immich and your AI provider

Go through the setup flow, then open **Settings** and configure:

- your Immich URL and API key
- an AI provider such as OpenAI, OpenRouter, or Ollama
- whether AI may create new tags or new album names

### 2. Create a few buckets

Buckets are the categories the AI uses to organize your library. A simple starting point is:

- **Family** -> Parent Group
- **Travel** -> Parent Group
- **Receipts** -> Virtual
- **Favourites Archive** -> Immich Album
- **Trash** -> Immich Trash

Each bucket can have its own prompt, priority, and confidence threshold.

### 3. Sync and run AI

From the dashboard, choose a scope:

- **All Photos & Videos**
- **Favourites Only**
- **Specific Albums**

Then choose a workflow:

- **Sync Only**
- **Sync + AI**
- **AI Only**

For a first run, **Sync + AI** is usually the easiest option.

### 4. Review and approve

Open **Review** to check the suggestions. For each asset you can:

- change the bucket
- rewrite the description
- add or remove tags
- accept or change the album/sub-album
- approve or reject the result

### 5. Roll it out gradually

A good first rollout is:

1. start with a few clear buckets
2. run on favourites or specific albums
3. review results closely
4. adjust prompts and priorities
5. expand to more of your library

## Architecture

```
┌─────────────┐    ┌──────────────────────┐    ┌────────────┐
│   Browser   │───▶│   FastAPI (Python)   │───▶│   Immich   │
│  React SPA  │    │                      │    │   Server   │
└─────────────┘    │  ImmichClient        │    └────────────┘
                   │  ImagePrepService    │
                   │  OpenAIProvider      │───▶ OpenAI API
                   │  OllamaProvider      │     (base64 data URL,
                   │  OpenRouterProvider  │      never raw URL)
                   │  PromptAssembly      │
                   │  ClassificationOrch  │
                   │  ReviewDecisionSvc   │
                   │  JobProgressService  │
                   └──────────────────────┘
                          │
                   ┌──────┘
                   ▼
              SQLite DB
           (persistent vol)
```

Background jobs run in-process via a `ThreadPoolExecutor` by default — no
extra services needed.  If you already run Redis on your home lab, set
`REDIS_URL` and jobs will be dispatched through RQ instead.

## Quick Start

1. Copy the example env file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your Immich URL, API key, and (optionally) an OpenAI key.

3. Run with Docker Compose:
   ```bash
   docker compose up -d
   ```

   If your Docker install is too old for `docker compose build` (for example older Unraid packages), use the published image with `docker compose up -d`, or build locally with `./build.sh` and then start Compose.

4. Open http://localhost:8000 in your browser.

5. Complete the **setup wizard** to create the first admin account.

6. Go to **Dashboard** → **Sync Assets** to pull your Immich library.

7. Click **Run AI Classification** to start processing.

8. Go to **Review** to approve or edit each suggestion.

## Default Buckets

| Bucket | Purpose |
|--------|---------|
| Documents | Receipts, invoices, forms, scans, photos of paper |
| Business | Work sites, tools, project documentation |
| Personal | Family, travel, events, everyday life |
| Trash | Blurry, accidental, no-value shots |

Documents always beats Business when the asset is clearly a receipt, invoice, contract, or photo of paper.

Trash is **non-destructive** — nothing is ever deleted automatically.

## Features

### AI-First Pipeline
- One AI call per asset (image + metadata combined)
- Structured JSON output with strict schema validation
- Malformed responses surfaced as errors, never silently dropped

### Image Handling
- Thumbnails fetched server-side from Immich
- Converted to base64 data URLs before sending to AI provider
- Private Immich URLs **never** passed to external providers

### AI Providers
- **OpenAI** — GPT-4o (default), GPT-4o-mini, or any vision model
- **Ollama** — local models (llava, llava-phi3, moondream, etc.)
- **OpenRouter** — any model available on openrouter.ai
- All configured per-user in the UI; API keys never leave your server

### Prompt System
- Global classification, description, and tags prompts
- Per-bucket classification prompts
- All prompts stored in DB, editable in UI, versioned

### Review Workflow
- Thumbnail shown for every item
- Approve/edit description, tags, bucket
- Override bucket with dropdown
- Bulk approve/reject
- Clicking thumbnail opens large preview

### Jobs & Progress
- Real-time progress bar (processed/total, %, step)
- Live log panel per job
- Job states: queued → syncing → preparing_image → classifying_ai → completed
- Pause, resume, and cancel support

### Write-back
- Explicit: only after user approval
- Logged to AuditLog table
- Failures surfaced clearly (not silently swallowed)
- External library write limitations detected and warned

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12 + FastAPI |
| Database | SQLite (persistent volume) |
| Background jobs | ThreadPoolExecutor (built-in); optional Redis + RQ |
| Frontend | React 18 + TypeScript + Vite |
| AI | OpenAI, Ollama, OpenRouter |
| Container | Docker + Docker Compose |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `IMMICH_URL` | — | Your Immich server URL (can also be set in the UI) |
| `IMMICH_API_KEY` | — | Immich API key (can also be set in the UI) |
| `OPENAI_API_KEY` | — | OpenAI API key (optional — configure provider in the UI) |
| `OPENAI_MODEL` | `gpt-4o` | OpenAI model to use |
| `APP_PORT` | `8000` | Host port to expose |
| `REDIS_URL` | *(empty)* | Optional Redis URL — leave blank for built-in thread pool |
| `WORKER_CONCURRENCY` | `2` | Thread-pool workers (ignored when REDIS_URL is set) |
| `DATABASE_URL` | `sqlite:////data/immich_gpt.db` | SQLite database path |
| `LOG_LEVEL` | `INFO` | Logging verbosity: DEBUG, INFO, WARNING, ERROR |
| `SESSION_COOKIE_SECURE` | `false` | Set `true` behind HTTPS |

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET/POST | `/api/settings/immich` | Immich connection settings |
| GET/POST | `/api/settings/providers` | AI provider config |
| GET/POST/PATCH/DELETE | `/api/buckets` | Bucket CRUD |
| GET/POST/PATCH/DELETE | `/api/prompts` | Prompt template CRUD |
| GET | `/api/assets` | List synced assets |
| GET | `/api/assets/count` | Asset count |
| POST | `/api/jobs/sync` | Start asset sync job |
| POST | `/api/jobs/classify` | Start classification job |
| GET | `/api/jobs/{id}` | Job status + logs |
| GET | `/api/jobs/{id}/stream` | SSE stream for real-time job updates |
| GET | `/api/review/queue` | Review queue |
| GET | `/api/review/queue/count` | Pending count |
| POST | `/api/review/item/{id}/approve` | Approve with edits |
| POST | `/api/review/item/{id}/reject` | Reject suggestion |
| POST | `/api/review/bulk` | Bulk approve/reject |
| GET | `/api/thumbnails/{asset_id}` | Proxied thumbnail |
| GET | `/api/albums` | Immich albums (for bucket mapping) |

## Running Tests

```bash
cd backend
pip install -r requirements.txt
python3 -m pytest tests/ -v
```

238 backend tests covering auth, admin, settings, assets, buckets, prompts, jobs,
review, thumbnails, audit logs, AI providers, migrations, user isolation, and more.

```bash
cd frontend
npm test
```

48 frontend tests (Vitest + React Testing Library).

## Unraid Deployment

1. Use the published `ghcr.io/titatom/immich-gpt:latest` image in Unraid, or build locally with `./build.sh` if you need a source build on an older Docker stack.
2. Map `/data` to a persistent path on your array (e.g. `/mnt/user/appdata/immich-gpt`).
3. Optionally map `/logs` for persistent log files.
4. Set environment variables in Unraid's Docker template.
5. Ensure the container can reach your Immich instance on the local network.
6. On first visit, complete the web setup wizard to create the admin account.

## Reverse Proxy / HTTPS

See [`docs/reverse-proxy.md`](docs/reverse-proxy.md) for Nginx and Caddy configuration examples, including the SSE stream endpoint and `SESSION_COOKIE_SECURE` guidance.

## License

This project is licensed under the GNU Affero General Public License v3.0.
See [`LICENSE`](LICENSE) for the full text.

If you modify immich-gpt and let users interact with that modified version
over a network, AGPL-3.0 requires you to make the corresponding source code
of that version available to those users.

## Roadmap

- [ ] Asset detail view
- [ ] Video thumbnail support
- [ ] Duplicate/junk heuristic pre-filter
- [ ] Immich face/people metadata
- [ ] SMTP / email delivery for password resets
