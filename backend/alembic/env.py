import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Make sure the app package is importable from backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import settings  # noqa: E402
from app.database import Base  # noqa: E402

# Import all models so Alembic can detect them for autogenerate
import app.models.asset  # noqa: F401
import app.models.bucket  # noqa: F401
import app.models.prompt_template  # noqa: F401
import app.models.prompt_run  # noqa: F401
import app.models.suggested_classification  # noqa: F401
import app.models.suggested_metadata  # noqa: F401
import app.models.review_decision  # noqa: F401
import app.models.job_run  # noqa: F401
import app.models.audit_log  # noqa: F401
import app.models.provider_config  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use the DATABASE_URL from app settings so migrations always target the right DB.
# Allow override via ALEMBIC_DATABASE_URL for CI/testing scenarios.
_db_url = os.environ.get("ALEMBIC_DATABASE_URL", settings.DATABASE_URL)
config.set_main_option("sqlalchemy.url", _db_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # required for SQLite ALTER TABLE support
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # required for SQLite ALTER TABLE support
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
