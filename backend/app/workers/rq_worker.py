#!/usr/bin/env python
"""RQ worker entry point."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from redis import Redis
from rq import Worker, Queue, Connection
from app.config import settings

listen = ["default", "high", "low"]

conn = Redis.from_url(settings.REDIS_URL)

if __name__ == "__main__":
    with Connection(conn):
        worker = Worker(list(map(Queue, listen)))
        worker.work()
