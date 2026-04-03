"""
Tests for GET /api/buckets/stats endpoint.
"""
import uuid

import pytest

from app.models.bucket import Bucket
from app.models.suggested_classification import SuggestedClassification


def _make_classification(db, bucket_name, status="pending_review", bucket_id=None):
    sc = SuggestedClassification(
        id=str(uuid.uuid4()),
        asset_id=str(uuid.uuid4()),
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
    _make_classification(db, "Personal", "pending_review")
    _make_classification(db, "Personal", "approved")
    _make_classification(db, "Business", "pending_review")
    r = client.get("/api/buckets/stats")
    assert r.status_code == 200
    data = {s["bucket_name"]: s for s in r.json()}
    assert data["Personal"]["total"] == 2
    assert data["Business"]["total"] == 1


def test_bucket_stats_by_status(client, db):
    _make_classification(db, "Documents", "approved")
    _make_classification(db, "Documents", "rejected")
    _make_classification(db, "Documents", "pending_review")
    r = client.get("/api/buckets/stats")
    stat = next(s for s in r.json() if s["bucket_name"] == "Documents")
    assert stat["by_status"]["approved"] == 1
    assert stat["by_status"]["rejected"] == 1
    assert stat["by_status"]["pending_review"] == 1
    assert stat["total"] == 3
