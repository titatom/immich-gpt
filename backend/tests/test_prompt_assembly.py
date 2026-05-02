"""Test 1: Prompt assembly using global + bucket + field prompts."""
import pytest
from app.services.prompt_assembly import PromptAssemblyService
from app.models.bucket import Bucket
import uuid


def test_assembles_system_and_user_messages(db):
    from tests.conftest import TEST_USER_ID
    svc = PromptAssemblyService(db, user_id=TEST_USER_ID)
    buckets = db.query(Bucket).filter(Bucket.user_id == TEST_USER_ID).all()

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
    from tests.conftest import TEST_USER_ID
    svc = PromptAssemblyService(db, user_id=TEST_USER_ID)
    buckets = db.query(Bucket).filter(Bucket.user_id == TEST_USER_ID).all()

    messages = svc.assemble_classification_messages({}, buckets)
    system = messages[0]["content"]
    for b in buckets:
        assert b.name in system


def test_system_prompt_includes_global_classification(db):
    from tests.conftest import TEST_USER_ID
    svc = PromptAssemblyService(db, user_id=TEST_USER_ID)
    buckets = db.query(Bucket).filter(Bucket.user_id == TEST_USER_ID).all()

    messages = svc.assemble_classification_messages({}, buckets)
    system = messages[0]["content"]
    assert "Classify" in system


def test_metadata_included_in_user_message(db):
    from tests.conftest import TEST_USER_ID
    svc = PromptAssemblyService(db, user_id=TEST_USER_ID)
    buckets = db.query(Bucket).filter(Bucket.user_id == TEST_USER_ID).all()

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


def test_location_prompt_only_enabled_without_geo_data(db):
    from tests.conftest import TEST_USER_ID
    svc = PromptAssemblyService(db, user_id=TEST_USER_ID)
    buckets = db.query(Bucket).filter(Bucket.user_id == TEST_USER_ID).all()

    missing_geo = svc.assemble_classification_messages({"original_filename": "tokyo.jpg"}, buckets)
    assert "Suggest location only when evidence supports it" in missing_geo[0]["content"]

    with_geo = svc.assemble_classification_messages({
        "original_filename": "tokyo.jpg",
        "raw_metadata": {"exifInfo": {"latitude": 35.0, "longitude": 139.0}},
    }, buckets)
    assert "Return location_suggestion as null" in with_geo[0]["content"]


def test_suggestion_settings_disable_fields(db):
    from tests.conftest import TEST_USER_ID
    from app.models.app_setting import AppSetting
    db.add(AppSetting(id=str(uuid.uuid4()), user_id=TEST_USER_ID, key="suggest_tags", value="false"))
    db.add(AppSetting(id=str(uuid.uuid4()), user_id=TEST_USER_ID, key="suggest_subalbums", value="false"))
    db.commit()

    svc = PromptAssemblyService(db, user_id=TEST_USER_ID)
    buckets = db.query(Bucket).filter(Bucket.user_id == TEST_USER_ID).all()
    system = svc.assemble_classification_messages({}, buckets)[0]["content"]
    assert "Return tags as an empty array" in system
    assert "Set subalbum_suggestion to null" in system


def test_output_schema_contains_bucket_names(db):
    from tests.conftest import TEST_USER_ID
    svc = PromptAssemblyService(db, user_id=TEST_USER_ID)
    buckets = db.query(Bucket).filter(Bucket.user_id == TEST_USER_ID).all()

    messages = svc.assemble_classification_messages({}, buckets)
    system = messages[0]["content"]
    assert "bucket_name" in system
    assert "confidence" in system
    assert "tags" in system


def test_disabled_buckets_excluded(db):
    from app.models.bucket import Bucket as B
    from tests.conftest import TEST_USER_ID
    b = B(id=str(uuid.uuid4()), user_id=TEST_USER_ID, name="Disabled", enabled=False, priority=999, mapping_mode="virtual")
    db.add(b)
    db.commit()

    svc = PromptAssemblyService(db, user_id=TEST_USER_ID)
    enabled_buckets = db.query(B).filter(B.enabled == True, B.user_id == TEST_USER_ID).all()
    messages = svc.assemble_classification_messages({}, enabled_buckets)
    system = messages[0]["content"]
    assert "Disabled" not in system


def test_custom_bucket_prompt_overrides_default(db):
    from app.models.prompt_template import PromptTemplate as PT
    from tests.conftest import TEST_USER_ID
    buckets = db.query(Bucket).filter(Bucket.user_id == TEST_USER_ID).all()
    biz = next(b for b in buckets if b.name == "Business")

    custom_pt = PT(
        id=str(uuid.uuid4()),
        user_id=TEST_USER_ID,
        prompt_type="bucket_classification",
        name="Custom Business",
        content="Custom: This is MY business prompt.",
        enabled=True,
        version=2,
        bucket_id=biz.id,
    )
    db.add(custom_pt)
    db.commit()

    svc = PromptAssemblyService(db, user_id=TEST_USER_ID)
    messages = svc.assemble_classification_messages({}, buckets)
    system = messages[0]["content"]
    assert "Custom: This is MY business prompt." in system
