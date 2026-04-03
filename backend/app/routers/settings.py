from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..schemas.provider import (
    ImmichSettingsUpdate, ImmichSettingsOut,
    ProviderConfigCreate, ProviderConfigUpdate, ProviderConfigOut,
)
from ..models.provider_config import ProviderConfig
from ..services.immich_client import ImmichClient, ImmichError
from ..config import settings
import uuid

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/immich", response_model=ImmichSettingsOut)
def get_immich_settings():
    url = settings.IMMICH_URL
    if not url:
        return ImmichSettingsOut(immich_url="", connected=False, error="Not configured")
    try:
        client = ImmichClient(url, settings.IMMICH_API_KEY)
        info = client.check_connectivity()
        count = client.get_asset_count()
        return ImmichSettingsOut(immich_url=url, connected=True, asset_count=count)
    except ImmichError as e:
        return ImmichSettingsOut(immich_url=url, connected=False, error=str(e))


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
