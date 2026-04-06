"""
Tests for /api/auth/* endpoints.
Covers: login, logout, me, change-password, forgot-password, reset-password,
force_password_change gate enforcement.
"""
import uuid
import pytest
from unittest.mock import patch

from app.models.user import User
from app.services.auth_service import hash_password, create_session
from tests.conftest import TEST_USER_ID, TEST_ADMIN_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(
    db,
    email="test@example.com",
    username="tester",
    password="secret123",
    role="user",
    is_active=True,
    force_password_change=False,
):
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        username=username,
        hashed_password=hash_password(password),
        role=role,
        is_active=is_active,
        force_password_change=force_password_change,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _auth_client(app, db, user):
    """Return a TestClient with a valid session cookie for the given user."""
    from fastapi.testclient import TestClient
    from app.database import get_db
    from app.dependencies import get_current_user, require_active_user, require_admin

    def override_get_db():
        yield db

    def override_get_current_user():
        return user

    def override_require_active_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[require_active_user] = override_require_active_user

    with patch("app.main.init_db"), patch("app.main._bootstrap_admin"):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------

class TestLogin:
    def test_login_success(self, db):
        from app.main import app
        from app.database import get_db
        from fastapi.testclient import TestClient

        user = _make_user(db, email="login@test.com", password="goodpass")

        def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db
        with patch("app.main.init_db"), patch("app.main._bootstrap_admin"):
            with TestClient(app) as c:
                r = c.post("/api/auth/login", json={"email": "login@test.com", "password": "goodpass"})

        app.dependency_overrides.clear()

        assert r.status_code == 200
        data = r.json()
        assert data["email"] == "login@test.com"
        assert data["role"] == "user"
        assert "force_password_change" in data
        assert "session_id" in r.cookies

    def test_login_wrong_password(self, db):
        from app.main import app
        from app.database import get_db
        from fastapi.testclient import TestClient

        _make_user(db, email="bad@test.com", password="correct")

        def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db
        with patch("app.main.init_db"), patch("app.main._bootstrap_admin"):
            with TestClient(app) as c:
                r = c.post("/api/auth/login", json={"email": "bad@test.com", "password": "wrong"})

        app.dependency_overrides.clear()
        assert r.status_code == 401

    def test_login_unknown_email(self, db):
        from app.main import app
        from app.database import get_db
        from fastapi.testclient import TestClient

        def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db
        with patch("app.main.init_db"), patch("app.main._bootstrap_admin"):
            with TestClient(app) as c:
                r = c.post("/api/auth/login", json={"email": "nobody@test.com", "password": "x"})

        app.dependency_overrides.clear()
        assert r.status_code == 401

    def test_login_disabled_user(self, db):
        from app.main import app
        from app.database import get_db
        from fastapi.testclient import TestClient

        _make_user(db, email="disabled@test.com", password="pass", is_active=False)

        def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db
        with patch("app.main.init_db"), patch("app.main._bootstrap_admin"):
            with TestClient(app) as c:
                r = c.post("/api/auth/login", json={"email": "disabled@test.com", "password": "pass"})

        app.dependency_overrides.clear()
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/auth/me
# ---------------------------------------------------------------------------

class TestMe:
    def test_me_returns_current_user(self, client, test_user):
        r = client.get("/api/auth/me")
        assert r.status_code == 200
        assert r.json()["id"] == test_user.id
        assert r.json()["email"] == test_user.email

    def test_me_unauthenticated(self, db):
        from app.main import app
        from app.database import get_db
        from fastapi.testclient import TestClient

        def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db
        with patch("app.main.init_db"), patch("app.main._bootstrap_admin"):
            with TestClient(app) as c:
                r = c.get("/api/auth/me")

        app.dependency_overrides.clear()
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/auth/logout
# ---------------------------------------------------------------------------

class TestLogout:
    def test_logout_success(self, client):
        r = client.post("/api/auth/logout")
        assert r.status_code == 200
        assert r.json()["logged_out"] is True


# ---------------------------------------------------------------------------
# POST /api/auth/change-password
# ---------------------------------------------------------------------------

class TestChangePassword:
    def test_change_password_success(self, client, test_user, db):
        r = client.post(
            "/api/auth/change-password",
            json={"current_password": "testpassword", "new_password": "newpass123"},
        )
        assert r.status_code == 200
        assert r.json()["changed"] is True

        # Verify password was actually changed
        db.refresh(test_user)
        from app.services.auth_service import verify_password
        assert verify_password("newpass123", test_user.hashed_password)
        assert test_user.force_password_change is False

    def test_change_password_wrong_current(self, client):
        r = client.post(
            "/api/auth/change-password",
            json={"current_password": "wrong_password", "new_password": "newpass123"},
        )
        assert r.status_code == 400

    def test_change_password_too_short(self, client):
        r = client.post(
            "/api/auth/change-password",
            json={"current_password": "testpassword", "new_password": "short"},
        )
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# force_password_change gate
# ---------------------------------------------------------------------------

