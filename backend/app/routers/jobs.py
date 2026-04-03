import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from redis import Redis
from rq import Queue

from ..database import get_db
from ..models.job_run import JobRun
from ..schemas.job import JobRunOut, JobStartResponse
from ..services.job_progress import JobProgressService
from ..config import settings

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _job_to_out(j: JobRun) -> JobRunOut:
    return JobRunOut(
        id=j.id,
        job_type=j.job_type,
        status=j.status,
        current_step=j.current_step,
        progress_percent=j.progress_percent or 0.0,
        processed_count=j.processed_count or 0,
        total_count=j.total_count or 0,
        success_count=j.success_count or 0,
        error_count=j.error_count or 0,
        message=j.message,
        log_lines=j.log_lines_json or [],
        started_at=j.started_at,
        updated_at=j.updated_at,
        completed_at=j.completed_at,
        created_at=j.created_at,
    )


def _get_queue():
    try:
        conn = Redis.from_url(settings.REDIS_URL)
        return Queue(connection=conn)
    except Exception:
        return None


@router.get("", response_model=List[JobRunOut])
def list_jobs(
    job_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    svc = JobProgressService(db)
    return [_job_to_out(j) for j in svc.list_jobs(job_type, status, limit)]


@router.get("/{job_id}", response_model=JobRunOut)
def get_job(job_id: str, db: Session = Depends(get_db)):
    svc = JobProgressService(db)
    j = svc.get_job(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_out(j)


@router.post("/sync", response_model=JobStartResponse)
def start_sync_job(db: Session = Depends(get_db)):
    from ..workers.tasks import run_asset_sync
    svc = JobProgressService(db)
    job = svc.create_job("asset_sync")

    q = _get_queue()
    if q:
        q.enqueue(run_asset_sync, job.id)
    else:
        # Run synchronously if Redis not available
        import threading
        t = threading.Thread(target=run_asset_sync, args=(job.id,), daemon=True)
        t.start()

    return JobStartResponse(job_id=job.id, status="queued", message="Sync job started")


@router.post("/classify", response_model=JobStartResponse)
def start_classify_job(
    asset_ids: Optional[List[str]] = None,
    limit: Optional[int] = None,
    db: Session = Depends(get_db),
):
    from ..workers.tasks import run_classification
    svc = JobProgressService(db)
    job = svc.create_job("classification", params={"asset_ids": asset_ids, "limit": limit})

    q = _get_queue()
    if q:
        q.enqueue(run_classification, job.id, asset_ids, limit)
    else:
        import threading
        t = threading.Thread(
            target=run_classification, args=(job.id, asset_ids, limit), daemon=True
        )
        t.start()

    return JobStartResponse(job_id=job.id, status="queued", message="Classification job started")


@router.post("/{job_id}/cancel")
def cancel_job(job_id: str, db: Session = Depends(get_db)):
    svc = JobProgressService(db)
    j = svc.get_job(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    if j.status in ("completed", "failed", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Job already in terminal state: {j.status}")
    svc.cancel_job(job_id)
    return {"cancelled": True}
