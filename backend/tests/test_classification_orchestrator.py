"""
Test 4: one-by-one AI orchestration.
"""
import uuid
import pytest
from unittest.mock import MagicMock, patch
from app.services.classification_orchestrator import ClassificationOrchestrator
from app.services.ai_provider import AIClassificationResult
from app.models.asset import Asset
from app.models.bucket import Bucket
from app.models.job_run import JobRun
from app.services.job_progress import JobProgressService


def make_asset(db) -> Asset:
    a = Asset(
        id=str(uuid.uuid4()),
        immich_id="immich-abc-123",
        original_filename="photo.jpg",
        asset_type="IMAGE",
        mime_type="image/jpeg",
        is_favorite=False,
        is_archived=False,
        is_trashed=False,
        is_external_library=False,
    )
    db.add(a)
    db.commit()
    return a


def make_job(db) -> JobRun:
    svc = JobProgressService(db)
    return svc.create_job("classification")


def make_mock_provider():
    provider = MagicMock()
    provider.provider_name = "openai"
    provider.classify_asset.return_value = AIClassificationResult(
        bucket_name="Personal",
        confidence=0.9,
        explanation="Family photo",
        description_suggestion="A family gathering photo",
        tags=["family", "indoor"],
        subalbum_suggestion=None,
        review_recommended=False,
    )
    return provider


def make_mock_image_service():
    svc = MagicMock()
    svc.prepare_for_provider.return_value = {
        "data_url": "data:image/jpeg;base64,abc",
        "mime_type": "image/jpeg",
        "size_bytes": 500,
    }
    return svc


def test_processes_single_asset(db):
    asset = make_asset(db)
    job = make_job(db)
    provider = make_mock_provider()

    orchestrator = ClassificationOrchestrator(db, provider)
    orchestrator.image_service = make_mock_image_service()

    orchestrator.run_classification_job(job.id, asset_ids=[asset.id])

    from app.models.suggested_classification import SuggestedClassification
    sc = db.query(SuggestedClassification).filter(
        SuggestedClassification.asset_id == asset.id
    ).first()
    assert sc is not None
    assert sc.suggested_bucket_name == "Personal"
    assert sc.confidence == 0.9
    assert sc.status == "pending_review"


def test_saves_suggested_metadata(db):
    asset = make_asset(db)
    job = make_job(db)
    provider = make_mock_provider()

    orchestrator = ClassificationOrchestrator(db, provider)
    orchestrator.image_service = make_mock_image_service()
    orchestrator.run_classification_job(job.id, asset_ids=[asset.id])

    from app.models.suggested_metadata import SuggestedMetadata
    sm = db.query(SuggestedMetadata).filter(SuggestedMetadata.asset_id == asset.id).first()
    assert sm is not None
    assert sm.description_suggestion == "A family gathering photo"
    assert "family" in sm.tags_json


def test_job_completes_successfully(db):
    asset = make_asset(db)
    job = make_job(db)
    provider = make_mock_provider()

    orchestrator = ClassificationOrchestrator(db, provider)
    orchestrator.image_service = make_mock_image_service()
    orchestrator.run_classification_job(job.id, asset_ids=[asset.id])

    db.refresh(job)
    assert job.status == "completed"
    assert job.success_count == 1
    assert job.error_count == 0


def test_handles_ai_error_gracefully(db):
    asset = make_asset(db)
    job = make_job(db)

    provider = MagicMock()
    provider.provider_name = "openai"
    provider.classify_asset.side_effect = ValueError("AI is broken")

    orchestrator = ClassificationOrchestrator(db, provider)
    orchestrator.image_service = make_mock_image_service()
    orchestrator.run_classification_job(job.id, asset_ids=[asset.id])

    db.refresh(job)
    # Should still complete (not crash), but count the error
    assert job.error_count == 1


def test_image_failure_continues_with_text_only(db):
    asset = make_asset(db)
    job = make_job(db)
    provider = make_mock_provider()

    image_service = MagicMock()
    image_service.prepare_for_provider.side_effect = Exception("Thumbnail not available")

    orchestrator = ClassificationOrchestrator(db, provider)
    orchestrator.image_service = image_service
    orchestrator.run_classification_job(job.id, asset_ids=[asset.id])

    db.refresh(job)
    # Should still classify (no image but AI still called)
    assert provider.classify_asset.called
