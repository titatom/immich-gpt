import os
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
from .seeds import seed_defaults
from .middleware.auth import BearerTokenMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_defaults()
    yield


app = FastAPI(
    title="Immich GPT",
    description="AI-first metadata enrichment and organization for Immich",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(BearerTokenMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    return {"status": "ok", "version": "0.1.0"}


# Serve frontend static files in production
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
_static_dir_exists = os.path.isdir(static_dir)

if _static_dir_exists:
    # Mount the built assets directory (JS/CSS bundles) as a static sub-path.
    # The /assets path in Vite's output is always a subdirectory of the build root.
    assets_build_dir = os.path.join(static_dir, "assets")
    if os.path.isdir(assets_build_dir):
        app.mount("/assets", StaticFiles(directory=assets_build_dir), name="assets-bundle")

    # SPA catch-all: serve index.html for any non-API path so that client-side
    # routing (React Router) works correctly on hard refresh or direct navigation.
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str, request: Request):
        index_file = os.path.join(static_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"error": "Frontend not built. Run: cd frontend && npx vite build"}
