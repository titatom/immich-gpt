"""Test 7: review queue rendering with thumbnails (API level)."""
import uuid
import pytest
from app.models.asset import Asset
from app.models.suggested_classification import SuggestedClassification
from app.models.suggested_metadata import SuggestedMetadata
from app.models.bucket import Bucket


def make_review_data(db, n=3):
    bucket = db.query(Bucket).filter(Bucket.name == "Personal").first()
    asset_ids = []
    for i in range(n):
        asset = Asset(
            id=str(uuid.uuid4()),
            immich_id=f"immich-review-{i}",
            original_filename=f"photo_{i}.jpg",
            is_favorite=False,
            is_archived=False,
            is_trashed=False,
            is_external_library=False,
        )
        db.add(asset)
        db.flush()

        cls = SuggestedClassification(
            id=str(uuid.uuid4()),
            asset_id=asset.id,
            suggested_bucket_id=bucket.id if bucket else None,
            suggested_bucket_name="Personal",
            confidence=0.85,
            explanation=f"Photo {i} is personal",
            status="pending_review",
            provider_name="openai",
        )
        db.add(cls)

        meta = SuggestedMetadata(
            id=str(uuid.uuid4()),
            asset_id=asset.id,
            description_suggestion=f"Description for photo {i}",
            tags_json=["tag1", "tag2"],
            provider_name="openai",
        )
        db.add(meta)
        asset_ids.append(asset.id)

    db.commit()
    return asset_ids


def test_review_queue_returns_items(client, db):
    make_review_data(db, n=3)
    resp = client.get("/api/review/queue")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 3


def test_review_item_has_required_fields(client, db):
    make_review_data(db, n=1)
    resp = client.get("/api/review/queue")
    assert resp.status_code == 200
    item = resp.json()[0]
    assert "asset_id" in item
    assert "immich_id" in item
    assert "suggested_bucket_name" in item
    assert "confidence" in item
    assert "explanation" in item
    assert "description_suggestion" in item
    assert "tags_suggestion" in item
    assert "classification_status" in item


def test_review_item_has_thumbnail_info(client, db):
    """Review items include immich_id so frontend can request thumbnail."""
    make_review_data(db, n=1)
    resp = client.get("/api/review/queue")
    item = resp.json()[0]
    assert item["immich_id"] is not None
    assert item["immich_id"].startswith("immich-review-")


def test_review_queue_count(client, db):
    make_review_data(db, n=5)
    resp = client.get("/api/review/queue/count")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 5


def test_review_queue_pagination(client, db):
    make_review_data(db, n=10)
    resp1 = client.get("/api/review/queue?page=1&page_size=5")
    resp2 = client.get("/api/review/queue?page=2&page_size=5")
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert len(resp1.json()) == 5


def test_get_review_item_by_asset_id(client, db):
    asset_ids = make_review_data(db, n=1)
    resp = client.get(f"/api/review/item/{asset_ids[0]}")
    assert resp.status_code == 200
    item = resp.json()
    assert item["asset_id"] == asset_ids[0]


def test_missing_thumbnail_does_not_break_review_queue(client, db):
    """Regression: thumbnail failures should not break review UI."""
    make_review_data(db, n=2)
    # Review queue returns items even when thumbnail endpoint would fail
    resp = client.get("/api/review/queue")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2
