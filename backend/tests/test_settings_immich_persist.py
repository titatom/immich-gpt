"""
Tests for POST /api/settings/immich (persist credentials to DB).
"""
from unittest.mock import MagicMock, patch
from app.services.immich_client import ImmichError
from tests.conftest import TEST_USER_ID


def test_save_immich_settings_connected(client):
    mock_client = MagicMock()
    mock_client.check_connectivity.return_value = {"connected": True}
    mock_client.get_asset_count.return_value = 99

    with patch("app.routers.settings.ImmichClient", return_value=mock_client):
        r = client.post(
            "/api/settings/immich",
            json={"immich_url": "http://immich.local", "immich_api_key": "key123"},
        )

    assert r.status_code == 200
    data = r.json()
    assert data["connected"] is True
    assert data["asset_count"] == 99
    assert data["immich_url"] == "http://immich.local"


def test_save_immich_settings_persists_to_db(client, db):
    from app.models.app_setting import AppSetting

    mock_client = MagicMock()
    mock_client.check_connectivity.return_value = {}
    mock_client.get_asset_count.return_value = 5

    with patch("app.routers.settings.ImmichClient", return_value=mock_client):
        client.post(
            "/api/settings/immich",
            json={"immich_url": "http://saved.local", "immich_api_key": "saved-key"},
        )

    url_row = db.query(AppSetting).filter(
        AppSetting.user_id == TEST_USER_ID,
        AppSetting.key == "immich_url",
    ).first()
    assert url_row is not None
    assert url_row.value == "http://saved.local"


def test_save_immich_settings_connection_failure(client):
    mock_client = MagicMock()
    mock_client.check_connectivity.side_effect = ImmichError("bad credentials")

    with patch("app.routers.settings.ImmichClient", return_value=mock_client):
        r = client.post(
            "/api/settings/immich",
            json={"immich_url": "http://bad.host", "immich_api_key": "wrong"},
        )

    assert r.status_code == 200
    assert r.json()["connected"] is False
    assert "bad credentials" in r.json()["error"]


def test_get_immich_settings_reads_from_db(client, db):
    """After saving via POST, GET should reflect DB-persisted credentials."""
    from app.models.app_setting import AppSetting
    import uuid

    db.add(AppSetting(id=str(uuid.uuid4()), user_id=TEST_USER_ID, key="immich_url", value="http://db.local"))
    db.add(AppSetting(id=str(uuid.uuid4()), user_id=TEST_USER_ID, key="immich_api_key", value="db-key"))
    db.commit()

    mock_client = MagicMock()
    mock_client.check_connectivity.return_value = {}
    mock_client.get_asset_count.return_value = 42

    with patch("app.routers.settings.ImmichClient", return_value=mock_client):
        r = client.get("/api/settings/immich")

    assert r.status_code == 200
    assert r.json()["immich_url"] == "http://db.local"
    assert r.json()["connected"] is True
