import uuid
import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from redis import Redis
from rq import Queue
from rq.job import Retry

from ..database import get_db, SessionLocal
from ..models.job_run import JobRun
from ..schemas.job import JobRunOut, JobStartResponse
from ..services.job_progress import JobProgressService
from ..config import settings

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

_TERMINAL = frozenset({"completed", "failed", "cancelled"})


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


@router.get("/{job_id}/stream")
async def stream_job(job_id: str):
    """
    Server-Sent Events stream for real-time job progress.

    Each event is a JSON-encoded JobRunOut. The stream ends automatically
    when the job reaches a terminal state (completed / failed / cancelled).

    Usage (browser):
        const es = new EventSource('/api/jobs/<id>/stream');
        es.onmessage = e => console.log(JSON.parse(e.data));
    """

    async def _event_generator():
        # Use a fresh DB session per generator — don't share the request session
        # across async iterations.
        last_updated_at = None
        while True:
            db = SessionLocal()
            try:
                j = db.query(JobRun).filter(JobRun.id == job_id).first()
                if not j:
                    yield f"event: error\ndata: {json.dumps({'detail': 'Job not found'})}\n\n"
                    return

                # Only push an event when something changed
                if j.updated_at != last_updated_at:
                    last_updated_at = j.updated_at
                    payload = _job_to_out(j).model_dump_json()
                    yield f"data: {payload}\n\n"

                if j.status in _TERMINAL:
                    yield "event: done\ndata: {}\n\n"
                    return
            finally:
                db.close()

            await asyncio.sleep(1)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/sync", response_model=JobStartResponse)
def start_sync_job(db: Session = Depends(get_db)):
    from ..workers.tasks import run_asset_sync
    svc = JobProgressService(db)
    job = svc.create_job("asset_sync")

    q = _get_queue()
    if q:
        q.enqueue(run_asset_sync, job.id, retry=Retry(max=3, interval=[10, 30, 60]))
    else:
        import threading
        t = threading.Thread(target=run_asset_sync, args=(job.id,), daemon=True)
        t.start()

    return JobStartResponse(job_id=job.id, status="queued", message="Sync job started")


@router.post("/classify", response_model=JobStartResponse)
def start_classify_job(
    asset_ids: Optional[List[str]] = None,
    limit: Optional[int] = None,
    force: bool = False,
    db: Session = Depends(get_db),
):
    from ..workers.tasks import run_classification
    svc = JobProgressService(db)
    job = svc.create_job("classification", params={"asset_ids": asset_ids, "limit": limit, "force": force})

    q = _get_queue()
    if q:
        q.enqueue(run_classification, job.id, asset_ids, limit, force,
                  retry=Retry(max=3, interval=[10, 30, 60]))
    else:
        import threading
        t = threading.Thread(
            target=run_classification, args=(job.id, asset_ids, limit, force), daemon=True
        )
        t.start()

    return JobStartResponse(job_id=job.id, status="queued", message="Classification job started")


@router.post("/{job_id}/cancel")
def cancel_job(job_id: str, db: Session = Depends(get_db)):
    svc = JobProgressService(db)
    j = svc.get_job(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    if j.status in _TERMINAL:
        raise HTTPException(status_code=400, detail=f"Job already in terminal state: {j.status}")
    svc.cancel_job(job_id)
    return {"cancelled": True}
