import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from ..database import get_db
from ..dependencies import require_active_user
from ..schemas.provider import (
    ImmichSettingsUpdate, ImmichSettingsOut,
    ProviderConfigCreate, ProviderConfigUpdate, ProviderConfigOut,
)
from ..models.provider_config import ProviderConfig
from ..models.app_setting import AppSetting
from ..services.immich_client import ImmichClient, ImmichError

router = APIRouter(prefix="/api/settings", tags=["settings"])

_KEY_IMMICH_URL = "immich_url"
_KEY_IMMICH_API_KEY = "immich_api_key"
_KEY_ALLOW_NEW_TAGS = "allow_new_tags"
_KEY_ALLOW_NEW_ALBUMS = "allow_new_albums"


def _get_setting(db: Session, user_id: str, key: str) -> Optional[str]:
    row = db.query(AppSetting).filter(
        AppSetting.user_id == user_id, AppSetting.key == key
    ).first()
    return row.value if row else None


def _set_setting(db: Session, user_id: str, key: str, value: str) -> None:
    row = db.query(AppSetting).filter(
        AppSetting.user_id == user_id, AppSetting.key == key
    ).first()
    if row:
        row.value = value
    else:
        db.add(AppSetting(id=str(uuid.uuid4()), user_id=user_id, key=key, value=value))
    db.commit()


def _get_immich_credentials(db: Session, user_id: str):
    from ..config import settings
    url = _get_setting(db, user_id, _KEY_IMMICH_URL) or settings.IMMICH_URL
    api_key = _get_setting(db, user_id, _KEY_IMMICH_API_KEY) or settings.IMMICH_API_KEY
    return url, api_key


