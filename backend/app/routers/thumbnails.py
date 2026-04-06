"""
Thumbnail proxy router.
Fetches thumbnails from Immich server-side and serves them to the browser.
This avoids exposing private Immich URLs or credentials to the frontend.
"""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_immich_client
from ..models.asset import Asset
from ..services.immich_client import ImmichClient, ImmichError

router = APIRouter(prefix="/api/thumbnails", tags=["thumbnails"])


@router.get("/{asset_id}")
def get_thumbnail(
    asset_id: str,
    size: str = "thumbnail",
    db: Session = Depends(get_db),
    client: ImmichClient = Depends(get_immich_client),
):
    """
    Proxy thumbnail from Immich.
    asset_id is the internal DB id; we resolve to immich_id.
    """
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        asset = db.query(Asset).filter(Asset.immich_id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

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
    client: ImmichClient = Depends(get_immich_client),
):
    """Proxy thumbnail directly by Immich asset ID."""
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
