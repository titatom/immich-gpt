from pydantic import BaseModel, ConfigDict, ConfigDict
from typing import Optional, List, Any
from datetime import datetime


class AssetOut(BaseModel):
    id: str
    immich_id: str
    original_filename: Optional[str]
    file_created_at: Optional[datetime]
    asset_type: Optional[str]
    mime_type: Optional[str]
    city: Optional[str]
    country: Optional[str]
    camera_make: Optional[str]
    camera_model: Optional[str]
    description: Optional[str]
    tags: Optional[List[str]]
    is_favorite: bool
    is_archived: bool
    is_external_library: bool
    synced_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssetSyncResult(BaseModel):
    synced: int
    created: int
    updated: int
    errors: int
