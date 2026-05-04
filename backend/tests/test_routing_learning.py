"""RoutingLearningService tests."""
import uuid
from app.services.routing_learning import RoutingLearningService, LEARN_SETTING_KEY
from app.services.routing_tree import RoutingTreeService
from app.services.routing_plan_service import RoutingPlanService
from app.services.routing_schemas import RoutingDecision, Candidate
from app.schemas.bucket import RoutingNodeCreate
from app.models.bucket import Bucket
from app.models.routing_example import RoutingExample
from app.models.app_setting import AppSetting
from app.models.asset import Asset
from tests.conftest import TEST_USER_ID


def _clean(db):
    db.query(Bucket).filter(Bucket.user_id == TEST_USER_ID).delete()
    db.query(RoutingExample).filter(RoutingExample.user_id == TEST_USER_ID).delete()
    db.query(AppSetting).filter(AppSetting.user_id == TEST_USER_ID).delete()
    db.commit()


def _make_asset(db, name="x.jpg"):
    a = Asset(
        id=str(uuid.uuid4()),
        user_id=TEST_USER_ID,
        immich_id=f"i-{name}",
        original_filename=name,
        asset_type="IMAGE",
    )
    db.add(a)
    db.commit()
    return a


def _enable_learning(db, enabled: bool):
    db.add(AppSetting(
        id=str(uuid.uuid4()),
        user_id=TEST_USER_ID,
        key=LEARN_SETTING_KEY,
        value="true" if enabled else "false",
    ))
    db.commit()


def test_default_disabled(db):
    _clean(db)
    learner = RoutingLearningService(db, TEST_USER_ID)
    assert learner.is_enabled() is False
    out = learner.record_correction("asset-1", "from-id", "to-id")
    assert out == []


def test_creates_examples_on_move_when_enabled(db):
    _clean(db)
    _enable_learning(db, True)
    asset = _make_asset(db, "lake.jpg")
    svc = RoutingTreeService(db, TEST_USER_ID)
    a = svc.create_node(RoutingNodeCreate(name="A"))
    b = svc.create_node(RoutingNodeCreate(name="B"))
    plan_svc = RoutingPlanService(db, TEST_USER_ID)
    plan = plan_svc.create_plan()
    item = plan_svc.add_item(
        plan,
        asset_id=asset.id,
        decision=RoutingDecision(
            primary=Candidate(bucket_id=a.id, path="A", confidence=0.9),
            disposition="keep", review_required=True,
        ),
        ai_metadata={},
    )
    plan_svc.move_items([item.id], b.id)

    examples = db.query(RoutingExample).filter(
        RoutingExample.user_id == TEST_USER_ID
    ).all()
    types = {(e.bucket_id, e.example_type) for e in examples}
    assert (b.id, "positive") in types
    assert (a.id, "negative") in types
