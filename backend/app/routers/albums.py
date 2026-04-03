from fastapi import APIRouter, HTTPException
from ..services.immich_client import ImmichClient, ImmichError

router = APIRouter(prefix="/api/albums", tags=["albums"])


@router.get("")
def list_albums():
    """List Immich albums for bucket mapping."""
    try:
        client = ImmichClient()
        albums = client.list_albums()
        return [
            {"id": a.get("id"), "albumName": a.get("albumName"), "assetCount": a.get("assetCount", 0)}
            for a in albums
        ]
    except ImmichError as e:
        raise HTTPException(status_code=502, detail=str(e))
