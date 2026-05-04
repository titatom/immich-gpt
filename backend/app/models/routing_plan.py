from sqlalchemy import Column, String, Boolean, Float, Text, DateTime, JSON
from sqlalchemy.sql import func
from ..database import Base


class RoutingPlan(Base):
    """A batch of routing decisions awaiting review or applied."""
    __tablename__ = "routing_plans"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    job_id = Column(String, nullable=True, index=True)

    # status: "draft", "ready", "partially_applied", "applied", "cancelled"
    status = Column(String, nullable=False, default="draft", index=True)

    scope_json = Column(JSON, nullable=True)
    summary_json = Column(JSON, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class RoutingPlanItem(Base):
    """
    A single asset's routing decision within a plan.
    """
    __tablename__ = "routing_plan_items"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    plan_id = Column(String, nullable=False, index=True)
    asset_id = Column(String, nullable=False, index=True)

    primary_bucket_id = Column(String, nullable=True, index=True)
    primary_bucket_path = Column(String, nullable=True)
    secondary_bucket_ids_json = Column(JSON, nullable=True)

    # disposition: "keep", "review", "trash_candidate"
    disposition = Column(String, nullable=False, default="review")

    confidence = Column(Float, nullable=True)
    review_required = Column(Boolean, default=True, nullable=False)
    auto_apply = Column(Boolean, default=False, nullable=False)

    review_reasons_json = Column(JSON, nullable=True)
    reason_codes_json = Column(JSON, nullable=True)
    safety_flags_json = Column(JSON, nullable=True)
    quality_flags_json = Column(JSON, nullable=True)

    suggested_description = Column(Text, nullable=True)
    suggested_tags_json = Column(JSON, nullable=True)
    suggested_location_json = Column(JSON, nullable=True)
    suggested_caption = Column(Text, nullable=True)

    raw_ai_response_json = Column(JSON, nullable=True)

    # status: "pending", "approved", "rejected", "applied", "failed"
    status = Column(String, nullable=False, default="pending", index=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
