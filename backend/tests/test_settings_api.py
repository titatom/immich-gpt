"""
Tests for /api/settings router.

Covers: Immich settings read/test, provider CRUD and test endpoint.
All external HTTP calls are patched.
"""
import uuid
from unittest.mock import patch, MagicMock

import pytest

from app.models.provider_config import ProviderConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_provider(db, name="openai", enabled=True, is_default=False) -> ProviderConfig:
    from tests.conftest import TEST_USER_ID
    p = ProviderConfig(
        id=str(uuid.uuid4()),
        user_id=TEST_USER_ID,
        provider_name=name,
        enabled=enabled,
        is_default=is_default,
        api_key_encrypted="sk-test",
        model_name="gpt-4o",
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


# ---------------------------------------------------------------------------
# GET /api/settings/immich
# ---------------------------------------------------------------------------

def test_get_immich_settings_not_configured(client):
    # No DB row and empty env vars → not configured
    with patch("app.routers.settings._get_immich_credentials", return_value=("", "")):
        r = client.get("/api/settings/immich")
    assert r.status_code == 200
    data = r.json()
    assert data["connected"] is False
    assert data["error"] == "Not configured"


def test_get_immich_settings_connected(client, db):
    from app.models.app_setting import AppSetting
    from tests.conftest import TEST_USER_ID
    db.add(AppSetting(id="1", user_id=TEST_USER_ID, key="immich_url", value="http://immich.local"))
    db.add(AppSetting(id="2", user_id=TEST_USER_ID, key="immich_api_key", value="key"))
    db.commit()

    mock_client = MagicMock()
    mock_client.check_connectivity.return_value = {"connected": True, "info": {}}
    mock_client.get_asset_count.return_value = 42

    with patch("app.routers.settings.ImmichClient", return_value=mock_client):
        r = client.get("/api/settings/immich")

    assert r.status_code == 200
    data = r.json()
    assert data["connected"] is True
    assert data["asset_count"] == 42


def test_get_immich_settings_error(client, db):
    from app.services.immich_client import ImmichError
    from app.models.app_setting import AppSetting
    from tests.conftest import TEST_USER_ID
    db.add(AppSetting(id="3", user_id=TEST_USER_ID, key="immich_url", value="http://immich.local"))
    db.add(AppSetting(id="4", user_id=TEST_USER_ID, key="immich_api_key", value="key"))
    db.commit()

    mock_client = MagicMock()
    mock_client.check_connectivity.side_effect = ImmichError("timeout")

    with patch("app.routers.settings.ImmichClient", return_value=mock_client):
        r = client.get("/api/settings/immich")

    assert r.status_code == 200
    data = r.json()
    assert data["connected"] is False
    assert "timeout" in data["error"]


# ---------------------------------------------------------------------------
# POST /api/settings/immich/test
# ---------------------------------------------------------------------------

def test_test_immich_connection_ok(client):
    mock_client = MagicMock()
    mock_client.check_connectivity.return_value = {"connected": True, "info": {"version": "1.0"}}
    mock_client.get_asset_count.return_value = 10

    with patch("app.routers.settings.ImmichClient", return_value=mock_client):
        r = client.post(
            "/api/settings/immich/test",
            json={"immich_url": "http://immich.local", "immich_api_key": "key"},
        )

    assert r.status_code == 200
    data = r.json()
    assert data["connected"] is True
    assert data["asset_count"] == 10


def test_test_immich_connection_failure(client):
    from app.services.immich_client import ImmichError

    mock_client = MagicMock()
    mock_client.check_connectivity.side_effect = ImmichError("bad credentials")

    with patch("app.routers.settings.ImmichClient", return_value=mock_client):
        r = client.post(
            "/api/settings/immich/test",
            json={"immich_url": "http://immich.local", "immich_api_key": "wrong"},
        )

    assert r.status_code == 400
    assert "bad credentials" in r.json()["detail"]


# ---------------------------------------------------------------------------
# GET /api/settings/providers
# ---------------------------------------------------------------------------

def test_list_providers_empty(client):
    r = client.get("/api/settings/providers")
    assert r.status_code == 200
    assert r.json() == []


def test_list_providers(client, db):
    _make_provider(db, "openai")
    _make_provider(db, "ollama")
    r = client.get("/api/settings/providers")
    assert r.status_code == 200
    assert len(r.json()) == 2


# ---------------------------------------------------------------------------
# POST /api/settings/providers  (upsert)
# ---------------------------------------------------------------------------

def test_create_provider(client):
    payload = {
        "provider_name": "openai",
        "enabled": True,
        "is_default": True,
        "api_key": "sk-abc",
        "model_name": "gpt-4o",
    }
    r = client.post("/api/settings/providers", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["provider_name"] == "openai"
    assert data["enabled"] is True
    assert data["has_api_key"] is True


def test_upsert_provider_updates_existing(client, db):
    _make_provider(db, "openai", enabled=False)
    payload = {
        "provider_name": "openai",
        "enabled": True,
        "is_default": False,
    }
    r = client.post("/api/settings/providers", json=payload)
    assert r.status_code == 200
    assert r.json()["enabled"] is True


def test_create_provider_sets_default_clears_others(client, db):
    _make_provider(db, "openai", is_default=True)
    payload = {
        "provider_name": "ollama",
        "enabled": True,
        "is_default": True,
    }
    r = client.post("/api/settings/providers", json=payload)
    assert r.status_code == 200
    # The new one should be default
    assert r.json()["is_default"] is True
    # The old default should be cleared
    openai_r = client.get("/api/settings/providers")
    providers = {p["provider_name"]: p for p in openai_r.json()}
    assert providers["openai"]["is_default"] is False


# ---------------------------------------------------------------------------
# DELETE /api/settings/providers/{provider_name}
# ---------------------------------------------------------------------------

def test_delete_provider(client, db):
    _make_provider(db, "openai")
    r = client.delete("/api/settings/providers/openai")
    assert r.status_code == 200
    assert r.json()["deleted"] is True


def test_delete_provider_not_found(client):
    r = client.delete("/api/settings/providers/nonexistent")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/settings/providers/{provider_name}/test
# ---------------------------------------------------------------------------

def test_test_provider_not_found(client):
    r = client.get("/api/settings/providers/nonexistent/test")
    assert r.status_code == 404


def test_test_provider_ok(client, db):
    _make_provider(db, "openai")
    mock_provider = MagicMock()
    mock_provider.health_check.return_value = True

    with patch("app.services.ai_provider.build_provider", return_value=mock_provider):
        r = client.get("/api/settings/providers/openai/test")

    assert r.status_code == 200
    assert r.json()["connected"] is True


def test_test_provider_failure(client, db):
    _make_provider(db, "openai")
    with patch("app.services.ai_provider.build_provider", side_effect=Exception("bad key")):
        r = client.get("/api/settings/providers/openai/test")

    assert r.status_code == 400
    assert "bad key" in r.json()["detail"]
