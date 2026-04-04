"""
Optional Bearer-token auth middleware.

Activated by setting AUTH_ENABLED=true in .env / environment.
When enabled every request must include:
    Authorization: Bearer <SECRET_KEY>

Requests to /api/health and the SSE job-stream endpoint bypass auth so
healthchecks and EventSource (which cannot set headers) still work.
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import settings

_BYPASS_PREFIXES = ("/api/health", "/health", "/api/jobs/")
_BYPASS_SUFFIXES = ("/stream",)


class BearerTokenMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.AUTH_ENABLED:
            return await call_next(request)

        path = request.url.path

        # Allow health probes and SSE streams (EventSource can't send auth headers)
        if any(path.startswith(p) for p in _BYPASS_PREFIXES):
            if path.endswith("/stream") or path in ("/api/health", "/health"):
                return await call_next(request)

        # Allow unauthenticated access to the static SPA assets
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
