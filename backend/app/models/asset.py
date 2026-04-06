from sqlalchemy import Column, String, DateTime, JSON, Boolean, Text, UniqueConstraint
from sqlalchemy.sql import func
from ..database import Base


class Asset(Base):
    __tablename__ = "assets"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    immich_id = Column(String, nullable=False, index=True)
    original_filename = Column(String, nullable=True)
    file_created_at = Column(DateTime, nullable=True)
    file_modified_at = Column(DateTime, nullable=True)
    local_date_time = Column(DateTime, nullable=True)
    asset_type = Column(String, nullable=True)  # IMAGE, VIDEO
    mime_type = Column(String, nullable=True)
    duration = Column(String, nullable=True)
    is_favorite = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    is_trashed = Column(Boolean, default=False)
    is_external_library = Column(Boolean, default=False)
    city = Column(String, nullable=True)
    country = Column(String, nullable=True)
    camera_make = Column(String, nullable=True)
    camera_model = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    tags_json = Column(JSON, nullable=True)
    album_ids_json = Column(JSON, nullable=True)
    raw_metadata_json = Column(JSON, nullable=True)
    synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "immich_id", name="uq_assets_user_immich"),
    )
