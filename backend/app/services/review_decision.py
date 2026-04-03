"""
ReviewDecisionService: apply user approvals and trigger write-backs to Immich.
All writes are explicit, logged, and safe.
"""
import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from ..models.asset import Asset
from ..models.suggested_classification import SuggestedClassification
from ..models.suggested_metadata import SuggestedMetadata
from ..models.review_decision import ReviewDecision
from ..models.audit_log import AuditLog
from ..models.bucket import Bucket
from ..services.immich_client import ImmichClient, ImmichError


class WritebackResult:
    def __init__(self, asset_id: str):
        self.asset_id = asset_id
        self.description_written = False
        self.tags_written = False
        self.album_assigned = False
        self.errors: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "description_written": self.description_written,
            "tags_written": self.tags_written,
            "album_assigned": self.album_assigned,
            "errors": self.errors,
        }


class ReviewDecisionService:
    def __init__(self, db: Session, immich_client: Optional[ImmichClient] = None):
        self.db = db
        self.immich = immich_client or ImmichClient()

    def approve_asset(
        self,
        asset_id: str,
        approved_bucket_id: Optional[str],
        approved_bucket_name: Optional[str],
        approved_description: Optional[str],
        approved_tags: Optional[List[str]],
        approved_subalbum: Optional[str],
        subalbum_approved: bool,
        trigger_writeback: bool = True,
    ) -> WritebackResult:
        asset = self.db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            raise ValueError(f"Asset {asset_id} not found")

        classification = self.db.query(SuggestedClassification).filter(
            SuggestedClassification.asset_id == asset_id,
            SuggestedClassification.status == "pending_review",
        ).first()

        metadata_suggestion = self.db.query(SuggestedMetadata).filter(
            SuggestedMetadata.asset_id == asset_id,
        ).order_by(SuggestedMetadata.created_at.desc()).first()

        # Determine if this is an override
        if classification:
            is_override = (
                approved_bucket_id and
                approved_bucket_id != classification.suggested_bucket_id
            )
            classification.status = "overridden" if is_override else "approved"
            if is_override:
                classification.override_bucket_id = approved_bucket_id
                classification.override_bucket_name = approved_bucket_name

        # Store approved metadata
        if metadata_suggestion:
            metadata_suggestion.approved_description = approved_description
            metadata_suggestion.approved_tags_json = approved_tags

        # Create decision record
        decision = ReviewDecision(
            id=str(uuid.uuid4()),
            asset_id=asset_id,
            suggested_classification_id=classification.id if classification else None,
            suggested_metadata_id=metadata_suggestion.id if metadata_suggestion else None,
            decision_type="approve_all",
            approved_bucket_id=approved_bucket_id,
            approved_bucket_name=approved_bucket_name,
            approved_description=approved_description,
            approved_tags_json=approved_tags,
            approved_subalbum=approved_subalbum,
            subalbum_approved=subalbum_approved,
            writeback_triggered=trigger_writeback,
        )
        self.db.add(decision)
        self.db.commit()

        result = WritebackResult(asset_id)

        if trigger_writeback:
            self._do_writeback(
                asset=asset,
                decision=decision,
                bucket_id=approved_bucket_id,
                bucket_name=approved_bucket_name,
                description=approved_description,
                tags=approved_tags,
                subalbum=approved_subalbum if subalbum_approved else None,
                metadata_suggestion=metadata_suggestion,
                result=result,
            )

        return result

    def reject_asset(self, asset_id: str) -> None:
        classification = self.db.query(SuggestedClassification).filter(
            SuggestedClassification.asset_id == asset_id,
            SuggestedClassification.status == "pending_review",
        ).first()
        if classification:
            classification.status = "rejected"

        decision = ReviewDecision(
            id=str(uuid.uuid4()),
            asset_id=asset_id,
            suggested_classification_id=classification.id if classification else None,
            decision_type="reject",
        )
        self.db.add(decision)
        self.db.commit()

    def _do_writeback(
        self,
        asset: Asset,
        decision: ReviewDecision,
        bucket_id: Optional[str],
        bucket_name: Optional[str],
        description: Optional[str],
        tags: Optional[List[str]],
        subalbum: Optional[str],
        metadata_suggestion: Optional[SuggestedMetadata],
        result: WritebackResult,
    ) -> None:
        is_external = asset.is_external_library
        if is_external:
            result.errors.append(
                "Asset is from an external library. Description/tag writes may be restricted."
            )

        # Write description
        if description and description.strip():
            try:
                self.immich.update_asset_description(asset.immich_id, description)
                result.description_written = True
                self._audit(asset.id, "writeback_description", "success",
                            {"description": description[:100]})
            except ImmichError as e:
                msg = f"Failed to write description: {e}"
                result.errors.append(msg)
                self._audit(asset.id, "writeback_description", "failed", error=msg)
                if metadata_suggestion:
                    metadata_suggestion.writeback_status = "failed"
                    metadata_suggestion.writeback_error = msg

        # Write tags
        if tags:
            tag_errors = []
            tag_ids = []
            for tag_name in tags:
                try:
                    tag = self.immich.get_or_create_tag(tag_name)
                    tag_ids.append(tag["id"])
                except ImmichError as e:
                    tag_errors.append(f"Tag '{tag_name}': {e}")

            if tag_ids:
                try:
                    self.immich.tag_asset(asset.immich_id, tag_ids)
                    result.tags_written = True
                    self._audit(asset.id, "writeback_tags", "success", {"tags": tags})
                except ImmichError as e:
                    msg = f"Failed to apply tags: {e}"
                    result.errors.append(msg)
                    self._audit(asset.id, "writeback_tags", "failed", error=msg)
            if tag_errors:
                result.errors.extend(tag_errors)

        # Album assignment
        if subalbum:
            bucket = (
                self.db.query(Bucket).filter(Bucket.id == bucket_id).first()
                if bucket_id else None
            )
            album_id = bucket.immich_album_id if bucket else None
            if album_id:
                try:
                    self.immich.add_asset_to_album(album_id, [asset.immich_id])
                    result.album_assigned = True
                    self._audit(asset.id, "writeback_album", "success",
                                {"album_id": album_id})
                except ImmichError as e:
                    msg = f"Failed to assign album: {e}"
                    result.errors.append(msg)
                    self._audit(asset.id, "writeback_album", "failed", error=msg)
        elif bucket_id:
            bucket = self.db.query(Bucket).filter(Bucket.id == bucket_id).first()
            if bucket and bucket.immich_album_id and bucket.mapping_mode == "immich_album":
                try:
                    self.immich.add_asset_to_album(
                        bucket.immich_album_id, [asset.immich_id]
                    )
                    result.album_assigned = True
                    self._audit(asset.id, "writeback_album", "success",
                                {"album_id": bucket.immich_album_id})
                except ImmichError as e:
                    msg = f"Failed to assign bucket album: {e}"
                    result.errors.append(msg)
                    self._audit(asset.id, "writeback_album", "failed", error=msg)

        if metadata_suggestion:
            metadata_suggestion.writeback_status = (
                "written" if not result.errors else "failed"
            )
        self.db.commit()

    def _audit(
        self,
        asset_id: str,
        action: str,
        status: str,
        details: Optional[dict] = None,
        error: Optional[str] = None,
    ) -> None:
        log = AuditLog(
            id=str(uuid.uuid4()),
            asset_id=asset_id,
            action=action,
            status=status,
            details_json=details,
            error_message=error,
        )
        self.db.add(log)
        self.db.commit()
