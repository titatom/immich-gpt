# immich-gpt

> AI-first metadata enrichment and organization for Immich — "Paperless-GPT for Immich"

A self-hosted web app that connects to your Immich instance, processes your photos one-by-one with AI, and suggests metadata enrichments for human review before writing anything back.

## What it does

- **Connects** to your Immich instance and syncs asset metadata
- **Fetches thumbnails** server-side (never exposes your Immich credentials to AI providers)
- **Classifies** each asset into a user-defined Bucket using OpenAI vision
- **Generates** description and tag suggestions per asset
- **Stages** all suggestions in a review queue — nothing is written automatically
- **After approval**, writes descriptions and tags back to Immich

## Architecture

```
┌─────────────┐    ┌──────────────────────┐    ┌────────────┐
│   Browser   │───▶│   FastAPI (Python)   │───▶│   Immich   │
│  React SPA  │    │                      │    │   Server   │
└─────────────┘    │  ImmichClient        │    └────────────┘
                   │  ImagePrepService    │
                   │  OpenAIProvider      │───▶ OpenAI API
                   │  PromptAssembly      │     (base64 data URL,
                   │  ClassificationOrch  │      never raw URL)
                   │  ReviewDecisionSvc   │
                   │  JobProgressService  │
                   └──────────────────────┘
                          │        │
                   ┌──────┘        └──────┐
                   ▼                      ▼
              SQLite DB             Redis + RQ
           (persistent vol)       (background jobs)
```

## Quick Start

1. Copy the example env file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your Immich URL, API key, and OpenAI key.

3. Run with Docker Compose:
   ```bash
   docker compose up -d
   ```

   If your Docker install is too old for `docker compose build` (for example older Unraid packages), use the published image with `docker compose up -d`, or build locally with `./build.sh` and then start Compose.

4. Open http://localhost:8000 in your browser.

5. Go to **Dashboard** → **Sync Assets** to pull your Immich library.

6. Click **Run AI Classification** to start processing.

7. Go to **Review** to approve or edit each suggestion.

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
- Converted to base64 data URLs before sending to OpenAI
- Private Immich URLs **never** passed to external providers

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
- Cancel support

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
| Background jobs | Redis + RQ |
| Frontend | React 18 + TypeScript + Vite |
| AI | OpenAI (gpt-4o default), Ollama/OpenRouter stubs |
| Container | Docker + Docker Compose |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `IMMICH_URL` | — | Your Immich server URL |
| `IMMICH_API_KEY` | — | Immich API key |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o` | OpenAI model to use |
| `APP_PORT` | `8000` | Host port to expose |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection string |
| `DATABASE_URL` | `sqlite:////data/immich_gpt.db` | SQLite database path |

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

61 tests covering:
- Prompt assembly (global + bucket + field prompts)
- ImmichClient (auth headers, thumbnail fetch, external library detection)
- ImagePreparationService (data URL, no raw URL regression, oversized handling)
- OpenAIProvider (schema validation, malformed JSON, image injection)
- ClassificationOrchestrator (end-to-end, error handling, image failures)
- JobProgressService (all state transitions)
- ReviewDecisionService (write-back flows, failure reporting, external library warning)
- Review API (queue rendering, thumbnails, pagination)
- Bucket API (CRUD)

## Unraid Deployment

1. Use the published `ghcr.io/titatom/immich-gpt:latest` image in Unraid, or build locally with `./build.sh` if you need a source build on an older Docker stack.
2. Map `/data` and `/logs` volumes to persistent paths on your array.
3. Set environment variables in Unraid's Docker template.
4. Ensure the container can reach your Immich instance on the local network.

## Roadmap

- [ ] Ollama provider (local models)
- [ ] OpenRouter provider
- [ ] SSE for real-time job updates
- [ ] Asset detail view
- [ ] Video thumbnail support
- [ ] Duplicate/junk heuristic pre-filter
- [ ] Immich face/people metadata
