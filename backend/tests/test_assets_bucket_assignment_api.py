import uuid

from app.models.asset import Asset
from app.models.bucket import Bucket
from app.models.suggested_classification import SuggestedClassification


def _make_asset(db, user_id: str, suffix: str = "1") -> Asset:
    asset = Asset(
        id=str(uuid.uuid4()),
        user_id=user_id,
        immich_id=f"immich-assign-{suffix}",
        original_filename=f"assign_{suffix}.jpg",
        is_favorite=False,
        is_archived=False,
        is_trashed=False,
        is_external_library=False,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def test_assign_bucket_creates_approved_classification(client, db):
    from tests.conftest import TEST_USER_ID

    asset = _make_asset(db, TEST_USER_ID)
    bucket = db.query(Bucket).filter(Bucket.name == "Personal").first()

    resp = client.post(
        "/api/assets/assign-bucket",
        json={"asset_ids": [asset.id], "bucket_id": bucket.id},
    )

    assert resp.status_code == 200
    assert resp.json()["assigned"] == 1

    classification = db.query(SuggestedClassification).filter(
        SuggestedClassification.asset_id == asset.id,
    ).first()
    assert classification.suggested_bucket_id == bucket.id
    assert classification.suggested_bucket_name == bucket.name
    assert classification.status == "approved"
    assert classification.provider_name == "manual"


def test_assign_bucket_rejects_bucket_from_other_user(client, db):
    from tests.conftest import TEST_ADMIN_ID, TEST_USER_ID

    asset = _make_asset(db, TEST_USER_ID)
    bucket = Bucket(
        id=str(uuid.uuid4()),
        user_id=TEST_ADMIN_ID,
        name="OtherUserBucket",
        enabled=True,
        priority=1,
        mapping_mode="virtual",
    )
    db.add(bucket)
    db.commit()

    resp = client.post(
        "/api/assets/assign-bucket",
        json={"asset_ids": [asset.id], "bucket_id": bucket.id},
    )

    assert resp.status_code == 404
