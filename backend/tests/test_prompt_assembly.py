"""Test 1: Prompt assembly using global + bucket + field prompts."""
import pytest
from app.services.prompt_assembly import PromptAssemblyService
from app.models.bucket import Bucket
import uuid


def test_assembles_system_and_user_messages(db):
    svc = PromptAssemblyService(db)
    buckets = db.query(Bucket).all()

    metadata = {
        "original_filename": "receipt.jpg",
        "asset_type": "IMAGE",
        "mime_type": "image/jpeg",
        "city": "Chicago",
        "country": "US",
        "camera_make": None,
        "camera_model": None,
        "description": None,
        "tags": [],
    }

    messages = svc.assemble_classification_messages(metadata, buckets)
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


def test_system_prompt_includes_bucket_names(db):
    svc = PromptAssemblyService(db)
    buckets = db.query(Bucket).all()

    messages = svc.assemble_classification_messages({}, buckets)
    system = messages[0]["content"]
    for b in buckets:
        assert b.name in system


def test_system_prompt_includes_global_classification(db):
    svc = PromptAssemblyService(db)
    buckets = db.query(Bucket).all()

    messages = svc.assemble_classification_messages({}, buckets)
    system = messages[0]["content"]
    assert "Classify" in system


def test_metadata_included_in_user_message(db):
    svc = PromptAssemblyService(db)
    buckets = db.query(Bucket).all()

    metadata = {
        "original_filename": "invoice_2024.pdf",
        "city": "New York",
        "country": "US",
        "asset_type": "IMAGE",
    }

    messages = svc.assemble_classification_messages(metadata, buckets)
    user_content = messages[1]["content"]
    assert "invoice_2024.pdf" in user_content
    assert "New York" in user_content


def test_output_schema_contains_bucket_names(db):
    svc = PromptAssemblyService(db)
    buckets = db.query(Bucket).all()

    messages = svc.assemble_classification_messages({}, buckets)
    system = messages[0]["content"]
    assert "bucket_name" in system
    assert "confidence" in system
    assert "tags" in system


def test_disabled_buckets_excluded(db):
    from app.models.bucket import Bucket as B
    b = B(id=str(uuid.uuid4()), name="Disabled", enabled=False, priority=999, mapping_mode="virtual")
    db.add(b)
    db.commit()

    svc = PromptAssemblyService(db)
    enabled_buckets = db.query(B).filter(B.enabled == True).all()
    messages = svc.assemble_classification_messages({}, enabled_buckets)
    system = messages[0]["content"]
    assert "Disabled" not in system


def test_custom_bucket_prompt_overrides_default(db):
    from app.models.prompt_template import PromptTemplate as PT
    buckets = db.query(Bucket).all()
    biz = next(b for b in buckets if b.name == "Business")

    custom_pt = PT(
        id=str(uuid.uuid4()),
        prompt_type="bucket_classification",
        name="Custom Business",
        content="Custom: This is MY business prompt.",
        enabled=True,
        version=2,
        bucket_id=biz.id,
    )
    db.add(custom_pt)
    db.commit()

    svc = PromptAssemblyService(db)
    messages = svc.assemble_classification_messages({}, buckets)
    system = messages[0]["content"]
    assert "Custom: This is MY business prompt." in system
