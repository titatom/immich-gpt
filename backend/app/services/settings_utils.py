"""
Shared helpers for reading per-user behaviour settings from AppSetting rows.
"""
from typing import Optional
from sqlalchemy.orm import Session


def get_behaviour_setting(
    db: Session,
    key: str,
    default: bool,
    user_id: Optional[str] = None,
) -> bool:
    """Return a boolean behaviour setting for a user, falling back to *default*."""
    from ..models.app_setting import AppSetting

    q = db.query(AppSetting).filter(AppSetting.key == key)
    if user_id:
        q = q.filter(AppSetting.user_id == user_id)
    row = q.first()
    if row is None:
        return default
    return row.value.lower() not in ("false", "0", "no")