class TestForcePasswordChangeGate:
    def test_force_change_blocks_api_access(self, db):
        """require_active_user must raise 403 when force_password_change=True."""
        from app.main import app
        from app.database import get_db
        from app.dependencies import get_current_user
        from fastapi.testclient import TestClient

        blocked_user = _make_user(
            db, email="blocked@test.com", password="x", force_password_change=True
        )

        def override_get_db():
            yield db

        def override_get_current_user():
            return blocked_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        with patch("app.main.init_db"), patch("app.main._bootstrap_admin"):
            with TestClient(app) as c:
                r = c.get("/api/buckets")

        app.dependency_overrides.clear()
        assert r.status_code == 403
        assert "Password change required" in r.json()["detail"]

    def test_force_change_allows_change_password_endpoint(self, db):
        """change-password itself must work even with force_password_change=True."""
        from app.main import app
        from app.database import get_db
        from app.dependencies import get_current_user
        from fastapi.testclient import TestClient

        user = _make_user(
            db, email="mustchange@test.com", password="oldpass", force_password_change=True
        )

        def override_get_db():
            yield db

        def override_get_current_user():
            return user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        with patch("app.main.init_db"), patch("app.main._bootstrap_admin"):
            with TestClient(app) as c:
                r = c.post(
                    "/api/auth/change-password",
                    json={"current_password": "oldpass", "new_password": "newpass123"},
                )

        app.dependency_overrides.clear()
        assert r.status_code == 200
        assert r.json()["changed"] is True


# ---------------------------------------------------------------------------
# POST /api/auth/forgot-password + reset-password
# ---------------------------------------------------------------------------

class TestPasswordReset:
    def test_forgot_password_returns_token_for_known_email(self, db):
        """Admin can generate a reset token for a known user."""
        from app.main import app
        from app.database import get_db
        from app.dependencies import get_current_user, require_active_user, require_admin
        from fastapi.testclient import TestClient

        admin = _make_user(db, email="fpadmin@test.com", username="fpadmin", password="adminpass", role="admin")
        _make_user(db, email="reset@test.com", username="resetuser", password="pass")

        def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = lambda: admin
        app.dependency_overrides[require_active_user] = lambda: admin
        app.dependency_overrides[require_admin] = lambda: admin
        with patch("app.main.init_db"), patch("app.main._bootstrap_admin"):
            with TestClient(app) as c:
                r = c.post("/api/auth/forgot-password", json={"email": "reset@test.com"})

        app.dependency_overrides.clear()
        assert r.status_code == 200
        assert "token" in r.json()

    def test_forgot_password_unknown_email_returns_404(self, db):
        """Admin gets a 404 for a user that does not exist (admin-only endpoint)."""
        from app.main import app
        from app.database import get_db
        from app.dependencies import get_current_user, require_active_user, require_admin
        from fastapi.testclient import TestClient

        admin = _make_user(db, email="fpadmin2@test.com", username="fpadmin2", password="adminpass", role="admin")

        def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = lambda: admin
        app.dependency_overrides[require_active_user] = lambda: admin
        app.dependency_overrides[require_admin] = lambda: admin
        with patch("app.main.init_db"), patch("app.main._bootstrap_admin"):
            with TestClient(app) as c:
                r = c.post("/api/auth/forgot-password", json={"email": "nobody@test.com"})

        app.dependency_overrides.clear()
        assert r.status_code == 404

    def test_forgot_password_requires_admin(self, db):
        """Unauthenticated callers receive 401."""
        from app.main import app
        from app.database import get_db
        from fastapi.testclient import TestClient

        def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db
        with patch("app.main.init_db"), patch("app.main._bootstrap_admin"):
            with TestClient(app) as c:
                r = c.post("/api/auth/forgot-password", json={"email": "anyone@test.com"})

        app.dependency_overrides.clear()
        assert r.status_code == 401

    def test_reset_password_with_valid_token(self, db):
        from app.main import app
        from app.database import get_db
        from app.services.auth_service import create_reset_token
        from fastapi.testclient import TestClient

        user = _make_user(db, email="tokenreset@test.com", password="oldpass")
        raw_token = create_reset_token(db, user.id)

        def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db
        with patch("app.main.init_db"), patch("app.main._bootstrap_admin"):
            with TestClient(app) as c:
                r = c.post(
                    "/api/auth/reset-password",
                    json={"token": raw_token, "new_password": "brandnewpass"},
                )

        app.dependency_overrides.clear()
        assert r.status_code == 200
        db.refresh(user)
        from app.services.auth_service import verify_password
        assert verify_password("brandnewpass", user.hashed_password)

    def test_reset_password_invalid_token(self, db):
        from app.main import app
        from app.database import get_db
        from fastapi.testclient import TestClient

        def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db
        with patch("app.main.init_db"), patch("app.main._bootstrap_admin"):
            with TestClient(app) as c:
                r = c.post(
                    "/api/auth/reset-password",
                    json={"token": "bogus-token", "new_password": "newpass123"},
                )

        app.dependency_overrides.clear()
        assert r.status_code == 400

    def test_reset_token_cannot_be_reused(self, db):
        from app.main import app
        from app.database import get_db
        from app.services.auth_service import create_reset_token
        from fastapi.testclient import TestClient

        user = _make_user(db, email="onetime@test.com", password="oldpass")
        raw_token = create_reset_token(db, user.id)

        def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db
        with patch("app.main.init_db"), patch("app.main._bootstrap_admin"):
            with TestClient(app) as c:
                c.post("/api/auth/reset-password", json={"token": raw_token, "new_password": "pass1234"})
                r2 = c.post("/api/auth/reset-password", json={"token": raw_token, "new_password": "pass5678"})

        app.dependency_overrides.clear()
        assert r2.status_code == 400
