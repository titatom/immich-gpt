"""
RoutingLearningService — turn user corrections into examples.

Phase 6 of the routing-tree plan: when a user moves a plan item from
leaf A to leaf B, optionally:
  - add a positive example to leaf B
  - add a negative example to leaf A

Behavior is gated by a per-user setting; the default is OFF so the
system does nothing surprising.
"""
from __future__ import annotations
import uuid
from typing import Optional, List

from sqlalchemy.orm import Session

from ..models.app_setting import AppSetting
from ..models.bucket import Bucket  # noqa: F401  (used implicitly via FK)
from ..models.routing_example import RoutingExample
from ..models.asset import Asset


LEARN_SETTING_KEY = "routing_learn_from_corrections"


class RoutingLearningService:
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id

    def is_enabled(self) -> bool:
        row = (
            self.db.query(AppSetting)
            .filter(
                AppSetting.user_id == self.user_id,
                AppSetting.key == LEARN_SETTING_KEY,
            )
            .first()
        )
        if row is None:
            return False
        return str(row.value).strip().lower() in ("1", "true", "yes", "on")

    def record_correction(
        self,
        asset_id: str,
        from_bucket_id: Optional[str],
        to_bucket_id: str,
    ) -> List[RoutingExample]:
        """Add example rows when learning is enabled."""
        if not self.is_enabled():
            return []
        if not to_bucket_id or to_bucket_id == from_bucket_id:
            return []

        created: List[RoutingExample] = []
        note = self._build_note(asset_id)

        if from_bucket_id:
            created.append(self._add_example(
                bucket_id=from_bucket_id,
                asset_id=asset_id,
                example_type="negative",
                note=note,
            ))
        created.append(self._add_example(
            bucket_id=to_bucket_id,
            asset_id=asset_id,
            example_type="positive",
            note=note,
        ))
        self.db.commit()
        return created

    def _add_example(
        self,
        bucket_id: str,
        asset_id: str,
        example_type: str,
        note: Optional[str] = None,
    ) -> RoutingExample:
        ex = RoutingExample(
            id=str(uuid.uuid4()),
            user_id=self.user_id,
            bucket_id=bucket_id,
            asset_id=asset_id,
            example_type=example_type,
            source="correction",
            note=note,
        )
        self.db.add(ex)
        return ex

    def _build_note(self, asset_id: str) -> str:
        asset = self.db.query(Asset).filter(Asset.id == asset_id).first()
        if asset and asset.original_filename:
            return asset.original_filename
        if asset and asset.immich_id:
            return asset.immich_id
        return asset_id
