# Troubleshooting

This guide covers the most common issues when deploying or running `immich-gpt`.

## The app does not start

### `SECRET_KEY` validation error

`SECRET_KEY` is required by the backend and must be a strong random value at least 32 characters long.

In Docker deployments, leaving `SECRET_KEY` blank is fine because the container entrypoint generates one automatically on first boot and stores it in `/data/.secret_key`.

For native runs, generate one manually:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Then place it in `backend/.env` or your shell environment.

## Login works locally but fails behind HTTPS

Set:

```env
SESSION_COOKIE_SECURE=true
```

When the browser reaches the app over HTTPS, the session cookie must be marked `Secure`.

Also make sure your reverse proxy forwards:

- `Host`
- `X-Real-IP`
- `X-Forwarded-For`
- `X-Forwarded-Proto`

See [`reverse-proxy.md`](reverse-proxy.md) for working examples.

## Login fails on plain HTTP

If you are testing over plain HTTP and `SESSION_COOKIE_SECURE=true`, most browsers will silently reject the session cookie.

For LAN-only HTTP testing, use:

```env
SESSION_COOKIE_SECURE=false
```

## Immich connection test fails

Check the following:

1. `IMMICH_URL` includes the correct scheme and port.
2. The API key was created in Immich and is still valid.
3. The `immich-gpt` container can reach the Immich server on the network.
4. If you saved values in the UI, remember that UI settings override environment variables for that user.

Useful checks:

- open **Settings** -> **Immich Connection**
- click **Save & Test**
- review the returned error message

## Jobs do not start or look stuck

### Single-container mode

This is the default mode. Jobs run in-process using a Python thread pool. No Redis is required.

Check:

- `WORKER_CONCURRENCY` is not set to `0`
- the app logs show job creation and progress
- the Immich connection and AI provider both test successfully

### Redis / RQ mode

If `REDIS_URL` is set:

- confirm Redis is reachable from the app container
- confirm the optional worker container is running if you use one
- confirm the same `DATABASE_URL` and `REDIS_URL` are shared by the app and worker

If Redis enqueue fails, the app attempts to fall back to in-process execution.

## Real-time progress does not update behind a reverse proxy

The Jobs page uses Server-Sent Events for live progress streaming. Reverse proxies must not buffer the response.

For Nginx or Nginx Proxy Manager, disable buffering:

```nginx
proxy_buffering    off;
proxy_cache        off;
proxy_read_timeout 3600s;
```

For Caddy, use:

```caddy
flush_interval -1
```

See [`reverse-proxy.md`](reverse-proxy.md) for full examples.

## OpenRouter or Ollama model list does not load

### OpenRouter

Check:

- the API key is valid
- outbound internet access is available from the app
- the provider entry is saved before fetching models

### Ollama

Check:

- `base_url` points to a reachable Ollama host such as `http://localhost:11434`
- the Ollama server is already running
- the desired model is actually installed in Ollama

If model browsing still fails, you can type a model name manually in the provider configuration.

## AI classification produces poor results

Start small and tune incrementally:

1. define a few clear buckets first
2. keep bucket descriptions specific
3. adjust per-bucket prompts and examples
4. test on favourites or one album instead of the full library
5. review suggestions before broad rollout

Also check the behaviour settings:

- `allow_new_tags`
- `allow_new_albums`

Disabling them constrains the model to existing entities and can improve consistency.

## Approved items do not write all metadata back

Some assets may come from external libraries or have Immich-side restrictions. In those cases, description or tag writes can be limited.

Review the app logs and audit logs to see whether the write-back partially succeeded or was skipped with a warning.

## Password reset expectations do not match the UI

Password reset is not email-driven yet.

Current flow:

1. an admin opens the password reset flow
2. the backend generates a reset token
3. the admin shares that token securely with the user
4. the user resets the password using the token

There is no SMTP-based mail delivery yet.

## Frontend dev server cannot reach the backend

When developing locally:

- run the backend on port `8000`
- run Vite on port `3000`
- start the backend from the `backend/` directory so `.env` is loaded correctly

If you use a different backend origin, set `CORS_ORIGINS` accordingly.

## Migrations or database path problems

The Docker deployment uses:

```env
DATABASE_URL=sqlite:////data/immich_gpt.db
```

Native development often uses:

```env
DATABASE_URL=sqlite:///./data/immich_gpt.db
```

The difference is expected:

- `/data/...` is for containers with a mounted volume
- `./data/...` is for native runs relative to `backend/`

If the app starts with the wrong working directory, it may create a database in an unexpected place.

## Still stuck?

Collect these details before opening an issue:

- deployment method (`docker compose`, `docker run`, native dev, Unraid)
- exact `immich-gpt` version
- relevant log lines
- whether Redis is enabled
- whether HTTPS / reverse proxy is involved
- what you already tested
