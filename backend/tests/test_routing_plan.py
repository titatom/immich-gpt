"""RoutingPlanService and routing API tests."""
import uuid
import pytest
from datetime import datetime
from app.models.asset import Asset
from app.services.routing_plan_service import RoutingPlanService
from app.services.routing_tree import RoutingTreeService
from app.services.routing_classification import RoutingClassificationOrchestrator
from app.services.routing_schemas import (
    RoutingDecision, Candidate,
)
from app.schemas.bucket import RoutingNodeCreate
from app.models.bucket import Bucket
from app.models.asset import Asset
from tests.conftest import TEST_USER_ID


def _clean(db):
    db.query(Bucket).filter(Bucket.user_id == TEST_USER_ID).delete()
    db.commit()


def _make_decision(bucket_id: str, path: str, confidence: float = 0.9, review: bool = False, auto: bool = False) -> RoutingDecision:
    return RoutingDecision(
        primary=Candidate(bucket_id=bucket_id, path=path, confidence=confidence),
        secondary=[],
        disposition="keep",
        review_required=review,
        auto_apply=auto,
    )


def _make_asset(db, asset_id: str, immich_id: str) -> Asset:
    asset = Asset(
        id=asset_id,
        user_id=TEST_USER_ID,
        immich_id=immich_id,
        original_filename=f"{immich_id}.jpg",
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


class _DummyProvider:
    provider_name = "dummy"


def _make_asset(db, immich_id: str) -> Asset:
    asset = Asset(
        id=str(uuid.uuid4()),
        user_id=TEST_USER_ID,
        immich_id=immich_id,
        original_filename=f"{immich_id}.jpg",
        synced_at=datetime.utcnow(),
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


class _FakeProvider:
    provider_name = "fake"
    model = "fake-model"

    def classify_routing(self, messages, image_payload):
        raise AssertionError("Provider should not be called by _load_assets tests")


def _make_orchestrator(db) -> RoutingClassificationOrchestrator:
    return RoutingClassificationOrchestrator(
        db,
        _FakeProvider(),
        user_id=TEST_USER_ID,
        immich_client=object(),
    )


def test_plan_groups_items_by_destination(db):
    _clean(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    a = svc.create_node(RoutingNodeCreate(name="A"))
    b = svc.create_node(RoutingNodeCreate(name="B"))
    plan_svc = RoutingPlanService(db, TEST_USER_ID)
    plan = plan_svc.create_plan()

    for i in range(3):
        plan_svc.add_item(
            plan,
            asset_id=f"asset-a-{i}",
            decision=_make_decision(a.id, "A", review=False),
            ai_metadata={"description": "x", "tags": []},
        )
    for i in range(2):
        plan_svc.add_item(
            plan,
            asset_id=f"asset-b-{i}",
            decision=_make_decision(b.id, "B", review=True),
            ai_metadata={},
        )

    summary = plan_svc.summarize(plan.id)
    assert summary["total"] == 5
    ready = {g["path"]: g["count"] for g in summary["groups"]["ready_to_approve"]}
    needs = {g["path"]: g["count"] for g in summary["groups"]["needs_review"]}
    assert ready.get("A") == 3
    assert needs.get("B") == 2


def test_approve_and_reject_groups(db):
    _clean(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    a = svc.create_node(RoutingNodeCreate(name="A"))
    plan_svc = RoutingPlanService(db, TEST_USER_ID)
    plan = plan_svc.create_plan()

    items = []
    for i in range(3):
        items.append(plan_svc.add_item(
            plan,
            asset_id=f"asset-{i}",
            decision=_make_decision(a.id, "A", review=True),
            ai_metadata={},
        ))

    approved = plan_svc.approve_items([items[0].id, items[1].id])
    rejected = plan_svc.reject_items([items[2].id])
    assert approved == 2
    assert rejected == 1
    db.refresh(items[0]); db.refresh(items[2])
    assert items[0].status == "approved"
    assert items[2].status == "rejected"


def test_plan_approve_does_not_mutate_items_from_other_plan(client, db):
    _clean(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    a = svc.create_node(RoutingNodeCreate(name="A"))
    plan_svc = RoutingPlanService(db, TEST_USER_ID)
    plan_a = plan_svc.create_plan()
    plan_b = plan_svc.create_plan()
    item_b = plan_svc.add_item(
        plan_b,
        asset_id="foreign-plan-asset",
        decision=_make_decision(a.id, "A", review=True),
        ai_metadata={},
    )

    resp = client.post(
        f"/api/routing/plans/{plan_a.id}/approve",
        json={"item_ids": [item_b.id]},
    )

    assert resp.status_code == 200
    assert resp.json()["approved"] == 0
    db.refresh(item_b)
    assert item_b.status == "pending"


def test_move_items_to_new_leaf(db):
    _clean(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    a = svc.create_node(RoutingNodeCreate(name="A"))
    b = svc.create_node(RoutingNodeCreate(name="B", destination_type="immich_trash"))
    plan_svc = RoutingPlanService(db, TEST_USER_ID)
    plan = plan_svc.create_plan()
    item = plan_svc.add_item(
        plan,
        asset_id="asset-x",
        decision=_make_decision(a.id, "A", review=True),
        ai_metadata={},
    )
    moved = plan_svc.move_items([item.id], b.id)
    assert moved == 1
    db.refresh(item)
    assert item.primary_bucket_id == b.id
    assert item.primary_bucket_path == "B"
    assert item.disposition == "trash_candidate"


def test_routing_classify_endpoint_creates_job_and_plan(client, monkeypatch):
    """The /api/routing/classify endpoint should enqueue a job & return ids."""
    captured = {}

    def fake_enqueue(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs

    monkeypatch.setattr("app.workers.executor.enqueue", fake_enqueue)

    resp = client.post("/api/routing/classify", json={"limit": 5, "force": False})
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"]
    assert body["plan_id"]
    assert body["status"] == "queued"


def test_routing_tree_endpoint_returns_nested(client, db):
    _clean(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    parent = svc.create_node(RoutingNodeCreate(name="Personal", is_leaf=False))
    svc.create_node(RoutingNodeCreate(name="Lake House", parent_id=parent.id))
    resp = client.get("/api/routing/tree")
    assert resp.status_code == 200
    nodes = resp.json()["nodes"]
    assert any(n["path"] == "Personal" and len(n["children"]) == 1 for n in nodes)


def test_routing_node_create_endpoint(client, db):
    _clean(db)
    resp = client.post("/api/routing/nodes", json={
        "name": "Family",
        "destination_type": "virtual",
        "is_leaf": True,
    })
    assert resp.status_code == 200
    assert resp.json()["path"] == "Family"


def test_routing_node_prompt_preview(client, db):
    _clean(db)
    resp = client.post("/api/routing/nodes", json={
        "name": "Family",
        "is_leaf": True,
        "positive_criteria": ["family photos"],
    })
    node_id = resp.json()["id"]
    preview = client.get(f"/api/routing/nodes/{node_id}/prompt-preview")
    assert preview.status_code == 200
    body = preview.json()
    assert body["path"] == "Family"
    assert "family photos" in body["compiled_prompt"]


def test_examples_lifecycle(client, db):
    _clean(db)
    create = client.post("/api/routing/nodes", json={"name": "Lake"})
    node_id = create.json()["id"]
    add = client.post(f"/api/routing/nodes/{node_id}/examples", json={
        "example_type": "positive",
        "note": "kayak"
    })
    assert add.status_code == 200
    ex_id = add.json()["id"]
    listed = client.get(f"/api/routing/nodes/{node_id}/examples")
    assert listed.status_code == 200
    assert any(e["id"] == ex_id for e in listed.json())
    deleted = client.delete(f"/api/routing/examples/{ex_id}")
    assert deleted.status_code == 200


def test_add_example_rejects_other_users_asset(client, db):
    _clean(db)
    create = client.post("/api/routing/nodes", json={"name": "Lake"})
    node_id = create.json()["id"]
    db.add(Asset(
        id="other-user-asset",
        user_id="other-user",
        immich_id="other-immich-id",
        original_filename="other.jpg",
    ))
    db.commit()

    resp = client.post(f"/api/routing/nodes/{node_id}/examples", json={
        "asset_id": "other-user-asset",
        "example_type": "positive",
    })

    assert resp.status_code == 404
