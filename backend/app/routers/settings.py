from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from ..database import get_db
from ..schemas.provider import (
    ImmichSettingsUpdate, ImmichSettingsOut,
    ProviderConfigCreate, ProviderConfigUpdate, ProviderConfigOut,
)
from ..models.provider_config import ProviderConfig
from ..models.app_setting import AppSetting
from ..services.immich_client import ImmichClient, ImmichError
from ..config import settings
import uuid

router = APIRouter(prefix="/api/settings", tags=["settings"])

# Keys used in app_settings table
_KEY_IMMICH_URL = "immich_url"
_KEY_IMMICH_API_KEY = "immich_api_key"
_KEY_ALLOW_NEW_TAGS = "allow_new_tags"
_KEY_ALLOW_NEW_ALBUMS = "allow_new_albums"


def _get_immich_credentials(db: Session):
    """Return (url, api_key) from DB overrides, falling back to env vars."""
    url_row = db.query(AppSetting).filter(AppSetting.key == _KEY_IMMICH_URL).first()
    key_row = db.query(AppSetting).filter(AppSetting.key == _KEY_IMMICH_API_KEY).first()
    url = (url_row.value if url_row and url_row.value else None) or settings.IMMICH_URL
    api_key = (key_row.value if key_row and key_row.value else None) or settings.IMMICH_API_KEY
    return url, api_key


def _set_app_setting(db: Session, key: str, value: str) -> None:
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if row:
        row.value = value
    else:
        db.add(AppSetting(key=key, value=value))
    db.commit()


@router.get("/immich", response_model=ImmichSettingsOut)
def get_immich_settings(db: Session = Depends(get_db)):
    url, api_key = _get_immich_credentials(db)
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
def save_immich_settings(body: ImmichSettingsUpdate, db: Session = Depends(get_db)):
    """Persist Immich URL and API key to the database."""
    _set_app_setting(db, _KEY_IMMICH_URL, body.immich_url)
    if body.immich_api_key:
        _set_app_setting(db, _KEY_IMMICH_API_KEY, body.immich_api_key)
    try:
        client = ImmichClient(body.immich_url, body.immich_api_key)
        client.check_connectivity()
        count = client.get_asset_count()
        return ImmichSettingsOut(immich_url=body.immich_url, connected=True, asset_count=count)
    except ImmichError as e:
        return ImmichSettingsOut(immich_url=body.immich_url, connected=False, error=str(e))


@router.post("/immich/test")
def test_immich_connection(body: ImmichSettingsUpdate):
    try:
        client = ImmichClient(body.immich_url, body.immich_api_key)
        info = client.check_connectivity()
        count = client.get_asset_count()
        return {"connected": True, "asset_count": count, "info": info.get("info", {})}
    except ImmichError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/providers", response_model=List[ProviderConfigOut])
def list_providers(db: Session = Depends(get_db)):
    rows = db.query(ProviderConfig).all()
    return [_provider_to_out(r) for r in rows]


@router.post("/providers", response_model=ProviderConfigOut)
def upsert_provider(body: ProviderConfigCreate, db: Session = Depends(get_db)):
    existing = db.query(ProviderConfig).filter(
        ProviderConfig.provider_name == body.provider_name
    ).first()

    if body.is_default:
        db.query(ProviderConfig).update({"is_default": False})

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
def delete_provider(provider_name: str, db: Session = Depends(get_db)):
    row = db.query(ProviderConfig).filter(
        ProviderConfig.provider_name == provider_name
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Provider not found")
    db.delete(row)
    db.commit()
    return {"deleted": True}


@router.get("/providers/{provider_name}/test")
def test_provider(provider_name: str, db: Session = Depends(get_db)):
    from ..services.ai_provider import build_provider
    row = db.query(ProviderConfig).filter(
        ProviderConfig.provider_name == provider_name
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
        return {"connected": ok}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/providers/{provider_name}/models")
def list_provider_models(provider_name: str, db: Session = Depends(get_db)):
    """Fetch available models from the provider (OpenRouter/Ollama only)."""
    row = db.query(ProviderConfig).filter(
        ProviderConfig.provider_name == provider_name
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
def get_behaviour_settings(db: Session = Depends(get_db)):
    """Return AI behaviour settings (tag/album creation)."""
    def _get(key: str, default: bool) -> bool:
        row = db.query(AppSetting).filter(AppSetting.key == key).first()
        if row is None:
            return default
        return row.value.lower() not in ("false", "0", "no")

    return BehaviourSettings(
        allow_new_tags=_get(_KEY_ALLOW_NEW_TAGS, True),
        allow_new_albums=_get(_KEY_ALLOW_NEW_ALBUMS, True),
    )


@router.post("/behaviour", response_model=BehaviourSettings)
def save_behaviour_settings(body: BehaviourSettings, db: Session = Depends(get_db)):
    """Persist AI behaviour settings."""
    _set_app_setting(db, _KEY_ALLOW_NEW_TAGS, "true" if body.allow_new_tags else "false")
    _set_app_setting(db, _KEY_ALLOW_NEW_ALBUMS, "true" if body.allow_new_albums else "false")
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
