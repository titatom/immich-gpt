"""LeafPromptCompiler tests."""
import uuid
from app.services.leaf_prompt_compiler import LeafPromptCompiler
from app.services.routing_tree import RoutingTreeService
from app.schemas.bucket import RoutingNodeCreate
from app.models.routing_example import RoutingExample
from app.models.bucket import Bucket
from tests.conftest import TEST_USER_ID


def _clean(db):
    db.query(Bucket).filter(Bucket.user_id == TEST_USER_ID).delete()
    db.commit()


def test_compile_includes_path_and_description(db):
    _clean(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    parent = svc.create_node(RoutingNodeCreate(name="Personal", is_leaf=False))
    leaf = svc.create_node(RoutingNodeCreate(
        name="Lake House", parent_id=parent.id,
        description="Photos at the family lake house.",
    ))
    out = LeafPromptCompiler(db, TEST_USER_ID).compile(leaf)
    assert "Personal/Lake House" in out
    assert "lake house" in out.lower()


def test_compile_includes_positive_and_negative_criteria(db):
    _clean(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    leaf = svc.create_node(RoutingNodeCreate(
        name="X",
        positive_criteria=["sharp image", "clear subject"],
        negative_criteria=["blurry", "dark"],
    ))
    out = LeafPromptCompiler(db, TEST_USER_ID).compile(leaf)
    assert "sharp image" in out
    assert "clear subject" in out
    assert "blurry" in out


def test_compile_includes_privacy_rules(db):
    _clean(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    leaf = svc.create_node(RoutingNodeCreate(
        name="X",
        privacy_rules={"address_visible": "reject", "faces_visible": "review"},
    ))
    out = LeafPromptCompiler(db, TEST_USER_ID).compile(leaf)
    assert "address_visible" in out
    assert "reject" in out
    assert "faces_visible" in out


def test_compile_includes_quality_rules(db):
    _clean(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    leaf = svc.create_node(RoutingNodeCreate(
        name="HQ",
        minimum_quality="high",
        allow_blurry=False,
        allow_dark=False,
    ))
    out = LeafPromptCompiler(db, TEST_USER_ID).compile(leaf)
    assert "high" in out.lower()
    assert "blurry" in out.lower()


def test_compile_includes_examples(db):
    _clean(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    leaf = svc.create_node(RoutingNodeCreate(name="L"))
    db.add(RoutingExample(
        id=str(uuid.uuid4()),
        user_id=TEST_USER_ID,
        bucket_id=leaf.id,
        example_type="positive",
        source="manual",
        note="kayak on the lake",
    ))
    db.add(RoutingExample(
        id=str(uuid.uuid4()),
        user_id=TEST_USER_ID,
        bucket_id=leaf.id,
        example_type="negative",
        source="manual",
        note="receipt scan",
    ))
    db.commit()
    out = LeafPromptCompiler(db, TEST_USER_ID).compile(leaf)
    assert "kayak on the lake" in out
    assert "receipt scan" in out


def test_custom_prompt_appended_when_enabled(db):
    _clean(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    leaf = svc.create_node(RoutingNodeCreate(
        name="L",
        custom_prompt_enabled=True,
        custom_prompt="Always look for the dock.",
    ))
    out = LeafPromptCompiler(db, TEST_USER_ID).compile(leaf)
    assert "Always look for the dock." in out


def test_custom_prompt_skipped_when_disabled(db):
    _clean(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    leaf = svc.create_node(RoutingNodeCreate(
        name="L",
        custom_prompt_enabled=False,
        custom_prompt="Hidden.",
    ))
    out = LeafPromptCompiler(db, TEST_USER_ID).compile(leaf)
    assert "Hidden." not in out
