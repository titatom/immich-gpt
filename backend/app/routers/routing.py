"""
Routing tree, examples, plans, and classification endpoints.
"""
from __future__ import annotations
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_active_user
from ..models.bucket import Bucket
from ..models.routing_example import RoutingExample
from ..models.routing_plan import RoutingPlan, RoutingPlanItem
from ..models.asset import Asset
from ..schemas.bucket import (
    RoutingNodeCreate, RoutingNodeUpdate, RoutingNodeOut, RoutingNodeMove,
    RoutingExampleCreate, RoutingExampleOut,
    RoutingPlanOut, RoutingPlanItemOut,
    RoutingClassifyRequest,
    PlanItemMoveRequest, PlanItemActionRequest,
    PromptPreviewOut,
)
from ..services.routing_tree import RoutingTreeService, RoutingTreeError
from ..services.leaf_prompt_compiler import LeafPromptCompiler
from ..services.routing_plan_service import RoutingPlanService
from ..services.routing_writeback import RoutingWritebackService

router = APIRouter(prefix="/api/routing", tags=["routing"])


# ---------------------------------------------------------------------------
# Tree CRUD
# ---------------------------------------------------------------------------

@router.get("/tree")
def get_tree(
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    svc = RoutingTreeService(db, current_user.id)
    return {"nodes": svc.build_tree()}


@router.get("/nodes", response_model=List[RoutingNodeOut])
def list_nodes(
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    svc = RoutingTreeService(db, current_user.id)
    return [svc.serialize(n) for n in svc.list_nodes()]


@router.post("/nodes", response_model=RoutingNodeOut)
def create_node(
    body: RoutingNodeCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    svc = RoutingTreeService(db, current_user.id)
    try:
        node = svc.create_node(body)
    except RoutingTreeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return svc.serialize(node)


@router.get("/nodes/{node_id}", response_model=RoutingNodeOut)
def get_node(
    node_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    svc = RoutingTreeService(db, current_user.id)
    try:
        node = svc.get_node(node_id)
    except RoutingTreeError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return svc.serialize(node)


@router.patch("/nodes/{node_id}", response_model=RoutingNodeOut)
def update_node(
    node_id: str,
    body: RoutingNodeUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    svc = RoutingTreeService(db, current_user.id)
    try:
        node = svc.update_node(node_id, body)
    except RoutingTreeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return svc.serialize(node)


@router.delete("/nodes/{node_id}")
def delete_node(
    node_id: str,
    cascade: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    svc = RoutingTreeService(db, current_user.id)
    try:
        svc.delete_node(node_id, cascade=cascade)
    except RoutingTreeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"deleted": True}


@router.post("/nodes/{node_id}/move", response_model=RoutingNodeOut)
def move_node(
    node_id: str,
    body: RoutingNodeMove,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    svc = RoutingTreeService(db, current_user.id)
    try:
        node = svc.move_node(node_id, body.new_parent_id)
    except RoutingTreeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return svc.serialize(node)


@router.post("/nodes/{node_id}/duplicate", response_model=RoutingNodeOut)
def duplicate_node(
    node_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    svc = RoutingTreeService(db, current_user.id)
    try:
        node = svc.duplicate_node(node_id)
    except RoutingTreeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return svc.serialize(node)


# ---------------------------------------------------------------------------
# Examples
# ---------------------------------------------------------------------------

@router.get("/nodes/{node_id}/examples", response_model=List[RoutingExampleOut])
def list_examples(
    node_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    svc = RoutingTreeService(db, current_user.id)
    try:
        svc.get_node(node_id)
    except RoutingTreeError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return (
        db.query(RoutingExample)
        .filter(
            RoutingExample.user_id == current_user.id,
            RoutingExample.bucket_id == node_id,
        )
        .order_by(RoutingExample.created_at.desc())
        .all()
    )


@router.post("/nodes/{node_id}/examples", response_model=RoutingExampleOut)
def add_example(
    node_id: str,
    body: RoutingExampleCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    svc = RoutingTreeService(db, current_user.id)
    try:
        svc.get_node(node_id)
    except RoutingTreeError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if body.example_type not in ("positive", "negative"):
        raise HTTPException(status_code=400, detail="example_type must be 'positive' or 'negative'")
    example = RoutingExample(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        bucket_id=node_id,
        asset_id=body.asset_id,
        example_type=body.example_type,
        source=body.source or "manual",
        note=body.note,
    )
    db.add(example)
    db.commit()
    db.refresh(example)
    return example


@router.delete("/examples/{example_id}")
def delete_example(
    example_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    example = (
        db.query(RoutingExample)
        .filter(
            RoutingExample.id == example_id,
            RoutingExample.user_id == current_user.id,
        )
        .first()
    )
    if not example:
        raise HTTPException(status_code=404, detail="Example not found")
    db.delete(example)
    db.commit()
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Prompt preview
# ---------------------------------------------------------------------------

@router.get("/nodes/{node_id}/prompt-preview", response_model=PromptPreviewOut)
def prompt_preview(
    node_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    svc = RoutingTreeService(db, current_user.id)
    try:
        node = svc.get_node(node_id)
    except RoutingTreeError as e:
        raise HTTPException(status_code=404, detail=str(e))
    compiler = LeafPromptCompiler(db, current_user.id)
    return PromptPreviewOut(
        bucket_id=node.id,
        path=node.path or node.name,
        compiled_prompt=compiler.compile(node),
    )


# ---------------------------------------------------------------------------
# Routing classification job
# ---------------------------------------------------------------------------

@router.post("/classify")
def classify(
    body: RoutingClassifyRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """
    Trigger a routing classification job.  Uses the existing job queue.
    Returns the job id and the plan id immediately; results land in the
    plan after the job completes.
    """
    from ..workers.executor import enqueue_routing_classification
    job_id, plan_id = enqueue_routing_classification(
        db,
        user_id=current_user.id,
        asset_ids=body.asset_ids,
        limit=body.limit,
        force=body.force,
    )
    return {"job_id": job_id, "plan_id": plan_id, "status": "queued"}


# ---------------------------------------------------------------------------
# Plans
# ---------------------------------------------------------------------------

def _plan_to_out(plan: RoutingPlan, item_count: int) -> RoutingPlanOut:
    return RoutingPlanOut(
        id=plan.id,
        job_id=plan.job_id,
        status=plan.status,
        scope=plan.scope_json or {},
        summary=plan.summary_json or {},
        item_count=item_count,
        created_at=plan.created_at,
        updated_at=plan.updated_at or plan.created_at,
    )


@router.get("/plans", response_model=List[RoutingPlanOut])
def list_plans(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    svc = RoutingPlanService(db, current_user.id)
    plans = svc.list_plans(status=status)
    counts = svc.item_counts_by_plan([p.id for p in plans])
    return [_plan_to_out(p, counts.get(p.id, 0)) for p in plans]


@router.get("/plans/{plan_id}", response_model=RoutingPlanOut)
def get_plan(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    svc = RoutingPlanService(db, current_user.id)
    plan = svc.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    items = svc.list_items(plan_id)
    return _plan_to_out(plan, len(items))


@router.get("/plans/{plan_id}/summary")
def plan_summary(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    svc = RoutingPlanService(db, current_user.id)
    plan = svc.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return svc.summarize(plan_id)


@router.get("/plans/{plan_id}/items", response_model=List[RoutingPlanItemOut])
def plan_items(
    plan_id: str,
    status: Optional[str] = None,
    bucket_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    svc = RoutingPlanService(db, current_user.id)
    plan = svc.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    items = svc.list_items(plan_id, status=status, bucket_id=bucket_id)
    return [_plan_item_to_out(item) for item in items]


def _plan_item_to_out(item: RoutingPlanItem) -> RoutingPlanItemOut:
    return RoutingPlanItemOut(
        id=item.id,
        plan_id=item.plan_id,
        asset_id=item.asset_id,
        primary_bucket_id=item.primary_bucket_id,
        primary_bucket_path=item.primary_bucket_path,
        secondary_bucket_ids=list(item.secondary_bucket_ids_json or []),
        disposition=item.disposition,
        confidence=item.confidence,
        review_required=bool(item.review_required),
        auto_apply=bool(item.auto_apply),
        review_reasons=list(item.review_reasons_json or []),
        reason_codes=list(item.reason_codes_json or []),
        safety_flags=dict(item.safety_flags_json or {}),
        quality_flags=dict(item.quality_flags_json or {}),
        suggested_description=item.suggested_description,
        suggested_tags=list(item.suggested_tags_json or []),
        suggested_location=item.suggested_location_json,
        suggested_caption=item.suggested_caption,
        status=item.status,
        error_message=item.error_message,
    )


@router.post("/plans/{plan_id}/approve")
def plan_approve(
    plan_id: str,
    body: PlanItemActionRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    svc = RoutingPlanService(db, current_user.id)
    if not svc.get_plan(plan_id):
        raise HTTPException(status_code=404, detail="Plan not found")

    item_ids = body.item_ids or []
    if body.bucket_id:
        items = svc.list_items(plan_id, status="pending", bucket_id=body.bucket_id)
        item_ids = list(set(item_ids) | {i.id for i in items})
    if not item_ids and not body.bucket_id:
        items = svc.list_items(plan_id, status="pending")
        item_ids = [i.id for i in items]
    count = svc.approve_items(item_ids)
    return {"approved": count}


@router.post("/plans/{plan_id}/reject")
def plan_reject(
    plan_id: str,
    body: PlanItemActionRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    svc = RoutingPlanService(db, current_user.id)
    if not svc.get_plan(plan_id):
        raise HTTPException(status_code=404, detail="Plan not found")
    item_ids = body.item_ids or []
    if body.bucket_id:
        items = svc.list_items(plan_id, bucket_id=body.bucket_id)
        item_ids = list(set(item_ids) | {i.id for i in items})
    if not item_ids:
        items = svc.list_items(plan_id, status="pending")
        item_ids = [i.id for i in items]
    count = svc.reject_items(item_ids)
    return {"rejected": count}


@router.post("/plans/{plan_id}/items/move")
def plan_move(
    plan_id: str,
    body: PlanItemMoveRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    svc = RoutingPlanService(db, current_user.id)
    if not svc.get_plan(plan_id):
        raise HTTPException(status_code=404, detail="Plan not found")
    try:
        count = svc.move_items(body.item_ids, body.target_bucket_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"moved": count}


@router.post("/plans/{plan_id}/apply")
def plan_apply(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    svc = RoutingPlanService(db, current_user.id)
    plan = svc.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    writeback = RoutingWritebackService(db, current_user.id)
    items = svc.list_items(plan_id, status="approved")
    applied = 0
    failed = 0
    for item in items:
        try:
            result = writeback.apply_item(item)
            if result.errors:
                item.status = "failed"
                item.error_message = "; ".join(result.errors)[:500]
                failed += 1
            else:
                item.status = "applied"
                applied += 1
            db.commit()
        except Exception as e:  # pragma: no cover
            item.status = "failed"
            item.error_message = str(e)[:500]
            db.commit()
            failed += 1
    svc.mark_plan_applied(plan_id)
    return {"applied": applied, "failed": failed}
