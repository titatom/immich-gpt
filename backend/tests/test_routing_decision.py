"""Routing decision / rule evaluation tests."""
import pytest
from app.models.bucket import Bucket
from app.services.routing_tree import RoutingTreeService
from app.services.routing_decision import RoutingDecisionService
from app.services.routing_schemas import (
    AIRoutingResult, AISafetyFlags, AIQualityFlags, AISecondaryPath, AIMetadata,
)
from app.schemas.bucket import RoutingNodeCreate
from tests.conftest import TEST_USER_ID


def _clean(db):
    db.query(Bucket).filter(Bucket.user_id == TEST_USER_ID).delete()
    db.commit()


def _make_leaf(svc, **overrides):
    data = dict(name="Lake", is_leaf=True)
    data.update(overrides)
    return svc.create_node(RoutingNodeCreate(**data))


def test_rejects_when_privacy_flag_is_reject(db):
    _clean(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    leaf = _make_leaf(svc, privacy_rules={"address_visible": "reject"})
    decision = RoutingDecisionService(db, TEST_USER_ID).evaluate_leaf_rules(
        leaf,
        confidence=0.95,
        safety_flags=AISafetyFlags(address_visible=True),
        quality_flags=AIQualityFlags(),
    )
    assert decision.rejected is True
    assert "address_visible" in (decision.reason or "")


def test_marks_review_when_privacy_flag_is_review(db):
    _clean(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    leaf = _make_leaf(svc, privacy_rules={"children_visible": "review"})
    decision = RoutingDecisionService(db, TEST_USER_ID).evaluate_leaf_rules(
        leaf,
        confidence=0.95,
        safety_flags=AISafetyFlags(children_visible=True),
        quality_flags=AIQualityFlags(),
    )
    assert decision.rejected is False
    assert decision.review_required is True
    assert any("children_visible" in r for r in decision.review_reasons)


def test_allow_privacy_does_not_affect_routing(db):
    _clean(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    leaf = _make_leaf(svc, privacy_rules={"faces_visible": "allow"})
    decision = RoutingDecisionService(db, TEST_USER_ID).evaluate_leaf_rules(
        leaf,
        confidence=0.99,
        safety_flags=AISafetyFlags(faces_visible=True),
        quality_flags=AIQualityFlags(),
    )
    assert decision.rejected is False
    assert decision.review_required is False


def test_rejects_blurry_when_not_allowed(db):
    _clean(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    leaf = _make_leaf(svc, allow_blurry=False)
    decision = RoutingDecisionService(db, TEST_USER_ID).evaluate_leaf_rules(
        leaf, confidence=0.99,
        safety_flags=AISafetyFlags(),
        quality_flags=AIQualityFlags(blurry=True),
    )
    assert decision.rejected is True


def test_low_confidence_marks_review(db):
    _clean(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    leaf = _make_leaf(svc, review_below_threshold=0.9)
    decision = RoutingDecisionService(db, TEST_USER_ID).evaluate_leaf_rules(
        leaf, confidence=0.5,
        safety_flags=AISafetyFlags(),
        quality_flags=AIQualityFlags(),
    )
    assert decision.review_required is True
    assert "low_confidence" in decision.review_reasons


def test_higher_priority_wins(db):
    _clean(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    high_priority = _make_leaf(svc, name="HighPri", priority=10)
    low_priority = _make_leaf(svc, name="LowPri", priority=100)
    leaves = [low_priority, high_priority]

    ai_result = AIRoutingResult(
        disposition="keep",
        primary_path="LowPri", primary_confidence=0.99,
        secondary_paths=[AISecondaryPath(path="HighPri", confidence=0.6)],
        review_required=False,
    )
    decision = RoutingDecisionService(db, TEST_USER_ID).resolve_routing(ai_result, leaves)
    assert decision.primary is not None
    assert decision.primary.path == "HighPri"


def test_higher_confidence_wins_on_priority_tie(db):
    _clean(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    a = _make_leaf(svc, name="A", priority=50)
    b = _make_leaf(svc, name="B", priority=50)
    ai_result = AIRoutingResult(
        disposition="keep",
        primary_path="A", primary_confidence=0.6,
        secondary_paths=[AISecondaryPath(path="B", confidence=0.95)],
        review_required=False,
    )
    decision = RoutingDecisionService(db, TEST_USER_ID).resolve_routing(ai_result, [a, b])
    assert decision.primary.path == "B"


def test_exclusive_primary_removes_secondary(db):
    _clean(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    primary = _make_leaf(svc, name="P", priority=10, exclusive=True)
    other = _make_leaf(svc, name="O", priority=20)
    ai_result = AIRoutingResult(
        disposition="keep",
        primary_path="P", primary_confidence=0.95,
        secondary_paths=[AISecondaryPath(path="O", confidence=0.9)],
        review_required=False,
    )
    decision = RoutingDecisionService(db, TEST_USER_ID).resolve_routing(ai_result, [primary, other])
    assert decision.primary.path == "P"
    assert decision.secondary == []


def test_allow_secondary_false_prevents_secondaries(db):
    _clean(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    primary = _make_leaf(svc, name="P", priority=10, allow_secondary=False)
    other = _make_leaf(svc, name="O", priority=20)
    ai_result = AIRoutingResult(
        disposition="keep",
        primary_path="P", primary_confidence=0.99,
        secondary_paths=[AISecondaryPath(path="O", confidence=0.9)],
        review_required=False,
    )
    decision = RoutingDecisionService(db, TEST_USER_ID).resolve_routing(ai_result, [primary, other])
    assert decision.secondary == []


def test_auto_apply_blocked_below_threshold(db):
    _clean(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    leaf = _make_leaf(
        svc, name="L",
        auto_apply_enabled=True, auto_apply_threshold=0.95,
        review_below_threshold=None,
    )
    ai_result = AIRoutingResult(
        disposition="keep",
        primary_path="L", primary_confidence=0.7,
        review_required=False,
    )
    decision = RoutingDecisionService(db, TEST_USER_ID).resolve_routing(ai_result, [leaf])
    assert decision.auto_apply is False


def test_auto_apply_blocked_when_review_required(db):
    _clean(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    leaf = _make_leaf(
        svc, name="L",
        auto_apply_enabled=True, auto_apply_threshold=0.5,
        privacy_rules={"faces_visible": "review"},
        review_below_threshold=None,
    )
    ai_result = AIRoutingResult(
        disposition="keep",
        primary_path="L", primary_confidence=0.99,
        review_required=False,
        safety_flags=AISafetyFlags(faces_visible=True),
    )
    decision = RoutingDecisionService(db, TEST_USER_ID).resolve_routing(ai_result, [leaf])
    assert decision.review_required is True
    assert decision.auto_apply is False


def test_trash_leaf_does_not_auto_apply_by_default(db):
    """Trash never auto-applies unless explicitly enabled — the leaf
    setting auto_apply_enabled=False keeps it review-only."""
    _clean(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    leaf = _make_leaf(
        svc, name="TrashLeaf",
        destination_type="immich_trash",
        auto_apply_enabled=False,
        auto_apply_threshold=0.5,
        review_below_threshold=None,
    )
    ai_result = AIRoutingResult(
        disposition="trash_candidate",
        primary_path="TrashLeaf", primary_confidence=0.99,
        review_required=False,
    )
    decision = RoutingDecisionService(db, TEST_USER_ID).resolve_routing(ai_result, [leaf])
    assert decision.auto_apply is False


def test_auto_apply_succeeds_when_all_rules_pass(db):
    _clean(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    leaf = _make_leaf(
        svc, name="L",
        destination_type="immich_album",
        auto_apply_enabled=True,
        auto_apply_threshold=0.9,
        review_below_threshold=0.5,
    )
    ai_result = AIRoutingResult(
        disposition="keep",
        primary_path="L", primary_confidence=0.99,
        review_required=False,
    )
    decision = RoutingDecisionService(db, TEST_USER_ID).resolve_routing(ai_result, [leaf])
    assert decision.review_required is False
    assert decision.auto_apply is True
    assert decision.primary.path == "L"


def test_disabled_leaf_is_excluded(db):
    _clean(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    leaf = _make_leaf(svc, name="L", enabled=False)
    ai_result = AIRoutingResult(
        disposition="keep",
        primary_path="L", primary_confidence=0.99,
        review_required=False,
    )
    decision = RoutingDecisionService(db, TEST_USER_ID).resolve_routing(ai_result, [leaf])
    assert decision.primary is None
    assert decision.review_required is True
