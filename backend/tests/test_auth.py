"""
Tests for the /api/auth/login endpoint.

These tests use a real (in-memory SQLite) database and do NOT override the
get_current_user / require_active_user dependencies, so the full authentication
code-path (authenticate_user, session creation, cookie setting) is exercised.
"""
import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

import app.models.user  # noqa – register with Base
import app.models.session  # noqa

from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.services.auth_service import hash_password


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_db():
    """Fresh in-memory DB with one active user."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()

    user = User(
        id="auth-test-user-id",
        email="user@example.com",
        username="authuser",
        hashed_password=hash_password("correct-password"),
        role="user",
        is_active=True,
        force_password_change=False,
    )
    db.add(user)
    db.commit()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def raw_client(auth_db):
    """TestClient that only overrides the DB; auth deps are NOT mocked."""
    def override_get_db():
        try:
            yield auth_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.main.init_db"), patch("app.main._bootstrap_admin"):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Login via username
# ---------------------------------------------------------------------------

def test_login_success_by_username(raw_client):
    resp = raw_client.post("/api/auth/login", json={
        "username": "authuser",
        "password": "correct-password",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "authuser"
    assert data["email"] == "user@example.com"


def test_login_success_by_email(raw_client):
    """Login still works when the user types their e-mail address."""
    resp = raw_client.post("/api/auth/login", json={
        "username": "user@example.com",
        "password": "correct-password",
    })
    assert resp.status_code == 200
    assert resp.json()["username"] == "authuser"


def test_login_email_case_insensitive(raw_client):
    """E-mail lookup is case-insensitive."""
    resp = raw_client.post("/api/auth/login", json={
        "username": "User@Example.COM",
        "password": "correct-password",
    })
    assert resp.status_code == 200


def test_login_wrong_password(raw_client):
    resp = raw_client.post("/api/auth/login", json={
        "username": "authuser",
        "password": "wrong-password",
    })
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid username or password"


def test_login_unknown_username(raw_client):
    resp = raw_client.post("/api/auth/login", json={
        "username": "nobody",
        "password": "correct-password",
    })
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid username or password"


def test_login_inactive_user(raw_client, auth_db):
    auth_db.query(User).filter(User.id == "auth-test-user-id").update({"is_active": False})
    auth_db.commit()

    resp = raw_client.post("/api/auth/login", json={
        "username": "authuser",
        "password": "correct-password",
    })
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid username or password"


def test_login_sets_session_cookie(raw_client):
    resp = raw_client.post("/api/auth/login", json={
        "username": "authuser",
        "password": "correct-password",
    })
    assert resp.status_code == 200
    assert "session_id" in resp.cookies or any(
        "session" in k.lower() for k in resp.cookies
    )


# ---------------------------------------------------------------------------
# Bootstrap / first-start credentials
# ---------------------------------------------------------------------------

@pytest.fixture
def empty_db():
    """Completely empty in-memory DB (no seed users) to simulate first boot."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_bootstrap_admin_with_explicit_credentials(empty_db):
    """ensure_admin_exists creates a working admin when explicit creds are supplied."""
    from app.services.user_service import ensure_admin_exists
    from app.services.auth_service import authenticate_user

    ensure_admin_exists(
        empty_db,
        email="owner@example.com",
        password="strongpass123",
        username="owner",
    )

    user = authenticate_user(empty_db, "owner", "strongpass123")
    assert user is not None
    assert user.username == "owner"
    assert user.role == "admin"
    assert user.force_password_change is True


def test_bootstrap_admin_login_via_api(empty_db):
    """Full HTTP login works with explicit bootstrap credentials."""
    from app.services.user_service import ensure_admin_exists

    ensure_admin_exists(
        empty_db,
        email="owner@example.com",
        password="strongpass123",
        username="owner",
    )

    def override_get_db():
        try:
            yield empty_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.main.init_db"), patch("app.main._bootstrap_admin"):
        with TestClient(app, raise_server_exceptions=True) as c:
            resp = c.post("/api/auth/login", json={"username": "owner", "password": "strongpass123"})

    app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "owner"
    assert data["force_password_change"] is True


# ---------------------------------------------------------------------------
# Missing / weak bootstrap credentials
# ---------------------------------------------------------------------------

def test_bootstrap_admin_missing_credentials_fail_closed(empty_db):
    """_bootstrap_admin must not create a default admin when creds are missing."""
    from app.main import _bootstrap_admin
    from app.services.auth_service import authenticate_user
    from app.models.user import User

    mock_settings = type("S", (), {
        "ADMIN_SKIP_BOOTSTRAP": False,
        "ADMIN_EMAIL": "",
        "ADMIN_PASSWORD": "",
        "ADMIN_USERNAME": "",
    })()

    with patch("app.main.app_settings", mock_settings), \
         patch("app.database.SessionLocal", return_value=empty_db):
        _bootstrap_admin()

    assert empty_db.query(User).count() == 0
    assert authenticate_user(empty_db, "admin", "admin") is None


def test_bootstrap_admin_short_password_fail_closed(empty_db):
    """_bootstrap_admin must reject bootstrap passwords shorter than 8 chars."""
    from app.main import _bootstrap_admin
    from app.models.user import User

    mock_settings = type("S", (), {
        "ADMIN_SKIP_BOOTSTRAP": False,
        "ADMIN_EMAIL": "owner@example.com",
        "ADMIN_PASSWORD": "short",
        "ADMIN_USERNAME": "owner",
    })()

    with patch("app.main.app_settings", mock_settings), \
         patch("app.database.SessionLocal", return_value=empty_db):
        _bootstrap_admin()

    assert empty_db.query(User).count() == 0


def test_bootstrap_admin_username_defaults_to_email(empty_db):
    """ADMIN_USERNAME may be blank; bootstrap falls back to ADMIN_EMAIL."""
    from app.main import _bootstrap_admin
    from app.services.auth_service import authenticate_user

    mock_settings = type("S", (), {
        "ADMIN_SKIP_BOOTSTRAP": False,
        "ADMIN_EMAIL": "owner@example.com",
        "ADMIN_PASSWORD": "strongpass123",
        "ADMIN_USERNAME": "",
    })()

    with patch("app.main.app_settings", mock_settings), \
         patch("app.database.SessionLocal", return_value=empty_db):
        _bootstrap_admin()

    user = authenticate_user(empty_db, "owner@example.com", "strongpass123")
    assert user is not None
    assert user.username == "owner@example.com"


def test_bootstrap_admin_skip_flag(empty_db):
    """ADMIN_SKIP_BOOTSTRAP=true suppresses auto-creation entirely."""
    from app.main import _bootstrap_admin
    from app.models.user import User

    mock_settings = type("S", (), {
        "ADMIN_SKIP_BOOTSTRAP": True,
    })()

    with patch("app.main.app_settings", mock_settings):
        _bootstrap_admin()

    assert empty_db.query(User).count() == 0, \
        "no user should be created when ADMIN_SKIP_BOOTSTRAP is true"
