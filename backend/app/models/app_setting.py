from sqlalchemy import Column, String, Text, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from ..database import Base


class AppSetting(Base):
    """Key-value store for per-user runtime-configurable settings."""
    __tablename__ = "app_settings"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    key = Column(String, nullable=False)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "key", name="uq_app_settings_user_key"),
    )
