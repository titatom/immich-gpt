import uuid

from app.models.bucket import Bucket
from app.models.suggested_classification import SuggestedClassification
from app.services.asset_sync import AssetSyncService


class FakeImmichClient:
    def __init__(self):
        self.pages = {
            1: [
                {"id": "immich-sync-1", "originalFileName": "one.jpg", "type": "IMAGE"},
                {"id": "immich-sync-2", "originalFileName": "two.jpg", "type": "IMAGE"},
            ],
            2: [],
        }

    def list_assets(self, page=1, page_size=100, **_kwargs):
        return self.pages.get(page, [])

    def is_external_library_asset(self, _raw):
        return False


def test_sync_assigns_synced_assets_to_bucket(db):
    from tests.conftest import TEST_USER_ID

    bucket = db.query(Bucket).filter(Bucket.name == "Personal").first()
    service = AssetSyncService(db, FakeImmichClient(), user_id=TEST_USER_ID)

    result = service.sync_all(bucket_id=bucket.id)

    assert result["created"] == 2
    rows = db.query(SuggestedClassification).filter(
        SuggestedClassification.suggested_bucket_id == bucket.id,
        SuggestedClassification.provider_name == "sync",
        SuggestedClassification.status == "approved",
    ).all()
    assert len(rows) == 2


def test_sync_rejects_bucket_from_another_user(db):
    from tests.conftest import TEST_ADMIN_ID, TEST_USER_ID

    other_bucket = Bucket(
        id=str(uuid.uuid4()),
        user_id=TEST_ADMIN_ID,
        name="Admin Bucket",
        enabled=True,
        priority=1,
        mapping_mode="virtual",
    )
    db.add(other_bucket)
    db.commit()

    service = AssetSyncService(db, FakeImmichClient(), user_id=TEST_USER_ID)

    try:
        service.sync_all(bucket_id=other_bucket.id)
    except ValueError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("Expected cross-user bucket assignment to be rejected")
