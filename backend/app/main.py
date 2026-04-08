import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .database import init_db
from .routers import (
    settings, buckets, prompts, assets, jobs, review,
    thumbnails, albums, audit_logs,
)
from .routers.auth import router as auth_router
from .routers.admin import router as admin_router
from .config import settings as app_settings

logger = logging.getLogger(__name__)

_SECRET_KEY_WARNING = """
╔══════════════════════════════════════════════════════════════════╗
║  ⚠  SECURITY WARNING: SECRET_KEY is set to the default value.  ║
║                                                                  ║
║  Session tokens can be forged with this key.                    ║
║  Set a strong random SECRET_KEY in your .env or environment     ║
║  before exposing this service to any network.                   ║
║                                                                  ║
║  Generate one with:  python -c "import secrets; print(secrets.token_hex(32))"  ║
╚══════════════════════════════════════════════════════════════════╝
"""

_ADMIN_BOOTSTRAP_WARNING = """
╔══════════════════════════════════════════════════════════════════╗
║  ⚠  ADMIN BOOTSTRAP SKIPPED                                    ║
║                                                                  ║
║  No users exist yet, but ADMIN_EMAIL or ADMIN_PASSWORD is       ║
║  missing/invalid. Set explicit bootstrap credentials before     ║
║  first start instead of relying on a default admin account.     ║
║                                                                  ║
║  Required: ADMIN_EMAIL, ADMIN_PASSWORD                          ║
║  Optional: ADMIN_USERNAME (falls back to ADMIN_EMAIL)           ║
╚══════════════════════════════════════════════════════════════════╝
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    if app_settings.secret_key_is_default:
        logger.warning(_SECRET_KEY_WARNING)
    init_db()
    _bootstrap_admin()
    yield


def _bootstrap_admin() -> None:
    """Create the first admin account from explicit env vars if configured."""
    if app_settings.ADMIN_SKIP_BOOTSTRAP:
        return
    from .database import SessionLocal
    from .models.user import User
    from .services.user_service import ensure_admin_exists
    db = SessionLocal()
    try:
        if db.query(User).count() != 0:
            return

        email = app_settings.ADMIN_EMAIL.strip()
        password = app_settings.ADMIN_PASSWORD.strip()
        username = app_settings.ADMIN_USERNAME.strip() or email

        if not email or len(password) < 8:
            logger.warning(_ADMIN_BOOTSTRAP_WARNING)
            return

        ensure_admin_exists(db, email=email, password=password, username=username)
    finally:
        db.close()


app = FastAPI(
    title="Immich GPT",
    description="AI-first metadata enrichment and organization for Immich",
    version="0.2.0",
    lifespan=lifespan,
)

_cors_origins = app_settings.cors_origins_list
app.add_middleware(
    CORSMiddleware,
    # When specific origins are configured we can safely allow credentials.
    # Falling back to ["*"] with allow_credentials=True is rejected by browsers
    # per the CORS spec, so we only set credentials when origins are explicit.
    allow_origins=_cors_origins if _cors_origins else ["*"],
    allow_credentials=bool(_cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(settings.router)
app.include_router(buckets.router)
app.include_router(prompts.router)
app.include_router(assets.router)
app.include_router(jobs.router)
app.include_router(review.router)
app.include_router(thumbnails.router)
app.include_router(albums.router)
app.include_router(audit_logs.router)


@app.get("/api/health")
@app.get("/health")
def health():
    return {"status": "ok", "version": "0.2.0"}


# Serve frontend static files in production
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
_static_dir_exists = os.path.isdir(static_dir)

if _static_dir_exists:
    assets_build_dir = os.path.join(static_dir, "assets")
    if os.path.isdir(assets_build_dir):
        app.mount("/assets", StaticFiles(directory=assets_build_dir), name="assets-bundle")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str, request: Request):
        index_file = os.path.join(static_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"error": "Frontend not built. Run: cd frontend && npx vite build"}
