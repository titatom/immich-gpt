from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from ..database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True)
    asset_id = Column(String, nullable=True, index=True)
    job_run_id = Column(String, nullable=True, index=True)
    action = Column(String, nullable=False)
    status = Column(String, nullable=True)
    details_json = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
