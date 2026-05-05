from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional

from ..database import get_db
from ..dependencies import require_active_user
from ..models.asset import Asset
from ..schemas.asset import AssetOut

router = APIRouter(prefix="/api/assets", tags=["assets"])


def _to_out(a: Asset) -> AssetOut:
    return AssetOut(
        id=a.id,
        immich_id=a.immich_id,
        original_filename=a.original_filename,
        file_created_at=a.file_created_at,
        asset_type=a.asset_type,
        mime_type=a.mime_type,
        city=a.city,
        country=a.country,
        camera_make=a.camera_make,
        camera_model=a.camera_model,
        description=a.description,
        tags=a.tags_json,
        album_ids=a.album_ids_json,
        is_favorite=a.is_favorite,
        is_archived=a.is_archived,
        is_external_library=a.is_external_library,
        synced_at=a.synced_at,
        created_at=a.created_at,
    )


def _user_asset_query(db: Session, user_id: str):
    return db.query(Asset).filter(Asset.user_id == user_id)


def _apply_asset_filters(query, asset_type: Optional[str], q: Optional[str]):
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Asset.original_filename.ilike(like),
                Asset.description.ilike(like),
                Asset.city.ilike(like),
                Asset.country.ilike(like),
            )
        )
    return query


@router.get("", response_model=List[AssetOut])
def list_assets(
    page: int = 1,
    page_size: int = 50,
    asset_type: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    query = _apply_asset_filters(
        _user_asset_query(db, current_user.id), asset_type, q,
    )
    offset = (page - 1) * page_size
    assets = (
        query.order_by(Asset.file_created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return [_to_out(a) for a in assets]


@router.get("/count")
def count_assets(
    asset_type: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    query = _apply_asset_filters(
        _user_asset_query(db, current_user.id), asset_type, q,
    )
    return {"count": query.count()}


@router.get("/ids")
def list_asset_ids(
    asset_type: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    query = db.query(Asset.id).filter(Asset.user_id == current_user.id)
    query = _apply_asset_filters(query, asset_type, q)
    rows = query.order_by(Asset.file_created_at.desc()).all()
    return {"ids": [r[0] for r in rows]}


@router.get("/{asset_id}", response_model=AssetOut)
def get_asset(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    a = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.user_id == current_user.id,
    ).first()
    if not a:
        raise HTTPException(status_code=404, detail="Asset not found")
    return _to_out(a)
