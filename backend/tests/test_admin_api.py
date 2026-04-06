"""
Tests for /api/admin/users endpoints.
Covers: list, create, update, reset-password, delete.
Admin-only: non-admin users must get 403.
"""
import uuid
import pytest
from unittest.mock import patch

from app.models.user import User
from app.services.auth_service import hash_password


def _make_extra_user(db, email="extra@test.com", username="extra", role="user"):
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        username=username,
        hashed_password=hash_password("pass"),
        role=role,
        is_active=True,
        force_password_change=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------

class TestAdminAccessControl:
    def test_non_admin_cannot_list_users(self, client):
        r = client.get("/api/admin/users")
        assert r.status_code == 403

    def test_non_admin_cannot_create_user(self, client):
        r = client.post("/api/admin/users", json={
            "email": "x@x.com", "username": "x", "password": "pass1234",
            "role": "user", "force_password_change": True,
        })
        assert r.status_code == 403

    def test_non_admin_cannot_delete_user(self, client, db, test_user):
        r = client.delete(f"/api/admin/users/{test_user.id}")
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# GET /api/admin/users
# ---------------------------------------------------------------------------

class TestAdminListUsers:
    def test_admin_can_list_users(self, admin_client, db):
        r = admin_client.get("/api/admin/users")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_users_does_not_expose_password(self, admin_client, db):
        r = admin_client.get("/api/admin/users")
        for user in r.json():
            assert "hashed_password" not in user
            assert "password" not in user

    def test_list_users_response_shape(self, admin_client, db):
        r = admin_client.get("/api/admin/users")
        assert r.status_code == 200
        for u in r.json():
            for field in ("id", "email", "username", "role", "is_active",
                          "force_password_change", "created_at"):
                assert field in u


# ---------------------------------------------------------------------------
# POST /api/admin/users
# ---------------------------------------------------------------------------

