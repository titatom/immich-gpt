from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Float, DateTime, JSON,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from ..database import Base


class Bucket(Base):
    """
    Routing tree node.

    A Bucket represents either an organizational parent node or a final
    routing destination (leaf). All routing behavior is driven by the
    settings on this row — no category-specific logic is allowed.
    """
    __tablename__ = "buckets"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)

    # Hierarchical tree
    parent_id = Column(String, nullable=True, index=True)
    path = Column(String, nullable=True, index=True)
    is_leaf = Column(Boolean, default=True, nullable=False)

    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=100)

    # Legacy/back-compat: still consulted by the older writeback path.
    mapping_mode = Column(String, default="virtual")
    immich_album_id = Column(String, nullable=True)

    # Routing destination
    # destination_type: "virtual", "immich_album", "immich_trash", "review_only"
    destination_type = Column(String, default="virtual", nullable=False)
    immich_album_name = Column(String, nullable=True)
    create_album_if_missing = Column(Boolean, default=True, nullable=False)

    # Automation
    auto_apply_enabled = Column(Boolean, default=False, nullable=False)
    auto_apply_threshold = Column(Float, default=0.95, nullable=False)
    review_below_threshold = Column(Float, default=0.85, nullable=True)

    # Conflict resolution
    exclusive = Column(Boolean, default=False, nullable=False)
    allow_secondary = Column(Boolean, default=True, nullable=False)

    # Quality
    minimum_quality = Column(String, default="any", nullable=False)
    allow_blurry = Column(Boolean, default=True, nullable=False)
    allow_dark = Column(Boolean, default=True, nullable=False)
    allow_screenshot = Column(Boolean, default=True, nullable=False)
    allow_duplicate = Column(Boolean, default=True, nullable=False)

    # Metadata behavior
    suggest_description = Column(Boolean, default=True, nullable=False)
    suggest_tags = Column(Boolean, default=True, nullable=False)
    suggest_location = Column(Boolean, default=False, nullable=False)
    suggest_caption = Column(Boolean, default=False, nullable=False)
    write_description = Column(Boolean, default=True, nullable=False)
    write_tags = Column(Boolean, default=True, nullable=False)
    write_location = Column(Boolean, default=False, nullable=False)

    # AI prompt
    custom_prompt_enabled = Column(Boolean, default=False, nullable=False)
    custom_prompt = Column(Text, nullable=True)
    classification_prompt = Column(Text, nullable=True)  # legacy

    # Criteria + JSON rule blobs (stored as JSON-serialised text)
    positive_criteria_json = Column(JSON, nullable=True)
    negative_criteria_json = Column(JSON, nullable=True)
    privacy_rules_json = Column(JSON, nullable=True)
    quality_rules_json = Column(JSON, nullable=True)
    automation_rules_json = Column(JSON, nullable=True)
    metadata_rules_json = Column(JSON, nullable=True)

    # Legacy example arrays (still usable by old prompt assembly)
    examples_json = Column(JSON, nullable=True)
    negative_examples_json = Column(JSON, nullable=True)
    confidence_threshold = Column(Float, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "path", name="uq_buckets_user_path"),
    )