@router.get("/immich", response_model=ImmichSettingsOut)
def get_immich_settings(
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    url, api_key = _get_immich_credentials(db, current_user.id)
    if not url:
        return ImmichSettingsOut(immich_url="", connected=False, error="Not configured")
    try:
        client = ImmichClient(url, api_key)
        client.check_connectivity()
        count = client.get_asset_count()
        return ImmichSettingsOut(immich_url=url, connected=True, asset_count=count)
    except ImmichError as e:
        return ImmichSettingsOut(immich_url=url, connected=False, error=str(e))


@router.post("/immich", response_model=ImmichSettingsOut)
def save_immich_settings(
    body: ImmichSettingsUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    _set_setting(db, current_user.id, _KEY_IMMICH_URL, body.immich_url)
    if body.immich_api_key:
        _set_setting(db, current_user.id, _KEY_IMMICH_API_KEY, body.immich_api_key)
    try:
        client = ImmichClient(body.immich_url, body.immich_api_key)
        client.check_connectivity()
        count = client.get_asset_count()
        return ImmichSettingsOut(immich_url=body.immich_url, connected=True, asset_count=count)
    except ImmichError as e:
        return ImmichSettingsOut(immich_url=body.immich_url, connected=False, error=str(e))


@router.post("/immich/test")
def test_immich_connection(
    body: ImmichSettingsUpdate,
    _user=Depends(require_active_user),
):
    try:
        client = ImmichClient(body.immich_url, body.immich_api_key)
        info = client.check_connectivity()
        count = client.get_asset_count()
        return {"connected": True, "asset_count": count, "info": info.get("info", {})}
    except ImmichError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/providers", response_model=List[ProviderConfigOut])
def list_providers(
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    rows = db.query(ProviderConfig).filter(
        ProviderConfig.user_id == current_user.id
    ).all()
    return [_provider_to_out(r) for r in rows]


@router.post("/providers", response_model=ProviderConfigOut)
def upsert_provider(
    body: ProviderConfigCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    existing = db.query(ProviderConfig).filter(
        ProviderConfig.user_id == current_user.id,
        ProviderConfig.provider_name == body.provider_name,
    ).first()

    if body.is_default:
        db.query(ProviderConfig).filter(
            ProviderConfig.user_id == current_user.id
        ).update({"is_default": False})

    if existing:
        existing.enabled = body.enabled
        existing.is_default = body.is_default
        if body.api_key:
            existing.api_key_encrypted = body.api_key
        if body.base_url is not None:
            existing.base_url = body.base_url
        if body.model_name is not None:
            existing.model_name = body.model_name
        if body.extra_config is not None:
            existing.extra_config_json = body.extra_config
        db.commit()
        db.refresh(existing)
        return _provider_to_out(existing)
    else:
        row = ProviderConfig(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            provider_name=body.provider_name,
            enabled=body.enabled,
            is_default=body.is_default,
            api_key_encrypted=body.api_key,
            base_url=body.base_url,
            model_name=body.model_name,
            extra_config_json=body.extra_config,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return _provider_to_out(row)


@router.delete("/providers/{provider_name}")
def delete_provider(
    provider_name: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    row = db.query(ProviderConfig).filter(
        ProviderConfig.user_id == current_user.id,
        ProviderConfig.provider_name == provider_name,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Provider not found")
    db.delete(row)
    db.commit()
    return {"deleted": True}


@router.get("/providers/{provider_name}/test")
def test_provider(
    provider_name: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    from ..services.ai_provider import build_provider
    row = db.query(ProviderConfig).filter(
        ProviderConfig.user_id == current_user.id,
        ProviderConfig.provider_name == provider_name,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Provider not found")
    try:
        p = build_provider(provider_name, {
            "api_key": row.api_key_encrypted or "",
            "model_name": row.model_name,
            "base_url": row.base_url,
        })
        ok = p.health_check()
        if not ok:
            return {"connected": False, "error": "Provider unreachable or invalid API key"}
        return {"connected": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/providers/{provider_name}/models")
def list_provider_models(
    provider_name: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    row = db.query(ProviderConfig).filter(
        ProviderConfig.user_id == current_user.id,
        ProviderConfig.provider_name == provider_name,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Provider not found")
    try:
        if provider_name == "openrouter":
            import httpx
            r = httpx.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {row.api_key_encrypted or ''}"},
                timeout=10,
            )
            r.raise_for_status()
            data = r.json().get("data", [])
            return [{"id": m["id"], "name": m.get("name", m["id"])} for m in data]
        elif provider_name == "ollama":
            import httpx
            base = row.base_url or "http://localhost:11434"
            r = httpx.get(f"{base}/api/tags", timeout=10)
            r.raise_for_status()
            models = r.json().get("models", [])
            return [{"id": m["name"], "name": m["name"]} for m in models]
        else:
            raise HTTPException(status_code=400, detail=f"Model listing not supported for {provider_name}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


class BehaviourSettings(BaseModel):
    allow_new_tags: bool = True
    allow_new_albums: bool = True


@router.get("/behaviour", response_model=BehaviourSettings)
def get_behaviour_settings(
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    def _get(key: str, default: bool) -> bool:
        val = _get_setting(db, current_user.id, key)
        if val is None:
            return default
        return val.lower() not in ("false", "0", "no")

    return BehaviourSettings(
        allow_new_tags=_get(_KEY_ALLOW_NEW_TAGS, True),
        allow_new_albums=_get(_KEY_ALLOW_NEW_ALBUMS, True),
    )


@router.post("/behaviour", response_model=BehaviourSettings)
def save_behaviour_settings(
    body: BehaviourSettings,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    _set_setting(db, current_user.id, _KEY_ALLOW_NEW_TAGS, "true" if body.allow_new_tags else "false")
    _set_setting(db, current_user.id, _KEY_ALLOW_NEW_ALBUMS, "true" if body.allow_new_albums else "false")
    return body


def _provider_to_out(row: ProviderConfig) -> ProviderConfigOut:
    return ProviderConfigOut(
        id=row.id,
        provider_name=row.provider_name,
        enabled=row.enabled,
        is_default=row.is_default,
        base_url=row.base_url,
        model_name=row.model_name,
        has_api_key=bool(row.api_key_encrypted),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
