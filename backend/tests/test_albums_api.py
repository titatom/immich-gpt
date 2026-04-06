"""
Tests for /api/albums router.

Covers: list albums success (proxied from Immich), 502 on Immich error.
"""
from unittest.mock import MagicMock, patch

import pytest

from app.services.immich_client import ImmichError


def _mock_immich_albums(albums=None, raise_error=None):
    mock = MagicMock()
    if raise_error:
        mock.list_albums.side_effect = raise_error
    else:
        mock.list_albums.return_value = albums or []
    return mock


def test_list_albums_success(client):
    fake_albums = [
        {"id": "album-1", "albumName": "Vacation", "assetCount": 10},
        {"id": "album-2", "albumName": "Family", "assetCount": 5},
    ]
    mock = _mock_immich_albums(fake_albums)
    with patch("app.routers.albums._get_user_immich_client", return_value=mock):
        r = client.get("/api/albums")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert data[0]["id"] == "album-1"
    assert data[0]["albumName"] == "Vacation"
    assert data[0]["assetCount"] == 10


def test_list_albums_response_shape(client):
    fake_albums = [{"id": "x", "albumName": "Test Album", "assetCount": 3, "extra_field": "ignored"}]
    mock = _mock_immich_albums(fake_albums)
    with patch("app.routers.albums._get_user_immich_client", return_value=mock):
        data = client.get("/api/albums").json()
    assert len(data) == 1
    item = data[0]
    assert set(item.keys()) == {"id", "albumName", "assetCount"}


def test_list_albums_empty(client):
    mock = _mock_immich_albums([])
    with patch("app.routers.albums._get_user_immich_client", return_value=mock):
        r = client.get("/api/albums")
    assert r.status_code == 200
    assert r.json() == []


def test_list_albums_missing_fields(client):
    """Albums with missing optional fields should be returned with None values."""
    fake_albums = [{"id": "x"}]
    mock = _mock_immich_albums(fake_albums)
    with patch("app.routers.albums._get_user_immich_client", return_value=mock):
        data = client.get("/api/albums").json()
    assert data[0]["id"] == "x"
    assert data[0]["albumName"] is None
    assert data[0]["assetCount"] == 0


def test_list_albums_immich_error(client):
    mock = _mock_immich_albums(raise_error=ImmichError("Immich unavailable", 503))
    with patch("app.routers.albums._get_user_immich_client", return_value=mock):
        r = client.get("/api/albums")
    assert r.status_code == 502
    assert "Immich unavailable" in r.json()["detail"]


def test_list_albums_immich_auth_error(client):
    mock = _mock_immich_albums(raise_error=ImmichError("Unauthorized", 401))
    with patch("app.routers.albums._get_user_immich_client", return_value=mock):
        r = client.get("/api/albums")
    assert r.status_code == 502
