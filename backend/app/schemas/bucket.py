from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ---------------------------------------------------------------------------
# Routing tree schemas
# ---------------------------------------------------------------------------

VALID_DESTINATION_TYPES = {"virtual", "immich_album", "immich_trash", "review_only"}
VALID_PRIVACY_ACTIONS = {"allow", "tag", "review", "reject"}
VALID_QUALITY_LEVELS = {"any", "usable", "high"}


class RoutingNodeCreate(BaseModel):
    name: str
    parent_id: Optional[str] = None
    is_leaf: bool = True
    description: Optional[str] = None
    enabled: bool = True
    priority: int = 100

    destination_type: str = "virtual"
    immich_album_name: Optional[str] = None
    create_album_if_missing: bool = True

    auto_apply_enabled: bool = False
    auto_apply_threshold: float = 0.95
    review_below_threshold: Optional[float] = 0.85

    exclusive: bool = False
    allow_secondary: bool = True

    minimum_quality: str = "any"
    allow_blurry: bool = True
    allow_dark: bool = True
    allow_screenshot: bool = True
    allow_duplicate: bool = True

    suggest_description: bool = True
    suggest_tags: bool = True
    suggest_location: bool = False
    suggest_caption: bool = False
    write_description: bool = True
    write_tags: bool = True
    write_location: bool = False

    custom_prompt_enabled: bool = False
    custom_prompt: Optional[str] = None

    positive_criteria: Optional[List[str]] = None
    negative_criteria: Optional[List[str]] = None
    privacy_rules: Optional[Dict[str, str]] = None
    quality_rules: Optional[Dict[str, Any]] = None
    automation_rules: Optional[Dict[str, Any]] = None
    metadata_rules: Optional[Dict[str, Any]] = None


class RoutingNodeUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[str] = None
    is_leaf: Optional[bool] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None

    destination_type: Optional[str] = None
    immich_album_name: Optional[str] = None
    create_album_if_missing: Optional[bool] = None

    auto_apply_enabled: Optional[bool] = None
    auto_apply_threshold: Optional[float] = None
    review_below_threshold: Optional[float] = None

    exclusive: Optional[bool] = None
    allow_secondary: Optional[bool] = None

    minimum_quality: Optional[str] = None
    allow_blurry: Optional[bool] = None
    allow_dark: Optional[bool] = None
    allow_screenshot: Optional[bool] = None
    allow_duplicate: Optional[bool] = None

    suggest_description: Optional[bool] = None
    suggest_tags: Optional[bool] = None
    suggest_location: Optional[bool] = None
    suggest_caption: Optional[bool] = None
    write_description: Optional[bool] = None
    write_tags: Optional[bool] = None
    write_location: Optional[bool] = None

    custom_prompt_enabled: Optional[bool] = None
    custom_prompt: Optional[str] = None

    positive_criteria: Optional[List[str]] = None
    negative_criteria: Optional[List[str]] = None
    privacy_rules: Optional[Dict[str, str]] = None
    quality_rules: Optional[Dict[str, Any]] = None
    automation_rules: Optional[Dict[str, Any]] = None
    metadata_rules: Optional[Dict[str, Any]] = None


class RoutingNodeOut(BaseModel):
    id: str
    parent_id: Optional[str]
    name: str
    path: str
    is_leaf: bool
    description: Optional[str]
    enabled: bool
    priority: int

    destination_type: str
    immich_album_name: Optional[str]
    create_album_if_missing: bool

    auto_apply_enabled: bool
    auto_apply_threshold: float
    review_below_threshold: Optional[float]

    exclusive: bool
    allow_secondary: bool

    minimum_quality: str
    allow_blurry: bool
    allow_dark: bool
    allow_screenshot: bool
    allow_duplicate: bool

    suggest_description: bool
    suggest_tags: bool
    suggest_location: bool
    suggest_caption: bool
    write_description: bool
    write_tags: bool
    write_location: bool

    custom_prompt_enabled: bool
    custom_prompt: Optional[str]

    positive_criteria: List[str] = Field(default_factory=list)
    negative_criteria: List[str] = Field(default_factory=list)
    privacy_rules: Dict[str, str] = Field(default_factory=dict)
    quality_rules: Dict[str, Any] = Field(default_factory=dict)
    automation_rules: Dict[str, Any] = Field(default_factory=dict)
    metadata_rules: Dict[str, Any] = Field(default_factory=dict)

    children: List["RoutingNodeOut"] = Field(default_factory=list)

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


RoutingNodeOut.model_rebuild()


class RoutingNodeMove(BaseModel):
    new_parent_id: Optional[str] = None


class RoutingExampleCreate(BaseModel):
    asset_id: Optional[str] = None
    example_type: str = "positive"
    source: str = "manual"
    note: Optional[str] = None


class RoutingExampleOut(BaseModel):
    id: str
    bucket_id: str
    asset_id: Optional[str]
    example_type: str
    source: str
    note: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoutingPlanItemOut(BaseModel):
    id: str
    plan_id: str
    asset_id: str
    primary_bucket_id: Optional[str]
    primary_bucket_path: Optional[str]
    secondary_bucket_ids: List[str] = Field(default_factory=list)
    disposition: str
    confidence: Optional[float]
    review_required: bool
    auto_apply: bool
    review_reasons: List[str] = Field(default_factory=list)
    reason_codes: List[str] = Field(default_factory=list)
    safety_flags: Dict[str, Any] = Field(default_factory=dict)
    quality_flags: Dict[str, Any] = Field(default_factory=dict)
    suggested_description: Optional[str]
    suggested_tags: List[str] = Field(default_factory=list)
    suggested_location: Optional[Dict[str, Any]] = None
    suggested_caption: Optional[str] = None
    status: str
    error_message: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class RoutingPlanOut(BaseModel):
    id: str
    job_id: Optional[str]
    status: str
    scope: Optional[Dict[str, Any]] = None
    summary: Optional[Dict[str, Any]] = None
    item_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoutingClassifyRequest(BaseModel):
    asset_ids: Optional[List[str]] = None
    limit: Optional[int] = None
    force: bool = False


class PlanItemMoveRequest(BaseModel):
    item_ids: List[str]
    target_bucket_id: str


class PlanItemActionRequest(BaseModel):
    item_ids: Optional[List[str]] = None
    bucket_id: Optional[str] = None
    disposition: Optional[str] = None


class PromptPreviewOut(BaseModel):
    bucket_id: str
    path: str
    compiled_prompt: str
