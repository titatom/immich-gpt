"""
Cross-user data isolation tests.
Verifies that a user cannot read or mutate another user's data through any API endpoint.
"""
import uuid
import pytest
from unittest.mock import patch

from app.models.user import User
from app.models.bucket import Bucket
from app.models.asset import Asset
from app.models.job_run import JobRun
from app.models.prompt_template import PromptTemplate
from app.models.provider_config import ProviderConfig
from app.models.app_setting import AppSetting
from app.services.auth_service import hash_password

USER_A_ID = "user-a-isolation-test"
USER_B_ID = "user-b-isolation-test"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def isolation_db(db):
    """DB seeded with two separate users, each with their own data."""
    user_a = User(
        id=USER_A_ID,
        email="usera@isolation.test",
        username="usera",
        hashed_password=hash_password("pass"),
        role="user",
        is_active=True,
        force_password_change=False,
    )
    user_b = User(
        id=USER_B_ID,
        email="userb@isolation.test",
        username="userb",
        hashed_password=hash_password("pass"),
        role="user",
        is_active=True,
        force_password_change=False,
    )
    db.add(user_a)
    db.add(user_b)
    db.flush()

    # User A data
    db.add(Bucket(
        id=str(uuid.uuid4()), user_id=USER_A_ID, name="BucketA",
        enabled=True, priority=1, mapping_mode="virtual",
    ))
    db.add(Asset(
        id="asset-a-1", user_id=USER_A_ID, immich_id="immich-a-1",
        is_favorite=False, is_archived=False, is_external_library=False,
    ))
    db.add(JobRun(
        id="job-a-1", user_id=USER_A_ID, job_type="asset_sync", status="queued",
        processed_count=0, total_count=0, success_count=0, error_count=0,
        progress_percent=0.0, log_lines_json=[],
    ))
    db.add(PromptTemplate(
        id=str(uuid.uuid4()), user_id=USER_A_ID, prompt_type="global_classification",
        name="PromptA", content="User A prompt", enabled=True, version=1,
    ))
    db.add(ProviderConfig(
        id=str(uuid.uuid4()), user_id=USER_A_ID, provider_name="openai",
        enabled=True, is_default=True, api_key_encrypted="sk-a",
    ))
    db.add(AppSetting(
        id=str(uuid.uuid4()), user_id=USER_A_ID, key="immich_url", value="http://a.local",
    ))

    # User B data
    db.add(Bucket(
        id=str(uuid.uuid4()), user_id=USER_B_ID, name="BucketB",
        enabled=True, priority=1, mapping_mode="virtual",
    ))
    db.add(Asset(
        id="asset-b-1", user_id=USER_B_ID, immich_id="immich-b-1",
        is_favorite=False, is_archived=False, is_external_library=False,
    ))

    db.commit()
    return db


def _make_client_for_user(app, db, user_obj):
    """Context-manager-safe client authenticated as a specific user."""
    from app.database import get_db
    from app.dependencies import get_current_user, require_active_user

    def override_get_db():
        yield db

    def override_get_current_user():
        return user_obj

    def override_require_active_user():
        return user_obj

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[require_active_user] = override_require_active_user


# ---------------------------------------------------------------------------
# Buckets isolation
# ---------------------------------------------------------------------------

class TestBucketIsolation:
    def test_user_sees_only_own_buckets(self, isolation_db):
        from app.main import app
        from fastapi.testclient import TestClient
        user_a = isolation_db.query(User).filter(User.id == USER_A_ID).first()
        _make_client_for_user(app, isolation_db, user_a)

        with patch("app.main.init_db"):
            with TestClient(app) as c:
                r = c.get("/api/buckets")

        app.dependency_overrides.clear()
        assert r.status_code == 200
        names = [b["name"] for b in r.json()]
        assert "BucketA" in names
        assert "BucketB" not in names

    def test_user_cannot_get_other_users_bucket(self, isolation_db):
        from app.main import app
        from fastapi.testclient import TestClient
        user_b = isolation_db.query(User).filter(User.id == USER_B_ID).first()
        bucket_a = isolation_db.query(Bucket).filter(Bucket.name == "BucketA").first()
        _make_client_for_user(app, isolation_db, user_b)

        with patch("app.main.init_db"):
            with TestClient(app) as c:
                r = c.get(f"/api/buckets/{bucket_a.id}")

        app.dependency_overrides.clear()
        assert r.status_code == 404

    def test_user_cannot_update_other_users_bucket(self, isolation_db):
        from app.main import app
        from fastapi.testclient import TestClient
        user_b = isolation_db.query(User).filter(User.id == USER_B_ID).first()
        bucket_a = isolation_db.query(Bucket).filter(Bucket.name == "BucketA").first()
        _make_client_for_user(app, isolation_db, user_b)

        with patch("app.main.init_db"):
            with TestClient(app) as c:
                r = c.patch(f"/api/buckets/{bucket_a.id}", json={"description": "hacked"})

        app.dependency_overrides.clear()
        assert r.status_code == 404

    def test_user_cannot_delete_other_users_bucket(self, isolation_db):
        from app.main import app
        from fastapi.testclient import TestClient
        user_b = isolation_db.query(User).filter(User.id == USER_B_ID).first()
        bucket_a = isolation_db.query(Bucket).filter(Bucket.name == "BucketA").first()
        _make_client_for_user(app, isolation_db, user_b)

        with patch("app.main.init_db"):
            with TestClient(app) as c:
                r = c.delete(f"/api/buckets/{bucket_a.id}")

        app.dependency_overrides.clear()
        assert r.status_code == 404
        # Bucket A must still exist
        assert isolation_db.query(Bucket).filter(Bucket.id == bucket_a.id).first() is not None


