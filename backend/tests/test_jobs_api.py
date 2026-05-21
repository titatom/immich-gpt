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
    from tests.conftest import TEST_USER_ID
    job = JobRun(
        id=str(uuid.uuid4()),
        user_id=TEST_USER_ID,
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


def _make_legacy_job(db, job_type="asset_sync", status="queued") -> JobRun:
    job = JobRun(
        id=str(uuid.uuid4()),
        user_id=None,
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


def test_get_legacy_unowned_job_not_found(client, db):
    job = _make_legacy_job(db)
    r = client.get(f"/api/jobs/{job.id}")
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
    with patch("app.routers.jobs._enqueue") as mock_enqueue:
        r = client.post("/api/jobs/sync")
    assert r.status_code == 200
    data = r.json()
    assert "job_id" in data
    assert data["status"] == "queued"
    mock_enqueue.assert_called_once()


def test_start_sync_job_creates_db_record(client, db):
    with patch("app.routers.jobs._enqueue"):
        r = client.post("/api/jobs/sync")
    job_id = r.json()["job_id"]
    job = db.query(JobRun).filter(JobRun.id == job_id).first()
    assert job is not None
    assert job.job_type == "asset_sync"


def test_start_sync_job_persists_route_after_sync(client, db):
    with patch("app.routers.jobs._enqueue") as mock_enqueue:
        r = client.post("/api/jobs/sync", json={"scope": "all", "run_routing_after": True})
    assert r.status_code == 200
    job = db.query(JobRun).filter(JobRun.id == r.json()["job_id"]).first()
    assert job.params_json["run_routing_after"] is True
    assert mock_enqueue.call_args.args[-1] is True


def test_run_asset_sync_enqueues_routing_after_success(db, monkeypatch):
    from app.services.job_progress import JobProgressService
    from app.workers.tasks import run_asset_sync
    from tests.conftest import TEST_USER_ID

    job = JobProgressService(db).create_job(
        "asset_sync",
        params={"scope": "all", "run_routing_after": True},
        user_id=TEST_USER_ID,
    )
    enqueued = []

    class FakeAssetSyncService:
        def __init__(self, *args, **kwargs):
            pass

        def sync_all(self, **kwargs):
            return {"synced": 1, "created": 1, "updated": 0, "errors": 0}

    monkeypatch.setattr("app.workers.tasks.SessionLocal", lambda: db)
    monkeypatch.setattr("app.workers.tasks._get_user_immich_client", lambda *args: object())
    monkeypatch.setattr("app.workers.tasks.AssetSyncService", FakeAssetSyncService)
    monkeypatch.setattr(
        "app.workers.executor.enqueue_routing_classification",
        lambda *args, **kwargs: enqueued.append((args, kwargs)),
    )

    job_id = job.id
    run_asset_sync(job_id, user_id=TEST_USER_ID, run_routing_after=True)

    refreshed = db.query(JobRun).filter(JobRun.id == job_id).first()
    assert refreshed.status == "completed"
    assert enqueued
    assert enqueued[0][1]["user_id"] == TEST_USER_ID
    assert enqueued[0][1]["force"] is False


def test_run_asset_sync_does_not_enqueue_routing_when_paused(db, monkeypatch):
    from app.services.job_progress import JobProgressService
    from app.workers.tasks import run_asset_sync
    from tests.conftest import TEST_USER_ID

    job = JobProgressService(db).create_job(
        "asset_sync",
        params={"scope": "all", "run_routing_after": True},
        user_id=TEST_USER_ID,
    )
    enqueued = []

    class FakeAssetSyncService:
        def __init__(self, *args, **kwargs):
            pass

        def sync_all(self, **kwargs):
            job.status = "paused"
            db.commit()
            return {"synced": 0, "created": 0, "updated": 0, "errors": 0}

    monkeypatch.setattr("app.workers.tasks.SessionLocal", lambda: db)
    monkeypatch.setattr("app.workers.tasks._get_user_immich_client", lambda *args: object())
    monkeypatch.setattr("app.workers.tasks.AssetSyncService", FakeAssetSyncService)
    monkeypatch.setattr(
        "app.workers.executor.enqueue_routing_classification",
        lambda *args, **kwargs: enqueued.append((args, kwargs)),
    )

    job_id = job.id
    run_asset_sync(job_id, user_id=TEST_USER_ID, run_routing_after=True)

    refreshed = db.query(JobRun).filter(JobRun.id == job_id).first()
    assert refreshed.status == "paused"
    assert enqueued == []


# ---------------------------------------------------------------------------
# POST /api/routing/classify
# ---------------------------------------------------------------------------

def test_start_routing_classify_job(client):
    with patch("app.workers.executor.enqueue") as mock_enqueue:
        r = client.post("/api/routing/classify", json={})
    assert r.status_code == 200
    data = r.json()
    assert "job_id" in data
    assert "plan_id" in data
    assert data["status"] == "queued"
    mock_enqueue.assert_called_once()


def test_start_routing_classify_creates_db_record(client, db):
    with patch("app.workers.executor.enqueue"):
        r = client.post("/api/routing/classify", json={"limit": 10})
    job_id = r.json()["job_id"]
    job = db.query(JobRun).filter(JobRun.id == job_id).first()
    assert job is not None
    assert job.job_type == "routing_classification"


def test_start_routing_classify_persists_plan_id(client, db):
    with patch("app.workers.executor.enqueue"):
        r = client.post("/api/routing/classify", json={"limit": 10})
    job = db.query(JobRun).filter(JobRun.id == r.json()["job_id"]).first()
    assert job.params_json["plan_id"] == r.json()["plan_id"]


def test_resume_routing_classification_uses_original_plan(db, monkeypatch):
    from app.routers.jobs import _resume_job_task
    from app.services.job_progress import JobProgressService
    from app.services.routing_plan_service import RoutingPlanService
    from tests.conftest import TEST_USER_ID

    job = JobProgressService(db).create_job(
        "routing_classification",
        params={"asset_ids": None, "limit": None, "force": False},
        user_id=TEST_USER_ID,
    )
    plan = RoutingPlanService(db, TEST_USER_ID).create_plan(job_id=job.id)
    plan_id = plan.id
    job.params_json = {"asset_ids": None, "limit": None, "force": False, "plan_id": plan_id}
    db.commit()
    captured = []

    monkeypatch.setattr("app.database.SessionLocal", lambda: db)
    monkeypatch.setattr(
        "app.workers.tasks.run_routing_classification",
        lambda *args: captured.append(args),
    )

    _resume_job_task(job.id)

    assert captured
    assert captured[0][0] == job.id
    assert captured[0][1] == plan_id


def test_resume_legacy_job_without_owner_fails(db, monkeypatch):
    from app.routers.jobs import _resume_job_task

    job = _make_legacy_job(db, job_type="routing_classification", status="queued")
    monkeypatch.setattr("app.database.SessionLocal", lambda: db)

    _resume_job_task(job.id)

    refreshed = db.query(JobRun).filter(JobRun.id == job.id).first()
    assert refreshed.status == "failed"
    assert "missing an owner" in refreshed.message


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


def test_cancel_legacy_unowned_job_not_found(client, db):
    job = _make_legacy_job(db)
    r = client.post(f"/api/jobs/{job.id}/cancel")
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
