"""
Tests for GET /api/buckets/stats endpoint.
"""
import uuid

import pytest

from app.models.asset import Asset
from app.models.bucket import Bucket
from app.models.suggested_classification import SuggestedClassification
from tests.conftest import TEST_USER_ID


def _make_asset_with_classification(db, bucket_name, status="pending_review", bucket_id=None):
    asset = Asset(
        id=str(uuid.uuid4()),
        user_id=TEST_USER_ID,
        immich_id=str(uuid.uuid4()),
        original_filename="photo.jpg",
        is_favorite=False,
        is_archived=False,
        is_external_library=False,
    )
    db.add(asset)
    db.flush()

    sc = SuggestedClassification(
        id=str(uuid.uuid4()),
        asset_id=asset.id,
        suggested_bucket_name=bucket_name,
        suggested_bucket_id=bucket_id,
        confidence=0.9,
        explanation="test",
        status=status,
        provider_name="openai",
        review_recommended=True,
    )
    db.add(sc)
    db.commit()
    return sc


def test_bucket_stats_empty(client):
    r = client.get("/api/buckets/stats")
    assert r.status_code == 200
    assert r.json() == []


def test_bucket_stats_counts(client, db):
    _make_asset_with_classification(db, "Personal", "pending_review")
    _make_asset_with_classification(db, "Personal", "approved")
    _make_asset_with_classification(db, "Business", "pending_review")
    r = client.get("/api/buckets/stats")
    assert r.status_code == 200
    data = {s["bucket_name"]: s for s in r.json()}
    assert data["Personal"]["total"] == 2
    assert data["Business"]["total"] == 1


def test_bucket_stats_by_status(client, db):
    _make_asset_with_classification(db, "Documents", "approved")
    _make_asset_with_classification(db, "Documents", "rejected")
    _make_asset_with_classification(db, "Documents", "pending_review")
    r = client.get("/api/buckets/stats")
    stat = next(s for s in r.json() if s["bucket_name"] == "Documents")
    assert stat["by_status"]["approved"] == 1
    assert stat["by_status"]["rejected"] == 1
    assert stat["by_status"]["pending_review"] == 1
    assert stat["total"] == 3
