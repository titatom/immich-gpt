"""
Tests for /api/jobs router.

Covers: list, get, start sync, start classify, cancel.
Redis / RQ are never touched; patched out entirely.
"""
import uuid
from unittest.mock import patch

import pytest

from app.models.job_run import JobRun


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_job(db, job_type="asset_sync", status="queued") -> JobRun:
    job = JobRun(
        id=str(uuid.uuid4()),
        job_type=job_type,
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


# ---------------------------------------------------------------------------
# GET /api/jobs
# ---------------------------------------------------------------------------

def test_list_jobs_empty(client):
    r = client.get("/api/jobs")
    assert r.status_code == 200
    assert r.json() == []


def test_list_jobs_returns_all(client, db):
    _make_job(db, "asset_sync", "queued")
    _make_job(db, "classification", "completed")
    r = client.get("/api/jobs")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_list_jobs_filter_by_type(client, db):
    _make_job(db, "asset_sync", "queued")
    _make_job(db, "classification", "queued")
    r = client.get("/api/jobs?job_type=asset_sync")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["job_type"] == "asset_sync"


def test_list_jobs_filter_by_status(client, db):
    _make_job(db, "asset_sync", "completed")
    _make_job(db, "asset_sync", "failed")
    r = client.get("/api/jobs?status=completed")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["status"] == "completed"


def test_list_jobs_limit(client, db):
    for _ in range(5):
        _make_job(db)
    r = client.get("/api/jobs?limit=3")
    assert r.status_code == 200
    assert len(r.json()) == 3


# ---------------------------------------------------------------------------
# GET /api/jobs/{job_id}
# ---------------------------------------------------------------------------

def test_get_job(client, db):
    job = _make_job(db)
    r = client.get(f"/api/jobs/{job.id}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == job.id
    assert data["job_type"] == "asset_sync"
    assert data["status"] == "queued"


def test_get_job_not_found(client):
    r = client.get("/api/jobs/nonexistent-id")
    assert r.status_code == 404


def test_get_job_fields(client, db):
    job = _make_job(db)
    data = client.get(f"/api/jobs/{job.id}").json()
    for field in ("id", "job_type", "status", "progress_percent",
                  "processed_count", "total_count", "success_count",
                  "error_count", "created_at"):
        assert field in data


# ---------------------------------------------------------------------------
# POST /api/jobs/sync
# ---------------------------------------------------------------------------

def test_start_sync_job(client):
    with (
        patch("app.routers.jobs._get_queue", return_value=None),
        patch("threading.Thread") as mock_thread,
    ):
        mock_thread.return_value.start = lambda: None
        r = client.post("/api/jobs/sync")
    assert r.status_code == 200
    data = r.json()
    assert "job_id" in data
    assert data["status"] == "queued"


def test_start_sync_job_creates_db_record(client, db):
    with (
        patch("app.routers.jobs._get_queue", return_value=None),
        patch("threading.Thread") as mock_thread,
    ):
        mock_thread.return_value.start = lambda: None
        r = client.post("/api/jobs/sync")
    job_id = r.json()["job_id"]
    job = db.query(JobRun).filter(JobRun.id == job_id).first()
    assert job is not None
    assert job.job_type == "asset_sync"


# ---------------------------------------------------------------------------
# POST /api/jobs/classify
# ---------------------------------------------------------------------------

def test_start_classify_job(client):
    with (
        patch("app.routers.jobs._get_queue", return_value=None),
        patch("threading.Thread") as mock_thread,
    ):
        mock_thread.return_value.start = lambda: None
        r = client.post("/api/jobs/classify")
    assert r.status_code == 200
    data = r.json()
    assert "job_id" in data
    assert data["status"] == "queued"


def test_start_classify_job_with_asset_ids(client):
    with (
        patch("app.routers.jobs._get_queue", return_value=None),
        patch("threading.Thread") as mock_thread,
    ):
        mock_thread.return_value.start = lambda: None
        r = client.post(
            "/api/jobs/classify",
            params={"asset_ids": ["id1", "id2"], "limit": 10},
        )
    assert r.status_code == 200


def test_start_classify_job_creates_db_record(client, db):
    with (
        patch("app.routers.jobs._get_queue", return_value=None),
        patch("threading.Thread") as mock_thread,
    ):
        mock_thread.return_value.start = lambda: None
        r = client.post("/api/jobs/classify")
    job_id = r.json()["job_id"]
    job = db.query(JobRun).filter(JobRun.id == job_id).first()
    assert job is not None
    assert job.job_type == "classification"


# ---------------------------------------------------------------------------
# POST /api/jobs/{job_id}/cancel
# ---------------------------------------------------------------------------

def test_cancel_job(client, db):
    job = _make_job(db, status="queued")
    r = client.post(f"/api/jobs/{job.id}/cancel")
    assert r.status_code == 200
    assert r.json()["cancelled"] is True


def test_cancel_job_not_found(client):
    r = client.post("/api/jobs/nonexistent/cancel")
    assert r.status_code == 404


def test_cancel_completed_job_rejected(client, db):
    job = _make_job(db, status="completed")
    r = client.post(f"/api/jobs/{job.id}/cancel")
    assert r.status_code == 400


def test_cancel_failed_job_rejected(client, db):
    job = _make_job(db, status="failed")
    r = client.post(f"/api/jobs/{job.id}/cancel")
    assert r.status_code == 400


def test_cancel_already_cancelled_rejected(client, db):
    job = _make_job(db, status="cancelled")
    r = client.post(f"/api/jobs/{job.id}/cancel")
    assert r.status_code == 400
