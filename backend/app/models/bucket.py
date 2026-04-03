from sqlalchemy import Column, String, Text, Boolean, Integer, Float, DateTime, JSON
from sqlalchemy.sql import func
from ..database import Base


class Bucket(Base):
    __tablename__ = "buckets"

    id = Column(String, primary_key=True)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=100)
    # mapping_mode: "immich_album", "virtual", "parent_group"
    mapping_mode = Column(String, default="virtual")
    immich_album_id = Column(String, nullable=True)
    classification_prompt = Column(Text, nullable=True)
    examples_json = Column(JSON, nullable=True)
    negative_examples_json = Column(JSON, nullable=True)
    confidence_threshold = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
