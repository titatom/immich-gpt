"""
User CRUD service and admin bootstrap.
"""
import uuid
from typing import Optional, List
from sqlalchemy.orm import Session

from ..models.user import User
from ..services.auth_service import hash_password, delete_all_user_sessions


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

    # Seed personal defaults for non-admin users
    if role == "user":
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
) -> Optional[User]:
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    user.hashed_password = hash_password(new_password)
    if clear_force_flag:
        user.force_password_change = False
    db.commit()
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
    from ..models.prompt_template import PromptTemplate
    from ..models.review_decision import ReviewDecision
    from ..models.suggested_classification import SuggestedClassification
    from ..models.suggested_metadata import SuggestedMetadata
    from ..models.audit_log import AuditLog
    from ..models.session import UserSession, PasswordResetToken

    user = get_user_by_id(db, user_id)
    if not user:
        return False

    # Nullify audit log attribution (retain the audit trail)
    db.query(AuditLog).filter(AuditLog.user_id == user_id).update({"user_id": None})

    # Hard-delete all user-owned runtime data
    asset_ids = [r[0] for r in db.query(Asset.id).filter(Asset.user_id == user_id).all()]
    if asset_ids:
        db.query(SuggestedClassification).filter(
            SuggestedClassification.asset_id.in_(asset_ids)
        ).delete(synchronize_session=False)
        db.query(SuggestedMetadata).filter(
            SuggestedMetadata.asset_id.in_(asset_ids)
        ).delete(synchronize_session=False)
        db.query(ReviewDecision).filter(
            ReviewDecision.asset_id.in_(asset_ids)
        ).delete(synchronize_session=False)

    db.query(Asset).filter(Asset.user_id == user_id).delete(synchronize_session=False)
    db.query(JobRun).filter(JobRun.user_id == user_id).delete(synchronize_session=False)
    db.query(Bucket).filter(Bucket.user_id == user_id).delete(synchronize_session=False)
    db.query(PromptTemplate).filter(
        PromptTemplate.user_id == user_id
    ).delete(synchronize_session=False)
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
# Bootstrap: ensure at least one admin exists on startup
# ---------------------------------------------------------------------------

def ensure_admin_exists(db: Session, email: str, password: str, username: str = "admin") -> None:
    """Create the initial admin account if no users exist yet."""
    count = db.query(User).count()
    if count == 0:
        create_user(
            db,
            email=email,
            username=username,
            password=password,
            role="admin",
            force_password_change=True,
        )


# ---------------------------------------------------------------------------
# Default seeding for new users
# ---------------------------------------------------------------------------

DEFAULT_BUCKETS = [
    {
        "name": "Business",
        "description": "Construction, renovation, work sites, tools, project documentation, invoices",
        "priority": 10,
        "classification_prompt": (
            "Business includes construction, handyman, renovation sites, tools, materials, "
            "estimates, invoices, work progress, finished work, and project documentation."
        ),
    },
    {
        "name": "Documents",
        "description": "Receipts, invoices, contracts, scans, screenshots, notes, paper",
        "priority": 5,
        "classification_prompt": (
            "Documents include receipts, invoices, forms, scans, contracts, screenshots of "
            "emails, notes, whiteboards, and photos of paper. Documents beat Business when "
            "the asset is clearly a receipt, invoice, contract, scan, or photo of paper."
        ),
    },
    {
        "name": "Personal",
        "description": "Family, social events, travel, everyday life",
        "priority": 20,
        "classification_prompt": (
            "Personal includes family photos, selfies, social events, travel, food, pets, "
            "hobbies, and everyday life moments."
        ),
    },
    {
        "name": "Trash",
        "description": "Blurry, accidental, duplicates, test shots, no value",
        "priority": 100,
        "classification_prompt": (
            "Trash includes blurry photos, accidental shots, duplicates, test shots, "
            "completely dark or overexposed images with no value. "
            "When in doubt, do NOT classify as Trash — prefer another bucket."
        ),
    },
]

DEFAULT_PROMPTS = [
    {
        "prompt_type": "global_classification",
        "name": "Global Classification",
        "content": (
            "Classify this asset into the most appropriate Bucket using both image content "
            "and metadata. Be conservative when uncertain."
        ),
    },
    {
        "prompt_type": "description_generation",
        "name": "Description Generation",
        "content": (
            "Generate a concise, useful description that improves future search and review."
        ),
    },
    {
        "prompt_type": "tags_generation",
        "name": "Tags Generation",
        "content": (
            "Generate 3 to 8 practical, search-friendly tags. "
            "Prefer concrete terms over vague words."
        ),
    },
    {
        "prompt_type": "review_guidance",
        "name": "Review Guidance",
        "content": (
            "When reviewing AI suggestions, consider whether the bucket assignment matches "
            "the visible content. Override if the confidence is low or the explanation "
            "does not match what you see."
        ),
    },
]


def _seed_user_defaults(db: Session, user_id: str) -> None:
    """Copy app-level default buckets and prompts into user ownership."""
    from ..models.bucket import Bucket
    from ..models.prompt_template import PromptTemplate

    for b in DEFAULT_BUCKETS:
        db.add(Bucket(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=b["name"],
            description=b["description"],
            enabled=True,
            priority=b["priority"],
            mapping_mode="virtual",
            classification_prompt=b["classification_prompt"],
        ))

    for p in DEFAULT_PROMPTS:
        db.add(PromptTemplate(
            id=str(uuid.uuid4()),
            user_id=user_id,
            prompt_type=p["prompt_type"],
            name=p["name"],
            content=p["content"],
            enabled=True,
            version=1,
        ))

    db.commit()
