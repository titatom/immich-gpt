# Getting started

This guide walks through a first install of immich-gpt and a safe first workflow.

## What you need

Before you begin, make sure you have:

- a running Immich server
- an Immich API key
- Docker and Docker Compose, or an Unraid setup that can run the published image
- at least one AI provider you want to use:
  - OpenAI
  - OpenRouter
  - Ollama

If you want the simplest path, use Docker Compose.

## Recommended installation path

1. Copy the sample environment file:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env`.

   Set these values first:

   - `DATA_DIR`
   - `IMMICH_URL`
   - `IMMICH_API_KEY`

   Optional but useful:

   - `OPENAI_API_KEY`
   - `OPENAI_MODEL`
   - `LOG_LEVEL`

3. Start the app:

   ```bash
   docker compose up -d
   ```

4. Open `http://localhost:8000`.

5. Complete the setup wizard to create the first admin account.

For alternate install paths, see [`../DOCKER.md`](../DOCKER.md).

## Important deployment notes

### `SECRET_KEY`

In Docker deployments, `SECRET_KEY` may be left blank. On first boot, the container generates a strong key and stores it in `/data/.secret_key` so it survives restarts.

If you prefer to set your own, generate one with:

```bash
openssl rand -hex 32
```

### `SESSION_COOKIE_SECURE`

- Use `SESSION_COOKIE_SECURE=false` for plain HTTP on a local network
- Use `SESSION_COOKIE_SECURE=true` whenever the browser reaches the app over HTTPS

If this value does not match your deployment, login will fail because the browser will reject the session cookie.

### Redis is optional

immich-gpt does not require Redis for normal use. Background jobs run in-process by default. Only set `REDIS_URL` if you already run Redis and want to use RQ workers.

## First login and initial setup

On the first visit, immich-gpt shows a setup screen when no users exist yet. The account you create there becomes the first admin.

After login, the main navigation includes:

- Dashboard
- Review
- Assets
- Buckets
- Prompts
- Jobs
- Logs
- Settings
- Users (admins only)

## First-run checklist

Open **Settings** and configure the app in this order.

### 1. Immich connection

Save:

- your Immich URL
- your Immich API key

Use the built-in **Save & Test** action to confirm the app can reach Immich and count assets.

### 2. AI provider

Add one provider first:

- **OpenAI** for hosted models
- **OpenRouter** for a broad hosted model catalog
- **Ollama** for a self-hosted local model

Set one provider as the default. You can add more later.

### 3. Behavior toggles

Decide whether the AI is allowed to:

- create new tags
- create new album names under the buckets that support album suggestions

If you want maximum control for a first rollout, disable both until you trust the prompts and outputs.

## Create buckets

Buckets define how the AI should group assets and what approval means.

Common starter buckets:

| Bucket | Mapping mode | Why it is useful |
|--------|--------------|------------------|
| Family | Parent Group | Lets AI suggest sub-albums such as trips or events |
| Travel | Parent Group | Good for destinations and trip-based sub-albums |
| Receipts | Virtual | Keeps document-like photos grouped without touching Immich albums |
| Favourites Archive | Immich Album | Routes approved items into one existing album |
| Trash | Immich Trash | Creates a review-first cleanup lane |

Useful bucket settings:

- priority
- confidence threshold
- bucket-specific prompt hints
- examples and negative examples

## Run your first workflow

Go to **Dashboard** and choose:

- scope:
  - **All Photos & Videos**
  - **Favourites Only**
  - **Specific Albums**
- workflow:
  - **Sync Only**
  - **Sync + AI**
  - **AI Only**

Recommended first run:

1. choose **Favourites Only** or **Specific Albums**
2. choose **Sync + AI**
3. wait for the job to complete
4. review the results carefully

## Review and approve

The **Review** page is where immich-gpt becomes safe to use at scale.

For each item, you can:

- change the bucket
- edit the description
- add or remove tags
- accept or replace the album suggestion
- approve
- reject

Nothing is written back until you approve.

## A safe rollout plan

Use a gradual rollout instead of processing the whole library on day one.

1. Start with a small, high-signal subset of assets
2. Keep the bucket set small and obvious
3. Review every result from the first few jobs
4. Tune prompts and thresholds
5. Expand the scope once the outputs are consistent

## Where to go next

- Need deployment details: [`../DOCKER.md`](../DOCKER.md)
- Need HTTPS or reverse proxy setup: [`reverse-proxy.md`](reverse-proxy.md)
- Need all config options: [`configuration.md`](configuration.md)
- Need help with a problem: [`troubleshooting.md`](troubleshooting.md)
