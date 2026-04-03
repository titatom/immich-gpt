from pydantic import BaseModel, ConfigDict, ConfigDict, Field
from typing import Optional, List
from datetime import datetime


class BucketCreate(BaseModel):
    name: str
    description: Optional[str] = None
    enabled: bool = True
    priority: int = 100
    mapping_mode: str = "virtual"
    immich_album_id: Optional[str] = None
    classification_prompt: Optional[str] = None
    examples: Optional[List[str]] = None
    negative_examples: Optional[List[str]] = None
    confidence_threshold: Optional[float] = None


class BucketUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None
    mapping_mode: Optional[str] = None
    immich_album_id: Optional[str] = None
    classification_prompt: Optional[str] = None
    examples: Optional[List[str]] = None
    negative_examples: Optional[List[str]] = None
    confidence_threshold: Optional[float] = None


class BucketOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    enabled: bool
    priority: int
    mapping_mode: str
    immich_album_id: Optional[str]
    classification_prompt: Optional[str]
    examples: Optional[List[str]]
    negative_examples: Optional[List[str]]
    confidence_threshold: Optional[float]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
