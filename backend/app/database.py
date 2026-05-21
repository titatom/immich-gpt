import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings

logger = logging.getLogger(__name__)
_db_url = settings.DATABASE_URL

# Ensure the data directory exists before SQLite tries to create the file.
if _db_url.startswith("sqlite:///"):
    _db_path = _db_url.replace("sqlite:///", "")
    _db_dir = os.path.dirname(_db_path)
    if _db_dir:
        os.makedirs(_db_dir, exist_ok=True)

# check_same_thread=False is required for SQLite when multiple threads share
# the same connection (FastAPI's thread-pool request handling).
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
        asset, bucket, prompt_run,
        job_run, audit_log, provider_config, app_setting,
        routing_example, routing_plan,
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
        if str(engine.url) not in {"sqlite:///:memory:", "sqlite://"}:
            logger.exception("Database migration failed")
            raise
        logger.exception("Database migration failed; falling back to create_all for in-memory test DB")

    # Fallback: plain create_all (used for in-memory SQLite in tests).
    Base.metadata.create_all(bind=engine)
