# Security Audit — immich-gpt

**Date:** 2026-04-05  
**Scope:** Full codebase — Python/FastAPI backend, React/TypeScript frontend, Docker/Compose infrastructure, CI/CD pipeline  
**Status:** Findings only — no code has been changed.

---

## Executive Summary

The application has a reasonable starting security posture for a self-hosted tool, but several issues ranging from **Critical** to **Low** severity need to be addressed before exposure to any untrusted network. The most serious problems are: authentication is **off by default** and the default secret key is a known public string, which together mean any user who deploys without reading the docs gets a completely open admin API; a CORS policy that combines wildcard origin with `allow_credentials=True` (which browsers refuse to honour — and the intent appears to be to accept all origins anyway); unvalidated/unescaped user-controlled strings that flow into SSE and error responses; API keys stored in plain text in the database; no rate limiting on any endpoint; and an SSE stream endpoint intentionally bypassed from authentication.

---

## Findings

### CRITICAL

---

#### SEC-001 — Authentication is opt-in and the default `SECRET_KEY` is publicly known

**Files:** `backend/app/config.py:35-36`, `docker-compose.yml:31-32`, `.env.example:16-17`

**Description:**  
`AUTH_ENABLED` defaults to `false`. `SECRET_KEY` defaults to the literal string `"change-me-in-production"`, which is committed to the public repository. Any deployment that does not explicitly override both variables is completely open — every destructive endpoint (start jobs, delete jobs, modify settings, trigger writeback to Immich, change provider API keys) is unauthenticated.

```python
# config.py
SECRET_KEY: str = "change-me-in-production"   # hard-coded, public
AUTH_ENABLED: bool = False                      # auth off by default
```

```yaml
# docker-compose.yml
SECRET_KEY: ${SECRET_KEY:-change-me-in-production}
AUTH_ENABLED: ${AUTH_ENABLED:-false}
```

**Risk:** Any user on the local network (or internet if the port is exposed) can read all synced photo metadata, trigger classification jobs that consume paid AI API quota, write back tags/albums/descriptions to the Immich library, and read/overwrite all application settings including the Immich API key and AI provider keys.

**Proposed solutions:**

1. **Require explicit opt-in for open access.** Remove the default `false` for `AUTH_ENABLED`; instead require a conscious choice. One approach: keep the default off but emit a loud startup warning (and include it in the health endpoint) whenever `AUTH_ENABLED=false` and the server is not bound to `127.0.0.1`. A stronger approach: change the default to `true` and auto-generate a random `SECRET_KEY` at first boot, printing it once to stdout.

2. **Auto-generate `SECRET_KEY` when it is the placeholder.** In `config.py`, detect when `SECRET_KEY == "change-me-in-production"` and replace it with `secrets.token_urlsafe(32)`, persisting it to an auto-created `.env` file so it survives restarts. Alternatively, generate a stable secret from the database file path's inode/UUID at startup, so a read-only filesystem still gets a non-trivial secret.

3. **Add a startup banner** whenever auth is disabled and the binding is `0.0.0.0`.

---

#### SEC-002 — SSE job-stream endpoint intentionally bypasses auth, enabling real-time data exfiltration

**File:** `backend/app/middleware/auth.py:17,29-31`

**Description:**  
The bypass rule is written as:

```python
_BYPASS_PREFIXES = ("/api/health", "/health", "/api/jobs/")
```

`/api/jobs/` is a **prefix bypass** — it bypasses auth for every URL that starts with `/api/jobs/`, which includes `/api/jobs/{id}` (job detail), `/api/jobs/{id}/cancel`, `/api/jobs/{id}/pause`, `/api/jobs/{id}/resume`, and `/api/jobs/{id}/stream`. Only `/api/jobs/{id}/stream` should need to bypass auth (because `EventSource` cannot send headers); the others should remain protected.

The comment explains the intent correctly ("EventSource can't send auth headers"), but the implementation is too broad.

