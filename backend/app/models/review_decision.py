from sqlalchemy import Column, String, Text, DateTime, JSON, Boolean
from sqlalchemy.sql import func
from ..database import Base


class ReviewDecision(Base):
    __tablename__ = "review_decisions"

    id = Column(String, primary_key=True)
    asset_id = Column(String, nullable=False, index=True)
    suggested_classification_id = Column(String, nullable=True)
    suggested_metadata_id = Column(String, nullable=True)
    # decision_type: "approve_classification", "override_classification",
    #                "approve_metadata", "approve_tags", "approve_all", "reject"
    decision_type = Column(String, nullable=False)
    approved_bucket_id = Column(String, nullable=True)
    approved_bucket_name = Column(String, nullable=True)
    approved_description = Column(Text, nullable=True)
    approved_tags_json = Column(JSON, nullable=True)
    approved_subalbum = Column(String, nullable=True)
    subalbum_approved = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    writeback_triggered = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
