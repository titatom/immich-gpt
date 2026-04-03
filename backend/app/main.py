import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
