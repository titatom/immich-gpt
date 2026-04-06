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
from ..models.app_setting import AppSetting
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
    def __init__(
        self,
        db: Session,
        immich_client: Optional[ImmichClient] = None,
        user_id: Optional[str] = None,
    ):
        self.db = db
        self.immich = immich_client or ImmichClient()
        self.user_id = user_id

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

    def _get_behaviour_setting(self, key: str, default: bool) -> bool:
        q = self.db.query(AppSetting).filter(AppSetting.key == key)
        if self.user_id:
            q = q.filter(AppSetting.user_id == self.user_id)
        row = q.first()
        if row is None:
            return default
        return row.value.lower() not in ("false", "0", "no")

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

        # Read behaviour settings to decide whether to create new entities.
        allow_new_tags = self._get_behaviour_setting("allow_new_tags", True)
        allow_new_albums = self._get_behaviour_setting("allow_new_albums", True)

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
            try:
                if allow_new_tags:
                    # Normal mode: create tags that don't exist yet.
                    tag_objects = self.immich.get_or_create_tags(tags)
                else:
                    # Restricted mode: only apply tags that already exist; skip unknowns.
                    tag_objects = self.immich.get_existing_tags_only(tags)
                    skipped = len(tags) - len(tag_objects)
                    if skipped:
                        result.errors.append(
                            f"{skipped} suggested tag(s) skipped — not found in Immich "
                            "(existing-tags-only mode is enabled)."
                        )
                if tag_objects:
                    tag_ids = [t["id"] for t in tag_objects]
                    self.immich.tag_asset(asset.immich_id, tag_ids)
                    result.tags_written = True
                    self._audit(asset.id, "writeback_tags", "success",
                                {"tags": [t.get("name") for t in tag_objects]})
            except ImmichError as e:
                msg = f"Failed to write tags: {e}"
                result.errors.append(msg)
                self._audit(asset.id, "writeback_tags", "failed", error=msg)

        # Album assignment
        # Priority: subalbum name → bucket immich_album_id → create album from bucket name
        target_album_id: Optional[str] = None
        target_album_name: Optional[str] = None

        if subalbum:
            if allow_new_albums:
                # Normal mode: find or create the album.
                try:
                    album = self.immich.get_or_create_album(subalbum)
                    target_album_id = album.get("id")
                    target_album_name = subalbum
                except ImmichError as e:
                    result.errors.append(f"Failed to resolve subalbum '{subalbum}': {e}")
            else:
                # Restricted mode: only use the album if it already exists.
                album = self.immich.get_existing_album(subalbum)
                if album:
                    target_album_id = album.get("id")
                    target_album_name = subalbum
                else:
                    result.errors.append(
                        f"Subalbum '{subalbum}' not found in Immich and was not created "
                        "(existing-albums-only mode is enabled)."
                    )

        if not target_album_id and bucket_id:
            bucket = self.db.query(Bucket).filter(Bucket.id == bucket_id).first()
            if bucket and bucket.mapping_mode == "immich_trash":
                try:
                    self.immich.trash_assets([asset.immich_id])
                    result.album_assigned = True
                    self._audit(asset.id, "writeback_trash", "success",
                                {"immich_id": asset.immich_id})
                except ImmichError as e:
                    msg = f"Failed to trash asset in Immich: {e}"
                    result.errors.append(msg)
                    self._audit(asset.id, "writeback_trash", "failed", error=msg)
                # Skip album assignment — trashing is the action for this bucket.
                target_album_id = None
            elif bucket and bucket.mapping_mode == "immich_album":
                if bucket.immich_album_id:
                    target_album_id = bucket.immich_album_id
                    target_album_name = bucket.name
                else:
                    if allow_new_albums:
                        # Auto-create an album named after the bucket.
                        try:
                            album = self.immich.get_or_create_album(bucket.name)
                            target_album_id = album.get("id")
                            target_album_name = bucket.name
                            # Persist the created album id back to the bucket for next time.
                            bucket.immich_album_id = target_album_id
                            self.db.commit()
                        except ImmichError as e:
                            result.errors.append(f"Failed to create album for bucket '{bucket.name}': {e}")
                    else:
                        album = self.immich.get_existing_album(bucket.name)
                        if album:
                            target_album_id = album.get("id")
                            target_album_name = bucket.name
                            bucket.immich_album_id = target_album_id
                            self.db.commit()

        if target_album_id:
            try:
                self.immich.add_asset_to_album(target_album_id, [asset.immich_id])
                result.album_assigned = True
                self._audit(asset.id, "writeback_album", "success",
                            {"album_id": target_album_id, "album_name": target_album_name})
            except ImmichError as e:
                msg = f"Failed to add asset to album '{target_album_name}': {e}"
                result.errors.append(msg)
                self._audit(asset.id, "writeback_album", "failed", error=msg)

        if metadata_suggestion:
            metadata_suggestion.writeback_status = (
                "written" if not result.errors else "partial"
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
            user_id=self.user_id,
            asset_id=asset_id,
            action=action,
            status=status,
            details_json=details,
            error_message=error,
        )
        self.db.add(log)
        self.db.commit()
