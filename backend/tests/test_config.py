"""
Tests for config.py — startup validation of SECRET_KEY and cookie defaults.

These tests instantiate Settings() directly with controlled env-var overrides
so they do not depend on the process-level SECRET_KEY set in conftest.py.
"""
import os
import pytest
from pydantic import ValidationError


def _make_settings(**kwargs):
    """Create a fresh Settings instance with the given environment overrides."""
    from importlib import reload
    import app.config as config_module

    old_env = {}
    try:
        for key, value in kwargs.items():
            old_env[key] = os.environ.get(key)
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

        # Clear any cached .env reads by re-instantiating Settings directly.
        from app.config import Settings
        return Settings()
    finally:
        for key, old_val in old_env.items():
            if old_val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_val


# ---------------------------------------------------------------------------
# SECRET_KEY validation
# ---------------------------------------------------------------------------

class TestSecretKeyValidation:
    def test_strong_key_accepted(self):
        """A long random key must be accepted without error."""
        s = _make_settings(SECRET_KEY="a" * 64)
        assert len(s.SECRET_KEY) == 64

    def test_exactly_minimum_length_accepted(self):
        """A key of exactly 32 characters must be accepted."""
        s = _make_settings(SECRET_KEY="x" * 32)
        assert len(s.SECRET_KEY) == 32

    def test_empty_key_rejected(self):
        """An empty SECRET_KEY must raise ValidationError at startup."""
        with pytest.raises(ValidationError, match="SECRET_KEY is not set"):
            _make_settings(SECRET_KEY="")

    def test_default_placeholder_rejected(self):
        """The well-known placeholder value must be rejected."""
        with pytest.raises(ValidationError, match="SECRET_KEY is not set or uses a known weak placeholder"):
            _make_settings(SECRET_KEY="change-me-in-production")

    def test_other_weak_placeholders_rejected(self):
        """Other common weak placeholder values must be rejected."""
        for weak in ["secret", "changeme", "insecure", "dev"]:
            with pytest.raises(ValidationError, match="SECRET_KEY"):
                _make_settings(SECRET_KEY=weak)

    def test_short_key_rejected(self):
        """A key shorter than 32 characters must be rejected."""
        with pytest.raises(ValidationError, match="at least 32 characters"):
            _make_settings(SECRET_KEY="a" * 31)

    def test_31_char_key_rejected(self):
        """31-character key is one below the threshold — must be rejected."""
        with pytest.raises(ValidationError, match="SECRET_KEY"):
            _make_settings(SECRET_KEY="s" * 31)

    def test_no_secret_key_env_var_rejected(self):
        """When SECRET_KEY is not set at all the validator must fail."""
        with pytest.raises(ValidationError, match="SECRET_KEY"):
            # Pass empty string — same as missing, since field default is "".
            _make_settings(SECRET_KEY="")


# ---------------------------------------------------------------------------
# Cookie security defaults
# ---------------------------------------------------------------------------

class TestCookieSecurityDefaults:
    def test_session_cookie_secure_defaults_to_false(self):
        """SESSION_COOKIE_SECURE must default to False.

        Browsers silently discard Secure cookies over plain HTTP, which breaks
        login for the majority of self-hosted (LAN/HTTP) deployments. The safe
        default is False; operators serving over HTTPS must opt in explicitly.
        """
        s = _make_settings(
            SECRET_KEY="a" * 64,
            SESSION_COOKIE_SECURE=None,  # remove override — use default
        )
        assert s.SESSION_COOKIE_SECURE is False

    def test_session_cookie_samesite_defaults_to_strict(self):
        """SESSION_COOKIE_SAMESITE must default to 'strict'."""
        s = _make_settings(
            SECRET_KEY="a" * 64,
            SESSION_COOKIE_SAMESITE=None,
        )
        assert s.SESSION_COOKIE_SAMESITE == "strict"

    def test_session_cookie_secure_can_be_overridden_to_false(self):
        """SESSION_COOKIE_SECURE=false must be accepted for local HTTP dev."""
        s = _make_settings(
            SECRET_KEY="a" * 64,
            SESSION_COOKIE_SECURE="false",
        )
        assert s.SESSION_COOKIE_SECURE is False

    def test_session_cookie_samesite_can_be_overridden(self):
        """SESSION_COOKIE_SAMESITE must accept explicit override."""
        s = _make_settings(
            SECRET_KEY="a" * 64,
            SESSION_COOKIE_SAMESITE="lax",
        )
        assert s.SESSION_COOKIE_SAMESITE == "lax"


# ---------------------------------------------------------------------------
# Cookie flags applied to login response
# ---------------------------------------------------------------------------

class TestLoginCookieFlags:
    """Verify that the login endpoint sets the expected cookie attributes."""

    def test_login_sets_httponly_cookie(self, db):
        """The session cookie set on login must always be HttpOnly."""
        from app.main import app
        from app.database import get_db
        from app.models.user import User
        from app.services.auth_service import hash_password
        from fastapi.testclient import TestClient
        from unittest.mock import patch
        import uuid

        user = User(
            id=str(uuid.uuid4()),
            email="cookietest@test.com",
            username="cookietest",
            hashed_password=hash_password("cookiepass1"),
            role="user",
            is_active=True,
            force_password_change=False,
        )
        db.add(user)
        db.commit()

        def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db
        with patch("app.main.init_db"):
            with TestClient(app, raise_server_exceptions=True) as c:
                r = c.post(
                    "/api/auth/login",
                    json={"username": "cookietest@test.com", "password": "cookiepass1"},
                )
        app.dependency_overrides.clear()

        assert r.status_code == 200
        # TestClient follows redirects and exposes cookies; check the raw
        # Set-Cookie header for the HttpOnly flag.
        set_cookie = r.headers.get("set-cookie", "")
        assert "HttpOnly" in set_cookie or "httponly" in set_cookie.lower()

    def test_login_sets_session_id_cookie(self, db):
        """The session cookie key must be 'session_id' (default name)."""
        from app.main import app
        from app.database import get_db
        from app.models.user import User
        from app.services.auth_service import hash_password
        from fastapi.testclient import TestClient
        from unittest.mock import patch
        import uuid

        user = User(
            id=str(uuid.uuid4()),
            email="cookiename@test.com",
            username="cookiename",
            hashed_password=hash_password("cookiepass2"),
            role="user",
            is_active=True,
            force_password_change=False,
        )
        db.add(user)
        db.commit()

        def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db
        with patch("app.main.init_db"):
            with TestClient(app, raise_server_exceptions=True) as c:
                r = c.post(
                    "/api/auth/login",
                    json={"username": "cookiename@test.com", "password": "cookiepass2"},
                )
        app.dependency_overrides.clear()

        assert r.status_code == 200
        assert "session_id" in r.cookies
