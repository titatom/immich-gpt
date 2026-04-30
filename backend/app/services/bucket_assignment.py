"""Helpers for assigning synced or selected assets to a bucket."""
import uuid
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from ..models.asset import Asset
from ..models.bucket import Bucket
from ..models.suggested_classification import SuggestedClassification


class BucketAssignmentService:
    def __init__(self, db: Session, user_id: str | None):
        self.db = db
        self.user_id = user_id

    def get_bucket(self, bucket_id: str) -> Optional[Bucket]:
        query = self.db.query(Bucket).filter(Bucket.id == bucket_id)
        if self.user_id:
            query = query.filter(Bucket.user_id == self.user_id)
        return query.first()

    def assign_assets(
        self,
        asset_ids: Iterable[str],
        bucket: Bucket,
        *,
        explanation: str = "Manually assigned to bucket.",
        provider_name: str = "manual",
    ) -> int:
        unique_ids = list(dict.fromkeys(asset_ids))
        if not unique_ids:
            return 0

        asset_query = self.db.query(Asset.id).filter(Asset.id.in_(unique_ids))
        if self.user_id:
            asset_query = asset_query.filter(Asset.user_id == self.user_id)
        owned_ids = [row[0] for row in asset_query.all()]

        for asset_id in owned_ids:
            self.add_assignment(
                asset_id,
                bucket,
                explanation=explanation,
                provider_name=provider_name,
            )

        return len(owned_ids)

    def add_assignment(
        self,
        asset_id: str,
        bucket: Bucket,
        *,
        explanation: str = "Manually assigned to bucket.",
        provider_name: str = "manual",
    ) -> None:
        self.db.add(
            SuggestedClassification(
                id=str(uuid.uuid4()),
                asset_id=asset_id,
                suggested_bucket_id=bucket.id,
                suggested_bucket_name=bucket.name,
                confidence=1.0,
                explanation=explanation,
                review_recommended=False,
                provider_name=provider_name,
                status="approved",
            )
        )
