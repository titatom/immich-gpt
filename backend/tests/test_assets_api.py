"""
Tests for /api/assets router.

Covers: list (pagination, filtering), count, get by id / not found.
"""
import uuid
from datetime import datetime

import pytest

from app.models.asset import Asset


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_asset(db, immich_id=None, asset_type="IMAGE") -> Asset:
    a = Asset(
        id=str(uuid.uuid4()),
        immich_id=immich_id or str(uuid.uuid4()),
        original_filename="photo.jpg",
        file_created_at=datetime(2024, 1, 1),
        asset_type=asset_type,
        mime_type="image/jpeg",
        is_favorite=False,
        is_archived=False,
        is_external_library=False,
        tags_json=[],
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


# ---------------------------------------------------------------------------
# GET /api/assets
# ---------------------------------------------------------------------------

def test_list_assets_empty(client):
    r = client.get("/api/assets")
    assert r.status_code == 200
    assert r.json() == []


def test_list_assets_returns_items(client, db):
    _make_asset(db)
    _make_asset(db)
    r = client.get("/api/assets")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_list_assets_pagination(client, db):
    for _ in range(5):
        _make_asset(db)
    r = client.get("/api/assets?page=1&page_size=2")
    assert r.status_code == 200
    assert len(r.json()) == 2
    r2 = client.get("/api/assets?page=2&page_size=2")
    assert r2.status_code == 200
    assert len(r2.json()) == 2
    r3 = client.get("/api/assets?page=3&page_size=2")
    assert r3.status_code == 200
    assert len(r3.json()) == 1


def test_list_assets_filter_by_type(client, db):
    _make_asset(db, asset_type="IMAGE")
    _make_asset(db, asset_type="VIDEO")
    r = client.get("/api/assets?asset_type=IMAGE")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["asset_type"] == "IMAGE"


def test_list_assets_response_shape(client, db):
    a = _make_asset(db)
    data = client.get("/api/assets").json()[0]
    for field in ("id", "immich_id", "original_filename", "asset_type",
                  "is_favorite", "is_archived", "created_at"):
        assert field in data
    assert data["immich_id"] == a.immich_id


# ---------------------------------------------------------------------------
# GET /api/assets/count
# ---------------------------------------------------------------------------

def test_count_assets_zero(client):
    r = client.get("/api/assets/count")
    assert r.status_code == 200
    assert r.json()["count"] == 0


def test_count_assets(client, db):
    _make_asset(db)
    _make_asset(db)
    r = client.get("/api/assets/count")
    assert r.status_code == 200
    assert r.json()["count"] == 2


# ---------------------------------------------------------------------------
# GET /api/assets/{asset_id}
# ---------------------------------------------------------------------------

def test_get_asset(client, db):
    a = _make_asset(db)
    r = client.get(f"/api/assets/{a.id}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == a.id
    assert data["immich_id"] == a.immich_id


def test_get_asset_not_found(client):
    r = client.get("/api/assets/nonexistent-id")
    assert r.status_code == 404


def test_get_asset_optional_fields(client, db):
    a = _make_asset(db)
    a.city = "Berlin"
    a.country = "Germany"
    a.camera_make = "Canon"
    a.description = "A test photo"
    a.tags_json = ["nature", "landscape"]
    db.commit()

    data = client.get(f"/api/assets/{a.id}").json()
    assert data["city"] == "Berlin"
    assert data["country"] == "Germany"
    assert data["camera_make"] == "Canon"
    assert data["description"] == "A test photo"
    assert data["tags"] == ["nature", "landscape"]
