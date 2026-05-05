"""
In-process RQ worker.

When ``REDIS_URL`` is configured, the FastAPI process used to enqueue jobs
to Redis but never spawn anything to consume them, leaving every job stuck
in the ``queued`` state forever unless the operator also ran a separate
``rq worker`` container.  For the single-container deployment (the
default Docker / Unraid layout) that almost never happens.

This module starts an :class:`rq.SimpleWorker` inside a daemon thread so
the same container that enqueues jobs also drains the queue.  Operators
that want true horizontal scaling can still run ``python -m
app.workers.rq_worker`` in a sidecar container — that worker will share
the queue and parallelise work across processes.

The worker is intentionally a :class:`SimpleWorker`: it does not fork,
which is required because ``Worker`` relies on ``os.fork()``.  In
addition, both ``Worker.work`` and the default ``UnixSignalDeathPenalty``
install POSIX signal handlers, which raise ``ValueError("signal only
works in main thread")`` from a daemon thread.  We subclass
``SimpleWorker`` to neutralise both call sites (see
:func:`_build_inline_worker_class`).  Concurrency on the in-process
path is controlled by ``WORKER_CONCURRENCY`` (one ``SimpleWorker``
thread is spawned per concurrency slot).
"""
from __future__ import annotations

import logging
import threading
from typing import List, Optional

from ..config import settings
from ..utils.logging import redact_url


logger = logging.getLogger(__name__)

# The queue names this in-process worker drains.  Mirrors LISTEN in
# ``rq_worker.py`` so the inline worker and the standalone worker behave
# identically when both are running.
QUEUE_NAMES: List[str] = ["high", "default", "low"]

_lock = threading.Lock()
_threads: List[threading.Thread] = []
_started = False


def _build_inline_worker_class():
    """Return a SimpleWorker subclass safe to ``work()`` on a non-main thread.

    Two pieces of RQ machinery use POSIX signals, both of which raise
    ``ValueError("signal only works in main thread of the main interpreter")``
    when invoked from a daemon thread:

    1. ``Worker.work`` calls ``signal.signal`` for SIGINT/SIGTERM via
       ``_install_signal_handlers``.
    2. The default ``UnixSignalDeathPenalty`` sets a SIGALRM handler to
       enforce per-job timeouts.

    We override #1 to a no-op (the FastAPI process handles its own
    shutdown signals) and replace #2 with ``TimerDeathPenalty``, which
    uses ``threading.Timer`` instead of SIGALRM.
    """
    from rq import SimpleWorker
    from rq.timeouts import TimerDeathPenalty

    class _InlineSimpleWorker(SimpleWorker):
        death_penalty_class = TimerDeathPenalty

        def _install_signal_handlers(self):
            return

    return _InlineSimpleWorker


def _run_worker_loop(worker_index: int) -> None:
    """Body of one worker thread.

    Reconnects to Redis lazily so that a brief Redis outage does not
    permanently kill the thread.  Each iteration generates a unique
    worker name so RQ's "active worker name already exists" check (which
    looks at stale heartbeat keys) does not lock us out after a crash.
    """
    import os
    import uuid

    from redis import Redis
    from redis.exceptions import RedisError
    from rq import Queue

    InlineSimpleWorker = _build_inline_worker_class()

    pid = os.getpid()
    backoff = 1.0
    while True:
        try:
            conn = Redis.from_url(settings.REDIS_URL)
            conn.ping()
            queues = [Queue(name, connection=conn) for name in QUEUE_NAMES]
            unique_suffix = uuid.uuid4().hex[:8]
            worker = InlineSimpleWorker(
                queues,
                connection=conn,
                name=f"inline-{pid}-{worker_index}-{unique_suffix}",
            )
            logger.info(
                "Inline RQ worker %s started (queues=%s)",
                worker.name, QUEUE_NAMES,
            )
            # ``with_scheduler=False`` keeps things simple — we don't use
            # RQ's scheduled-job feature.  ``burst=False`` means the
            # worker blocks on BRPOP and runs forever.
            worker.work(with_scheduler=False, burst=False)
            backoff = 1.0
        except RedisError as exc:
            logger.warning(
                "Inline RQ worker %d lost Redis connection (%s); "
                "retrying in %.1fs",
                worker_index, exc, backoff,
            )
            _sleep(backoff)
            backoff = min(backoff * 2, 30.0)
        except Exception:  # pragma: no cover - defensive
            logger.exception(
                "Inline RQ worker %d crashed; restarting in %.1fs",
                worker_index, backoff,
            )
            _sleep(backoff)
            backoff = min(backoff * 2, 30.0)


def _sleep(seconds: float) -> None:
    # Indirected for easier patching in tests.
    import time
    time.sleep(seconds)


def start_inline_workers(concurrency: Optional[int] = None) -> int:
    """Start the in-process RQ worker threads.

    Idempotent: subsequent calls are no-ops.  Returns the number of
    worker threads that are now running (0 when ``REDIS_URL`` is not
    set).  Safe to call from FastAPI's lifespan startup hook.
    """
    global _started

    with _lock:
        if _started:
            return len(_threads)

        if not settings.REDIS_URL:
            logger.debug(
                "REDIS_URL is empty; inline RQ worker not started "
                "(jobs will run via in-process ThreadPoolExecutor)."
            )
            _started = True
            return 0

        n = max(1, concurrency or settings.WORKER_CONCURRENCY)
        for i in range(n):
            t = threading.Thread(
                target=_run_worker_loop,
                args=(i,),
                name=f"rq-inline-worker-{i}",
                daemon=True,
            )
            t.start()
            _threads.append(t)
        _started = True
        logger.info(
            "Started %d inline RQ worker thread(s) for REDIS_URL=%s",
            n, redact_url(settings.REDIS_URL),
        )
        return n


def is_started() -> bool:
    """Test helper: True once :func:`start_inline_workers` has run."""
    with _lock:
        return _started


def _reset_for_tests() -> None:
    """Test helper: clear the started flag and the thread registry.

    Threads themselves are daemonic and will be torn down with the
    process; we only reset module-level state so a subsequent call to
    :func:`start_inline_workers` exercises the start logic again.
    """
    global _started
    with _lock:
        _started = False
        _threads.clear()
