#!/usr/bin/env python
"""
Standalone RQ worker entry point.

Use this script to run a dedicated RQ worker process when ``REDIS_URL`` is
configured.  Most users do **not** need to invoke this directly:

* When ``REDIS_URL`` is empty (the default) jobs run in-process via a
  ``ThreadPoolExecutor`` and no worker process is required.
* When ``REDIS_URL`` is set the FastAPI app auto-starts an in-process RQ
  worker thread (see ``app.workers.rq_inline_worker``) so the single
  container still drains its own queue.

This script is kept for power users who want to scale workers horizontally
on top of a shared Redis instance.

Usage::

    cd backend
    REDIS_URL=redis://localhost:6379/0 python -m app.workers.rq_worker
"""
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from redis import Redis
from rq import Queue, Worker

from app.config import settings


LISTEN = ["high", "default", "low"]


def main() -> int:
    if not settings.REDIS_URL:
        print(
            "REDIS_URL is not set. The standalone RQ worker requires Redis. "
            "Either set REDIS_URL=redis://host:6379/0 or rely on the built-in "
            "in-process ThreadPoolExecutor (the default).",
            file=sys.stderr,
        )
        return 2

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    conn = Redis.from_url(settings.REDIS_URL)
    queues = [Queue(name, connection=conn) for name in LISTEN]
    worker = Worker(queues, connection=conn)
    worker.work(with_scheduler=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
