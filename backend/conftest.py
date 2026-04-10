"""
Root-level pytest configuration for the backend test suite.

Module-level code here runs before pytest loads any test-directory conftest
files, which means os.environ changes are visible when app.config.Settings()
is first instantiated during the import chain triggered by tests/conftest.py.
"""
import os
import pytest

# Provide a valid SECRET_KEY so the Settings validator passes in tests.
# This value is used ONLY during automated testing and is never shipped.
os.environ.setdefault(
    "SECRET_KEY",
    "test-only-secret-key-not-for-production-use-1234",
)


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Clear the in-memory rate-limit store before each test.

    All TestClient requests share the "testclient" source IP.  Without a
    reset, login attempts accumulate across tests and eventually trip the
    10/minute limit, causing unrelated tests to receive 429 responses.
    """
    from app.limiter import limiter
    try:
        limiter.reset()
    except Exception:
        # Older slowapi versions may not expose reset(); safe to ignore.
        pass
    yield
