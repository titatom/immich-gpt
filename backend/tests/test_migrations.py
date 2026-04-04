"""
Alembic migration round-trip test.

Verifies that:
1. upgrade head applies all migrations cleanly to a fresh SQLite DB.
2. downgrade -1 from head can be applied without errors.
3. re-upgrade head succeeds after a downgrade.

These tests run against a temporary SQLite file and do NOT touch the
application database.  They require no Redis, Immich, or OpenAI.
"""
import os
import tempfile
import pytest
from alembic.config import Config
from alembic import command


@pytest.fixture(scope="module")
def alembic_cfg():
    """Return an Alembic Config pointing at the repo alembic.ini."""
    here = os.path.dirname(os.path.abspath(__file__))
    ini_path = os.path.join(here, "..", "alembic.ini")
    cfg = Config(ini_path)
    return cfg


def _run_with_temp_db(alembic_cfg: Config, fn):
    """Execute *fn(cfg)* against a fresh temporary SQLite database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        tmp_path = f.name
    try:
        cfg = Config(alembic_cfg.config_file_name)
        cfg.set_main_option("sqlalchemy.url", f"sqlite:///{tmp_path}")
        fn(cfg)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def test_upgrade_head(alembic_cfg):
    """All pending migrations apply to a blank DB without error."""
    def run(cfg):
        command.upgrade(cfg, "head")

    _run_with_temp_db(alembic_cfg, run)


def test_downgrade_minus_one(alembic_cfg):
    """Can downgrade one step from head without error."""
    def run(cfg):
        command.upgrade(cfg, "head")
        command.downgrade(cfg, "-1")

    _run_with_temp_db(alembic_cfg, run)


def test_upgrade_after_downgrade(alembic_cfg):
    """Re-upgrading after a downgrade returns to head cleanly."""
    def run(cfg):
        command.upgrade(cfg, "head")
        command.downgrade(cfg, "-1")
        command.upgrade(cfg, "head")

    _run_with_temp_db(alembic_cfg, run)


def test_full_downgrade_and_reupgrade(alembic_cfg):
    """Downgrade all the way to base, then upgrade back to head."""
    def run(cfg):
        command.upgrade(cfg, "head")
        command.downgrade(cfg, "base")
        command.upgrade(cfg, "head")

    _run_with_temp_db(alembic_cfg, run)
