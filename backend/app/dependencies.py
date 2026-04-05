"""
Shared FastAPI dependencies.
"""
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from .database import get_db
from .services.immich_client import ImmichClient
from .config import settings


# ---------------------------------------------------------------------------
# Auth: session-based user resolution
# ---------------------------------------------------------------------------

def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Resolve the current user from the session cookie.

    Raises 401 if no valid session exists.
    """
    from .models.user import User
    from .services.auth_service import get_session

    session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user


def require_admin(user=Depends(get_current_user)):
    """Require the current user to have the 'admin' role."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def require_active_user(user=Depends(get_current_user)):
    """Require a logged-in active user (any role). Enforces force_password_change gate."""
    if user.force_password_change:
        raise HTTPException(
            status_code=403,
            detail="Password change required before continuing",
            headers={"X-Force-Password-Change": "true"},
        )
    return user


# ---------------------------------------------------------------------------
# Immich client: resolved from the current user's settings
# ---------------------------------------------------------------------------

def get_immich_client(
    db: Session = Depends(get_db),
    request: Request = None,
) -> ImmichClient:
    """
    Resolve the Immich client using the current user's stored credentials,
    falling back to env vars for unauthenticated contexts (e.g. tests).
    """
    from .models.app_setting import AppSetting

    user_id = None
    if request is not None:
        session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)
        if session_id:
            from .services.auth_service import get_session
            session = get_session(db, session_id)
            if session:
                user_id = session.user_id

    q = db.query(AppSetting)
    if user_id:
        q = q.filter(AppSetting.user_id == user_id)

    url_row = q.filter(AppSetting.key == "immich_url").first()
    key_row = q.filter(AppSetting.key == "immich_api_key").first()
    url = (url_row.value if url_row and url_row.value else None) or settings.IMMICH_URL
    api_key = (key_row.value if key_row and key_row.value else None) or settings.IMMICH_API_KEY
    return ImmichClient(url, api_key)
