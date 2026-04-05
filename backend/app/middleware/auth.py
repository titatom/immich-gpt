"""
Optional Bearer-token auth middleware.

Activated by setting AUTH_ENABLED=true in .env / environment.
When enabled every request to /api/* must include:
    Authorization: Bearer <SECRET_KEY>

Bypassed routes (no auth required):
  - GET /health and GET /api/health  — health-check probes
  - GET /api/jobs/<id>/stream        — Server-Sent Events; EventSource cannot
                                       set custom request headers, so auth must
                                       be enforced at the client/proxy layer for
                                       this endpoint when AUTH_ENABLED=true.
  - Any non-/api path                — static SPA assets served by FastAPI
"""
import re
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import settings

_HEALTH_PATHS = frozenset({"/api/health", "/health"})

# Matches exactly /api/jobs/<job-id>/stream — nothing else under /api/jobs/
_SSE_STREAM_RE = re.compile(r"^/api/jobs/[^/]+/stream$")


class BearerTokenMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.AUTH_ENABLED:
            return await call_next(request)

        path = request.url.path

        # Health probes
        if path in _HEALTH_PATHS:
            return await call_next(request)

        # SSE stream — EventSource API cannot attach Authorization headers
        if _SSE_STREAM_RE.match(path):
            return await call_next(request)

        # Static SPA assets served from /  (non-/api paths)
        if not path.startswith("/api"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid Authorization header"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = auth_header[len("Bearer "):].strip()
        if token != settings.SECRET_KEY:
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid token"},
            )

        return await call_next(request)
