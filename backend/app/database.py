import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings

_db_url = settings.DATABASE_URL

# Ensure the data directory exists before SQLite tries to create the file.
if _db_url.startswith("sqlite:///"):
    _db_path = _db_url.replace("sqlite:///", "")
    _db_dir = os.path.dirname(_db_path)
    if _db_dir:
        os.makedirs(_db_dir, exist_ok=True)

# SQLite requires check_same_thread=False; PostgreSQL does not accept it.
_connect_args = {}
if _db_url.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    _db_url,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Apply all pending Alembic migrations.

    Falls back to ``create_all`` when Alembic is not configured (e.g. when
    running against a plain in-memory SQLite database during tests).
    """
    # Import every model so Base.metadata is fully populated before we
    # attempt either the Alembic run or the create_all fallback.
    from .models import (  # noqa: F401
        User, UserSession, PasswordResetToken,
        asset, bucket, prompt_template, prompt_run,
        suggested_classification, suggested_metadata,
        review_decision, job_run, audit_log, provider_config, app_setting,
    )

    try:
        from alembic.config import Config
        from alembic import command
        import os as _os

        # Locate alembic.ini relative to this file: backend/app/ → backend/
        _here = _os.path.dirname(_os.path.abspath(__file__))
        _alembic_ini = _os.path.join(_here, "..", "alembic.ini")

        if _os.path.isfile(_alembic_ini):
            alembic_cfg = Config(_alembic_ini)
            # Override the URL so it always matches the runtime engine.
            alembic_cfg.set_main_option("sqlalchemy.url", str(engine.url))
            command.upgrade(alembic_cfg, "head")
            return
    except Exception:
        pass

    # Fallback: plain create_all (used for in-memory SQLite in tests).
    Base.metadata.create_all(bind=engine)
