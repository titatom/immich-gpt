"""
Admin router: user account management.
Admin can manage account status but cannot read user content or secrets.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from ..database import get_db
from ..dependencies import require_admin
from ..services.user_service import (
    create_user,
    list_users,
    get_user_by_id,
    set_user_active,
    set_force_password_change,
    change_password,
    delete_user,
)
from ..services.auth_service import create_reset_token

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Schemas (no secrets, no user content)
# ---------------------------------------------------------------------------

class AdminUserOut(BaseModel):
    id: str
    email: str
    username: str
    role: str
    is_active: bool
    force_password_change: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class CreateUserRequest(BaseModel):
    email: str
    username: str
    password: str
    role: str = "user"
    force_password_change: bool = True


class UpdateUserRequest(BaseModel):
    is_active: Optional[bool] = None
    force_password_change: Optional[bool] = None


class AdminResetPasswordRequest(BaseModel):
    new_password: Optional[str] = None  # If None, generates a reset token instead


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/users", response_model=List[AdminUserOut])
def list_all_users(_admin=Depends(require_admin), db: Session = Depends(get_db)):
    users = list_users(db)
    return [
        AdminUserOut(
            id=u.id,
            email=u.email,
            username=u.username,
            role=u.role,
            is_active=u.is_active,
            force_password_change=u.force_password_change,
            created_at=u.created_at,
            updated_at=u.updated_at,
        )
        for u in users
    ]


@router.post("/users", response_model=AdminUserOut)
def create_user_endpoint(
    body: CreateUserRequest,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    from sqlalchemy.exc import IntegrityError
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    try:
        user = create_user(
            db,
            email=body.email,
            username=body.username,
            password=body.password,
            role=body.role,
            force_password_change=body.force_password_change,
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email or username already exists")
    return AdminUserOut(
        id=user.id,
        email=user.email,
        username=user.username,
        role=user.role,
        is_active=user.is_active,
        force_password_change=user.force_password_change,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def update_user(
    user_id: str,
    body: UpdateUserRequest,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.is_active is not None:
        user = set_user_active(db, user_id, body.is_active)
    if body.force_password_change is not None:
        user = set_force_password_change(db, user_id, body.force_password_change)

    return AdminUserOut(
        id=user.id,
        email=user.email,
        username=user.username,
        role=user.role,
        is_active=user.is_active,
        force_password_change=user.force_password_change,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post("/users/{user_id}/reset-password")
def admin_reset_password(
    user_id: str,
    body: AdminResetPasswordRequest,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.new_password:
        if len(body.new_password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
        change_password(db, user_id, body.new_password, clear_force_flag=False)
        set_force_password_change(db, user_id, True)
        return {
            "message": "Password reset. User must change it on next login.",
            "force_password_change": True,
        }
    else:
        raw_token = create_reset_token(db, user_id)
        return {
            "message": "Reset token generated. Share with the user securely.",
            "token": raw_token,
        }


@router.delete("/users/{user_id}")
def delete_user_endpoint(
    user_id: str,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    deleted = delete_user(db, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    return {"deleted": True}
