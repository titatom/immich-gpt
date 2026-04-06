"""phase2_multi_user

Revision ID: b1e2f3a4c5d6
Revises: 733fd949e72e
Create Date: 2026-04-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b1e2f3a4c5d6'
down_revision: Union[str, Sequence[str], None] = '733fd949e72e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. users table
    # ------------------------------------------------------------------
    op.create_table(
        'users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False, server_default='user'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('force_password_change', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index('ix_users_email', ['email'], unique=True)
        batch_op.create_index('ix_users_username', ['username'], unique=True)

    # ------------------------------------------------------------------
    # 2. user_sessions table
    # ------------------------------------------------------------------
    op.create_table(
        'user_sessions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('user_sessions', schema=None) as batch_op:
        batch_op.create_index('ix_user_sessions_user_id', ['user_id'], unique=False)

    # ------------------------------------------------------------------
    # 3. password_reset_tokens table
    # ------------------------------------------------------------------
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('token_hash', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('password_reset_tokens', schema=None) as batch_op:
        batch_op.create_index('ix_password_reset_tokens_user_id', ['user_id'], unique=False)
        batch_op.create_index('ix_password_reset_tokens_token_hash', ['token_hash'], unique=True)

    # ------------------------------------------------------------------
    # 4. Add user_id to app_settings + change PK
    # ------------------------------------------------------------------
    with op.batch_alter_table('app_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('user_id', sa.String(), nullable=True))

    # Populate id and user_id for any existing rows
    op.execute("UPDATE app_settings SET id = key, user_id = 'legacy' WHERE id IS NULL")

    # SQLite batch_alter_table can recreate the table with proper PK
    with op.batch_alter_table('app_settings', schema=None) as batch_op:
        batch_op.create_index('ix_app_settings_user_id', ['user_id'], unique=False)

    # ------------------------------------------------------------------
    # 5. Add user_id to provider_configs; drop old unique index on provider_name
    # ------------------------------------------------------------------
    with op.batch_alter_table('provider_configs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.String(), nullable=True))
        batch_op.drop_index('ix_provider_configs_provider_name')
        batch_op.create_index('ix_provider_configs_user_id', ['user_id'], unique=False)
        batch_op.create_index('ix_provider_configs_provider_name', ['provider_name'], unique=False)

    op.execute("UPDATE provider_configs SET user_id = 'legacy' WHERE user_id IS NULL")

    # ------------------------------------------------------------------
    # 6. Add user_id to assets; drop old global immich_id unique index
    # ------------------------------------------------------------------
    with op.batch_alter_table('assets', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.String(), nullable=True))
        batch_op.drop_index('ix_assets_immich_id')
        batch_op.create_index('ix_assets_user_id', ['user_id'], unique=False)
        batch_op.create_index('ix_assets_immich_id', ['immich_id'], unique=False)

    op.execute("UPDATE assets SET user_id = 'legacy' WHERE user_id IS NULL")

    # ------------------------------------------------------------------
    # 7. Add user_id to job_runs
    # ------------------------------------------------------------------
    with op.batch_alter_table('job_runs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.String(), nullable=True))
        batch_op.create_index('ix_job_runs_user_id', ['user_id'], unique=False)

    # ------------------------------------------------------------------
    # 8. Add user_id to buckets; drop old global name unique index
    # ------------------------------------------------------------------
    with op.batch_alter_table('buckets', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.String(), nullable=True))
        batch_op.drop_index('ix_buckets_name')
        batch_op.create_index('ix_buckets_user_id', ['user_id'], unique=False)
        batch_op.create_index('ix_buckets_name', ['name'], unique=False)

    op.execute("UPDATE buckets SET user_id = 'legacy' WHERE user_id IS NULL")

    # ------------------------------------------------------------------
    # 9. Add user_id to prompt_templates
    # ------------------------------------------------------------------
    with op.batch_alter_table('prompt_templates', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.String(), nullable=True))
        batch_op.create_index('ix_prompt_templates_user_id', ['user_id'], unique=False)

    op.execute("UPDATE prompt_templates SET user_id = 'legacy' WHERE user_id IS NULL")

    # ------------------------------------------------------------------
    # 10. Add user_id to audit_logs (nullable — preserved on user deletion)
    # ------------------------------------------------------------------
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.String(), nullable=True))
        batch_op.create_index('ix_audit_logs_user_id', ['user_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.drop_index('ix_audit_logs_user_id')
        batch_op.drop_column('user_id')

    with op.batch_alter_table('prompt_templates', schema=None) as batch_op:
        batch_op.drop_index('ix_prompt_templates_user_id')
        batch_op.drop_column('user_id')

    with op.batch_alter_table('buckets', schema=None) as batch_op:
        batch_op.drop_index('ix_buckets_name')
        batch_op.drop_index('ix_buckets_user_id')
        batch_op.drop_column('user_id')
        batch_op.create_index('ix_buckets_name', ['name'], unique=True)

    with op.batch_alter_table('job_runs', schema=None) as batch_op:
        batch_op.drop_index('ix_job_runs_user_id')
        batch_op.drop_column('user_id')

    with op.batch_alter_table('assets', schema=None) as batch_op:
        batch_op.drop_index('ix_assets_immich_id')
        batch_op.drop_index('ix_assets_user_id')
        batch_op.drop_column('user_id')
        batch_op.create_index('ix_assets_immich_id', ['immich_id'], unique=True)

    with op.batch_alter_table('provider_configs', schema=None) as batch_op:
        batch_op.drop_index('ix_provider_configs_provider_name')
        batch_op.drop_index('ix_provider_configs_user_id')
        batch_op.drop_column('user_id')
        batch_op.create_index('ix_provider_configs_provider_name', ['provider_name'], unique=True)

    with op.batch_alter_table('app_settings', schema=None) as batch_op:
        batch_op.drop_index('ix_app_settings_user_id')
        batch_op.drop_column('user_id')
        batch_op.drop_column('id')

    op.drop_table('password_reset_tokens')
    op.drop_table('user_sessions')
    op.drop_table('users')
