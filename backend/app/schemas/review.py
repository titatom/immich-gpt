from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


class ReviewItemOut(BaseModel):
    asset_id: str
    immich_id: str
    original_filename: Optional[str]
    file_created_at: Optional[datetime]
    asset_type: Optional[str]
    mime_type: Optional[str]
    city: Optional[str]
    country: Optional[str]
    camera_make: Optional[str]
    camera_model: Optional[str]
    current_description: Optional[str]
    current_tags: Optional[List[str]]
    # classification suggestion
    classification_id: Optional[str]
    suggested_bucket_id: Optional[str]
    suggested_bucket_name: Optional[str]
    confidence: Optional[float]
    explanation: Optional[str]
    subalbum_suggestion: Optional[str]
    review_recommended: bool
    classification_status: str
    # metadata suggestion
    metadata_id: Optional[str]
    description_suggestion: Optional[str]
    tags_suggestion: Optional[List[str]]
    provider_name: Optional[str]
    prompt_run_id: Optional[str]


class ReviewApproveRequest(BaseModel):
    approved_bucket_id: Optional[str] = None
    approved_bucket_name: Optional[str] = None
    approved_description: Optional[str] = None
    approved_tags: Optional[List[str]] = None
    approved_subalbum: Optional[str] = None
    subalbum_approved: bool = False
    trigger_writeback: bool = True


class BulkReviewRequest(BaseModel):
    asset_ids: List[str]
    action: str  # "approve_all", "reject_all"
    trigger_writeback: bool = True


class WritebackResult(BaseModel):
    asset_id: str
    description_written: bool
    tags_written: bool
    album_assigned: bool
    errors: List[str]
