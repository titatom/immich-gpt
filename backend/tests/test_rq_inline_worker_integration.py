"""
End-to-end integration test for the in-process RQ worker.

This test only runs when a real Redis is available on the host; it is
skipped otherwise so the default unit-test run remains hermetic.

It guards against a regression where jobs were enqueued to Redis but
never executed, leaving them stuck in the ``queued`` state.
"""
import time

import pytest


pytest.importorskip("redis")
pytest.importorskip("rq")


def _redis_available(url: str) -> bool:
    try:
        from redis import Redis
        Redis.from_url(url, socket_connect_timeout=0.5).ping()
        return True
    except Exception:
        return False


REDIS_URL = "redis://localhost:6379/15"


pytestmark = pytest.mark.skipif(
    not _redis_available(REDIS_URL),
    reason="Local Redis not reachable on db=15; integration test skipped.",
)


# Module-level callable so RQ can pickle it.  RQ refuses to enqueue jobs
# defined in __main__ or in a closure.
_RESULTS: list = []


def _record(value: str) -> str:
    _RESULTS.append(value)
    return value


def test_inline_worker_drains_a_job():
    """Enqueue a job, start the inline worker, assert the job ran."""
    from redis import Redis
    from rq import Queue
    from rq.job import Job

    from app.workers import rq_inline_worker

    conn = Redis.from_url(REDIS_URL)
    conn.flushdb()
    _RESULTS.clear()

    rq_inline_worker._reset_for_tests()

    q = Queue("default", connection=conn)
    enqueued = q.enqueue(_record, "hello")

    # Sanity: queue is non-empty before the worker starts.
    assert q.count == 1

    # Permanently set the URL on the singleton settings object — the worker
    # thread re-reads it whenever it reconnects to Redis, so a transient
    # patch context manager would race with the loop body.
    original_url = rq_inline_worker.settings.REDIS_URL
    original_concurrency = rq_inline_worker.settings.WORKER_CONCURRENCY
    rq_inline_worker.settings.REDIS_URL = REDIS_URL
    rq_inline_worker.settings.WORKER_CONCURRENCY = 1
    try:
        n = rq_inline_worker.start_inline_workers()
        assert n == 1

        # Wait up to 5 s for the worker thread to pick the job up.
        deadline = time.time() + 5.0
        while time.time() < deadline:
            job = Job.fetch(enqueued.id, connection=conn)
            if job.is_finished:
                break
            time.sleep(0.05)
        else:
            pytest.fail(
                f"Inline worker did not finish the job within 5 s "
                f"(status={job.get_status()})"
            )

        assert _RESULTS == ["hello"]
    finally:
        rq_inline_worker.settings.REDIS_URL = original_url
        rq_inline_worker.settings.WORKER_CONCURRENCY = original_concurrency
