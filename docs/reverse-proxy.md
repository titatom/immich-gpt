# Reverse Proxy Configuration

This guide covers running Immich GPT behind a reverse proxy for HTTPS access on a home lab.

When running behind a proxy, always set:

```env
SESSION_COOKIE_SECURE=true
```

This marks the session cookie `Secure` so it is only sent over HTTPS.

---

## Nginx

### Minimal configuration

```nginx
server {
    listen 443 ssl;
    server_name immich-gpt.example.com;

    ssl_certificate     /etc/ssl/certs/immich-gpt.crt;
    ssl_certificate_key /etc/ssl/private/immich-gpt.key;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;

        # Required for SSE (real-time job progress streaming).
        proxy_buffering    off;
        proxy_cache        off;
        proxy_read_timeout 3600s;
    }
}

# Redirect HTTP → HTTPS
server {
    listen 80;
    server_name immich-gpt.example.com;
    return 301 https://$host$request_uri;
}
```

### Nginx Proxy Manager

If you use Nginx Proxy Manager (common on Unraid), add the following in the
**Advanced** tab of your proxy host:

```nginx
proxy_buffering    off;
proxy_cache        off;
proxy_read_timeout 3600s;
```

This is required for the live job-progress SSE stream (`/api/jobs/{id}/stream`)
to work correctly.

---

## Caddy

Caddy handles HTTPS certificate provisioning automatically.

```caddy
immich-gpt.example.com {
    reverse_proxy 127.0.0.1:8000 {
        # Required for SSE (real-time job progress streaming).
        flush_interval -1
    }
}
```

For a local/LAN domain without public DNS (e.g. via a self-signed cert or
internal CA), use the `tls internal` directive:

```caddy
immich-gpt.home.arpa {
    tls internal
    reverse_proxy 127.0.0.1:8000 {
        flush_interval -1
    }
}
```

---

## Traefik (Docker labels)

Add these labels to the `app` service in `docker-compose.yml`:

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.immich-gpt.rule=Host(`immich-gpt.example.com`)"
  - "traefik.http.routers.immich-gpt.entrypoints=websecure"
  - "traefik.http.routers.immich-gpt.tls.certresolver=letsencrypt"
  - "traefik.http.services.immich-gpt.loadbalancer.server.port=8000"
  # Disable response buffering so SSE streams flush immediately.
  - "traefik.http.middlewares.immich-gpt-sse.headers.customresponseheaders.X-Accel-Buffering=no"
  - "traefik.http.routers.immich-gpt.middlewares=immich-gpt-sse"
```

---

## Notes

### SSE stream endpoint

The job-progress stream (`GET /api/jobs/{id}/stream`) uses
[Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events).
It requires the proxy to **not buffer** the response.  The Uvicorn server sets
`X-Accel-Buffering: no` on the response to hint Nginx, but you must also set
`proxy_buffering off` explicitly in Nginx.

### Client IP logging

The container runs Uvicorn with `--proxy-headers` so real client IPs are
correctly recorded in audit logs and used for rate-limiting — as long as the
proxy forwards `X-Forwarded-For` or `X-Real-IP`.  All examples above do this.

### SESSION_COOKIE_SECURE

This must be `true` whenever the browser reaches the app over HTTPS.  It
defaults to `false` in the shipped Compose file to support plain LAN deployments.
Override in `.env`:

```env
SESSION_COOKIE_SECURE=true
```
