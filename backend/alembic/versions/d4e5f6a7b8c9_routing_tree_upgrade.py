"""routing_tree_upgrade

Revision ID: d4e5f6a7b8c9
Revises: c8f3b2a1d4e5
Create Date: 2026-05-04 00:00:00.000000

Extend `buckets` into a hierarchical routing-tree node and add the
new `routing_examples`, `routing_plans`, and `routing_plan_items`
tables that power batch review / auto-apply.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c8f3b2a1d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(bind, table: str) -> set[str]:
    insp = sa.inspect(bind)
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    bucket_cols = _column_names(bind, "buckets")

    with op.batch_alter_table("buckets", schema=None) as batch_op:
        if "parent_id" not in bucket_cols:
            batch_op.add_column(sa.Column("parent_id", sa.String(), nullable=True))
        if "path" not in bucket_cols:
            batch_op.add_column(sa.Column("path", sa.String(), nullable=True))
        if "is_leaf" not in bucket_cols:
            batch_op.add_column(sa.Column("is_leaf", sa.Boolean(), nullable=False, server_default=sa.true()))

        if "destination_type" not in bucket_cols:
            batch_op.add_column(sa.Column("destination_type", sa.String(), nullable=False, server_default="virtual"))
        if "immich_album_name" not in bucket_cols:
            batch_op.add_column(sa.Column("immich_album_name", sa.String(), nullable=True))
        if "create_album_if_missing" not in bucket_cols:
            batch_op.add_column(sa.Column("create_album_if_missing", sa.Boolean(), nullable=False, server_default=sa.true()))

        if "auto_apply_enabled" not in bucket_cols:
            batch_op.add_column(sa.Column("auto_apply_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
        if "auto_apply_threshold" not in bucket_cols:
            batch_op.add_column(sa.Column("auto_apply_threshold", sa.Float(), nullable=False, server_default="0.95"))
        if "review_below_threshold" not in bucket_cols:
            batch_op.add_column(sa.Column("review_below_threshold", sa.Float(), nullable=True, server_default="0.85"))

        if "exclusive" not in bucket_cols:
            batch_op.add_column(sa.Column("exclusive", sa.Boolean(), nullable=False, server_default=sa.false()))
        if "allow_secondary" not in bucket_cols:
            batch_op.add_column(sa.Column("allow_secondary", sa.Boolean(), nullable=False, server_default=sa.true()))

        if "minimum_quality" not in bucket_cols:
            batch_op.add_column(sa.Column("minimum_quality", sa.String(), nullable=False, server_default="any"))
        if "allow_blurry" not in bucket_cols:
            batch_op.add_column(sa.Column("allow_blurry", sa.Boolean(), nullable=False, server_default=sa.true()))
        if "allow_dark" not in bucket_cols:
            batch_op.add_column(sa.Column("allow_dark", sa.Boolean(), nullable=False, server_default=sa.true()))
        if "allow_screenshot" not in bucket_cols:
            batch_op.add_column(sa.Column("allow_screenshot", sa.Boolean(), nullable=False, server_default=sa.true()))
        if "allow_duplicate" not in bucket_cols:
            batch_op.add_column(sa.Column("allow_duplicate", sa.Boolean(), nullable=False, server_default=sa.true()))

        if "suggest_description" not in bucket_cols:
            batch_op.add_column(sa.Column("suggest_description", sa.Boolean(), nullable=False, server_default=sa.true()))
        if "suggest_tags" not in bucket_cols:
            batch_op.add_column(sa.Column("suggest_tags", sa.Boolean(), nullable=False, server_default=sa.true()))
        if "suggest_location" not in bucket_cols:
            batch_op.add_column(sa.Column("suggest_location", sa.Boolean(), nullable=False, server_default=sa.false()))
        if "suggest_caption" not in bucket_cols:
            batch_op.add_column(sa.Column("suggest_caption", sa.Boolean(), nullable=False, server_default=sa.false()))
        if "write_description" not in bucket_cols:
            batch_op.add_column(sa.Column("write_description", sa.Boolean(), nullable=False, server_default=sa.true()))
        if "write_tags" not in bucket_cols:
            batch_op.add_column(sa.Column("write_tags", sa.Boolean(), nullable=False, server_default=sa.true()))
        if "write_location" not in bucket_cols:
            batch_op.add_column(sa.Column("write_location", sa.Boolean(), nullable=False, server_default=sa.false()))

        if "custom_prompt_enabled" not in bucket_cols:
            batch_op.add_column(sa.Column("custom_prompt_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
        if "custom_prompt" not in bucket_cols:
            batch_op.add_column(sa.Column("custom_prompt", sa.Text(), nullable=True))

        if "positive_criteria_json" not in bucket_cols:
            batch_op.add_column(sa.Column("positive_criteria_json", sa.JSON(), nullable=True))
        if "negative_criteria_json" not in bucket_cols:
            batch_op.add_column(sa.Column("negative_criteria_json", sa.JSON(), nullable=True))
        if "privacy_rules_json" not in bucket_cols:
            batch_op.add_column(sa.Column("privacy_rules_json", sa.JSON(), nullable=True))
        if "quality_rules_json" not in bucket_cols:
            batch_op.add_column(sa.Column("quality_rules_json", sa.JSON(), nullable=True))
        if "automation_rules_json" not in bucket_cols:
            batch_op.add_column(sa.Column("automation_rules_json", sa.JSON(), nullable=True))
        if "metadata_rules_json" not in bucket_cols:
            batch_op.add_column(sa.Column("metadata_rules_json", sa.JSON(), nullable=True))

    # Backfill: each existing bucket becomes a root-level leaf with
    # path = name and destination_type derived from mapping_mode.
    op.execute(
        "UPDATE buckets SET path = name WHERE path IS NULL OR path = ''"
    )
    op.execute(
        "UPDATE buckets SET is_leaf = 1 WHERE is_leaf IS NULL"
    )
    op.execute(
        "UPDATE buckets SET destination_type = "
        "CASE "
        "  WHEN mapping_mode = 'immich_trash' THEN 'immich_trash' "
        "  WHEN mapping_mode = 'immich_album' THEN 'immich_album' "
        "  WHEN mapping_mode = 'review_only' THEN 'review_only' "
        "  ELSE 'virtual' "
        "END "
        "WHERE destination_type IS NULL OR destination_type = ''"
    )

    # Index for parent_id and a composite (user_id, path) uniqueness guard.
    with op.batch_alter_table("buckets", schema=None) as batch_op:
        try:
            batch_op.create_index("ix_buckets_parent_id", ["parent_id"], unique=False)
        except Exception:
            pass
        try:
            batch_op.create_index("ix_buckets_path", ["path"], unique=False)
        except Exception:
            pass
        try:
            batch_op.create_unique_constraint("uq_buckets_user_path", ["user_id", "path"])
        except Exception:
            pass

    # ------------------------------------------------------------------
    # routing_examples
    # ------------------------------------------------------------------
    op.create_table(
        "routing_examples",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("bucket_id", sa.String(), nullable=False),
        sa.Column("asset_id", sa.String(), nullable=True),
        sa.Column("example_type", sa.String(), nullable=False, server_default="positive"),
        sa.Column("source", sa.String(), nullable=False, server_default="manual"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("routing_examples", schema=None) as batch_op:
        batch_op.create_index("ix_routing_examples_user_id", ["user_id"], unique=False)
        batch_op.create_index("ix_routing_examples_bucket_id", ["bucket_id"], unique=False)
        batch_op.create_index("ix_routing_examples_asset_id", ["asset_id"], unique=False)

    # ------------------------------------------------------------------
    # routing_plans
    # ------------------------------------------------------------------
    op.create_table(
        "routing_plans",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("scope_json", sa.JSON(), nullable=True),
        sa.Column("summary_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("routing_plans", schema=None) as batch_op:
        batch_op.create_index("ix_routing_plans_user_id", ["user_id"], unique=False)
        batch_op.create_index("ix_routing_plans_job_id", ["job_id"], unique=False)
        batch_op.create_index("ix_routing_plans_status", ["status"], unique=False)

    # ------------------------------------------------------------------
    # routing_plan_items
    # ------------------------------------------------------------------
    op.create_table(
        "routing_plan_items",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("plan_id", sa.String(), nullable=False),
        sa.Column("asset_id", sa.String(), nullable=False),
        sa.Column("primary_bucket_id", sa.String(), nullable=True),
        sa.Column("primary_bucket_path", sa.String(), nullable=True),
        sa.Column("secondary_bucket_ids_json", sa.JSON(), nullable=True),
        sa.Column("disposition", sa.String(), nullable=False, server_default="review"),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("review_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("auto_apply", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("review_reasons_json", sa.JSON(), nullable=True),
        sa.Column("reason_codes_json", sa.JSON(), nullable=True),
        sa.Column("safety_flags_json", sa.JSON(), nullable=True),
        sa.Column("quality_flags_json", sa.JSON(), nullable=True),
        sa.Column("suggested_description", sa.Text(), nullable=True),
        sa.Column("suggested_tags_json", sa.JSON(), nullable=True),
        sa.Column("suggested_location_json", sa.JSON(), nullable=True),
        sa.Column("suggested_caption", sa.Text(), nullable=True),
        sa.Column("raw_ai_response_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("routing_plan_items", schema=None) as batch_op:
        batch_op.create_index("ix_routing_plan_items_user_id", ["user_id"], unique=False)
        batch_op.create_index("ix_routing_plan_items_plan_id", ["plan_id"], unique=False)
        batch_op.create_index("ix_routing_plan_items_asset_id", ["asset_id"], unique=False)
        batch_op.create_index("ix_routing_plan_items_primary_bucket_id", ["primary_bucket_id"], unique=False)
        batch_op.create_index("ix_routing_plan_items_status", ["status"], unique=False)


def downgrade() -> None:
    op.drop_table("routing_plan_items")
    op.drop_table("routing_plans")
    op.drop_table("routing_examples")

    with op.batch_alter_table("buckets", schema=None) as batch_op:
        for ix in ("ix_buckets_parent_id", "ix_buckets_path"):
            try:
                batch_op.drop_index(ix)
            except Exception:
                pass
        try:
            batch_op.drop_constraint("uq_buckets_user_path", type_="unique")
        except Exception:
            pass
        for col in (
            "parent_id", "path", "is_leaf",
            "destination_type", "immich_album_name", "create_album_if_missing",
            "auto_apply_enabled", "auto_apply_threshold", "review_below_threshold",
            "exclusive", "allow_secondary",
            "minimum_quality", "allow_blurry", "allow_dark",
            "allow_screenshot", "allow_duplicate",
            "suggest_description", "suggest_tags", "suggest_location", "suggest_caption",
            "write_description", "write_tags", "write_location",
            "custom_prompt_enabled", "custom_prompt",
            "positive_criteria_json", "negative_criteria_json",
            "privacy_rules_json", "quality_rules_json",
            "automation_rules_json", "metadata_rules_json",
        ):
            try:
                batch_op.drop_column(col)
            except Exception:
                pass
