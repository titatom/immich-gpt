"""drop_legacy_review_pipeline

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-04 23:00:00.000000

The legacy bucket / prompt / review pipeline is fully replaced by the
routing-tree workflow.  This migration removes:

  - prompt_templates table
  - suggested_classifications table
  - suggested_metadata table
  - review_decisions table

  - legacy bucket columns:
      mapping_mode, classification_prompt,
      examples_json, negative_examples_json, confidence_threshold

This is a one-way migration.  Down-grading is not supported because the
data dropped here cannot be re-derived; the down() method only restores
empty table shells so Alembic stays consistent with the pre-cleanup
schema.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(bind, table: str) -> set[str]:
    insp = sa.inspect(bind)
    if table not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def _table_exists(bind, name: str) -> bool:
    insp = sa.inspect(bind)
    return name in insp.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()

    for table in ("review_decisions", "suggested_metadata",
                  "suggested_classifications", "prompt_templates"):
        if _table_exists(bind, table):
            op.drop_table(table)

    bucket_cols = _column_names(bind, "buckets")
    legacy_cols = (
        "mapping_mode",
        "classification_prompt",
        "examples_json",
        "negative_examples_json",
        "confidence_threshold",
    )
    if any(c in bucket_cols for c in legacy_cols):
        with op.batch_alter_table("buckets", schema=None) as batch_op:
            for col in legacy_cols:
                if col in bucket_cols:
                    try:
                        batch_op.drop_column(col)
                    except Exception:
                        pass


def downgrade() -> None:
    """One-way: recreate empty tables so Alembic version graph stays valid.

    No data is restored; the legacy review pipeline has been removed
    from the application code.
    """
    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("prompt_type", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=True),
        sa.Column("bucket_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("prompt_templates", schema=None) as batch_op:
        batch_op.create_index("ix_prompt_templates_prompt_type", ["prompt_type"], unique=False)
        batch_op.create_index("ix_prompt_templates_user_id", ["user_id"], unique=False)
    op.create_table(
        "suggested_classifications",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("asset_id", sa.String(), nullable=False),
        sa.Column("suggested_bucket_id", sa.String(), nullable=True),
        sa.Column("suggested_bucket_name", sa.String(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("subalbum_suggestion", sa.String(), nullable=True),
        sa.Column("review_recommended", sa.Boolean(), nullable=True),
        sa.Column("provider_name", sa.String(), nullable=True),
        sa.Column("prompt_run_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("override_bucket_id", sa.String(), nullable=True),
        sa.Column("override_bucket_name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("suggested_classifications", schema=None) as batch_op:
        batch_op.create_index("ix_suggested_classifications_asset_id", ["asset_id"], unique=False)
        batch_op.create_index("ix_suggested_classifications_status", ["status"], unique=False)
    op.create_table(
        "suggested_metadata",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("asset_id", sa.String(), nullable=False),
        sa.Column("description_suggestion", sa.Text(), nullable=True),
        sa.Column("tags_json", sa.JSON(), nullable=True),
        sa.Column("approved_description", sa.Text(), nullable=True),
        sa.Column("approved_tags_json", sa.JSON(), nullable=True),
        sa.Column("writeback_status", sa.String(), nullable=True),
        sa.Column("writeback_error", sa.Text(), nullable=True),
        sa.Column("provider_name", sa.String(), nullable=True),
        sa.Column("prompt_run_id", sa.String(), nullable=True),
        sa.Column("location_suggestion_json", sa.JSON(), nullable=True),
        sa.Column("approved_location_json", sa.JSON(), nullable=True),
        sa.Column("location_writeback_status", sa.String(), nullable=True),
        sa.Column("location_writeback_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("suggested_metadata", schema=None) as batch_op:
        batch_op.create_index("ix_suggested_metadata_asset_id", ["asset_id"], unique=False)
    op.create_table(
        "review_decisions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("asset_id", sa.String(), nullable=False),
        sa.Column("suggested_classification_id", sa.String(), nullable=True),
        sa.Column("suggested_metadata_id", sa.String(), nullable=True),
        sa.Column("decision_type", sa.String(), nullable=False),
        sa.Column("approved_bucket_id", sa.String(), nullable=True),
        sa.Column("approved_bucket_name", sa.String(), nullable=True),
        sa.Column("approved_description", sa.Text(), nullable=True),
        sa.Column("approved_tags_json", sa.JSON(), nullable=True),
        sa.Column("approved_subalbum", sa.String(), nullable=True),
        sa.Column("subalbum_approved", sa.Boolean(), nullable=True),
        sa.Column("approved_location_json", sa.JSON(), nullable=True),
        sa.Column("location_approved", sa.Boolean(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("writeback_triggered", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("review_decisions", schema=None) as batch_op:
        batch_op.create_index("ix_review_decisions_asset_id", ["asset_id"], unique=False)

    with op.batch_alter_table("buckets", schema=None) as batch_op:
        batch_op.add_column(sa.Column("mapping_mode", sa.String(), nullable=True, server_default="virtual"))
        batch_op.add_column(sa.Column("classification_prompt", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("examples_json", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("negative_examples_json", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("confidence_threshold", sa.Float(), nullable=True))
