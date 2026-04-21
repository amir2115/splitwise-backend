"""add registration, invited account, runtime settings, and phone verification flag

Revision ID: 20260421_000011
Revises: 20260420_000010
Create Date: 2026-04-21 00:00:11.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260421_000011"
down_revision = "20260420_000010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_phone_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute("UPDATE users SET is_phone_verified = CASE WHEN phone_number IS NOT NULL THEN TRUE ELSE FALSE END")

    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("value", sa.String(length=4096), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_app_settings_key"),
    )
    op.create_index(op.f("ix_app_settings_key"), "app_settings", ["key"], unique=False)

    op.create_table(
        "pending_registrations",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("phone_number", sa.String(length=16), nullable=False),
        sa.Column("code_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("send_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("verify_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pending_registrations_username"), "pending_registrations", ["username"], unique=False)
    op.create_index(op.f("ix_pending_registrations_phone_number"), "pending_registrations", ["phone_number"], unique=False)

    op.create_table(
        "invited_account_tokens",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_jti", sa.String(length=36), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("send_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("verify_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("code_hash", sa.String(length=255), nullable=True),
        sa.Column("code_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invited_account_tokens_user_id"), "invited_account_tokens", ["user_id"], unique=False)
    op.create_index(op.f("ix_invited_account_tokens_token_jti"), "invited_account_tokens", ["token_jti"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_invited_account_tokens_token_jti"), table_name="invited_account_tokens")
    op.drop_index(op.f("ix_invited_account_tokens_user_id"), table_name="invited_account_tokens")
    op.drop_table("invited_account_tokens")

    op.drop_index(op.f("ix_pending_registrations_phone_number"), table_name="pending_registrations")
    op.drop_index(op.f("ix_pending_registrations_username"), table_name="pending_registrations")
    op.drop_table("pending_registrations")

    op.drop_index(op.f("ix_app_settings_key"), table_name="app_settings")
    op.drop_table("app_settings")

    op.drop_column("users", "is_phone_verified")