# ---------------------------------------------------------------------------
# Assets isolation
# ---------------------------------------------------------------------------

class TestAssetIsolation:
    def test_user_sees_only_own_assets(self, isolation_db):
        from app.main import app
        from fastapi.testclient import TestClient
        user_a = isolation_db.query(User).filter(User.id == USER_A_ID).first()
        _make_client_for_user(app, isolation_db, user_a)

        with patch("app.main.init_db"):
            with TestClient(app) as c:
                r = c.get("/api/assets")

        app.dependency_overrides.clear()
        assert r.status_code == 200
        ids = [a["id"] for a in r.json()]
        assert "asset-a-1" in ids
        assert "asset-b-1" not in ids

    def test_user_cannot_get_other_users_asset(self, isolation_db):
        from app.main import app
        from fastapi.testclient import TestClient
        user_b = isolation_db.query(User).filter(User.id == USER_B_ID).first()
        _make_client_for_user(app, isolation_db, user_b)

        with patch("app.main.init_db"):
            with TestClient(app) as c:
                r = c.get("/api/assets/asset-a-1")

        app.dependency_overrides.clear()
        assert r.status_code == 404

    def test_asset_count_is_scoped(self, isolation_db):
        from app.main import app
        from fastapi.testclient import TestClient
        user_a = isolation_db.query(User).filter(User.id == USER_A_ID).first()
        _make_client_for_user(app, isolation_db, user_a)

        with patch("app.main.init_db"):
            with TestClient(app) as c:
                r = c.get("/api/assets/count")

        app.dependency_overrides.clear()
        assert r.status_code == 200
        assert r.json()["count"] == 1  # only user A's asset


# ---------------------------------------------------------------------------
# Jobs isolation
# ---------------------------------------------------------------------------

class TestJobIsolation:
    def test_user_sees_only_own_jobs(self, isolation_db):
        from app.main import app
        from fastapi.testclient import TestClient
        user_b = isolation_db.query(User).filter(User.id == USER_B_ID).first()
        _make_client_for_user(app, isolation_db, user_b)

        with patch("app.main.init_db"):
            with TestClient(app) as c:
                r = c.get("/api/jobs")

        app.dependency_overrides.clear()
        assert r.status_code == 200
        ids = [j["id"] for j in r.json()]
        assert "job-a-1" not in ids

    def test_user_cannot_get_other_users_job(self, isolation_db):
        from app.main import app
        from fastapi.testclient import TestClient
        user_b = isolation_db.query(User).filter(User.id == USER_B_ID).first()
        _make_client_for_user(app, isolation_db, user_b)

        with patch("app.main.init_db"):
            with TestClient(app) as c:
                r = c.get("/api/jobs/job-a-1")

        app.dependency_overrides.clear()
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Settings/provider isolation
# ---------------------------------------------------------------------------

class TestSettingsIsolation:
    def test_user_sees_only_own_providers(self, isolation_db):
        from app.main import app
        from fastapi.testclient import TestClient
        # User B has no providers
        user_b = isolation_db.query(User).filter(User.id == USER_B_ID).first()
        _make_client_for_user(app, isolation_db, user_b)

        with patch("app.main.init_db"):
            with TestClient(app) as c:
                r = c.get("/api/settings/providers")

        app.dependency_overrides.clear()
        assert r.status_code == 200
        assert r.json() == []  # user B has no providers

    def test_user_cannot_delete_other_users_provider(self, isolation_db):
        from app.main import app
        from fastapi.testclient import TestClient
        # User B tries to delete user A's openai provider
        user_b = isolation_db.query(User).filter(User.id == USER_B_ID).first()
        _make_client_for_user(app, isolation_db, user_b)

        with patch("app.main.init_db"):
            with TestClient(app) as c:
                r = c.delete("/api/settings/providers/openai")

        app.dependency_overrides.clear()
        assert r.status_code == 404
        # User A's provider must still exist
        assert isolation_db.query(ProviderConfig).filter(
            ProviderConfig.user_id == USER_A_ID,
            ProviderConfig.provider_name == "openai",
        ).first() is not None

    def test_immich_settings_are_scoped_per_user(self, isolation_db):
        from app.main import app
        from fastapi.testclient import TestClient
        # User B has no immich settings — should get "not configured"
        user_b = isolation_db.query(User).filter(User.id == USER_B_ID).first()
        _make_client_for_user(app, isolation_db, user_b)

        with patch("app.main.init_db"):
            with TestClient(app) as c:
                # Patch out env fallback too
                with patch("app.routers.settings._get_immich_credentials", return_value=("", "")):
                    r = c.get("/api/settings/immich")

        app.dependency_overrides.clear()
        assert r.status_code == 200
        assert r.json()["connected"] is False
        assert r.json()["error"] == "Not configured"
