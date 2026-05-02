"""add_location_suggestions

Revision ID: c8f3b2a1d4e5
Revises: b1e2f3a4c5d6
Create Date: 2026-05-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c8f3b2a1d4e5"
down_revision: Union[str, Sequence[str], None] = "b1e2f3a4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("suggested_metadata", schema=None) as batch_op:
        batch_op.add_column(sa.Column("location_suggestion_json", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("approved_location_json", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("location_writeback_status", sa.String(), nullable=True, server_default="pending"))
        batch_op.add_column(sa.Column("location_writeback_error", sa.Text(), nullable=True))

    with op.batch_alter_table("review_decisions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("approved_location_json", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("location_approved", sa.Boolean(), nullable=True, server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table("review_decisions", schema=None) as batch_op:
        batch_op.drop_column("location_approved")
        batch_op.drop_column("approved_location_json")

    with op.batch_alter_table("suggested_metadata", schema=None) as batch_op:
        batch_op.drop_column("location_writeback_error")
        batch_op.drop_column("location_writeback_status")
        batch_op.drop_column("approved_location_json")
        batch_op.drop_column("location_suggestion_json")
