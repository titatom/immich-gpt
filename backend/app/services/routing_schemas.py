"""
Pydantic schemas for AI routing output and rule-evaluation results.
"""
from __future__ import annotations
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class AISafetyFlags(BaseModel):
    faces_visible: bool = False
    children_visible: bool = False
    address_visible: bool = False
    documents_visible: bool = False
    license_plate_visible: bool = False
    private_info_visible: bool = False

    model_config = ConfigDict(extra="ignore")


class AIQualityFlags(BaseModel):
    blurry: bool = False
    dark: bool = False
    screenshot: bool = False
    duplicate_candidate: bool = False
    low_quality: bool = False

    model_config = ConfigDict(extra="ignore")


class AISecondaryPath(BaseModel):
    path: str
    confidence: float = Field(ge=0.0, le=1.0)


class AIMetadata(BaseModel):
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    location: Optional[Dict[str, Any]] = None
    caption: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class AIRoutingResult(BaseModel):
    disposition: Literal["keep", "review", "trash_candidate"] = "review"
    primary_path: Optional[str] = None
    primary_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    secondary_paths: List[AISecondaryPath] = Field(default_factory=list)
    review_required: bool = True
    review_reasons: List[str] = Field(default_factory=list)
    reason_codes: List[str] = Field(default_factory=list)
    safety_flags: AISafetyFlags = Field(default_factory=AISafetyFlags)
    quality_flags: AIQualityFlags = Field(default_factory=AIQualityFlags)
    metadata: AIMetadata = Field(default_factory=AIMetadata)

    model_config = ConfigDict(extra="ignore")


class RuleResult(BaseModel):
    rejected: bool = False
    reason: Optional[str] = None
    review_required: bool = False
    review_reasons: List[str] = Field(default_factory=list)


class Candidate(BaseModel):
    bucket_id: str
    path: str
    confidence: float
    review_required: bool = False
    review_reasons: List[str] = Field(default_factory=list)
    priority: int = 100
    exclusive: bool = False
    allow_secondary: bool = True


class RoutingDecision(BaseModel):
    primary: Optional[Candidate] = None
    secondary: List[Candidate] = Field(default_factory=list)
    disposition: str = "review"
    review_required: bool = True
    auto_apply: bool = False
    review_reasons: List[str] = Field(default_factory=list)
    reason_codes: List[str] = Field(default_factory=list)
    safety_flags: Dict[str, bool] = Field(default_factory=dict)
    quality_flags: Dict[str, bool] = Field(default_factory=dict)
    rejected_paths: List[Dict[str, Any]] = Field(default_factory=list)
