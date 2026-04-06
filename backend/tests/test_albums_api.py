"""
Tests for /api/albums router.

Covers: list albums success (proxied from Immich), 502 on Immich error.
"""
from unittest.mock import MagicMock

import pytest

from app.services.immich_client import ImmichError
from app.dependencies import get_immich_client
from app.main import app


def _mock_immich_albums(albums=None, raise_error=None):
    mock = MagicMock()
    if raise_error:
        mock.list_albums.side_effect = raise_error
    else:
        mock.list_albums.return_value = albums or []

    def override():
        return mock

    app.dependency_overrides[get_immich_client] = override
    return mock


def _clear():
    app.dependency_overrides.pop(get_immich_client, None)


# ---------------------------------------------------------------------------
# GET /api/albums
# ---------------------------------------------------------------------------

def test_list_albums_success(client):
    fake_albums = [
        {"id": "album-1", "albumName": "Vacation", "assetCount": 10},
        {"id": "album-2", "albumName": "Family", "assetCount": 5},
    ]
    _mock_immich_albums(fake_albums)
    try:
        r = client.get("/api/albums")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 2
        assert data[0]["id"] == "album-1"
        assert data[0]["albumName"] == "Vacation"
        assert data[0]["assetCount"] == 10
    finally:
        _clear()


def test_list_albums_response_shape(client):
    fake_albums = [{"id": "x", "albumName": "Test Album", "assetCount": 3, "extra_field": "ignored"}]
    _mock_immich_albums(fake_albums)
    try:
        data = client.get("/api/albums").json()
        assert len(data) == 1
        item = data[0]
        assert set(item.keys()) == {"id", "albumName", "assetCount"}
    finally:
        _clear()


def test_list_albums_empty(client):
    _mock_immich_albums([])
    try:
        r = client.get("/api/albums")
        assert r.status_code == 200
        assert r.json() == []
    finally:
        _clear()


def test_list_albums_missing_fields(client):
    """Albums with missing optional fields should be returned with None values."""
    fake_albums = [{"id": "x"}]
    _mock_immich_albums(fake_albums)
    try:
        data = client.get("/api/albums").json()
        assert data[0]["id"] == "x"
        assert data[0]["albumName"] is None
        assert data[0]["assetCount"] == 0
    finally:
        _clear()


def test_list_albums_immich_error(client):
    _mock_immich_albums(raise_error=ImmichError("Immich unavailable", 503))
    try:
        r = client.get("/api/albums")
        assert r.status_code == 502
        assert "Immich unavailable" in r.json()["detail"]
    finally:
        _clear()


def test_list_albums_immich_auth_error(client):
    _mock_immich_albums(raise_error=ImmichError("Unauthorized", 401))
    try:
        r = client.get("/api/albums")
        assert r.status_code == 502
    finally:
        _clear()
