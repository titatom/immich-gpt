"""
Tests for BearerTokenMiddleware (SEC-001 / SEC-002 fixes).

Verifies:
- Auth disabled (default): all /api/* endpoints pass through.
- Auth enabled: protected endpoints require a valid Bearer token.
- Auth enabled: health endpoints bypass auth.
- Auth enabled: SSE stream endpoint bypasses auth.
- Auth enabled: other /api/jobs/* endpoints (cancel, pause, resume, detail) are
  protected (SEC-002 fix — they must NOT bypass auth).
- Auth enabled: non-/api paths (static SPA) bypass auth.
- Valid token: request passes through.
- Invalid token: 403.
- Missing header: 401.
"""
import uuid
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.models.job_run import JobRun


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_job(db, status="queued") -> JobRun:
    job = JobRun(
        id=str(uuid.uuid4()),
        job_type="asset_sync",
        status=status,
        processed_count=0,
        total_count=0,
        success_count=0,
        error_count=0,
        progress_percent=0.0,
        log_lines_json=[],
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@pytest.fixture
def auth_client(db):
    """TestClient with AUTH_ENABLED=true and a known SECRET_KEY."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with (
        patch("app.main.init_db"),
        patch("app.main.seed_defaults"),
        patch("app.middleware.auth.settings") as mock_settings,
    ):
        mock_settings.AUTH_ENABLED = True
        mock_settings.SECRET_KEY = "test-secret-key-abc123"

        with TestClient(app, raise_server_exceptions=True) as c:
            yield c, "test-secret-key-abc123"

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Auth disabled (default) — everything passes
# ---------------------------------------------------------------------------

def test_auth_disabled_api_endpoint_passes(client):
    r = client.get("/api/health")
    assert r.status_code == 200


def test_auth_disabled_jobs_endpoint_passes(client):
    r = client.get("/api/jobs")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Auth enabled — health endpoints bypass
# ---------------------------------------------------------------------------

def test_health_bypasses_auth(auth_client):
    c, _ = auth_client
    assert c.get("/api/health").status_code == 200
    assert c.get("/health").status_code == 200


# ---------------------------------------------------------------------------
# Auth enabled — SSE stream bypasses auth (SEC-002)
# ---------------------------------------------------------------------------

def test_sse_stream_bypasses_auth(auth_client, db):
    c, _ = auth_client
    job = _make_job(db, status="completed")
    # The stream endpoint returns 200 without auth; it self-terminates quickly
    # because the job is already in a terminal state.
    with c.stream("GET", f"/api/jobs/{job.id}/stream") as resp:
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Auth enabled — other /api/jobs/* are PROTECTED (SEC-002 fix)
# ---------------------------------------------------------------------------

def test_jobs_list_requires_auth(auth_client):
    c, _ = auth_client
    r = c.get("/api/jobs")
    assert r.status_code == 401


def test_job_detail_requires_auth(auth_client, db):
    c, _ = auth_client
    job = _make_job(db)
    r = c.get(f"/api/jobs/{job.id}")
    assert r.status_code == 401


def test_job_cancel_requires_auth(auth_client, db):
    c, _ = auth_client
    job = _make_job(db)
    r = c.post(f"/api/jobs/{job.id}/cancel")
    assert r.status_code == 401


def test_job_pause_requires_auth(auth_client, db):
    c, _ = auth_client
    job = _make_job(db)
    r = c.post(f"/api/jobs/{job.id}/pause")
    assert r.status_code == 401


def test_job_resume_requires_auth(auth_client, db):
    c, _ = auth_client
    job = _make_job(db, status="paused")
    r = c.post(f"/api/jobs/{job.id}/resume")
    assert r.status_code == 401


def test_jobs_sync_requires_auth(auth_client):
    c, _ = auth_client
    r = c.post("/api/jobs/sync")
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Auth enabled — valid / invalid tokens
# ---------------------------------------------------------------------------

def test_valid_token_passes(auth_client):
    c, secret = auth_client
    r = c.get("/api/jobs", headers={"Authorization": f"Bearer {secret}"})
    assert r.status_code == 200


def test_invalid_token_rejected(auth_client):
    c, _ = auth_client
    r = c.get("/api/jobs", headers={"Authorization": "Bearer wrong-token"})
    assert r.status_code == 403


def test_missing_auth_header_rejected(auth_client):
    c, _ = auth_client
    r = c.get("/api/jobs")
    assert r.status_code == 401
    assert r.headers.get("WWW-Authenticate") == "Bearer"


def test_malformed_auth_header_rejected(auth_client):
    c, _ = auth_client
    r = c.get("/api/jobs", headers={"Authorization": "Token abc"})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Auth enabled — non-/api paths bypass (static SPA)
# ---------------------------------------------------------------------------

def test_non_api_path_bypasses_auth(auth_client):
    """Non-/api paths (SPA routes) must pass through without auth."""
    c, _ = auth_client
    # /some-spa-route does not exist as a real file; FastAPI returns 404 or
    # the SPA catch-all (only present when static/ is built). Either way the
    # middleware must not return 401.
    r = c.get("/some-spa-route")
    assert r.status_code != 401
    assert r.status_code != 403


# ---------------------------------------------------------------------------
# SEC-001: SECRET_KEY auto-rotation
# ---------------------------------------------------------------------------

def test_placeholder_key_is_replaced():
    """Settings must never expose the known placeholder as the active key."""
    from app.config import settings, _PLACEHOLDER_KEY
    assert settings.SECRET_KEY != _PLACEHOLDER_KEY, (
        "SECRET_KEY must be replaced with a random value at startup; "
        "the placeholder must never be used as the active token."
    )


def test_secret_key_has_adequate_entropy():
    """Auto-generated key must be long enough for meaningful security."""
    from app.config import settings
    assert len(settings.SECRET_KEY) >= 32, (
        "SECRET_KEY must be at least 32 characters."
    )
