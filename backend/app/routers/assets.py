from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

from ..database import get_db
from ..models.asset import Asset
from ..models.suggested_classification import SuggestedClassification
from ..models.suggested_metadata import SuggestedMetadata
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
    return [_to_out(a) for a in assets]


@router.get("/count")
def count_assets(db: Session = Depends(get_db)):
    return {"count": db.query(Asset).count()}


class ClassificationDetail(BaseModel):
    id: str
    suggested_bucket_id: Optional[str]
    suggested_bucket_name: Optional[str]
    confidence: Optional[float]
    explanation: Optional[str]
    subalbum_suggestion: Optional[str]
    status: Optional[str]
    provider_name: Optional[str]
    override_bucket_id: Optional[str]
    override_bucket_name: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class MetadataDetail(BaseModel):
    id: str
    description_suggestion: Optional[str]
    tags: Optional[List[str]]
    approved_description: Optional[str]
    approved_tags: Optional[List[str]]
    writeback_status: Optional[str]
    provider_name: Optional[str]
    model_config = ConfigDict(from_attributes=True)


class AssetDetailOut(AssetOut):
    classification: Optional[ClassificationDetail] = None
    metadata_suggestion: Optional[MetadataDetail] = None


@router.get("/{asset_id}", response_model=AssetOut)
def get_asset(asset_id: str, db: Session = Depends(get_db)):
    a = db.query(Asset).filter(Asset.id == asset_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Asset not found")
    return _to_out(a)


@router.get("/{asset_id}/detail", response_model=AssetDetailOut)
def get_asset_detail(asset_id: str, db: Session = Depends(get_db)):
    """Full asset detail including latest classification and metadata suggestion."""
    a = db.query(Asset).filter(Asset.id == asset_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Asset not found")

    base = _to_out(a)

    # Latest classification (most recent by created_at)
    cls = (
        db.query(SuggestedClassification)
        .filter(SuggestedClassification.asset_id == asset_id)
        .order_by(SuggestedClassification.created_at.desc())
        .first()
    )

    # Latest metadata suggestion
    meta = (
        db.query(SuggestedMetadata)
        .filter(SuggestedMetadata.asset_id == asset_id)
        .order_by(SuggestedMetadata.created_at.desc())
        .first()
    )

    classification = None
    if cls:
        classification = ClassificationDetail(
            id=cls.id,
            suggested_bucket_id=cls.suggested_bucket_id,
            suggested_bucket_name=cls.suggested_bucket_name,
            confidence=cls.confidence,
            explanation=cls.explanation,
            subalbum_suggestion=cls.subalbum_suggestion,
            status=cls.status,
            provider_name=cls.provider_name,
            override_bucket_id=cls.override_bucket_id,
            override_bucket_name=cls.override_bucket_name,
            created_at=cls.created_at,
        )

    metadata_suggestion = None
    if meta:
        metadata_suggestion = MetadataDetail(
            id=meta.id,
            description_suggestion=meta.description_suggestion,
            tags=meta.tags_json,
            approved_description=meta.approved_description,
            approved_tags=meta.approved_tags_json,
            writeback_status=meta.writeback_status,
            provider_name=meta.provider_name,
        )

    return AssetDetailOut(
        **base.model_dump(),
        classification=classification,
        metadata_suggestion=metadata_suggestion,
    )
