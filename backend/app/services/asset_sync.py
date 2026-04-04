"""
Asset sync service: pulls assets from Immich and stores them locally.
"""
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from ..models.asset import Asset
from ..services.immich_client import ImmichClient


def _parse_dt(val: Any) -> Optional[datetime]:
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
    except Exception:
        return None


class AssetSyncService:
    def __init__(self, db: Session, immich_client: Optional[ImmichClient] = None):
        self.db = db
        self.immich = immich_client or ImmichClient()

    def sync_all(
        self,
        job_progress_callback=None,
        page_size: int = 100,
    ) -> Dict[str, int]:
        """Sync all assets from Immich."""
        return self._sync_paged(
            fetch_fn=lambda page: self.immich.list_assets(page=page, page_size=page_size),
            job_progress_callback=job_progress_callback,
            page_size=page_size,
        )

    def sync_favorites(
        self,
        job_progress_callback=None,
        page_size: int = 100,
    ) -> Dict[str, int]:
        """Sync only favorited assets from Immich."""
        return self._sync_paged(
            fetch_fn=lambda page: self.immich.list_assets(
                page=page, page_size=page_size, is_favorite=True
            ),
            job_progress_callback=job_progress_callback,
            page_size=page_size,
        )

    def sync_album(
        self,
        album_id: str,
        job_progress_callback=None,
        page_size: int = 100,
    ) -> Dict[str, int]:
        """Sync assets from a specific album."""
        return self._sync_paged(
            fetch_fn=lambda page: self.immich.list_album_assets(
                album_id=album_id, page=page, page_size=page_size
            ),
            job_progress_callback=job_progress_callback,
            page_size=page_size,
        )

    def sync_albums(
        self,
        album_ids: List[str],
        job_progress_callback=None,
        page_size: int = 100,
    ) -> Dict[str, int]:
        """Sync assets from multiple albums."""
        total_created = total_updated = total_errors = 0
        for album_id in album_ids:
            if job_progress_callback:
                job_progress_callback(f"Syncing album {album_id}")
            result = self.sync_album(album_id, job_progress_callback=job_progress_callback, page_size=page_size)
            total_created += result["created"]
            total_updated += result["updated"]
            total_errors += result["errors"]
        synced = total_created + total_updated
        return {"synced": synced, "created": total_created, "updated": total_updated, "errors": total_errors}

    def _sync_paged(
        self,
        fetch_fn,
        job_progress_callback=None,
        page_size: int = 100,
    ) -> Dict[str, int]:
        created = updated = errors = 0
        page = 1
        synced_at = datetime.utcnow()

        while True:
            if job_progress_callback:
                job_progress_callback(f"Fetching page {page}")
            try:
                raw_assets = fetch_fn(page)
            except Exception as e:
                if job_progress_callback:
                    job_progress_callback(f"Error fetching page {page}: {e}")
                break

            if not raw_assets:
                break

            for raw in raw_assets:
                try:
                    c, u = self._upsert_asset(raw, synced_at)
                    created += c
                    updated += u
                except Exception:
                    errors += 1

            if len(raw_assets) < page_size:
                break
            page += 1

        return {"synced": created + updated, "created": created, "updated": updated, "errors": errors}

    def _upsert_asset(self, raw: Dict[str, Any], synced_at: datetime):
        immich_id = raw.get("id")
        if not immich_id:
            return 0, 0

        existing = self.db.query(Asset).filter(Asset.immich_id == immich_id).first()
        exif = raw.get("exifInfo") or {}
        people = raw.get("people") or []
        tags = [t.get("name") for t in (raw.get("tags") or []) if t.get("name")]

        data = {
            "immich_id": immich_id,
            "original_filename": raw.get("originalFileName"),
            "file_created_at": _parse_dt(raw.get("fileCreatedAt")),
            "file_modified_at": _parse_dt(raw.get("fileModifiedAt")),
            "local_date_time": _parse_dt(raw.get("localDateTime")),
            "asset_type": raw.get("type"),
            "mime_type": raw.get("originalMimeType"),
            "duration": raw.get("duration"),
            "is_favorite": raw.get("isFavorite", False),
            "is_archived": raw.get("isArchived", False),
            "is_trashed": raw.get("isTrashed", False),
            "is_external_library": self.immich.is_external_library_asset(raw),
            "city": exif.get("city"),
            "country": exif.get("country"),
            "camera_make": exif.get("make"),
            "camera_model": exif.get("model"),
            "description": raw.get("exifInfo", {}).get("description") if raw.get("exifInfo") else None,
            "tags_json": tags,
            "album_ids_json": [a.get("id") for a in (raw.get("albums") or []) if a.get("id")],
            "raw_metadata_json": raw,
            "synced_at": synced_at,
        }

        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
            self.db.commit()
            return 0, 1
        else:
            asset = Asset(id=str(uuid.uuid4()), **data)
            self.db.add(asset)
            self.db.commit()
            return 1, 0
