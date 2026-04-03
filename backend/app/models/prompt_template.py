from sqlalchemy import Column, String, Text, Boolean, DateTime, Integer
from sqlalchemy.sql import func
from ..database import Base


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id = Column(String, primary_key=True)
    # type: "global_classification", "bucket_classification",
    #        "description_generation", "tags_generation", "review_guidance"
    prompt_type = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    enabled = Column(Boolean, default=True)
    version = Column(Integer, default=1)
    bucket_id = Column(String, nullable=True)  # FK to buckets if type = bucket_classification
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