**Risk:** When `AUTH_ENABLED=true`, all per-job control actions (cancel, pause, resume) and the full job detail endpoint are unauthenticated, partially defeating the purpose of enabling auth. An attacker who learns a job ID can cancel/pause running jobs.

**Proposed solution:**

Narrow the bypass to the SSE stream specifically:

```python
# Only bypass the SSE stream endpoint — EventSource cannot send auth headers.
# Pattern: /api/jobs/<uuid>/stream
import re
_SSE_STREAM_RE = re.compile(r"^/api/jobs/[^/]+/stream$")

# In dispatch():
if path in ("/api/health", "/health") or _SSE_STREAM_RE.match(path):
    return await call_next(request)
```

Remove `/api/jobs/` from `_BYPASS_PREFIXES` entirely.

---

### HIGH

---

#### SEC-003 — CORS allows all origins with `allow_credentials=True`

**File:** `backend/app/main.py:32-38`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Description:**  
The W3C CORS spec (and all major browsers) reject the combination `allow_origins=["*"]` with `allow_credentials=True`. The browser will refuse to pass cookies/auth headers on cross-origin requests to this configuration, so the `allow_credentials=True` is silently inert — but the intent to allow all origins is still a security concern.

For a self-hosted single-user tool the wildcard origin is usually acceptable, but it creates two real risks:

1. **CSRF:** If authentication is later added via session cookies rather than bearer tokens, wildcard CORS with credentials would enable cross-site request forgery from any page the user visits.
2. **Data leakage to malicious sites:** Any page the user visits can make unauthenticated requests to the API (when `AUTH_ENABLED=false`) and read the full photo metadata, audit logs, and settings.

**Proposed solution:**

Option A (recommended for self-hosted): Remove `allow_credentials=True` — it is not needed since the frontend uses `Authorization` bearer headers, not cookies. The wildcard origin then becomes safe (no credential leakage).

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,   # bearer token auth; no cookies
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)
```

Option B (more restrictive): Allow only the same origin, with an optional override via an env var `CORS_ORIGINS`:

```python
cors_origins = settings.CORS_ORIGINS or ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

---

#### SEC-004 — AI provider API keys and Immich API key stored in plain text in SQLite

**Files:** `backend/app/models/provider_config.py:14`, `backend/app/models/app_setting.py`, `backend/app/routers/settings.py:61-63`

**Description:**  
The column is named `api_key_encrypted` but is a plain `Text` column with no encryption applied anywhere in the codebase. The Immich API key is stored in the `app_settings` table under the key `"immich_api_key"` as a plain string.

```python
# provider_config.py
api_key_encrypted = Column(Text, nullable=True)   # misleading: no encryption applied
```

