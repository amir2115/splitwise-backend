"""user client tracking

Revision ID: 20260529_000015
Revises: 20260514_000014
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260529_000015"
down_revision = "20260514_000014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("client_platform", sa.String(length=16), nullable=True))
    op.add_column("users", sa.Column("android_variant", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("last_client_seen_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_users_client_platform"), "users", ["client_platform"], unique=False)
    op.create_index(op.f("ix_users_android_variant"), "users", ["android_variant"], unique=False)

    op.add_column("pending_registrations", sa.Column("client_platform", sa.String(length=16), nullable=True))
    op.add_column("pending_registrations", sa.Column("android_variant", sa.String(length=32), nullable=True))
    op.add_column("pending_registrations", sa.Column("last_client_seen_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("pending_registrations", "last_client_seen_at")
    op.drop_column("pending_registrations", "android_variant")
    op.drop_column("pending_registrations", "client_platform")

    op.drop_index(op.f("ix_users_android_variant"), table_name="users")
    op.drop_index(op.f("ix_users_client_platform"), table_name="users")
    op.drop_column("users", "last_client_seen_at")
    op.drop_column("users", "android_variant")
    op.drop_column("users", "client_platform")
