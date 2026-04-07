from pydantic import BaseModel, ConfigDict
from typing import Optional, Any, Dict
from datetime import datetime


class ProviderConfigCreate(BaseModel):
    provider_name: str
    enabled: bool = False
    is_default: bool = False
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    extra_config: Optional[Dict[str, Any]] = None


class ProviderConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    is_default: Optional[bool] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    extra_config: Optional[Dict[str, Any]] = None


class ProviderConfigOut(BaseModel):
    id: str
    provider_name: str
    enabled: bool
    is_default: bool
    base_url: Optional[str]
    model_name: Optional[str]
    has_api_key: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ImmichSettingsUpdate(BaseModel):
    immich_url: str
    immich_api_key: Optional[str] = None


class ImmichSettingsOut(BaseModel):
    immich_url: str
    connected: bool
    asset_count: Optional[int] = None
    error: Optional[str] = None
