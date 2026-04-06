"""
JobProgressService: manages job state, progress updates, and log lines.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
from sqlalchemy.orm import Session
from ..models.job_run import JobRun


class JobProgressService:
    def __init__(self, db: Session):
        self.db = db

    def create_job(
        self,
        job_type: str,
        params: Optional[dict] = None,
        user_id: Optional[str] = None,
    ) -> JobRun:
        job = JobRun(
            id=str(uuid.uuid4()),
            user_id=user_id,
            job_type=job_type,
            status="queued",
            progress_percent=0.0,
            processed_count=0,
            total_count=0,
            success_count=0,
            error_count=0,
            params_json=params or {},
            log_lines_json=[],
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def start_job(self, job_id: str, total_count: int = 0) -> None:
        job = self._get(job_id)
        job.status = "starting"
        job.total_count = total_count
        job.started_at = _now()
        self.db.commit()

    def update_progress(
        self,
        job_id: str,
        status: Optional[str] = None,
        current_step: Optional[str] = None,
        processed: Optional[int] = None,
        total: Optional[int] = None,
        success_delta: int = 0,
        error_delta: int = 0,
        message: Optional[str] = None,
        log_line: Optional[str] = None,
    ) -> None:
        job = self._get(job_id)
        if status:
            job.status = status
        if current_step:
            job.current_step = current_step
        if processed is not None:
            job.processed_count = processed
        if total is not None:
            job.total_count = total
        job.success_count += success_delta
        job.error_count += error_delta
        if message:
            job.message = message
        if job.total_count > 0:
            job.progress_percent = round(
                (job.processed_count / job.total_count) * 100, 1
            )
        if log_line:
            lines = list(job.log_lines_json or [])
            ts = _now().strftime("%H:%M:%S")
            lines.append(f"[{ts}] {log_line}")
            # Keep last 500 lines
            job.log_lines_json = lines[-500:]
        job.updated_at = _now()
        self.db.commit()

    def complete_job(self, job_id: str, message: Optional[str] = None) -> None:
        job = self._get(job_id)
        job.status = "completed"
        job.progress_percent = 100.0
        job.completed_at = _now()
        job.updated_at = _now()
        if message:
            job.message = message
        self.db.commit()

    def fail_job(self, job_id: str, message: str) -> None:
        job = self._get(job_id)
        job.status = "failed"
        job.message = message
        job.completed_at = _now()
        job.updated_at = _now()
        self.db.commit()

    def reset_for_retry(self, job_id: str) -> None:
        """Reset a failed job back to queued so it can be re-enqueued by RQ retry."""
        job = self._get(job_id)
        job.status = "queued"
        job.progress_percent = 0.0
        job.processed_count = 0
        job.success_count = 0
        job.error_count = 0
        job.message = None
        job.started_at = None
        job.completed_at = None
        job.current_step = None
        # Preserve log history — append a separator line
        lines = list(job.log_lines_json or [])
        lines.append(f"[{_now().strftime('%H:%M:%S')}] --- retrying ---")
        job.log_lines_json = lines[-500:]
        self.db.commit()

    def cancel_job(self, job_id: str) -> None:
        job = self._get(job_id)
        job.status = "cancelled"
        job.completed_at = _now()
        job.updated_at = _now()
        self.db.commit()

    def pause_job(self, job_id: str) -> None:
        job = self._get(job_id)
        job.status = "paused"
        job.updated_at = _now()
        self.db.commit()

    def resume_job(self, job_id: str) -> None:
        job = self._get(job_id)
        job.status = "queued"
        job.updated_at = _now()
        self.db.commit()

    def delete_job(self, job_id: str) -> None:
        job = self._get(job_id)
        self.db.delete(job)
        self.db.commit()

    def get_job(self, job_id: str) -> Optional[JobRun]:
        return self.db.query(JobRun).filter(JobRun.id == job_id).first()

    def list_jobs(
        self,
        job_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
        user_id: Optional[str] = None,
    ) -> List[JobRun]:
        q = self.db.query(JobRun)
        if user_id:
            q = q.filter(JobRun.user_id == user_id)
        if job_type:
            q = q.filter(JobRun.job_type == job_type)
        if status:
            q = q.filter(JobRun.status == status)
        return q.order_by(JobRun.created_at.desc()).limit(limit).all()

    def _get(self, job_id: str) -> JobRun:
        job = self.db.query(JobRun).filter(JobRun.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        return job
