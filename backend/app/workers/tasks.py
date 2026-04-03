"""
RQ background tasks.
Decorated with rq.job so RQ can auto-retry on transient failures.
"""
from rq.job import Retry
from ..database import SessionLocal
from ..services.job_progress import JobProgressService
from ..services.asset_sync import AssetSyncService
from ..services.immich_client import ImmichClient
from ..services.classification_orchestrator import ClassificationOrchestrator
from ..services.ai_provider import build_provider
from ..models.provider_config import ProviderConfig
from typing import Optional, List


def run_asset_sync(job_id: str) -> dict:
    db = SessionLocal()
    try:
        job_svc = JobProgressService(db)
        # Reset counters in case this is a retry
        job_svc.reset_for_retry(job_id)
        job_svc.start_job(job_id)
        job_svc.update_progress(
            job_id, status="syncing_assets",
            current_step="Syncing assets from Immich",
            log_line="Asset sync started",
        )

        def progress_cb(msg: str):
            job_svc.update_progress(job_id, log_line=msg)

        immich = ImmichClient()
        sync_svc = AssetSyncService(db, immich)
        result = sync_svc.sync_all(job_progress_callback=progress_cb)

        job_svc.complete_job(
            job_id,
            message=(
                f"Sync complete. Created: {result['created']}, "
                f"Updated: {result['updated']}, Errors: {result['errors']}"
            ),
        )
        return result

    except Exception as e:
        db.rollback()
        try:
            JobProgressService(db).fail_job(job_id, str(e))
        except Exception:
            pass
        raise
    finally:
        db.close()


def run_classification(
    job_id: str,
    asset_ids: Optional[List[str]] = None,
    limit: Optional[int] = None,
    force: bool = False,
) -> dict:
    db = SessionLocal()
    try:
        provider_cfg = db.query(ProviderConfig).filter(
            ProviderConfig.is_default == True,
            ProviderConfig.enabled == True,
        ).first()

        if not provider_cfg:
            provider_cfg = db.query(ProviderConfig).filter(
                ProviderConfig.enabled == True
            ).first()

        if not provider_cfg:
            from ..config import settings
            if settings.OPENAI_API_KEY:
                provider_cfg_dict = {
                    "api_key": settings.OPENAI_API_KEY,
                    "model_name": settings.OPENAI_MODEL,
                }
                provider = build_provider("openai", provider_cfg_dict)
            else:
                raise ValueError(
                    "No AI provider configured. Set OPENAI_API_KEY or configure a provider."
                )
        else:
            cfg_dict = {
                "api_key": provider_cfg.api_key_encrypted or "",
                "model_name": provider_cfg.model_name,
                "base_url": provider_cfg.base_url,
            }
            if provider_cfg.extra_config_json:
                cfg_dict.update(provider_cfg.extra_config_json)
            provider = build_provider(provider_cfg.provider_name, cfg_dict)

        orchestrator = ClassificationOrchestrator(db, provider)
        orchestrator.run_classification_job(job_id, asset_ids=asset_ids, limit=limit, force=force)
        return {"status": "completed"}

    except Exception as e:
        db.rollback()
        try:
            JobProgressService(db).fail_job(job_id, str(e))
        except Exception:
            pass
        raise
    finally:
        db.close()
