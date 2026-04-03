from pydantic import BaseModel, ConfigDict, ConfigDict
from typing import Optional, List, Any
from datetime import datetime


class JobRunOut(BaseModel):
    id: str
    job_type: str
    status: str
    current_step: Optional[str]
    progress_percent: float
    processed_count: int
    total_count: int
    success_count: int
    error_count: int
    message: Optional[str]
    log_lines: Optional[List[str]]
    started_at: Optional[datetime]
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobStartResponse(BaseModel):
    job_id: str
    status: str
    message: str
