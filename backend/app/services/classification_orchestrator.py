"""
ClassificationOrchestrator: end-to-end asset processing pipeline.
Processes assets one-by-one with AI.
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from ..models.asset import Asset
from ..models.bucket import Bucket
from ..models.prompt_run import PromptRun
from ..models.suggested_classification import SuggestedClassification
from ..models.suggested_metadata import SuggestedMetadata
from ..models.audit_log import AuditLog
from ..services.immich_client import ImmichClient
from ..services.image_preparation import ImagePreparationService
from ..services.ai_provider import AIProvider, AIClassificationResult
from ..services.prompt_assembly import PromptAssemblyService
from ..services.job_progress import JobProgressService


class ClassificationOrchestrator:
    def __init__(
        self,
        db: Session,
        provider: AIProvider,
        immich_client: Optional[ImmichClient] = None,
    ):
        self.db = db
        self.provider = provider
        self.immich = immich_client or ImmichClient()
        self.image_service = ImagePreparationService(self.immich)
        self.prompt_service = PromptAssemblyService(db)
        self.job_service = JobProgressService(db)

    def run_classification_job(
        self,
        job_id: str,
        asset_ids: Optional[List[str]] = None,
        limit: Optional[int] = None,
        force: bool = False,
    ) -> None:
        """
        Main entry point for background classification job.
        Processes each asset one by one.
        """
        self.job_service.start_job(job_id)
        self.job_service.update_progress(
            job_id, status="syncing_assets",
            current_step="Loading assets",
            log_line="Starting classification job",
        )

        try:
            assets = self._load_assets(asset_ids, limit, force=force)
            total = len(assets)
            self.job_service.update_progress(
                job_id,
                total=total,
                log_line=f"Found {total} assets to process",
            )

            buckets = self.db.query(Bucket).filter(Bucket.enabled == True).order_by(Bucket.priority).all()
            if not buckets:
                self.job_service.fail_job(job_id, "No enabled buckets configured")
                return

            for idx, asset in enumerate(assets):
                self.job_service.update_progress(
                    job_id,
                    status="preparing_image",
                    current_step=f"Processing {asset.original_filename or asset.immich_id}",
                    processed=idx,
                    log_line=f"Processing asset {idx + 1}/{total}: {asset.immich_id}",
                )
                try:
                    self._process_asset(job_id, asset, buckets)
                    self.job_service.update_progress(
                        job_id,
                        processed=idx + 1,
                        success_delta=1,
                        log_line=f"✓ Asset {asset.immich_id} classified",
                    )
                except Exception as e:
                    self.job_service.update_progress(
                        job_id,
                        processed=idx + 1,
                        error_delta=1,
                        log_line=f"✗ Error on {asset.immich_id}: {str(e)[:200]}",
                    )
                    self._log_audit(asset.id, job_id, "classification_error", "failed", error=str(e))

            self.job_service.complete_job(
                job_id,
                message=f"Completed. {total} assets processed.",
            )

        except Exception as e:
            self.job_service.fail_job(job_id, f"Job failed: {str(e)}")
            raise

    def _process_asset(self, job_id: str, asset: Asset, buckets: List[Bucket]) -> None:
        """Process a single asset through the full pipeline."""
        metadata = self._asset_to_metadata_dict(asset)

        # Step 1: prepare image
        self.job_service.update_progress(
            job_id, status="preparing_image",
            log_line=f"  Fetching thumbnail for {asset.immich_id}",
        )
        image_payload = None
        try:
            image_payload = self.image_service.prepare_for_provider(asset.immich_id)
        except Exception as e:
            self.job_service.update_progress(
                job_id,
                log_line=f"  Warning: image prep failed ({e}), proceeding without image",
            )

        # Step 2: assemble prompt
        self.job_service.update_progress(job_id, status="classifying_ai")
        messages = self.prompt_service.assemble_classification_messages(metadata, buckets)
        prompt_record = self.prompt_service.get_assembled_prompt_record(metadata, buckets)

        # Step 3: AI call
        prompt_run = PromptRun(
            id=str(uuid.uuid4()),
            asset_id=asset.id,
            job_run_id=job_id,
            provider_name=self.provider.provider_name,
            assembled_prompt_json=prompt_record,
            status="pending",
        )
        self.db.add(prompt_run)
        self.db.flush()

        try:
            result: AIClassificationResult = self.provider.classify_asset(
                messages, image_payload
            )
            prompt_run.raw_response = result.model_dump_json()
            prompt_run.parsed_response_json = result.model_dump()
            prompt_run.status = "success"
        except Exception as e:
            prompt_run.status = "failed"
            prompt_run.error_message = str(e)
            self.db.commit()
            raise

        # Step 4: validate and save
        self.job_service.update_progress(job_id, status="validating_result")
        bucket = self._resolve_bucket(result.bucket_name, buckets)

        self.job_service.update_progress(job_id, status="saving_suggestion")
        self._save_suggestions(asset, result, bucket, prompt_run.id)
        self.db.commit()

    def _load_assets(
        self,
        asset_ids: Optional[List[str]],
        limit: Optional[int],
        force: bool = False,
    ) -> List[Asset]:
        q = self.db.query(Asset)
        if asset_ids:
            q = q.filter(Asset.id.in_(asset_ids))
        elif not force:
            # Skip assets that already have a pending or approved classification
            classified_ids = self.db.query(SuggestedClassification.asset_id).filter(
                SuggestedClassification.status.in_(["pending_review", "approved"])
            ).subquery()
            q = q.filter(~Asset.id.in_(classified_ids))
        if limit:
            q = q.limit(limit)
        return q.all()

    def _asset_to_metadata_dict(self, asset: Asset) -> Dict[str, Any]:
        return {
            "original_filename": asset.original_filename,
            "file_created_at": str(asset.file_created_at) if asset.file_created_at else None,
            "asset_type": asset.asset_type,
            "mime_type": asset.mime_type,
            "city": asset.city,
            "country": asset.country,
            "camera_make": asset.camera_make,
            "camera_model": asset.camera_model,
            "description": asset.description,
            "tags": asset.tags_json or [],
            "is_favorite": asset.is_favorite,
        }

    def _resolve_bucket(self, bucket_name: str, buckets: List[Bucket]) -> Optional[Bucket]:
        for b in buckets:
            if b.name.lower() == bucket_name.lower():
                return b
        # Fuzzy fallback - return first enabled bucket
        return buckets[0] if buckets else None

    def _save_suggestions(
        self,
        asset: Asset,
        result: AIClassificationResult,
        bucket: Optional[Bucket],
        prompt_run_id: str,
    ) -> None:
        # Remove any previous pending suggestions for this asset
        self.db.query(SuggestedClassification).filter(
            SuggestedClassification.asset_id == asset.id,
            SuggestedClassification.status == "pending_review",
        ).delete()
        self.db.query(SuggestedMetadata).filter(
            SuggestedMetadata.asset_id == asset.id,
        ).delete()

        classification = SuggestedClassification(
            id=str(uuid.uuid4()),
            asset_id=asset.id,
            suggested_bucket_id=bucket.id if bucket else None,
            suggested_bucket_name=result.bucket_name,
            confidence=result.confidence,
            explanation=result.explanation,
            subalbum_suggestion=result.subalbum_suggestion,
            review_recommended=result.review_recommended,
            provider_name=self.provider.provider_name,
            prompt_run_id=prompt_run_id,
            status="pending_review",
        )
        self.db.add(classification)

        metadata = SuggestedMetadata(
            id=str(uuid.uuid4()),
            asset_id=asset.id,
            description_suggestion=result.description_suggestion,
            tags_json=result.tags,
            provider_name=self.provider.provider_name,
            prompt_run_id=prompt_run_id,
        )
        self.db.add(metadata)

    def _log_audit(
        self,
        asset_id: str,
        job_id: str,
        action: str,
        status: str,
        error: Optional[str] = None,
    ) -> None:
        log = AuditLog(
            id=str(uuid.uuid4()),
            asset_id=asset_id,
            job_run_id=job_id,
            action=action,
            status=status,
            error_message=error,
        )
        self.db.add(log)
        self.db.commit()
