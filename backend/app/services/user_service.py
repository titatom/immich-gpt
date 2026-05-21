"""
User CRUD service and admin bootstrap.
"""
import uuid
from typing import Optional, List
from sqlalchemy.orm import Session

from ..models.user import User
from ..services.auth_service import (
    delete_all_user_sessions,
    delete_other_user_sessions,
    hash_password,
)


# ---------------------------------------------------------------------------
# User creation
# ---------------------------------------------------------------------------

def create_user(
    db: Session,
    email: str,
    username: str,
    password: str,
    role: str = "user",
    force_password_change: bool = True,
) -> User:
    user = User(
        id=str(uuid.uuid4()),
        email=email.lower().strip(),
        username=username.strip(),
        hashed_password=hash_password(password),
        role=role,
        is_active=True,
        force_password_change=force_password_change,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Seed personal defaults for every new user regardless of role
    _seed_user_defaults(db, user.id)

    return user


# ---------------------------------------------------------------------------
# User retrieval
# ---------------------------------------------------------------------------

def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email.lower().strip()).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username.strip()).first()


def list_users(db: Session) -> List[User]:
    return db.query(User).order_by(User.created_at.asc()).all()


# ---------------------------------------------------------------------------
# User mutation
# ---------------------------------------------------------------------------

def set_user_active(db: Session, user_id: str, is_active: bool) -> Optional[User]:
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    user.is_active = is_active
    if not is_active:
        delete_all_user_sessions(db, user_id)
    db.commit()
    db.refresh(user)
    return user


def set_force_password_change(db: Session, user_id: str, value: bool) -> Optional[User]:
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    user.force_password_change = value
    db.commit()
    db.refresh(user)
    return user


def change_password(
    db: Session,
    user_id: str,
    new_password: str,
    clear_force_flag: bool = True,
    keep_session_id: Optional[str] = None,
) -> Optional[User]:
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    user.hashed_password = hash_password(new_password)
    if clear_force_flag:
        user.force_password_change = False
    db.commit()
    if keep_session_id:
        delete_other_user_sessions(db, user_id, keep_session_id)
    else:
        delete_all_user_sessions(db, user_id)
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: str) -> bool:
    """
    Hard-delete all user-owned runtime data, secrets, and the user record.
    Audit logs are preserved with user_id nulled out.
    """
    from ..models.app_setting import AppSetting
    from ..models.provider_config import ProviderConfig
    from ..models.asset import Asset
    from ..models.job_run import JobRun
    from ..models.bucket import Bucket
    from ..models.audit_log import AuditLog
    from ..models.session import UserSession, PasswordResetToken
    from ..models.routing_example import RoutingExample
    from ..models.routing_plan import RoutingPlan, RoutingPlanItem

    user = get_user_by_id(db, user_id)
    if not user:
        return False

    # Nullify audit log attribution (retain the audit trail)
    db.query(AuditLog).filter(AuditLog.user_id == user_id).update({"user_id": None})

    # Hard-delete all user-owned runtime data
    db.query(RoutingPlanItem).filter(
        RoutingPlanItem.user_id == user_id
    ).delete(synchronize_session=False)
    db.query(RoutingPlan).filter(
        RoutingPlan.user_id == user_id
    ).delete(synchronize_session=False)
    db.query(RoutingExample).filter(
        RoutingExample.user_id == user_id
    ).delete(synchronize_session=False)

    db.query(Asset).filter(Asset.user_id == user_id).delete(synchronize_session=False)
    db.query(JobRun).filter(JobRun.user_id == user_id).delete(synchronize_session=False)
    db.query(Bucket).filter(Bucket.user_id == user_id).delete(synchronize_session=False)
    db.query(ProviderConfig).filter(
        ProviderConfig.user_id == user_id
    ).delete(synchronize_session=False)
    db.query(AppSetting).filter(AppSetting.user_id == user_id).delete(synchronize_session=False)
    db.query(UserSession).filter(UserSession.user_id == user_id).delete(synchronize_session=False)
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user_id
    ).delete(synchronize_session=False)

    db.delete(user)
    db.commit()
    return True


# ---------------------------------------------------------------------------
# Default routing tree for new users
# ---------------------------------------------------------------------------

# These leaves are NOT special-cased anywhere — they are normal routing
# leaves with generic settings, used only as a starter tree.
DEFAULT_LEAVES = [
    {
        "name": "Business",
        "description": "Construction, renovation, work sites, tools, project documentation, invoices.",
        "priority": 10,
        "destination_type": "virtual",
        "positive_criteria": [
            "construction or renovation site",
            "tools, materials, work progress, finished work",
            "estimates, invoices, project documentation",
        ],
    },
    {
        "name": "Documents",
        "description": "Receipts, invoices, contracts, scans, screenshots, notes, paper.",
        "priority": 5,
        "destination_type": "virtual",
        "positive_criteria": [
            "receipt, invoice, form, scan, contract",
            "screenshot of emails, notes, whiteboard",
            "photo of paper",
        ],
        "privacy_rules": {
            "documents_visible": "allow",
            "address_visible": "review",
        },
    },
    {
        "name": "Personal",
        "description": "Family, social events, travel, everyday life.",
        "priority": 20,
        "destination_type": "virtual",
        "positive_criteria": [
            "family photo, selfie, group photo",
            "social event, travel, food, pets, hobby",
            "everyday life moments",
        ],
    },
    {
        "name": "Trash",
        "description": "Blurry, accidental, duplicates, test shots — items with no value.",
        "priority": 100,
        "destination_type": "virtual",
        "auto_apply_enabled": False,
        "negative_criteria": [
            "valuable memories",
            "anything you might want to keep",
        ],
        "positive_criteria": [
            "blurry, dark, or overexposed shots with no value",
            "accidental, duplicate, or test shots",
        ],
    },
]


def _seed_user_defaults(db: Session, user_id: str) -> None:
    """Seed a starter routing tree for a new user."""
    from ..models.bucket import Bucket

    for b in DEFAULT_LEAVES:
        db.add(Bucket(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=b["name"],
            path=b["name"],
            is_leaf=True,
            description=b["description"],
            enabled=True,
            priority=b["priority"],
            destination_type=b.get("destination_type", "virtual"),
            positive_criteria_json=b.get("positive_criteria"),
            negative_criteria_json=b.get("negative_criteria"),
            privacy_rules_json=b.get("privacy_rules"),
            auto_apply_enabled=b.get("auto_apply_enabled", False),
        ))

    db.commit()
