"""
Tests for the in-process RQ worker bootstrap.

These tests do not require a running Redis: they patch the Redis /
SimpleWorker classes that ``app.workers.rq_inline_worker`` imports
lazily so we can assert behaviour deterministically.
"""
import importlib
import threading
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _reset_module_state():
    """Reset the module-level "started" flag before every test."""
    from app.workers import rq_inline_worker
    rq_inline_worker._reset_for_tests()
    yield
    rq_inline_worker._reset_for_tests()


def _patch_settings(redis_url: str = "", concurrency: int = 2):
    """Helper that patches the ``settings`` object used by the worker module."""
    from app.workers import rq_inline_worker
    return patch.multiple(
        rq_inline_worker.settings,
        REDIS_URL=redis_url,
        WORKER_CONCURRENCY=concurrency,
    )


# ---------------------------------------------------------------------------
# Behaviour: REDIS_URL empty
# ---------------------------------------------------------------------------

def test_no_workers_when_redis_url_empty():
    """When REDIS_URL is unset the inline worker is a no-op."""
    from app.workers import rq_inline_worker
    with _patch_settings(redis_url=""):
        n = rq_inline_worker.start_inline_workers()
    assert n == 0
    assert rq_inline_worker.is_started()


def test_idempotent_when_redis_url_empty():
    from app.workers import rq_inline_worker
    with _patch_settings(redis_url=""):
        rq_inline_worker.start_inline_workers()
        # Second call returns immediately without spawning anything.
        n = rq_inline_worker.start_inline_workers()
    assert n == 0


# ---------------------------------------------------------------------------
# Behaviour: REDIS_URL set
# ---------------------------------------------------------------------------

def test_starts_concurrent_threads_when_redis_url_set(monkeypatch):
    """One daemon thread per WORKER_CONCURRENCY slot."""
    from app.workers import rq_inline_worker

    started: list[threading.Thread] = []

    real_thread_init = threading.Thread.__init__

    def fake_thread_init(self, *args, **kwargs):
        # Force daemon=True regardless of caller, and capture the
        # constructed Thread for assertions.  Skip actually starting a
        # worker loop by replacing the target with a no-op.
        kwargs["target"] = lambda *a, **kw: None
        real_thread_init(self, *args, **kwargs)
        started.append(self)

    monkeypatch.setattr(threading.Thread, "__init__", fake_thread_init)

    with _patch_settings(redis_url="redis://localhost:6379/0", concurrency=3):
        n = rq_inline_worker.start_inline_workers()

    assert n == 3
    assert len(started) == 3
    for t in started:
        assert t.daemon is True
        assert t.name.startswith("rq-inline-worker-")


def test_idempotent_when_redis_url_set(monkeypatch):
    """Calling start_inline_workers twice is a no-op the second time."""
    from app.workers import rq_inline_worker

    spawned: list = []

    real_thread_init = threading.Thread.__init__

    def fake_thread_init(self, *args, **kwargs):
        kwargs["target"] = lambda *a, **kw: None
        real_thread_init(self, *args, **kwargs)
        spawned.append(self)

    monkeypatch.setattr(threading.Thread, "__init__", fake_thread_init)

    with _patch_settings(redis_url="redis://localhost:6379/0", concurrency=2):
        first = rq_inline_worker.start_inline_workers()
        second = rq_inline_worker.start_inline_workers()

    assert first == 2
    assert second == 2
    # No additional threads on the second call.
    assert len(spawned) == 2


# ---------------------------------------------------------------------------
# Behaviour: worker loop reconnects after Redis errors
# ---------------------------------------------------------------------------

def test_worker_loop_retries_on_redis_error(monkeypatch):
    """A RedisError in the loop body should sleep + retry, not die."""
    from app.workers import rq_inline_worker
    from redis.exceptions import RedisError

    # Patch out time.sleep used inside the loop so the test runs fast.
    sleeps: list[float] = []
    monkeypatch.setattr(rq_inline_worker, "_sleep", sleeps.append)

    call_count = {"n": 0}

    class FakeRedis:
        @classmethod
        def from_url(cls, url):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RedisError("boom")
            # Second iteration: raise a sentinel exception to break out
            # of the otherwise-infinite loop.
            raise SystemExit("stop loop")

    monkeypatch.setattr("redis.Redis", FakeRedis)

    with _patch_settings(redis_url="redis://localhost:6379/0", concurrency=1):
        with pytest.raises(SystemExit):
            rq_inline_worker._run_worker_loop(0)

    # First Redis error caused exactly one backoff sleep.
    assert sleeps and sleeps[0] >= 1.0


# ---------------------------------------------------------------------------
# rq_worker.py CLI entry point
# ---------------------------------------------------------------------------

def test_standalone_worker_main_requires_redis_url(capsys):
    """The standalone worker exits with code 2 and a hint when REDIS_URL is empty."""
    from app.workers import rq_worker

    with patch.object(rq_worker.settings, "REDIS_URL", ""):
        rc = rq_worker.main()

    assert rc == 2
    err = capsys.readouterr().err
    assert "REDIS_URL" in err


def test_standalone_worker_main_does_not_use_removed_connection_api(monkeypatch):
    """Regression: rq.Connection was removed in RQ 2.x — make sure rq_worker
    no longer imports it and that ``main()`` constructs a Worker via the
    keyword-arg API instead.
    """
    from app.workers import rq_worker
    import rq as rq_pkg

    # The whole point of the regression: the symbol must not exist any more
    # in modern RQ, and our module must not depend on it.
    assert not hasattr(rq_pkg, "Connection")
    assert "Connection" not in rq_worker.__dict__

    fake_worker = MagicMock()
    fake_worker.work.return_value = True
    monkeypatch.setattr(rq_worker, "Worker", MagicMock(return_value=fake_worker))
    fake_redis = MagicMock()
    monkeypatch.setattr(rq_worker, "Redis", MagicMock(from_url=lambda url: fake_redis))

    with patch.object(rq_worker.settings, "REDIS_URL", "redis://example:6379/0"):
        rc = rq_worker.main()

    assert rc == 0
    fake_worker.work.assert_called_once()
    # Worker must be constructed with explicit ``connection=`` kw arg
    # (the API that replaced ``with Connection(conn): Worker(...)``).
    _, kwargs = rq_worker.Worker.call_args
    assert "connection" in kwargs