Anyone with read access to `/data/immich_gpt.db` (e.g. via Unraid's file manager, a misconfigured volume mount, or a path-traversal bug) can extract all AI provider API keys and the Immich API key.

**Risk:** Credential theft from database backup, volume snapshot, or file-system access.

**Proposed solutions:**

1. **Rename the column** to `api_key` to remove the false assurance of encryption. This is a low-effort, correctness fix.

2. **Application-level encryption using Fernet (symmetric):** Derive a Fernet key from `SECRET_KEY` (already in config). Encrypt on write, decrypt on read in `settings.py` / `tasks.py`. The key never leaves the process environment.

```python
from cryptography.fernet import Fernet
import hashlib, base64

def _fernet(secret_key: str) -> Fernet:
    # Derive a 32-byte URL-safe base64-encoded key from SECRET_KEY
    derived = hashlib.sha256(secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(derived))

def encrypt_secret(value: str, secret_key: str) -> str:
    return _fernet(secret_key).encrypt(value.encode()).decode()

def decrypt_secret(token: str, secret_key: str) -> str:
    return _fernet(secret_key).decrypt(token.encode()).decode()
```

3. **Minimum viable fix without crypto library:** Base64-encode the keys. This does not add real security but removes plaintext readability from casual inspection and removes the false `_encrypted` label.

---

#### SEC-005 — No rate limiting on any endpoint

**File:** `backend/app/main.py` (no rate limiting middleware), all routers

**Description:**  
There is no rate limiting on any API endpoint. Of particular concern:

- `POST /api/jobs/classify` and `POST /api/assets/reclassify` trigger paid AI API calls. A user (or anyone with network access when auth is off) can spam these to exhaust OpenAI/OpenRouter API quota rapidly.
- `GET /api/settings/providers/{name}/test` and `GET /api/settings/providers/{name}/models` make external HTTP calls on every request.
- `POST /api/settings/immich/test` makes an external HTTP call on every request.
- The SSE stream (`GET /api/jobs/{id}/stream`) opens a persistent connection; without limits, a client can open many streams simultaneously, exhausting file descriptors.

**Proposed solution:**

Add `slowapi` (a FastAPI-native rate limiter built on `limits`):

```python
# requirements.txt
slowapi==0.1.9

# main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

Then decorate sensitive routes:

```python
@router.post("/classify")
@limiter.limit("10/minute")
def start_classify_job(...): ...

@router.post("/sync")
@limiter.limit("10/minute")
def start_sync_job(...): ...

@router.post("/reclassify")
@limiter.limit("20/minute")
def reclassify_assets(...): ...
```

For SSE streams, limit to a small number of concurrent connections per IP using a simple in-process counter.

---

#### SEC-006 — Thumbnail proxy does not validate the `size` query parameter

**File:** `backend/app/routers/thumbnails.py:17-45`

```python
@router.get("/{asset_id}")
def get_thumbnail(
    asset_id: str,
    size: str = "thumbnail",
    ...
):
    image_bytes = client.get_thumbnail(asset.immich_id, size=size)
```

**Description:**  
The `size` parameter is passed directly to `ImmichClient.get_thumbnail()`, which appends it to an Immich API query string:

```python
# immich_client.py:152
r = client.get(f"/api/assets/{asset_id}/thumbnail", params={"size": size}, ...)
```

There is no validation that `size` is one of the two allowed values (`"thumbnail"` or `"preview"`). An attacker can inject arbitrary query-string content via the `size` parameter.

**Risk:** While the value is passed as an HTTP query parameter (not a URL path segment), injecting unexpected values may cause unintended Immich API behaviours, parameter pollution, or in the worst case expose different asset endpoints depending on Immich's query routing.

**Proposed solution:**

Validate `size` against an allowlist using a `Literal` type or `Enum`:

```python
from typing import Literal

@router.get("/{asset_id}")
def get_thumbnail(
    asset_id: str,
    size: Literal["thumbnail", "preview"] = "thumbnail",
    ...
):
```

FastAPI will automatically reject invalid values with a 422 before the handler is called.

---

#### SEC-007 — `reorder_buckets` endpoint accepts arbitrary dicts with no schema validation

**File:** `backend/app/routers/buckets.py:149-157`

```python
@router.post("/reorder")
def reorder_buckets(order: List[dict], db: Session = Depends(get_db)):
    for item in order:
        b = db.query(Bucket).filter(Bucket.id == item["id"]).first()
        if b:
            b.priority = item["priority"]
```

**Description:**  
The `order` body is typed as `List[dict]`, bypassing Pydantic validation entirely. Any extra keys are silently ignored, but `item["id"]` and `item["priority"]` are accessed without type checks. If `item["priority"]` is not an integer (e.g. a string or `null`), it will be passed to SQLAlchemy's column update. If `item["id"]` is missing entirely, this raises an unhandled `KeyError`.

**Proposed solution:**

Define a proper Pydantic schema:

```python
class BucketReorderItem(BaseModel):
    id: str
    priority: int

@router.post("/reorder")
def reorder_buckets(order: List[BucketReorderItem], db: Session = Depends(get_db)):
    for item in order:
        b = db.query(Bucket).filter(Bucket.id == item.id).first()
        if b:
            b.priority = item.priority
    db.commit()
    return {"reordered": True}
```

---

### MEDIUM

---

#### SEC-008 — Sensitive data (AI provider API keys, Immich API key) returned to the API response in some paths / reflected in error messages

**File:** `backend/app/routers/settings.py:54-55`, `backend/app/routers/settings.py:68-70`

**Description:**  
`ImmichSettingsOut` includes the `immich_url` in the response body. More critically, when `ImmichError` is raised, `str(e)` is directly placed in the `error` field of the response and also raised as an `HTTPException(detail=str(e))`. The Immich error message can contain the URL that was attempted (e.g. `"Cannot connect to Immich: ...http://192.168.1.x:2283/..."`), which leaks internal network topology. Similarly, `test_provider` at line 161 does `raise HTTPException(status_code=400, detail=str(e))` where `e` is a raw exception that may contain API key fragments in stack traces.

The `ProviderConfigOut` schema correctly omits the `api_key_encrypted` field (`has_api_key: bool` only), which is good. But the `_provider_to_out` function does not sanitize the `base_url`, which can be returned to the client even when it contains credentials embedded in the URL (e.g. `http://user:pass@ollama-host:11434`).

**Proposed solutions:**

1. Sanitize `ImmichError` messages before returning them to clients — strip URLs and replace with a generic connectivity message.
2. Wrap all `except Exception as e: raise HTTPException(detail=str(e))` patterns to avoid leaking raw exception strings that may contain credentials or internal hostnames.
3. Scrub credentials from `base_url` before returning it in `ProviderConfigOut`.

```python
import re

def _sanitize_error(msg: str) -> str:
    """Remove URLs and potential credential fragments from error messages."""
    msg = re.sub(r'https?://\S+', '[URL redacted]', msg)
    return msg
```

---

#### SEC-009 — `ImmichSettingsUpdate` requires `immich_api_key` but exposes it unnecessarily on the test endpoint

**File:** `backend/app/routers/settings.py:73-81`

```python
@router.post("/immich/test")
def test_immich_connection(body: ImmichSettingsUpdate):  # no DB session
```

**Description:**  
`ImmichSettingsUpdate` has `immich_api_key: str` as a required field. The test endpoint accepts this but does not persist it — the key is only used in-memory for the test request. The issue is that the schema forces the frontend to always send the API key in clear text to test connectivity, even when the key is already stored in the database. An HTTPS-only deployment mitigates this, but if the app is served over plain HTTP (common in self-hosted LAN scenarios), the key is transmitted in every test request.

**Proposed solution:**  
Separate the test schema from the save schema:

```python
class ImmichTestRequest(BaseModel):
    immich_url: str
    immich_api_key: Optional[str] = None  # omit to use the stored key

@router.post("/immich/test")
def test_immich_connection(body: ImmichTestRequest, db: Session = Depends(get_db)):
    url, api_key = _get_immich_credentials(db)
    url = body.immich_url or url
    api_key = body.immich_api_key or api_key
    ...
```

---

#### SEC-010 — Redis connection is not authenticated

**File:** `backend/app/routers/jobs.py:51`, `docker-compose.yml:101`

```python
conn = Redis.from_url(settings.REDIS_URL)
```

```yaml
REDIS_URL: redis://redis:6379/0   # no password
```

**Description:**  
The Redis instance used for the job queue has no password. In the full-stack Docker Compose profile, Redis is isolated on an internal Docker bridge network (`immich_gpt_net`), which provides container-level isolation. However, if the bridge network is misconfigured, if additional containers share the network, or if the deployment is on a non-Docker environment where Redis binds to `0.0.0.0`, an attacker with network access can:

- Read and manipulate the job queue.
- Inject arbitrary job function calls (since RQ serializes function references with `pickle`), which in the worst case allows **remote code execution** if an attacker can push a crafted job.

**Proposed solutions:**

1. Add a `requirepass` directive to the Redis configuration and pass the password in `REDIS_URL`:
   ```yaml
   redis:
     image: redis:7-alpine
     command: redis-server --requirepass ${REDIS_PASSWORD:-changeme-redis}
   ```
   ```yaml
   REDIS_URL: redis://:${REDIS_PASSWORD:-changeme-redis}@redis:6379/0
   ```

2. Document the RCE risk of pickle-based deserialization in the RQ queue and note that the network isolation of the Docker bridge is the primary protection.

3. For defence in depth, consider using RQ's `serializer` parameter to replace pickle with a safer format for job arguments (though this requires custom serialization for the existing task functions).

---

#### SEC-011 — `page_size` parameters have no upper bound (unbounded DB queries)

**Files:** `backend/app/routers/assets.py:44`, `backend/app/routers/review.py:56`, `backend/app/routers/audit_logs.py:35`

```python
def list_assets(page: int = 1, page_size: int = 50, ...):
    ...
    assets = query.offset(offset).limit(page_size).all()
```

**Description:**  
`page_size` is an unbounded integer query parameter. A client can request `page_size=100000000`, causing SQLite to attempt to retrieve millions of rows in a single response, exhausting memory and blocking the event loop for an extended period.

**Proposed solution:**

Add `Query` validation:

```python
from fastapi import Query

def list_assets(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    ...
):
```

Apply the same cap to `list_audit_logs` (default 50, max 500 is appropriate), `get_review_queue` (default 20, max 100), and `list_jobs` (default 20, max 100).

---

#### SEC-012 — `extra_config_json` in `ProviderConfig` is deserialized directly into `build_provider` kwargs

**File:** `backend/app/workers/tasks.py:119-121`

```python
if provider_cfg.extra_config_json:
    cfg_dict.update(provider_cfg.extra_config_json)
provider = build_provider(provider_cfg.provider_name, cfg_dict)
```

**Description:**  
`extra_config_json` is a JSON blob stored in the database without schema validation. Calling `cfg_dict.update(provider_cfg.extra_config_json)` allows the database record to override any key in `cfg_dict`, including `api_key`, `model_name`, and `base_url`. If an attacker can write to `extra_config_json` (e.g. via the `POST /api/settings/providers` endpoint), they can redirect all AI calls to an arbitrary endpoint and exfiltrate all photos and prompts.

This is mitigated by authentication, but since auth is off by default (SEC-001) it is a real attack vector.

**Proposed solution:**

Only allow a safe allowlist of known extra-config keys when merging:

```python
ALLOWED_EXTRA_KEYS = {"timeout", "max_retries", "proxy"}

if provider_cfg.extra_config_json:
    safe_extra = {
        k: v for k, v in provider_cfg.extra_config_json.items()
        if k in ALLOWED_EXTRA_KEYS
    }
    cfg_dict.update(safe_extra)
```

Alternatively, define a typed Pydantic schema for `extra_config` and validate on write.

---

#### SEC-013 — `DEBUG` mode flag exists but has no effect on security-sensitive behaviour

**File:** `backend/app/config.py:9`

```python
DEBUG: bool = False
```

**Description:**  
`DEBUG` is declared in config but is never passed to FastAPI (which would enable detailed exception tracebacks in API responses, path operation listings, etc.). FastAPI itself does not expose a debug mode that leaks stack traces in production, but uvicorn does when started with `--reload` or in debug mode. More importantly, if `DEBUG=true` is set in `.env`, operators may expect it to enable verbose error responses, but it currently does nothing — leaving them with false expectations.

If `DEBUG` is plumbed into FastAPI in the future (e.g. `FastAPI(debug=settings.DEBUG)`) without care, it would enable detailed error pages that expose stack traces to API callers.

**Proposed solution:**

Either wire the flag through correctly (adding safe guards), or remove it from config to avoid misleading operators. At minimum, document what the flag does and does not do.

---

### LOW

---

#### SEC-014 — `pytest` and `pytest-asyncio` packages are listed in production `requirements.txt`

**File:** `backend/requirements.txt:16-20`

```
pytest==8.3.4
pytest-asyncio==0.25.0
httpx==0.28.1     # already listed on line 7 — duplicate entry
pytest-mock==3.14.0
anyio==4.8.0
```

**Description:**  
Test dependencies are included in the production image's `pip install`. This increases the attack surface (more installed packages = more potential vulnerable packages), slightly increases image size, and `httpx` is listed twice (lines 7 and 17) — indicating the file is not well-maintained.

**Proposed solution:**

Separate production and test dependencies:

```
# requirements.txt (production only)
fastapi==0.115.6
uvicorn[standard]==0.34.0
sqlalchemy==2.0.36
alembic==1.14.0
pydantic==2.10.3
pydantic-settings==2.7.0
httpx==0.28.1
pillow==11.1.0
openai==1.59.3
redis==5.2.1
rq==2.1.0
python-multipart==0.0.20
python-dotenv==1.0.1
aiosqlite==0.20.0
greenlet==3.1.1

# requirements-dev.txt (test/dev only)
pytest==8.3.4
pytest-asyncio==0.25.0
pytest-mock==3.14.0
anyio==4.8.0
```

Update `Dockerfile.unraid` and `backend/Dockerfile` to only `pip install -r requirements.txt`. Update CI/local dev to run `pip install -r requirements-dev.txt` in addition.

---

#### SEC-015 — No `Content-Security-Policy` header set

**File:** `backend/app/main.py` (no security headers middleware)

**Description:**  
The application serves a React SPA with no `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options`, or `Referrer-Policy` headers. This is lower risk for a self-hosted tool, but:

- Absence of `X-Frame-Options: DENY` allows the UI to be embedded in an iframe on a malicious page (clickjacking).
- Absence of `Content-Security-Policy` provides no browser-level XSS mitigation.
- Absence of `X-Content-Type-Options: nosniff` allows MIME sniffing attacks on the thumbnail proxy response.

**Proposed solution:**

Add a simple security headers middleware:

```python
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Permissive CSP suitable for a self-hosted SPA that loads from same origin
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "  # Vite inlines some scripts
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "connect-src 'self';"
        )
        return response
```

---

#### SEC-016 — `Optional` import in `config.py` is unused

**File:** `backend/app/config.py:2`

```python
from typing import Optional
```

This import is not used anywhere in the file. Minor code quality issue — no security impact, but indicates the file has not been reviewed recently.

**Proposed solution:** Remove the unused import.

---

#### SEC-017 — The `ConfigDict` import in `provider.py` is duplicated

**File:** `backend/app/schemas/provider.py:1`

```python
from pydantic import BaseModel, ConfigDict, ConfigDict   # ConfigDict imported twice
```

**Proposed solution:** `from pydantic import BaseModel, ConfigDict`

---

#### SEC-018 — Thumbnail `Cache-Control: public, max-age=3600` may cache sensitive photos in shared proxies

**File:** `backend/app/routers/thumbnails.py:38`

```python
headers={"Cache-Control": "public, max-age=3600"},
```

**Description:**  
`Cache-Control: public` allows any intermediate cache (CDN, reverse proxy, shared corporate proxy) to store the thumbnail and serve it to other users. For a private photo library this is inappropriate — thumbnails should only be cached by the end user's browser.

**Proposed solution:**

```python
headers={"Cache-Control": "private, max-age=3600"},
```

---

#### SEC-019 — The `OpenRouterProvider.health_check` returns `True` for HTTP 401

**File:** `backend/app/services/ai_provider.py:310`

```python
return r.status_code in (200, 401)
```

**Description:**  
A 401 response means the API key is invalid. Treating this as "healthy" causes the UI to show the provider as connected when it is actually not authenticated. This is a logic bug with a minor security implication: users may believe their credentials are valid when they are not, and the provider will continue to be used for classification jobs that will all fail with 401 errors (potentially after consuming per-request costs for some providers).

**Proposed solution:**

```python
return r.status_code == 200
```

---

#### SEC-020 — The Docker image runs as `root`

**File:** `Dockerfile.unraid:84`

```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

There is no `USER` directive; the process runs as root inside the container.

**Risk:** If a vulnerability in the application or any dependency allows command execution, the attacker runs as root inside the container. While container isolation provides some protection, running as root increases the blast radius of a container escape.

**Proposed solution:**

Add a non-root user in the Dockerfile:

```dockerfile
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
RUN chown -R appuser:appgroup /app /data /logs
USER appuser
```

Ensure the `/data` volume is owned by `appuser` before switching.

---

## Summary Table

| ID | Severity | Title |
|----|----------|-------|
| SEC-001 | **Critical** | Auth off by default; default `SECRET_KEY` is public |
| SEC-002 | **Critical** | Auth bypass covers all `/api/jobs/` routes, not just SSE stream |
| SEC-003 | **High** | `allow_origins=["*"]` + `allow_credentials=True` (broken + overly permissive CORS) |
| SEC-004 | **High** | API keys stored in plain text despite column named `api_key_encrypted` |
| SEC-005 | **High** | No rate limiting — AI API quota exhaustion and resource abuse |
| SEC-006 | **High** | Thumbnail `size` param unsanitized — passes user input to Immich API |
| SEC-007 | **High** | `reorder_buckets` accepts unvalidated `List[dict]` |
| SEC-008 | **Medium** | Error messages may leak internal URLs and credentials |
| SEC-009 | **Medium** | Immich API key always transmitted in test requests |
| SEC-010 | **Medium** | Redis has no authentication password |
| SEC-011 | **Medium** | `page_size` has no upper bound — unbounded DB queries |
| SEC-012 | **Medium** | `extra_config_json` can override `api_key` / `base_url` in provider config |
| SEC-013 | **Medium** | `DEBUG` flag declared but unused — misleading and risky if wired in future |
| SEC-014 | **Low** | Test dependencies (`pytest`) included in production `requirements.txt` |
| SEC-015 | **Low** | No HTTP security headers (`CSP`, `X-Frame-Options`, etc.) |
| SEC-016 | **Low** | Unused `Optional` import in `config.py` |
| SEC-017 | **Low** | Duplicate `ConfigDict` import in `schemas/provider.py` |
| SEC-018 | **Low** | Thumbnail responses use `Cache-Control: public` — may cache in shared proxies |
| SEC-019 | **Low** | OpenRouter health check treats HTTP 401 as healthy |
| SEC-020 | **Low** | Docker container runs as root |

---

## Recommended Remediation Priority

1. **SEC-001** — Fix the default auth posture immediately. This is the root cause that makes most other issues exploitable.
2. **SEC-002** — Narrow the auth bypass to the SSE stream endpoint only.
3. **SEC-004** — Rename the column and (optionally) add Fernet encryption. Misleading name should be fixed regardless.
4. **SEC-003** — Remove `allow_credentials=True` from CORS.
5. **SEC-006, SEC-007, SEC-011** — Input validation hardening; straightforward Pydantic/FastAPI fixes.
6. **SEC-005** — Rate limiting; add `slowapi` to protect AI quota.
7. **SEC-010** — Redis password; one-line change in Compose.
8. **SEC-012** — Restrict `extra_config_json` key allowlist.
9. **SEC-008, SEC-009, SEC-015, SEC-018, SEC-020** — Security hygiene improvements.
10. **SEC-013, SEC-014, SEC-016, SEC-017, SEC-019** — Low-effort cleanup.
