from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_active_user
from ..services.immich_client import ImmichClient, ImmichError
from ..config import settings as app_settings

router = APIRouter(prefix="/api/albums", tags=["albums"])


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


@router.get("")
def list_albums(
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """List Immich albums for bucket mapping using the current user's credentials."""
    client = _get_user_immich_client(db, current_user.id)
    try:
        albums = client.list_albums()
        return [
            {"id": a.get("id"), "albumName": a.get("albumName"), "assetCount": a.get("assetCount", 0)}
            for a in albums
        ]
    except ImmichError as e:
        raise HTTPException(status_code=502, detail=str(e))
