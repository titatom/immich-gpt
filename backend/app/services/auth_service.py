"""
Authentication and session management service.
Handles password hashing, session lifecycle, and password reset tokens.
"""
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session

from passlib.context import CryptContext

from ..models.user import User
from ..models.session import UserSession, PasswordResetToken

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

SESSION_IDLE_SECONDS = 24 * 3600       # 24 h without activity → expires
SESSION_HARD_MAX_SECONDS = 7 * 24 * 3600  # 7 days absolute ceiling
RESET_TOKEN_TTL_SECONDS = 3600         # 1 h for password-reset tokens


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

def create_session(
    db: Session,
    user_id: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> UserSession:
    now = datetime.now(timezone.utc)
    session = UserSession(
        id=str(uuid.uuid4()),
        user_id=user_id,
        created_at=now,
        expires_at=now + timedelta(seconds=SESSION_IDLE_SECONDS),
        last_seen_at=now,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: Session, session_id: str) -> Optional[UserSession]:
    now = datetime.now(timezone.utc)
    session = db.query(UserSession).filter(UserSession.id == session_id).first()
    if not session:
        return None
    # Make expires_at timezone-aware for comparison
    expires = session.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < now:
        db.delete(session)
        db.commit()
        return None
    # Enforce hard max: created_at + 7 days
    created = session.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    if now - created > timedelta(seconds=SESSION_HARD_MAX_SECONDS):
        db.delete(session)
        db.commit()
        return None
    # Slide the expiry window
    session.expires_at = now + timedelta(seconds=SESSION_IDLE_SECONDS)
    session.last_seen_at = now
    db.commit()
    return session


def delete_session(db: Session, session_id: str) -> None:
    session = db.query(UserSession).filter(UserSession.id == session_id).first()
    if session:
        db.delete(session)
        db.commit()


def delete_all_user_sessions(db: Session, user_id: str) -> None:
    db.query(UserSession).filter(UserSession.user_id == user_id).delete()
    db.commit()


# ---------------------------------------------------------------------------
# Password reset tokens
# ---------------------------------------------------------------------------

def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def create_reset_token(db: Session, user_id: str) -> str:
    """Create a password-reset token and return the *raw* value (shown once)."""
    raw_token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    record = PasswordResetToken(
        id=str(uuid.uuid4()),
        user_id=user_id,
        token_hash=_hash_token(raw_token),
        expires_at=now + timedelta(seconds=RESET_TOKEN_TTL_SECONDS),
    )
    db.add(record)
    db.commit()
    return raw_token


def consume_reset_token(db: Session, raw_token: str) -> Optional[str]:
    """
    Validate and consume a reset token.
    Returns the user_id if valid; None otherwise.
    """
    token_hash = _hash_token(raw_token)
    now = datetime.now(timezone.utc)
    record = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
        )
        .first()
    )
    if not record:
        return None
    expires = record.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < now:
        return None
    record.used_at = now
    db.commit()
    return record.user_id


# ---------------------------------------------------------------------------
# User login helper
# ---------------------------------------------------------------------------

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Return User on success; None on failure."""
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
