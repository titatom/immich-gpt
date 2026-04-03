from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from ..database import Base


class PromptRun(Base):
    __tablename__ = "prompt_runs"

    id = Column(String, primary_key=True)
    asset_id = Column(String, nullable=False, index=True)
    job_run_id = Column(String, nullable=True, index=True)
    provider_name = Column(String, nullable=False)
    model_name = Column(String, nullable=True)
    assembled_prompt_json = Column(JSON, nullable=True)
    raw_response = Column(Text, nullable=True)
    parsed_response_json = Column(JSON, nullable=True)
    status = Column(String, default="pending")  # pending, success, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
