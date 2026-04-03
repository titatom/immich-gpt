from sqlalchemy import Column, String, Float, Text, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from ..database import Base


class SuggestedClassification(Base):
    __tablename__ = "suggested_classifications"

    id = Column(String, primary_key=True)
    asset_id = Column(String, nullable=False, index=True)
    suggested_bucket_id = Column(String, nullable=True)
    suggested_bucket_name = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    explanation = Column(Text, nullable=True)
    subalbum_suggestion = Column(String, nullable=True)
    review_recommended = Column(Boolean, default=True)
    provider_name = Column(String, nullable=True)
    prompt_run_id = Column(String, nullable=True)
    # status: "pending_review", "approved", "overridden", "rejected"
    status = Column(String, default="pending_review", index=True)
    override_bucket_id = Column(String, nullable=True)
    override_bucket_name = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
