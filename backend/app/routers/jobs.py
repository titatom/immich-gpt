import uuid
import json
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db, SessionLocal
from ..dependencies import require_active_user, get_current_user
from ..models.job_run import JobRun
from ..schemas.job import JobRunOut, JobStartResponse, SyncJobRequest
from ..services.job_progress import JobProgressService
from ..config import settings

logger = logging.getLogger(__name__)

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


def _enqueue(fn, *args):
    """Dispatch a background task via RQ or in-process ThreadPoolExecutor."""
    if settings.REDIS_URL:
        try:
            from redis import Redis
            from rq import Queue
            from rq.job import Retry
            conn = Redis.from_url(settings.REDIS_URL)
            q = Queue(connection=conn)
            q.enqueue(fn, *args, retry=Retry(max=3, interval=[10, 30, 60]))
            return
        except Exception:
            logger.warning(
                "Redis enqueue failed (REDIS_URL=%s); falling back to in-process executor.",
                settings.REDIS_URL,
                exc_info=True,
            )
    from ..workers.executor import submit
    submit(fn, *args)


@router.delete("")
def clear_terminal_jobs(
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """Delete all completed, failed, and cancelled jobs for the current user."""
    deleted = db.query(JobRun).filter(
        JobRun.user_id == current_user.id,
        JobRun.status.in_(list(_TERMINAL)),
    ).delete(synchronize_session=False)
    db.commit()
    return {"deleted": deleted}


@router.get("", response_model=List[JobRunOut])
def list_jobs(
    job_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    svc = JobProgressService(db)
    jobs = svc.list_jobs(job_type, status, limit, user_id=current_user.id)
    return [_job_to_out(j) for j in jobs]


@router.get("/{job_id}", response_model=JobRunOut)
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    svc = JobProgressService(db)
    j = svc.get_job(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    if j.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_out(j)


@router.get("/{job_id}/stream")
async def stream_job(job_id: str, request: Request):
    """
    Server-Sent Events stream for real-time job progress.
    Requires authentication via session cookie.
    """
    # Validate session before streaming
    db_check = SessionLocal()
    try:
        user = get_current_user(request, db_check)
        # Verify job ownership
        j = db_check.query(JobRun).filter(JobRun.id == job_id).first()
        if not j or (j.user_id is not None and j.user_id != user.id):
            return StreamingResponse(
                iter([f"event: error\ndata: {json.dumps({'detail': 'Job not found'})}\n\n"]),
                media_type="text/event-stream",
            )
        user_id = user.id
    except HTTPException as exc:
        return StreamingResponse(
            iter([f"event: error\ndata: {json.dumps({'detail': exc.detail})}\n\n"]),
            media_type="text/event-stream",
        )
    finally:
        db_check.close()

    async def _event_generator():
        last_updated_at = None
        while True:
            db = SessionLocal()
            try:
                j = db.query(JobRun).filter(JobRun.id == job_id).first()
                if not j:
                    yield f"event: error\ndata: {json.dumps({'detail': 'Job not found'})}\n\n"
                    return

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
def start_sync_job(
    body: Optional[SyncJobRequest] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    from ..workers.tasks import run_asset_sync
    req = body or SyncJobRequest()
    svc = JobProgressService(db)
    job = svc.create_job(
        "asset_sync",
        params={"scope": req.scope, "album_ids": req.album_ids},
        user_id=current_user.id,
    )

    _enqueue(run_asset_sync, job.id, req.scope, req.album_ids, current_user.id)

    return JobStartResponse(job_id=job.id, status="queued", message="Sync job started")


@router.post("/classify", response_model=JobStartResponse)
def start_classify_job(
    asset_ids: Optional[List[str]] = None,
    limit: Optional[int] = None,
    force: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    from ..workers.tasks import run_classification
    svc = JobProgressService(db)
    job = svc.create_job(
        "classification",
        params={"asset_ids": asset_ids, "limit": limit, "force": force},
        user_id=current_user.id,
    )

    _enqueue(run_classification, job.id, asset_ids, limit, force, current_user.id)
    return JobStartResponse(job_id=job.id, status="queued", message="Classification job started")


@router.post("/{job_id}/cancel")
def cancel_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    svc = JobProgressService(db)
    j = svc.get_job(job_id)
    if not j or (j.user_id is not None and j.user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Job not found")
    if j.status in _TERMINAL:
        raise HTTPException(status_code=400, detail=f"Job already in terminal state: {j.status}")
    svc.cancel_job(job_id)
    return {"cancelled": True}


@router.post("/{job_id}/pause")
def pause_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    svc = JobProgressService(db)
    j = svc.get_job(job_id)
    if not j or (j.user_id is not None and j.user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Job not found")
    if j.status in _TERMINAL or j.status == "paused":
        raise HTTPException(status_code=400, detail=f"Cannot pause job in state: {j.status}")
    svc.pause_job(job_id)
    return {"paused": True}


@router.post("/{job_id}/resume")
def resume_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    svc = JobProgressService(db)
    j = svc.get_job(job_id)
    if not j or (j.user_id is not None and j.user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Job not found")
    if j.status != "paused":
        raise HTTPException(status_code=400, detail=f"Job is not paused (status: {j.status})")
    svc.resume_job(job_id)
    _enqueue(_resume_job_task, job_id)
    return {"resumed": True}


@router.delete("/{job_id}")
def delete_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    svc = JobProgressService(db)
    j = svc.get_job(job_id)
    if not j or (j.user_id is not None and j.user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Job not found")
    if j.status not in _TERMINAL:
        raise HTTPException(status_code=400, detail="Can only delete completed, failed, or cancelled jobs")
    svc.delete_job(job_id)
    return {"deleted": True}


def _resume_job_task(job_id: str) -> None:
    from ..database import SessionLocal
    db = SessionLocal()
    try:
        from ..models.job_run import JobRun
        j = db.query(JobRun).filter(JobRun.id == job_id).first()
        if not j or j.status != "queued":
            return
        params = j.params_json or {}
        user_id = j.user_id
        if j.job_type == "asset_sync":
            from ..workers.tasks import run_asset_sync
            run_asset_sync(job_id, params.get("scope", "all"), params.get("album_ids"), user_id)
        elif j.job_type == "classification":
            from ..workers.tasks import run_classification
            run_classification(job_id, params.get("asset_ids"), params.get("limit"), params.get("force", False), user_id)
    finally:
        db.close()
