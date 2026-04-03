"""Test 8: job progress state transitions."""
import pytest
from app.services.job_progress import JobProgressService


def test_create_job(db):
    svc = JobProgressService(db)
    job = svc.create_job("asset_sync")
    assert job.id is not None
    assert job.status == "queued"
    assert job.progress_percent == 0.0


def test_start_job(db):
    svc = JobProgressService(db)
    job = svc.create_job("classification")
    svc.start_job(job.id, total_count=50)

    db.refresh(job)
    assert job.status == "starting"
    assert job.total_count == 50
    assert job.started_at is not None


def test_update_progress(db):
    svc = JobProgressService(db)
    job = svc.create_job("classification")
    svc.start_job(job.id, total_count=10)
    svc.update_progress(
        job.id,
        status="classifying_ai",
        current_step="Processing asset 3/10",
        processed=3,
        success_delta=3,
    )

    db.refresh(job)
    assert job.status == "classifying_ai"
    assert job.processed_count == 3
    assert job.success_count == 3
    assert job.progress_percent == 30.0


def test_complete_job(db):
    svc = JobProgressService(db)
    job = svc.create_job("classification")
    svc.start_job(job.id)
    svc.complete_job(job.id, message="All done")

    db.refresh(job)
    assert job.status == "completed"
    assert job.progress_percent == 100.0
    assert job.completed_at is not None
    assert job.message == "All done"


def test_fail_job(db):
    svc = JobProgressService(db)
    job = svc.create_job("classification")
    svc.start_job(job.id)
    svc.fail_job(job.id, "Something went wrong")

    db.refresh(job)
    assert job.status == "failed"
    assert "Something went wrong" in job.message
    assert job.completed_at is not None


def test_cancel_job(db):
    svc = JobProgressService(db)
    job = svc.create_job("classification")
    svc.start_job(job.id)
    svc.cancel_job(job.id)

    db.refresh(job)
    assert job.status == "cancelled"


def test_log_lines_appended(db):
    svc = JobProgressService(db)
    job = svc.create_job("classification")
    svc.update_progress(job.id, log_line="Step 1 started")
    svc.update_progress(job.id, log_line="Step 2 running")

    db.refresh(job)
    lines = job.log_lines_json
    assert len(lines) == 2
    assert any("Step 1 started" in l for l in lines)
    assert any("Step 2 running" in l for l in lines)


def test_list_jobs(db):
    svc = JobProgressService(db)
    svc.create_job("asset_sync")
    svc.create_job("classification")
    jobs = svc.list_jobs()
    assert len(jobs) >= 2


def test_list_jobs_filtered_by_type(db):
    svc = JobProgressService(db)
    svc.create_job("asset_sync")
    svc.create_job("classification")
    sync_jobs = svc.list_jobs(job_type="asset_sync")
    assert all(j.job_type == "asset_sync" for j in sync_jobs)
