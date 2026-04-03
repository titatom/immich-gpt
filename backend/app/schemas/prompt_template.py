from pydantic import BaseModel, ConfigDict, ConfigDict
from typing import Optional
from datetime import datetime


class PromptTemplateCreate(BaseModel):
    prompt_type: str
    name: str
    content: str
    enabled: bool = True
    bucket_id: Optional[str] = None


class PromptTemplateUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    enabled: Optional[bool] = None


class PromptTemplateOut(BaseModel):
    id: str
    prompt_type: str
    name: str
    content: str
    enabled: bool
    version: int
    bucket_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
