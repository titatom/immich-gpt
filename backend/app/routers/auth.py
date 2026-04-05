"""
Authentication router: login, logout, me, password flows.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..config import settings
from ..dependencies import get_current_user
from ..services.auth_service import (
    authenticate_user,
    create_session,
    delete_session,
    create_reset_token,
    consume_reset_token,
    verify_password,
)
from ..services.user_service import (
    change_password,
    get_user_by_email,
    get_user_by_id,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

_COOKIE = settings.SESSION_COOKIE_NAME
_SECURE = settings.SESSION_COOKIE_SECURE
_SAMESITE = settings.SESSION_COOKIE_SAMESITE


def _set_session_cookie(response: Response, session_id: str) -> None:
    response.set_cookie(
        key=_COOKIE,
        value=session_id,
        httponly=True,
        secure=_SECURE,
        samesite=_SAMESITE,
        max_age=7 * 24 * 3600,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=_COOKIE, path="/")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    username: str
    role: str
    force_password_change: bool


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/login", response_model=UserOut)
def login(body: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    user = authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    session = create_session(db, user.id, ip_address=ip, user_agent=ua)
    _set_session_cookie(response, session.id)

    return UserOut(
        id=user.id,
        email=user.email,
        username=user.username,
        role=user.role,
        force_password_change=user.force_password_change,
    )


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    session_id = request.cookies.get(_COOKIE)
    if session_id:
        delete_session(db, session_id)
    _clear_session_cookie(response)
    return {"logged_out": True}


@router.get("/me", response_model=UserOut)
def me(current_user=Depends(get_current_user)):
    return UserOut(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        role=current_user.role,
        force_password_change=current_user.force_password_change,
    )


@router.post("/change-password")
def change_password_endpoint(
    body: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    change_password(db, current_user.id, body.new_password, clear_force_flag=True)
    return {"changed": True}


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Generate a password-reset token for the given email address.

    The token is returned in the response body — suitable for admin-managed
    workflows (admin creates accounts and resets passwords for users).
    A future iteration can add email/SMTP delivery instead.
    """
    user = get_user_by_email(db, body.email)
    if not user or not user.is_active:
        # Return success regardless to avoid email enumeration
        return {"message": "If that email is registered, a reset token has been issued"}

    raw_token = create_reset_token(db, user.id)
    return {
        "message": "Reset token generated",
        "token": raw_token,
        "note": "Share this token with the user securely. It expires in 1 hour.",
    }


@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")

    user_id = consume_reset_token(db, body.token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user = get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="User not found or inactive")

    change_password(db, user_id, body.new_password, clear_force_flag=True)
    return {"message": "Password has been reset. Please log in."}
