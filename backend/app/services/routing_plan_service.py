"""
RoutingPlanService — manage routing plans and their items.
"""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models.routing_plan import RoutingPlan, RoutingPlanItem
from ..models.bucket import Bucket
from .routing_decision import RoutingDecision


class RoutingPlanService:
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create_plan(
        self,
        job_id: Optional[str] = None,
        scope: Optional[Dict[str, Any]] = None,
        status: str = "draft",
    ) -> RoutingPlan:
        plan = RoutingPlan(
            id=str(uuid.uuid4()),
            user_id=self.user_id,
            job_id=job_id,
            status=status,
            scope_json=scope or {},
            summary_json={},
        )
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def get_plan(self, plan_id: str) -> Optional[RoutingPlan]:
        return (
            self.db.query(RoutingPlan)
            .filter(RoutingPlan.id == plan_id, RoutingPlan.user_id == self.user_id)
            .first()
        )

    def list_plans(self, status: Optional[str] = None) -> List[RoutingPlan]:
        q = self.db.query(RoutingPlan).filter(RoutingPlan.user_id == self.user_id)
        if status:
            q = q.filter(RoutingPlan.status == status)
        return q.order_by(RoutingPlan.created_at.desc()).all()

    def item_counts_by_plan(self, plan_ids: List[str]) -> Dict[str, int]:
        if not plan_ids:
            return {}
        rows = (
            self.db.query(RoutingPlanItem.plan_id, func.count(RoutingPlanItem.id))
            .filter(
                RoutingPlanItem.user_id == self.user_id,
                RoutingPlanItem.plan_id.in_(plan_ids),
            )
            .group_by(RoutingPlanItem.plan_id)
            .all()
        )
        return {plan_id: count for plan_id, count in rows}

    def add_item(
        self,
        plan: RoutingPlan,
        asset_id: str,
        decision: RoutingDecision,
        ai_metadata: Dict[str, Any],
        raw_ai_response: Optional[Dict[str, Any]] = None,
    ) -> RoutingPlanItem:
        primary = decision.primary

        if decision.auto_apply:
            status = "approved"
        elif decision.review_required:
            status = "pending"
        else:
            status = "approved"

        item = RoutingPlanItem(
            id=str(uuid.uuid4()),
            user_id=self.user_id,
            plan_id=plan.id,
            asset_id=asset_id,
            primary_bucket_id=primary.bucket_id if primary else None,
            primary_bucket_path=primary.path if primary else None,
            secondary_bucket_ids_json=[c.bucket_id for c in decision.secondary],
            disposition=decision.disposition,
            confidence=primary.confidence if primary else None,
            review_required=decision.review_required,
            auto_apply=decision.auto_apply,
            review_reasons_json=list(decision.review_reasons),
            reason_codes_json=list(decision.reason_codes),
            safety_flags_json=dict(decision.safety_flags),
            quality_flags_json=dict(decision.quality_flags),
            suggested_description=ai_metadata.get("description"),
            suggested_tags_json=list(ai_metadata.get("tags") or []),
            suggested_location_json=ai_metadata.get("location"),
            suggested_caption=ai_metadata.get("caption"),
            raw_ai_response_json=raw_ai_response or {},
            status=status,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def list_items(
        self,
        plan_id: str,
        status: Optional[str] = None,
        bucket_id: Optional[str] = None,
    ) -> List[RoutingPlanItem]:
        q = self.db.query(RoutingPlanItem).filter(
            RoutingPlanItem.user_id == self.user_id,
            RoutingPlanItem.plan_id == plan_id,
        )
        if status:
            q = q.filter(RoutingPlanItem.status == status)
        if bucket_id:
            q = q.filter(RoutingPlanItem.primary_bucket_id == bucket_id)
        return q.order_by(RoutingPlanItem.created_at.asc()).all()

    def get_item(self, item_id: str) -> Optional[RoutingPlanItem]:
        return (
            self.db.query(RoutingPlanItem)
            .filter(
                RoutingPlanItem.id == item_id,
                RoutingPlanItem.user_id == self.user_id,
            )
            .first()
        )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summarize(self, plan_id: str) -> Dict[str, Any]:
        items = self.list_items(plan_id)
        groups: Dict[str, Dict[str, Any]] = {
            "auto_applied": {},
            "ready_to_approve": {},
            "needs_review": {},
            "trash_candidates": {},
            "rejected": {},
            "failed": {},
        }
        for item in items:
            group = self._classify_group(item)
            path = item.primary_bucket_path or "(no destination)"
            bucket = groups[group].setdefault(
                path,
                {
                    "path": path,
                    "bucket_id": item.primary_bucket_id,
                    "count": 0,
                    "item_ids": [],
                },
            )
            bucket["count"] += 1
            bucket["item_ids"].append(item.id)

        total = len(items)
        return {
            "plan_id": plan_id,
            "total": total,
            "groups": {
                k: list(v.values()) for k, v in groups.items()
            },
        }

    def _classify_group(self, item: RoutingPlanItem) -> str:
        if item.status == "applied":
            return "auto_applied"
        if item.status == "failed":
            return "failed"
        if item.status == "rejected":
            return "rejected"
        if item.disposition == "trash_candidate":
            return "trash_candidates"
        if item.review_required:
            return "needs_review"
        return "ready_to_approve"

    # ------------------------------------------------------------------
    # Item actions
    # ------------------------------------------------------------------

    def approve_items(self, item_ids: List[str], plan_id: Optional[str] = None) -> int:
        items = self._items_by_ids(item_ids, plan_id=plan_id)
        count = 0
        for item in items:
            if item.status in ("pending",):
                item.status = "approved"
                count += 1
        self.db.commit()
        return count

    def reject_items(self, item_ids: List[str], plan_id: Optional[str] = None) -> int:
        items = self._items_by_ids(item_ids, plan_id=plan_id)
        count = 0
        for item in items:
            if item.status not in ("applied", "failed"):
                item.status = "rejected"
                count += 1
        self.db.commit()
        return count

    def move_items(
        self,
        item_ids: List[str],
        target_bucket_id: str,
        plan_id: Optional[str] = None,
    ) -> int:
        target = (
            self.db.query(Bucket)
            .filter(Bucket.id == target_bucket_id, Bucket.user_id == self.user_id)
            .first()
        )
        if not target:
            raise ValueError(f"Target bucket {target_bucket_id} not found")
        items = self._items_by_ids(item_ids, plan_id=plan_id)
        count = 0
        from .routing_learning import RoutingLearningService
        learner = RoutingLearningService(self.db, self.user_id)
        for item in items:
            from_bucket = item.primary_bucket_id
            item.primary_bucket_id = target.id
            item.primary_bucket_path = target.path or target.name
            if target.destination_type == "immich_trash":
                item.disposition = "trash_candidate"
            elif item.disposition == "trash_candidate":
                item.disposition = "review"
            count += 1
            try:
                learner.record_correction(item.asset_id, from_bucket, target.id)
            except Exception:
                # Learning is best-effort; never block the move.
                pass
        self.db.commit()
        return count

    def update_status(self, item_id: str, status: str, error: Optional[str] = None) -> None:
        item = self.get_item(item_id)
        if not item:
            return
        item.status = status
        if error is not None:
            item.error_message = error
        self.db.commit()

    def _items_by_ids(
        self,
        item_ids: List[str],
        plan_id: Optional[str] = None,
    ) -> List[RoutingPlanItem]:
        if not item_ids:
            return []
        query = self.db.query(RoutingPlanItem).filter(
            RoutingPlanItem.user_id == self.user_id,
            RoutingPlanItem.id.in_(item_ids),
        )
        if plan_id is not None:
            query = query.filter(RoutingPlanItem.plan_id == plan_id)
        return query.all()

    def mark_plan_applied(self, plan_id: str) -> None:
        plan = self.get_plan(plan_id)
        if not plan:
            return
        items = self.list_items(plan_id)
        any_pending = any(i.status in ("pending", "approved") for i in items)
        any_applied = any(i.status == "applied" for i in items)
        if any_pending:
            plan.status = "partially_applied"
        elif any_applied:
            plan.status = "applied"
        plan.updated_at = datetime.utcnow()
        self.db.commit()
