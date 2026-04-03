from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from ..database import Base


class SuggestedMetadata(Base):
    __tablename__ = "suggested_metadata"

    id = Column(String, primary_key=True)
    asset_id = Column(String, nullable=False, index=True)
    description_suggestion = Column(Text, nullable=True)
    tags_json = Column(JSON, nullable=True)
    approved_description = Column(Text, nullable=True)
    approved_tags_json = Column(JSON, nullable=True)
    # writeback_status: "pending", "written", "failed", "skipped"
    writeback_status = Column(String, default="pending")
    writeback_error = Column(Text, nullable=True)
    provider_name = Column(String, nullable=True)
    prompt_run_id = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
