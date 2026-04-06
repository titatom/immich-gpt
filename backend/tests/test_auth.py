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
    """Fresh in-memory DB with a single active user whose e-mail is stored lower-cased."""
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
        email="user@example.com",          # stored lower-case (as create_user does)
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
# Login tests
# ---------------------------------------------------------------------------

def test_login_success_exact_email(raw_client):
    resp = raw_client.post("/api/auth/login", json={
        "email": "user@example.com",
        "password": "correct-password",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "user@example.com"
    assert data["username"] == "authuser"


def test_login_success_uppercase_email(raw_client):
    """Email lookup must be case-insensitive: User@Example.COM should find the stored lower-case address."""
    resp = raw_client.post("/api/auth/login", json={
        "email": "User@Example.COM",
        "password": "correct-password",
    })
    assert resp.status_code == 200
    assert resp.json()["email"] == "user@example.com"


def test_login_success_mixed_case_email(raw_client):
    resp = raw_client.post("/api/auth/login", json={
        "email": "USER@EXAMPLE.COM",
        "password": "correct-password",
    })
    assert resp.status_code == 200


def test_login_wrong_password(raw_client):
    resp = raw_client.post("/api/auth/login", json={
        "email": "user@example.com",
        "password": "wrong-password",
    })
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password"


def test_login_unknown_email(raw_client):
    resp = raw_client.post("/api/auth/login", json={
        "email": "nobody@example.com",
        "password": "correct-password",
    })
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password"


def test_login_inactive_user(raw_client, auth_db):
    auth_db.query(User).filter(User.id == "auth-test-user-id").update({"is_active": False})
    auth_db.commit()

    resp = raw_client.post("/api/auth/login", json={
        "email": "user@example.com",
        "password": "correct-password",
    })
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password"


def test_login_sets_session_cookie(raw_client):
    resp = raw_client.post("/api/auth/login", json={
        "email": "user@example.com",
        "password": "correct-password",
    })
    assert resp.status_code == 200
    assert "session_id" in resp.cookies or any(
        "session" in k.lower() for k in resp.cookies
    )
