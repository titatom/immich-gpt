"""
In-process background executor.

Used when REDIS_URL is empty (single-container / Unraid deployments).
A module-level ThreadPoolExecutor keeps a bounded pool of worker threads
that share the process address space.  Jobs are fire-and-forget — the
API returns immediately and the task runs in the background.

The pool is intentionally small (default 2) because the bottleneck is
always the external AI provider, not CPU.
"""
from concurrent.futures import ThreadPoolExecutor
from ..config import settings

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
