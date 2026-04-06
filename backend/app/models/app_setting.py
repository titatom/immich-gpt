from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func
from ..database import Base


class AppSetting(Base):
    """Key-value store for runtime-configurable settings (e.g. Immich URL/key)."""
    __tablename__ = "app_settings"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
