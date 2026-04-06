from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

from ..database import get_db
from ..dependencies import require_active_user
from ..models.audit_log import AuditLog

router = APIRouter(prefix="/api/audit-logs", tags=["audit-logs"])


class AuditLogOut(BaseModel):
    id: str
    asset_id: Optional[str]
    job_run_id: Optional[str]
    action: str
    status: Optional[str]
    level: Optional[str]
    source: Optional[str]
    details_json: Optional[dict]
    error_message: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=List[AuditLogOut])
def list_audit_logs(
    asset_id: Optional[str] = None,
    job_run_id: Optional[str] = None,
    action: Optional[str] = None,
    status: Optional[str] = None,
    level: Optional[str] = None,
    source: Optional[str] = None,
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    query = db.query(AuditLog).filter(AuditLog.user_id == current_user.id)
    if asset_id:
        query = query.filter(AuditLog.asset_id == asset_id)
    if job_run_id:
        query = query.filter(AuditLog.job_run_id == job_run_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if status:
        query = query.filter(AuditLog.status == status)
    if level:
        query = query.filter(AuditLog.level == level)
    if source:
        query = query.filter(AuditLog.source == source)
    if q:
        like = f"%{q}%"
        query = query.filter(
            AuditLog.action.ilike(like) |
            AuditLog.error_message.ilike(like) |
            AuditLog.asset_id.ilike(like) |
            AuditLog.job_run_id.ilike(like)
        )
    offset = (page - 1) * page_size
    return query.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size).all()


@router.get("/count")
def count_audit_logs(
    asset_id: Optional[str] = None,
    job_run_id: Optional[str] = None,
    status: Optional[str] = None,
    level: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    query = db.query(AuditLog).filter(AuditLog.user_id == current_user.id)
    if asset_id:
        query = query.filter(AuditLog.asset_id == asset_id)
    if job_run_id:
        query = query.filter(AuditLog.job_run_id == job_run_id)
    if status:
        query = query.filter(AuditLog.status == status)
    if level:
        query = query.filter(AuditLog.level == level)
    return {"count": query.count()}


@router.get("/{log_id}", response_model=AuditLogOut)
def get_audit_log(
    log_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    log = db.query(AuditLog).filter(
        AuditLog.id == log_id,
        AuditLog.user_id == current_user.id,
    ).first()
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return log
