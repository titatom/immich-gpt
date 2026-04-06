from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON, UniqueConstraint
from sqlalchemy.sql import func
from ..database import Base


class ProviderConfig(Base):
    __tablename__ = "provider_configs"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    # provider_name: "openai", "ollama", "openrouter"
    provider_name = Column(String, nullable=False, index=True)
    enabled = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False)
    api_key_encrypted = Column(Text, nullable=True)
    base_url = Column(String, nullable=True)
    model_name = Column(String, nullable=True)
    extra_config_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "provider_name", name="uq_provider_configs_user_provider"),
    )