class TestAdminCreateUser:
    def test_create_user_success(self, admin_client):
        payload = {
            "email": "newuser@test.com",
            "username": "newuser",
            "password": "goodpass1",
            "role": "user",
            "force_password_change": True,
        }
        r = admin_client.post("/api/admin/users", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == "newuser@test.com"
        assert data["username"] == "newuser"
        assert data["role"] == "user"
        assert data["force_password_change"] is True
        assert "hashed_password" not in data

    def test_create_user_short_password_rejected(self, admin_client):
        r = admin_client.post("/api/admin/users", json={
            "email": "short@test.com", "username": "short",
            "password": "abc", "role": "user", "force_password_change": False,
        })
        assert r.status_code == 400

    def test_create_user_duplicate_email_rejected(self, admin_client, db):
        _make_extra_user(db, email="dup@test.com", username="dup1")
        r = admin_client.post("/api/admin/users", json={
            "email": "dup@test.com", "username": "dup2",
            "password": "goodpass1", "role": "user", "force_password_change": False,
        })
        assert r.status_code == 409

    def test_create_user_seeds_defaults(self, admin_client, db):
        """Creating a regular user should seed their default buckets."""
        from app.models.bucket import Bucket
        r = admin_client.post("/api/admin/users", json={
            "email": "seeded@test.com", "username": "seeded",
            "password": "goodpass1", "role": "user", "force_password_change": False,
        })
        assert r.status_code == 200
        user_id = r.json()["id"]
        buckets = db.query(Bucket).filter(Bucket.user_id == user_id).all()
        assert len(buckets) >= 4
        bucket_names = {b.name for b in buckets}
        assert "Business" in bucket_names
        assert "Personal" in bucket_names

    def test_create_admin_seeds_defaults(self, admin_client, db):
        """Creating an admin user should also seed their default buckets and prompts."""
        from app.models.bucket import Bucket
        from app.models.prompt_template import PromptTemplate
        r = admin_client.post("/api/admin/users", json={
            "email": "adminseeded@test.com", "username": "adminseeded",
            "password": "goodpass1", "role": "admin", "force_password_change": False,
        })
        assert r.status_code == 200
        user_id = r.json()["id"]
        buckets = db.query(Bucket).filter(Bucket.user_id == user_id).all()
        assert len(buckets) >= 4
        bucket_names = {b.name for b in buckets}
        assert "Business" in bucket_names
        assert "Personal" in bucket_names
        prompts = db.query(PromptTemplate).filter(PromptTemplate.user_id == user_id).all()
        assert len(prompts) >= 4
        prompt_types = {p.prompt_type for p in prompts}
        assert "global_classification" in prompt_types
        assert "review_guidance" in prompt_types


# ---------------------------------------------------------------------------
# PATCH /api/admin/users/{user_id}
# ---------------------------------------------------------------------------

class TestAdminUpdateUser:
    def test_disable_user(self, admin_client, db):
        user = _make_extra_user(db, email="dis@test.com", username="dis")
        r = admin_client.patch(f"/api/admin/users/{user.id}", json={"is_active": False})
        assert r.status_code == 200
        assert r.json()["is_active"] is False

    def test_enable_user(self, admin_client, db):
        user = _make_extra_user(db, email="en@test.com", username="en")
        user.is_active = False
        db.commit()
        r = admin_client.patch(f"/api/admin/users/{user.id}", json={"is_active": True})
        assert r.status_code == 200
        assert r.json()["is_active"] is True

    def test_set_force_password_change(self, admin_client, db):
        user = _make_extra_user(db, email="fpc@test.com", username="fpc")
        r = admin_client.patch(f"/api/admin/users/{user.id}", json={"force_password_change": True})
        assert r.status_code == 200
        assert r.json()["force_password_change"] is True

    def test_update_nonexistent_user(self, admin_client):
        r = admin_client.patch(f"/api/admin/users/{uuid.uuid4()}", json={"is_active": False})
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/admin/users/{user_id}/reset-password
# ---------------------------------------------------------------------------

class TestAdminResetPassword:
    def test_reset_generates_token(self, admin_client, db):
        user = _make_extra_user(db, email="tok@test.com", username="tok")
        r = admin_client.post(f"/api/admin/users/{user.id}/reset-password", json={})
        assert r.status_code == 200
        assert "token" in r.json()

    def test_reset_with_new_password_sets_force_change(self, admin_client, db):
        user = _make_extra_user(db, email="pw@test.com", username="pw")
        r = admin_client.post(
            f"/api/admin/users/{user.id}/reset-password",
            json={"new_password": "freshpass1"},
        )
        assert r.status_code == 200
        assert r.json()["force_password_change"] is True


# ---------------------------------------------------------------------------
# DELETE /api/admin/users/{user_id}
# ---------------------------------------------------------------------------

class TestAdminDeleteUser:
    def test_delete_user_success(self, admin_client, db):
        user = _make_extra_user(db, email="del@test.com", username="del")
        r = admin_client.delete(f"/api/admin/users/{user.id}")
        assert r.status_code == 200
        assert r.json()["deleted"] is True
        assert db.query(User).filter(User.id == user.id).first() is None

    def test_delete_nonexistent_user(self, admin_client):
        r = admin_client.delete(f"/api/admin/users/{uuid.uuid4()}")
        assert r.status_code == 404

    def test_delete_user_removes_owned_data(self, admin_client, db):
        """Hard-deleting a user must also remove their buckets."""
        from app.models.bucket import Bucket
        # Create user and verify they have buckets
        r = admin_client.post("/api/admin/users", json={
            "email": "todelete@test.com", "username": "todelete",
            "password": "goodpass1", "role": "user", "force_password_change": False,
        })
        assert r.status_code == 200
        user_id = r.json()["id"]
        assert db.query(Bucket).filter(Bucket.user_id == user_id).count() > 0

        # Delete and verify buckets gone
        admin_client.delete(f"/api/admin/users/{user_id}")
        assert db.query(Bucket).filter(Bucket.user_id == user_id).count() == 0
