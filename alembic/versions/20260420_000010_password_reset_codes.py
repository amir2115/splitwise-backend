"""add password reset codes

Revision ID: 20260420_000010
Revises: 20260420_000009
Create Date: 2026-04-20 00:00:10.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260420_000010"
down_revision = "20260420_000009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "password_reset_codes",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("identifier_snapshot", sa.String(length=64), nullable=False),
        sa.Column("phone_number", sa.String(length=16), nullable=False),
        sa.Column("code_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("send_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("verify_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reset_token_jti", sa.String(length=36), nullable=True),
        sa.Column("reset_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_password_reset_codes_phone_number"), "password_reset_codes", ["phone_number"], unique=False)
    op.create_index(op.f("ix_password_reset_codes_reset_token_jti"), "password_reset_codes", ["reset_token_jti"], unique=False)
    op.create_index(op.f("ix_password_reset_codes_user_id"), "password_reset_codes", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_password_reset_codes_user_id"), table_name="password_reset_codes")
    op.drop_index(op.f("ix_password_reset_codes_reset_token_jti"), table_name="password_reset_codes")
    op.drop_index(op.f("ix_password_reset_codes_phone_number"), table_name="password_reset_codes")
    op.drop_table("password_reset_codes")
