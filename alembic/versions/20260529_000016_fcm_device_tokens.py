"""fcm device tokens

Revision ID: 20260529_000016
Revises: 20260529_000015
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260529_000016"
down_revision = "20260529_000015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fcm_device_tokens",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("device_id", sa.String(length=128), nullable=False),
        sa.Column("token", sa.String(length=4096), nullable=False),
        sa.Column("platform", sa.String(length=16), server_default="android", nullable=False),
        sa.Column("android_variant", sa.String(length=32), nullable=True),
        sa.Column("app_version_name", sa.String(length=64), nullable=True),
        sa.Column("app_version_code", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "device_id", name="uq_fcm_device_tokens_user_device"),
    )
    op.create_index(op.f("ix_fcm_device_tokens_user_id"), "fcm_device_tokens", ["user_id"], unique=False)
    op.create_index(op.f("ix_fcm_device_tokens_device_id"), "fcm_device_tokens", ["device_id"], unique=False)
    op.create_index(op.f("ix_fcm_device_tokens_token"), "fcm_device_tokens", ["token"], unique=False)
    op.create_index(op.f("ix_fcm_device_tokens_platform"), "fcm_device_tokens", ["platform"], unique=False)
    op.create_index(op.f("ix_fcm_device_tokens_android_variant"), "fcm_device_tokens", ["android_variant"], unique=False)
    op.create_index(op.f("ix_fcm_device_tokens_is_active"), "fcm_device_tokens", ["is_active"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_fcm_device_tokens_is_active"), table_name="fcm_device_tokens")
    op.drop_index(op.f("ix_fcm_device_tokens_android_variant"), table_name="fcm_device_tokens")
    op.drop_index(op.f("ix_fcm_device_tokens_platform"), table_name="fcm_device_tokens")
    op.drop_index(op.f("ix_fcm_device_tokens_token"), table_name="fcm_device_tokens")
    op.drop_index(op.f("ix_fcm_device_tokens_device_id"), table_name="fcm_device_tokens")
    op.drop_index(op.f("ix_fcm_device_tokens_user_id"), table_name="fcm_device_tokens")
    op.drop_table("fcm_device_tokens")
