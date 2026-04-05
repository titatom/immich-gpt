"""
Thumbnail proxy router.
Fetches thumbnails from Immich server-side and serves them to the browser.
"""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_active_user
from ..models.asset import Asset
from ..services.immich_client import ImmichClient, ImmichError
from ..config import settings as app_settings

router = APIRouter(prefix="/api/thumbnails", tags=["thumbnails"])


def _get_user_immich_client(db: Session, user_id: str) -> ImmichClient:
    from ..models.app_setting import AppSetting
    url_row = db.query(AppSetting).filter(
        AppSetting.user_id == user_id, AppSetting.key == "immich_url"
    ).first()
    key_row = db.query(AppSetting).filter(
        AppSetting.user_id == user_id, AppSetting.key == "immich_api_key"
    ).first()
    url = (url_row.value if url_row and url_row.value else None) or app_settings.IMMICH_URL
    api_key = (key_row.value if key_row and key_row.value else None) or app_settings.IMMICH_API_KEY
    return ImmichClient(url, api_key)


@router.get("/{asset_id}")
def get_thumbnail(
    asset_id: str,
    size: str = "thumbnail",
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """Proxy thumbnail from Immich using the current user's credentials."""
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.user_id == current_user.id,
    ).first()
    if not asset:
        # Also allow immich_id lookup for the same user
        asset = db.query(Asset).filter(
            Asset.immich_id == asset_id,
            Asset.user_id == current_user.id,
        ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    client = _get_user_immich_client(db, current_user.id)
    try:
        image_bytes = client.get_thumbnail(asset.immich_id, size=size)
        return Response(
            content=image_bytes,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=3600"},
        )
    except ImmichError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Could not fetch thumbnail from Immich: {e}",
        )


@router.get("/immich/{immich_id}")
def get_thumbnail_by_immich_id(
    immich_id: str,
    size: str = "thumbnail",
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """Proxy thumbnail directly by Immich asset ID using the current user's credentials."""
    client = _get_user_immich_client(db, current_user.id)
    try:
        image_bytes = client.get_thumbnail(immich_id, size=size)
        return Response(
            content=image_bytes,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=3600"},
        )
    except ImmichError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Could not fetch thumbnail: {e}",
        )
