"""
RQ background tasks.
Decorated with rq.job so RQ can auto-retry on transient failures.
"""
from contextlib import nullcontext
from typing import Optional, List

from ..database import SessionLocal
from ..services.job_progress import JobProgressService
from ..services.asset_sync import AssetSyncService
from ..services.immich_client import ImmichClient
from ..services.routing_classification import RoutingClassificationOrchestrator
from ..services.ai_provider import build_provider
from ..services.secret_store import decrypt_secret
from ..models.provider_config import ProviderConfig


def _immich_client_context(client):
    """Use ImmichClient pooling when available while keeping simple test fakes valid."""
    if hasattr(client, "__enter__") and hasattr(client, "__exit__"):
        return client
    return nullcontext(client)


def _get_user_immich_client(db, user_id: Optional[str]) -> ImmichClient:
    """Resolve Immich credentials for a specific user."""
    from ..models.app_setting import AppSetting
    from ..config import settings
    if not user_id:
        raise ValueError("Job is missing an owner")
    url_row = db.query(AppSetting).filter(
        AppSetting.user_id == user_id, AppSetting.key == "immich_url"
    ).first()
    key_row = db.query(AppSetting).filter(
        AppSetting.user_id == user_id, AppSetting.key == "immich_api_key"
    ).first()
    url = (url_row.value if url_row and url_row.value else None) or settings.IMMICH_URL
    stored_key = key_row.value if key_row and key_row.value else None
    api_key = decrypt_secret(stored_key) if stored_key else settings.IMMICH_API_KEY
    return ImmichClient(url, api_key)


def run_asset_sync(
    job_id: str,
    scope: str = "all",
    album_ids: Optional[List[str]] = None,
    user_id: Optional[str] = None,
    run_routing_after: bool = False,
) -> dict:
    db = SessionLocal()
    try:
        from ..models.job_run import JobRun as _JobRun

        job_svc = JobProgressService(db)
        # Only reset counters for RQ automatic retries (job is in "failed" state).
        # For user-initiated resumes the job is already "queued" — preserve prior progress.
        current_job = job_svc.get_job(job_id)
        if current_job and current_job.status == "failed":
            job_svc.reset_for_retry(job_id)
        job_svc.start_job(job_id)

        scope_label = {
            "all": "all assets",
            "favorites": "favourited assets",
            "albums": f"{len(album_ids or [])} album(s)",
        }.get(scope, scope)

        job_svc.update_progress(
            job_id, status="syncing_assets",
            current_step=f"Syncing {scope_label} from Immich",
            log_line=f"Asset sync started (scope: {scope_label})",
        )

        def progress_cb(msg: str):
            job_svc.update_progress(job_id, log_line=msg, flush=False)

        def should_stop() -> bool:
            db.expire_all()
            j = db.query(_JobRun).filter(_JobRun.id == job_id).first()
            return j is not None and j.status in ("paused", "cancelled")

        with _immich_client_context(_get_user_immich_client(db, user_id)) as immich:
            sync_svc = AssetSyncService(db, immich, user_id=user_id)

            if scope == "favorites":
                result = sync_svc.sync_favorites(
                    job_progress_callback=progress_cb,
                    should_stop=should_stop,
                )
            elif scope == "albums" and album_ids:
                result = sync_svc.sync_albums(
                    album_ids,
                    job_progress_callback=progress_cb,
                    should_stop=should_stop,
                )
            else:
                result = sync_svc.sync_all(
                    job_progress_callback=progress_cb,
                    should_stop=should_stop,
                )

        job_svc.flush()
        db.expire_all()
        j = db.query(_JobRun).filter(_JobRun.id == job_id).first()
        if j and j.status not in ("paused", "cancelled"):
            job_svc.complete_job(
                job_id,
                message=(
                    f"Sync complete. Created: {result['created']}, "
                    f"Updated: {result['updated']}, Errors: {result['errors']}"
                ),
            )
            if run_routing_after:
                from ..workers.executor import enqueue_routing_classification
                enqueue_routing_classification(db, user_id=user_id, force=False)
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


def run_routing_classification(
    job_id: str,
    plan_id: Optional[str] = None,
    asset_ids: Optional[List[str]] = None,
    limit: Optional[int] = None,
    force: bool = False,
    user_id: Optional[str] = None,
) -> dict:
    """Background task: classify assets against the user's routing tree."""
    db = SessionLocal()
    try:
        if not user_id:
            raise ValueError("Job is missing an owner")
        q = db.query(ProviderConfig)
        q = q.filter(ProviderConfig.user_id == user_id)
        provider_cfg = q.filter(
            ProviderConfig.is_default == True,
            ProviderConfig.enabled == True,
        ).first()
        if not provider_cfg:
            provider_cfg = q.filter(ProviderConfig.enabled == True).first()
        if not provider_cfg:
            from ..config import settings
            if settings.OPENAI_API_KEY:
                provider = build_provider("openai", {
                    "api_key": settings.OPENAI_API_KEY,
                    "model_name": settings.OPENAI_MODEL,
                })
            else:
                raise ValueError(
                    "No AI provider configured. Set OPENAI_API_KEY or configure a provider."
                )
        else:
            cfg_dict = {
                "api_key": decrypt_secret(provider_cfg.api_key_encrypted) or "",
                "model_name": provider_cfg.model_name,
                "base_url": provider_cfg.base_url,
            }
            if provider_cfg.extra_config_json:
                cfg_dict.update(provider_cfg.extra_config_json)
            provider = build_provider(provider_cfg.provider_name, cfg_dict)

        with _immich_client_context(_get_user_immich_client(db, user_id)) as immich:
            orch = RoutingClassificationOrchestrator(
                db, provider, user_id=user_id, immich_client=immich,
            )
            orch.run_classification_job(
                job_id, asset_ids=asset_ids, limit=limit, force=force, plan_id=plan_id,
            )
        return {"status": "done"}

    except Exception as e:
        db.rollback()
        try:
            JobProgressService(db).fail_job(job_id, str(e))
        except Exception:
            pass
        raise
    finally:
        db.close()
