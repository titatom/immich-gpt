from sqlalchemy import Column, String, Text, DateTime, Float, Integer, JSON
from sqlalchemy.sql import func
from ..database import Base


class JobRun(Base):
    __tablename__ = "job_runs"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=True, index=True)  # nullable for backward compat
    job_type = Column(String, nullable=False, index=True)
    # status: queued, starting, syncing_assets, preparing_image, classifying_ai,
    #         validating_result, saving_suggestion, writing_results, completed, failed, cancelled, paused
    status = Column(String, default="queued", index=True)
    current_step = Column(String, nullable=True)
    progress_percent = Column(Float, default=0.0)
    processed_count = Column(Integer, default=0)
    total_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    message = Column(Text, nullable=True)
    params_json = Column(JSON, nullable=True)
    log_lines_json = Column(JSON, nullable=True, default=list)
    started_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
