"""
In-process background executor.

Used when REDIS_URL is empty (single-container / Unraid deployments).
A module-level ThreadPoolExecutor keeps a bounded pool of worker threads
that share the process address space.  Jobs are fire-and-forget — the
API returns immediately and the task runs in the background.

The pool is intentionally small (default 2) because the bottleneck is
always the external AI provider, not CPU.
"""
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from ..config import settings

logger = logging.getLogger(__name__)

_pool: ThreadPoolExecutor | None = None


def get_executor() -> ThreadPoolExecutor:
    global _pool
    if _pool is None:
        _pool = ThreadPoolExecutor(
            max_workers=settings.WORKER_CONCURRENCY,
            thread_name_prefix="immich_gpt_worker",
        )
    return _pool


def submit(fn, *args, **kwargs):
    """Submit a callable to the in-process pool.  Returns a Future."""
    return get_executor().submit(fn, *args, **kwargs)


def enqueue(fn, *args) -> None:
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
    submit(fn, *args)


def enqueue_routing_classification(
    db: Session,
    user_id: str,
    asset_ids: Optional[List[str]] = None,
    limit: Optional[int] = None,
    force: bool = False,
) -> Tuple[str, str]:
    """Create a routing-classification job + plan and enqueue the worker."""
    from ..services.job_progress import JobProgressService
    from ..services.routing_plan_service import RoutingPlanService
    from ..workers.tasks import run_routing_classification

    job_svc = JobProgressService(db)
    job = job_svc.create_job(
        "routing_classification",
        params={"asset_ids": asset_ids, "limit": limit, "force": force},
        user_id=user_id,
    )
    plan = RoutingPlanService(db, user_id).create_plan(
        job_id=job.id,
        scope={"asset_ids": asset_ids, "limit": limit, "force": force},
        status="draft",
    )
    job.params_json = {
        "asset_ids": asset_ids,
        "limit": limit,
        "force": force,
        "plan_id": plan.id,
    }
    db.commit()
    enqueue(
        run_routing_classification,
        job.id, plan.id, asset_ids, limit, force, user_id,
    )
    return job.id, plan.id
