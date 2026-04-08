"""
Root-level pytest configuration for the backend test suite.

Module-level code here runs before pytest loads any test-directory conftest
files, which means os.environ changes are visible when app.config.Settings()
is first instantiated during the import chain triggered by tests/conftest.py.
"""
import os

# Provide a valid SECRET_KEY so the Settings validator passes in tests.
# This value is used ONLY during automated testing and is never shipped.
os.environ.setdefault(
    "SECRET_KEY",
    "test-only-secret-key-not-for-production-use-1234",
)
