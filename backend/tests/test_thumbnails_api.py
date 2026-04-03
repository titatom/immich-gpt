"""
Tests for /api/thumbnails router.

Covers: proxy by internal DB id, proxy by immich id, 404 for unknown assets,
502 when Immich returns an error.
"""
import uuid
from unittest.mock import MagicMock

import pytest

from app.models.asset import Asset
from app.services.immich_client import ImmichError
from app.dependencies import get_immich_client
from app.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_IMAGE_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 100  # minimal JPEG-like bytes


def _make_asset(db) -> Asset:
    a = Asset(
        id=str(uuid.uuid4()),
        immich_id=str(uuid.uuid4()),
        original_filename="photo.jpg",
        asset_type="IMAGE",
        mime_type="image/jpeg",
        is_favorite=False,
        is_archived=False,
        is_external_library=False,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def _mock_immich(client_fixture, return_bytes=None, raise_error=None):
    """Override the get_immich_client dependency with a MagicMock."""
    mock = MagicMock()
    if raise_error:
        mock.get_thumbnail.side_effect = raise_error
    else:
        mock.get_thumbnail.return_value = return_bytes or FAKE_IMAGE_BYTES

    def override():
        return mock

    app.dependency_overrides[get_immich_client] = override
    return mock


def _clear_immich_override():
    app.dependency_overrides.pop(get_immich_client, None)


# ---------------------------------------------------------------------------
# GET /api/thumbnails/{asset_id}  — proxy by internal DB id
# ---------------------------------------------------------------------------

def test_get_thumbnail_by_db_id(client, db):
    asset = _make_asset(db)
    mock = _mock_immich(client)
    try:
        r = client.get(f"/api/thumbnails/{asset.id}")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("image/jpeg")
        assert r.content == FAKE_IMAGE_BYTES
        mock.get_thumbnail.assert_called_once_with(asset.immich_id, size="thumbnail")
    finally:
        _clear_immich_override()


def test_get_thumbnail_by_immich_id_fallback(client, db):
    asset = _make_asset(db)
    _mock_immich(client)
    try:
        r = client.get(f"/api/thumbnails/{asset.immich_id}")
        assert r.status_code == 200
    finally:
        _clear_immich_override()


def test_get_thumbnail_asset_not_found(client):
    r = client.get("/api/thumbnails/nonexistent-id")
    assert r.status_code == 404


def test_get_thumbnail_immich_error(client, db):
    asset = _make_asset(db)
    _mock_immich(client, raise_error=ImmichError("upstream unavailable", 503))
    try:
        r = client.get(f"/api/thumbnails/{asset.id}")
        assert r.status_code == 502
        assert "upstream unavailable" in r.json()["detail"]
    finally:
        _clear_immich_override()


def test_get_thumbnail_cache_header(client, db):
    asset = _make_asset(db)
    _mock_immich(client)
    try:
        r = client.get(f"/api/thumbnails/{asset.id}")
        assert "Cache-Control" in r.headers
        assert "max-age=3600" in r.headers["Cache-Control"]
    finally:
        _clear_immich_override()


def test_get_thumbnail_size_param_forwarded(client, db):
    asset = _make_asset(db)
    mock = _mock_immich(client)
    try:
        client.get(f"/api/thumbnails/{asset.id}?size=preview")
        mock.get_thumbnail.assert_called_once_with(asset.immich_id, size="preview")
    finally:
        _clear_immich_override()


# ---------------------------------------------------------------------------
# GET /api/thumbnails/immich/{immich_id}  — proxy directly by Immich id
# ---------------------------------------------------------------------------

def test_get_thumbnail_by_immich_id_direct(client):
    immich_id = str(uuid.uuid4())
    mock = _mock_immich(client)
    try:
        r = client.get(f"/api/thumbnails/immich/{immich_id}")
        assert r.status_code == 200
        mock.get_thumbnail.assert_called_once_with(immich_id, size="thumbnail")
    finally:
        _clear_immich_override()


def test_get_thumbnail_by_immich_id_direct_error(client):
    _mock_immich(client, raise_error=ImmichError("not found", 404))
    try:
        r = client.get("/api/thumbnails/immich/bad-id")
        assert r.status_code == 502
    finally:
        _clear_immich_override()
