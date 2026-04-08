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

    with patch("app.main.init_db"):
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
# First-run setup endpoint
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


def test_setup_status_no_users(empty_db):
    """GET /api/auth/setup/status returns setup_required=true when DB is empty."""
    def override_get_db():
        try:
            yield empty_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.main.init_db"):
        with TestClient(app, raise_server_exceptions=True) as c:
            resp = c.get("/api/auth/setup/status")

    app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json() == {"setup_required": True}


def test_setup_status_with_existing_users(auth_db):
    """GET /api/auth/setup/status returns setup_required=false when users exist."""
    def override_get_db():
        try:
            yield auth_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.main.init_db"):
        with TestClient(app, raise_server_exceptions=True) as c:
            resp = c.get("/api/auth/setup/status")

    app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json() == {"setup_required": False}


def test_setup_creates_first_admin(empty_db):
    """POST /api/auth/setup creates the first admin and returns a session cookie."""
    def override_get_db():
        try:
            yield empty_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.main.init_db"):
        with TestClient(app, raise_server_exceptions=True) as c:
            resp = c.post("/api/auth/setup", json={
                "email": "owner@example.com",
                "username": "owner",
                "password": "securepassword",
            })

    app.dependency_overrides.clear()

    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "owner@example.com"
    assert data["username"] == "owner"
    assert data["role"] == "admin"
    assert data["force_password_change"] is False
    assert "session_id" in resp.cookies


def test_setup_blocked_when_users_exist(auth_db):
    """POST /api/auth/setup returns 403 when at least one user already exists."""
    def override_get_db():
        try:
            yield auth_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.main.init_db"):
        with TestClient(app, raise_server_exceptions=True) as c:
            resp = c.post("/api/auth/setup", json={
                "email": "attacker@example.com",
                "username": "attacker",
                "password": "password123",
            })

    app.dependency_overrides.clear()

    assert resp.status_code == 403


def test_setup_short_password_rejected(empty_db):
    """POST /api/auth/setup rejects passwords shorter than 8 characters."""
    def override_get_db():
        try:
            yield empty_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.main.init_db"):
        with TestClient(app, raise_server_exceptions=True) as c:
            resp = c.post("/api/auth/setup", json={
                "email": "a@b.com",
                "username": "owner",
                "password": "short",
            })

    app.dependency_overrides.clear()

    assert resp.status_code == 400


def test_setup_can_login_after_creation(empty_db):
    """After setup, the created admin can log in via the normal login endpoint."""
    def override_get_db():
        try:
            yield empty_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.main.init_db"):
        with TestClient(app, raise_server_exceptions=True) as c:
            c.post("/api/auth/setup", json={
                "email": "first@example.com",
                "username": "firstadmin",
                "password": "mypassword1",
            })
            resp = c.post("/api/auth/login", json={
                "username": "firstadmin",
                "password": "mypassword1",
            })

    app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


def test_setup_idempotency_blocked_on_second_call(empty_db):
    """Calling POST /api/auth/setup twice: second call must return 403."""
    def override_get_db():
        try:
            yield empty_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.main.init_db"):
        with TestClient(app, raise_server_exceptions=True) as c:
            c.post("/api/auth/setup", json={
                "email": "first@example.com",
                "username": "firstadmin",
                "password": "mypassword1",
            })
            resp2 = c.post("/api/auth/setup", json={
                "email": "second@example.com",
                "username": "second",
                "password": "mypassword2",
            })

    app.dependency_overrides.clear()

    assert resp2.status_code == 403


def test_setup_audit_log_created(empty_db):
    """Creating the first admin via setup must write an audit log entry."""
    from app.models.audit_log import AuditLog

    def override_get_db():
        try:
            yield empty_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.main.init_db"):
        with TestClient(app, raise_server_exceptions=True) as c:
            c.post("/api/auth/setup", json={
                "email": "audit@example.com",
                "username": "auditadmin",
                "password": "password123",
            })

    app.dependency_overrides.clear()

    log = empty_db.query(AuditLog).filter(
        AuditLog.action == "first_admin_created"
    ).first()
    assert log is not None
    assert log.source == "setup"
