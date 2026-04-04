"""
Shared FastAPI dependencies.
"""
from fastapi import Depends
from sqlalchemy.orm import Session
from .database import get_db
from .services.immich_client import ImmichClient
from .config import settings


def get_immich_client(db: Session = Depends(get_db)) -> ImmichClient:
    """
    Resolve the Immich client using credentials stored in the DB (via POST
    /api/settings/immich) and fall back to env vars.  This ensures runtime
    configuration always takes precedence over deployment defaults.
    """
    from .models.app_setting import AppSetting
    url_row = db.query(AppSetting).filter(AppSetting.key == "immich_url").first()
    key_row = db.query(AppSetting).filter(AppSetting.key == "immich_api_key").first()
    url = (url_row.value if url_row and url_row.value else None) or settings.IMMICH_URL
    api_key = (key_row.value if key_row and key_row.value else None) or settings.IMMICH_API_KEY
    return ImmichClient(url, api_key)
