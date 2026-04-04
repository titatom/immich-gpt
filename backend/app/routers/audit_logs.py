from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

from ..database import get_db
from ..models.audit_log import AuditLog

router = APIRouter(prefix="/api/audit-logs", tags=["audit-logs"])


class AuditLogOut(BaseModel):
    id: str
    asset_id: Optional[str]
    job_run_id: Optional[str]
    action: str
    status: Optional[str]
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
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(AuditLog)
    if asset_id:
        q = q.filter(AuditLog.asset_id == asset_id)
    if job_run_id:
        q = q.filter(AuditLog.job_run_id == job_run_id)
    if action:
        q = q.filter(AuditLog.action == action)
    if status:
        q = q.filter(AuditLog.status == status)
    offset = (page - 1) * page_size
    return q.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size).all()


@router.get("/count")
def count_audit_logs(
    asset_id: Optional[str] = None,
    job_run_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(AuditLog)
    if asset_id:
        q = q.filter(AuditLog.asset_id == asset_id)
    if job_run_id:
        q = q.filter(AuditLog.job_run_id == job_run_id)
    if status:
        q = q.filter(AuditLog.status == status)
    return {"count": q.count()}


@router.get("/{log_id}", response_model=AuditLogOut)
def get_audit_log(log_id: str, db: Session = Depends(get_db)):
    log = db.query(AuditLog).filter(AuditLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return log
