from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func
from ..database import Base


class RoutingExample(Base):
    """
    Positive or negative example of an asset belonging to a routing leaf.
    Used to seed the AI prompt for that leaf.
    """
    __tablename__ = "routing_examples"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    bucket_id = Column(String, nullable=False, index=True)
    asset_id = Column(String, nullable=True, index=True)

    # example_type: "positive", "negative"
    example_type = Column(String, nullable=False, default="positive")
    # source: "manual", "correction", "imported_album", "seed"
    source = Column(String, nullable=False, default="manual")

    note = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
