import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..dependencies import require_active_user
from ..models.bucket import Bucket
from ..models.suggested_classification import SuggestedClassification
from ..schemas.bucket import BucketCreate, BucketUpdate, BucketOut

router = APIRouter(prefix="/api/buckets", tags=["buckets"])


def _to_out(b: Bucket) -> BucketOut:
    return BucketOut(
        id=b.id,
        name=b.name,
        description=b.description,
        enabled=b.enabled,
        priority=b.priority,
        mapping_mode=b.mapping_mode,
        immich_album_id=b.immich_album_id,
        classification_prompt=b.classification_prompt,
        examples=b.examples_json,
        negative_examples=b.negative_examples_json,
        confidence_threshold=b.confidence_threshold,
        created_at=b.created_at,
        updated_at=b.updated_at,
    )


@router.get("", response_model=List[BucketOut])
def list_buckets(
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    return [
        _to_out(b)
        for b in db.query(Bucket)
        .filter(Bucket.user_id == current_user.id)
        .order_by(Bucket.priority)
        .all()
    ]


@router.post("", response_model=BucketOut)
def create_bucket(
    body: BucketCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    existing = db.query(Bucket).filter(
        Bucket.user_id == current_user.id,
        Bucket.name == body.name,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Bucket '{body.name}' already exists")
    b = Bucket(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        name=body.name,
        description=body.description,
        enabled=body.enabled,
        priority=body.priority,
        mapping_mode=body.mapping_mode,
        immich_album_id=body.immich_album_id,
        classification_prompt=body.classification_prompt,
        examples_json=body.examples,
        negative_examples_json=body.negative_examples,
        confidence_threshold=body.confidence_threshold,
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return _to_out(b)


@router.get("/stats")
def bucket_stats(
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """
    Returns per-bucket classification counts broken down by status.
    Scoped to the current user's assets.

    IMPORTANT: must be registered before /{bucket_id} to avoid route shadowing.
    """
    from ..models.asset import Asset as AssetModel
    from sqlalchemy import select as sa_select

    user_asset_ids_stmt = sa_select(AssetModel.id).where(AssetModel.user_id == current_user.id)

    rows = (
        db.query(
            SuggestedClassification.suggested_bucket_name,
            SuggestedClassification.suggested_bucket_id,
            SuggestedClassification.status,
            func.count(SuggestedClassification.id).label("count"),
        )
        .filter(SuggestedClassification.asset_id.in_(user_asset_ids_stmt))
        .group_by(
            SuggestedClassification.suggested_bucket_name,
            SuggestedClassification.suggested_bucket_id,
            SuggestedClassification.status,
        )
        .all()
    )

    stats: dict = {}
    for row in rows:
        key = row.suggested_bucket_name or "unknown"
        if key not in stats:
            stats[key] = {
                "bucket_name": key,
                "bucket_id": row.suggested_bucket_id,
                "total": 0,
                "by_status": {},
            }
        stats[key]["by_status"][row.status] = row.count
        stats[key]["total"] += row.count

    return list(stats.values())


@router.get("/{bucket_id}", response_model=BucketOut)
def get_bucket(
    bucket_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    b = db.query(Bucket).filter(
        Bucket.id == bucket_id,
        Bucket.user_id == current_user.id,
    ).first()
    if not b:
        raise HTTPException(status_code=404, detail="Bucket not found")
    return _to_out(b)


@router.patch("/{bucket_id}", response_model=BucketOut)
def update_bucket(
    bucket_id: str,
    body: BucketUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    b = db.query(Bucket).filter(
        Bucket.id == bucket_id,
        Bucket.user_id == current_user.id,
    ).first()
    if not b:
        raise HTTPException(status_code=404, detail="Bucket not found")
    if body.name is not None:
        b.name = body.name
    if body.description is not None:
        b.description = body.description
    if body.enabled is not None:
        b.enabled = body.enabled
    if body.priority is not None:
        b.priority = body.priority
    if body.mapping_mode is not None:
        b.mapping_mode = body.mapping_mode
    if body.immich_album_id is not None:
        b.immich_album_id = body.immich_album_id
    if body.classification_prompt is not None:
        b.classification_prompt = body.classification_prompt
    if body.examples is not None:
        b.examples_json = body.examples
    if body.negative_examples is not None:
        b.negative_examples_json = body.negative_examples
    if body.confidence_threshold is not None:
        b.confidence_threshold = body.confidence_threshold
    db.commit()
    db.refresh(b)
    return _to_out(b)


@router.delete("/{bucket_id}")
def delete_bucket(
    bucket_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    b = db.query(Bucket).filter(
        Bucket.id == bucket_id,
        Bucket.user_id == current_user.id,
    ).first()
    if not b:
        raise HTTPException(status_code=404, detail="Bucket not found")
    db.delete(b)
    db.commit()
    return {"deleted": True}


@router.post("/reorder")
def reorder_buckets(
    order: List[dict],
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    for item in order:
        b = db.query(Bucket).filter(
            Bucket.id == item["id"],
            Bucket.user_id == current_user.id,
        ).first()
        if b:
            b.priority = item["priority"]
    db.commit()
    return {"reordered": True}
