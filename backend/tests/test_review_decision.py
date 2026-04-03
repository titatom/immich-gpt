"""
Tests 9, 10: tag and description write-back flows.
Failures on write-back limitations or permission issues.
"""
import uuid
import pytest
from unittest.mock import MagicMock, patch
from app.services.review_decision import ReviewDecisionService
from app.services.immich_client import ImmichError
from app.models.asset import Asset
from app.models.suggested_classification import SuggestedClassification
from app.models.suggested_metadata import SuggestedMetadata
from app.models.bucket import Bucket


def make_full_suggestion(db):
    """Create asset + classification + metadata suggestion."""
    asset = Asset(
        id=str(uuid.uuid4()),
        immich_id="immich-test-001",
        original_filename="test.jpg",
        is_favorite=False,
        is_archived=False,
        is_trashed=False,
        is_external_library=False,
    )
    db.add(asset)

    bucket = db.query(Bucket).filter(Bucket.name == "Personal").first()

    cls = SuggestedClassification(
        id=str(uuid.uuid4()),
        asset_id=asset.id,
        suggested_bucket_id=bucket.id if bucket else None,
        suggested_bucket_name="Personal",
        confidence=0.88,
        explanation="Family event",
        status="pending_review",
        provider_name="openai",
    )
    db.add(cls)

    meta = SuggestedMetadata(
        id=str(uuid.uuid4()),
        asset_id=asset.id,
        description_suggestion="Birthday party photo",
        tags_json=["birthday", "party", "family"],
        provider_name="openai",
    )
    db.add(meta)
    db.commit()
    return asset, cls, meta


def test_approve_writes_description(db):
    asset, cls, meta = make_full_suggestion(db)

    mock_immich = MagicMock()
    mock_immich.update_asset_description.return_value = {"id": asset.immich_id}
    mock_immich.get_or_create_tag.return_value = {"id": "tag-1", "name": "birthday"}
    mock_immich.tag_asset.return_value = None

    svc = ReviewDecisionService(db, immich_client=mock_immich)
    result = svc.approve_asset(
        asset_id=asset.id,
        approved_bucket_id=cls.suggested_bucket_id,
        approved_bucket_name="Personal",
        approved_description="Birthday party photo",
        approved_tags=["birthday", "party"],
        approved_subalbum=None,
        subalbum_approved=False,
        trigger_writeback=True,
    )

    mock_immich.update_asset_description.assert_called_once_with(
        asset.immich_id, "Birthday party photo"
    )
    assert result.description_written is True


def test_approve_writes_tags(db):
    asset, cls, meta = make_full_suggestion(db)

    mock_immich = MagicMock()
    mock_immich.update_asset_description.return_value = {}
    mock_immich.get_or_create_tag.side_effect = lambda name: {"id": f"tid-{name}", "name": name}
    mock_immich.tag_asset.return_value = None

    svc = ReviewDecisionService(db, immich_client=mock_immich)
    result = svc.approve_asset(
        asset_id=asset.id,
        approved_bucket_id=cls.suggested_bucket_id,
        approved_bucket_name="Personal",
        approved_description=None,
        approved_tags=["birthday", "family"],
        approved_subalbum=None,
        subalbum_approved=False,
        trigger_writeback=True,
    )

    mock_immich.tag_asset.assert_called_once()
    assert result.tags_written is True


def test_approve_without_writeback_does_not_call_immich(db):
    asset, cls, meta = make_full_suggestion(db)

    mock_immich = MagicMock()
    svc = ReviewDecisionService(db, immich_client=mock_immich)
    result = svc.approve_asset(
        asset_id=asset.id,
        approved_bucket_id=cls.suggested_bucket_id,
        approved_bucket_name="Personal",
        approved_description="Test",
        approved_tags=["test"],
        approved_subalbum=None,
        subalbum_approved=False,
        trigger_writeback=False,
    )

    mock_immich.update_asset_description.assert_not_called()
    mock_immich.tag_asset.assert_not_called()


def test_description_write_failure_reported(db):
    """Test 10: failures surfaced clearly, not silently swallowed."""
    asset, cls, meta = make_full_suggestion(db)

    mock_immich = MagicMock()
    mock_immich.update_asset_description.side_effect = ImmichError(
        "Permission denied - external library", 403
    )

    svc = ReviewDecisionService(db, immich_client=mock_immich)
    result = svc.approve_asset(
        asset_id=asset.id,
        approved_bucket_id=cls.suggested_bucket_id,
        approved_bucket_name="Personal",
        approved_description="Something",
        approved_tags=None,
        approved_subalbum=None,
        subalbum_approved=False,
        trigger_writeback=True,
    )

    assert result.description_written is False
    assert len(result.errors) > 0
    assert any("Permission denied" in e or "external library" in e.lower() for e in result.errors)


def test_tag_write_failure_reported(db):
    asset, cls, meta = make_full_suggestion(db)

    mock_immich = MagicMock()
    mock_immich.update_asset_description.return_value = {}
    mock_immich.get_or_create_tag.side_effect = ImmichError("Tag API error", 500)

    svc = ReviewDecisionService(db, immich_client=mock_immich)
    result = svc.approve_asset(
        asset_id=asset.id,
        approved_bucket_id=None,
        approved_bucket_name=None,
        approved_description=None,
        approved_tags=["broken-tag"],
        approved_subalbum=None,
        subalbum_approved=False,
        trigger_writeback=True,
    )

    assert result.tags_written is False
    assert len(result.errors) > 0


def test_reject_marks_classification_rejected(db):
    asset, cls, meta = make_full_suggestion(db)

    mock_immich = MagicMock()
    svc = ReviewDecisionService(db, immich_client=mock_immich)
    svc.reject_asset(asset.id)

    db.refresh(cls)
    assert cls.status == "rejected"


def test_external_library_warning_in_errors(db):
    asset, cls, meta = make_full_suggestion(db)
    asset.is_external_library = True
    db.commit()

    mock_immich = MagicMock()
    mock_immich.update_asset_description.return_value = {}
    mock_immich.get_or_create_tag.return_value = {"id": "tid", "name": "tag"}
    mock_immich.tag_asset.return_value = None

    svc = ReviewDecisionService(db, immich_client=mock_immich)
    result = svc.approve_asset(
        asset_id=asset.id,
        approved_bucket_id=None,
        approved_bucket_name=None,
        approved_description="test",
        approved_tags=["test"],
        approved_subalbum=None,
        subalbum_approved=False,
        trigger_writeback=True,
    )

    assert any("external library" in e.lower() for e in result.errors)
