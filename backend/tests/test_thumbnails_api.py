"""
Tests for /api/thumbnails router.

Covers: proxy by internal DB id, proxy by immich id, 404 for unknown assets,
502 when Immich returns an error.
"""
import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.models.asset import Asset
from app.services.immich_client import ImmichError
from tests.conftest import TEST_USER_ID


FAKE_IMAGE_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 100  # minimal JPEG-like bytes


def _make_asset(db) -> Asset:
    a = Asset(
        id=str(uuid.uuid4()),
        user_id=TEST_USER_ID,
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


def test_get_thumbnail_by_db_id(client, db):
    asset = _make_asset(db)
    mock_client = MagicMock()
    mock_client.get_thumbnail.return_value = FAKE_IMAGE_BYTES

    with patch("app.routers.thumbnails._get_user_immich_client", return_value=mock_client):
        r = client.get(f"/api/thumbnails/{asset.id}")

    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/jpeg")
    assert r.content == FAKE_IMAGE_BYTES
    mock_client.get_thumbnail.assert_called_once_with(asset.immich_id, size="thumbnail")


def test_get_thumbnail_by_immich_id_fallback(client, db):
    asset = _make_asset(db)
    mock_client = MagicMock()
    mock_client.get_thumbnail.return_value = FAKE_IMAGE_BYTES

    with patch("app.routers.thumbnails._get_user_immich_client", return_value=mock_client):
        r = client.get(f"/api/thumbnails/{asset.immich_id}")

    assert r.status_code == 200


def test_get_thumbnail_asset_not_found(client):
    r = client.get("/api/thumbnails/nonexistent-id")
    assert r.status_code == 404


def test_get_thumbnail_immich_error(client, db):
    asset = _make_asset(db)
    mock_client = MagicMock()
    mock_client.get_thumbnail.side_effect = ImmichError("upstream unavailable", 503)

    with patch("app.routers.thumbnails._get_user_immich_client", return_value=mock_client):
        r = client.get(f"/api/thumbnails/{asset.id}")

    assert r.status_code == 502
    assert "upstream unavailable" in r.json()["detail"]


def test_get_thumbnail_cache_header(client, db):
    asset = _make_asset(db)
    mock_client = MagicMock()
    mock_client.get_thumbnail.return_value = FAKE_IMAGE_BYTES

    with patch("app.routers.thumbnails._get_user_immich_client", return_value=mock_client):
        r = client.get(f"/api/thumbnails/{asset.id}")

    assert "Cache-Control" in r.headers
    assert "max-age=3600" in r.headers["Cache-Control"]


def test_get_thumbnail_size_param_forwarded(client, db):
    asset = _make_asset(db)
    mock_client = MagicMock()
    mock_client.get_thumbnail.return_value = FAKE_IMAGE_BYTES

    with patch("app.routers.thumbnails._get_user_immich_client", return_value=mock_client):
        client.get(f"/api/thumbnails/{asset.id}?size=preview")

    mock_client.get_thumbnail.assert_called_once_with(asset.immich_id, size="preview")


def test_get_thumbnail_by_immich_id_direct(client):
    immich_id = str(uuid.uuid4())
    mock_client = MagicMock()
    mock_client.get_thumbnail.return_value = FAKE_IMAGE_BYTES

    with patch("app.routers.thumbnails._get_user_immich_client", return_value=mock_client):
        r = client.get(f"/api/thumbnails/immich/{immich_id}")

    assert r.status_code == 200
    mock_client.get_thumbnail.assert_called_once_with(immich_id, size="thumbnail")


def test_get_thumbnail_by_immich_id_direct_error(client):
    mock_client = MagicMock()
    mock_client.get_thumbnail.side_effect = ImmichError("not found", 404)

    with patch("app.routers.thumbnails._get_user_immich_client", return_value=mock_client):
        r = client.get("/api/thumbnails/immich/bad-id")

    assert r.status_code == 502
