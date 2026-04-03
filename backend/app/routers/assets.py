from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..models.asset import Asset
from ..schemas.asset import AssetOut

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("", response_model=List[AssetOut])
def list_assets(
    page: int = 1,
    page_size: int = 50,
    asset_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Asset)
    if asset_type:
        q = q.filter(Asset.asset_type == asset_type)
    offset = (page - 1) * page_size
    assets = q.order_by(Asset.file_created_at.desc()).offset(offset).limit(page_size).all()

    return [
        AssetOut(
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
            is_favorite=a.is_favorite,
            is_archived=a.is_archived,
            is_external_library=a.is_external_library,
            synced_at=a.synced_at,
            created_at=a.created_at,
        )
        for a in assets
    ]


@router.get("/count")
def count_assets(db: Session = Depends(get_db)):
    return {"count": db.query(Asset).count()}


@router.get("/{asset_id}", response_model=AssetOut)
def get_asset(asset_id: str, db: Session = Depends(get_db)):
    a = db.query(Asset).filter(Asset.id == asset_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Asset not found")
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
        is_favorite=a.is_favorite,
        is_archived=a.is_archived,
        is_external_library=a.is_external_library,
        synced_at=a.synced_at,
        created_at=a.created_at,
    )
