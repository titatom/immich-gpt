from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from ..database import Base


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(String, primary_key=True)   # UUID — this is the cookie value
    user_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)
    last_seen_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
