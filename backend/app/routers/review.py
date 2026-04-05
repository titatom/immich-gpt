from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..dependencies import require_active_user
from ..models.asset import Asset
from ..models.suggested_classification import SuggestedClassification
from ..models.suggested_metadata import SuggestedMetadata
from ..schemas.review import (
    ReviewItemOut, ReviewApproveRequest, BulkReviewRequest, WritebackResult as WritebackResultSchema
)
from ..services.review_decision import ReviewDecisionService

router = APIRouter(prefix="/api/review", tags=["review"])


def _build_review_item(
    asset: Asset,
    classification: Optional[SuggestedClassification],
    metadata: Optional[SuggestedMetadata],
) -> ReviewItemOut:
    return ReviewItemOut(
        asset_id=asset.id,
        immich_id=asset.immich_id,
        original_filename=asset.original_filename,
        file_created_at=asset.file_created_at,
        asset_type=asset.asset_type,
        mime_type=asset.mime_type,
        city=asset.city,
        country=asset.country,
        camera_make=asset.camera_make,
        camera_model=asset.camera_model,
        current_description=asset.description,
        current_tags=asset.tags_json,
        classification_id=classification.id if classification else None,
        suggested_bucket_id=classification.suggested_bucket_id if classification else None,
        suggested_bucket_name=classification.suggested_bucket_name if classification else None,
        confidence=classification.confidence if classification else None,
        explanation=classification.explanation if classification else None,
        subalbum_suggestion=classification.subalbum_suggestion if classification else None,
        review_recommended=classification.review_recommended if classification else True,
        classification_status=classification.status if classification else "no_suggestion",
        metadata_id=metadata.id if metadata else None,
        description_suggestion=metadata.description_suggestion if metadata else None,
        tags_suggestion=metadata.tags_json if metadata else None,
        provider_name=classification.provider_name if classification else None,
        prompt_run_id=classification.prompt_run_id if classification else None,
    )


@router.get("/queue", response_model=List[ReviewItemOut])
def get_review_queue(
    status: str = "pending_review",
    bucket_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    user_asset_ids = db.query(Asset.id).filter(Asset.user_id == current_user.id).subquery()

    q = db.query(SuggestedClassification).filter(
        SuggestedClassification.status == status,
        SuggestedClassification.asset_id.in_(user_asset_ids),
    )
    if bucket_id:
        q = q.filter(SuggestedClassification.suggested_bucket_id == bucket_id)

    offset = (page - 1) * page_size
    classifications = q.order_by(
        SuggestedClassification.created_at.desc()
    ).offset(offset).limit(page_size).all()

    items = []
    for cls in classifications:
        asset = db.query(Asset).filter(Asset.id == cls.asset_id).first()
        if not asset:
            continue
        meta = db.query(SuggestedMetadata).filter(
            SuggestedMetadata.asset_id == cls.asset_id
        ).order_by(SuggestedMetadata.created_at.desc()).first()
        items.append(_build_review_item(asset, cls, meta))

    return items


@router.get("/queue/count")
def get_review_count(
    status: str = "pending_review",
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    user_asset_ids = db.query(Asset.id).filter(Asset.user_id == current_user.id).subquery()
    count = db.query(SuggestedClassification).filter(
        SuggestedClassification.status == status,
        SuggestedClassification.asset_id.in_(user_asset_ids),
    ).count()
    return {"count": count, "status": status}


@router.get("/queue/ids")
def get_review_queue_ids(
    status: str = "pending_review",
    bucket_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    user_asset_ids = db.query(Asset.id).filter(Asset.user_id == current_user.id).subquery()
    q = db.query(SuggestedClassification.asset_id).filter(
        SuggestedClassification.status == status,
        SuggestedClassification.asset_id.in_(user_asset_ids),
    )
    if bucket_id:
        q = q.filter(SuggestedClassification.suggested_bucket_id == bucket_id)
    rows = q.order_by(SuggestedClassification.created_at.desc()).all()
    return {"ids": [r[0] for r in rows]}


@router.get("/item/{asset_id}", response_model=ReviewItemOut)
def get_review_item(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.user_id == current_user.id,
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    classification = db.query(SuggestedClassification).filter(
        SuggestedClassification.asset_id == asset_id,
    ).order_by(SuggestedClassification.created_at.desc()).first()
    meta = db.query(SuggestedMetadata).filter(
        SuggestedMetadata.asset_id == asset_id,
    ).order_by(SuggestedMetadata.created_at.desc()).first()
    return _build_review_item(asset, classification, meta)


@router.post("/item/{asset_id}/approve")
def approve_asset(
    asset_id: str,
    body: ReviewApproveRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.user_id == current_user.id,
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    svc = ReviewDecisionService(db)
    try:
        result = svc.approve_asset(
            asset_id=asset_id,
            approved_bucket_id=body.approved_bucket_id,
            approved_bucket_name=body.approved_bucket_name,
            approved_description=body.approved_description,
            approved_tags=body.approved_tags,
            approved_subalbum=body.approved_subalbum,
            subalbum_approved=body.subalbum_approved,
            trigger_writeback=body.trigger_writeback,
        )
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/item/{asset_id}/reject")
def reject_asset(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.user_id == current_user.id,
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    svc = ReviewDecisionService(db)
    try:
        svc.reject_asset(asset_id)
        return {"rejected": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/bulk")
def bulk_review(
    body: BulkReviewRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    svc = ReviewDecisionService(db)
    results = []
    for asset_id in body.asset_ids:
        # Verify asset ownership
        asset = db.query(Asset).filter(
            Asset.id == asset_id,
            Asset.user_id == current_user.id,
        ).first()
        if not asset:
            results.append({"asset_id": asset_id, "status": "error", "error": "Asset not found"})
            continue
        try:
            if body.action == "approve_all":
                cls = db.query(SuggestedClassification).filter(
                    SuggestedClassification.asset_id == asset_id,
                    SuggestedClassification.status == "pending_review",
                ).first()
                meta = db.query(SuggestedMetadata).filter(
                    SuggestedMetadata.asset_id == asset_id,
                ).order_by(SuggestedMetadata.created_at.desc()).first()

                result = svc.approve_asset(
                    asset_id=asset_id,
                    approved_bucket_id=cls.suggested_bucket_id if cls else None,
                    approved_bucket_name=cls.suggested_bucket_name if cls else None,
                    approved_description=meta.description_suggestion if meta else None,
                    approved_tags=meta.tags_json if meta else None,
                    approved_subalbum=cls.subalbum_suggestion if cls else None,
                    subalbum_approved=False,
                    trigger_writeback=body.trigger_writeback,
                )
                results.append({"asset_id": asset_id, "status": "approved", **result.to_dict()})
            elif body.action == "reject_all":
                svc.reject_asset(asset_id)
                results.append({"asset_id": asset_id, "status": "rejected"})
        except Exception as e:
            results.append({"asset_id": asset_id, "status": "error", "error": str(e)})

    return {"results": results}
