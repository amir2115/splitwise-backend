"""add user phone number and phone verification codes

Revision ID: 20260420_000009
Revises: 20260413_000008
Create Date: 2026-04-20 00:00:09.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260420_000009"
down_revision = "20260413_000008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone_number", sa.String(length=16), nullable=True))
    op.create_index(op.f("ix_users_phone_number"), "users", ["phone_number"], unique=True)

    op.create_table(
        "phone_verification_codes",
        sa.Column("user_id", sa.String(length=36), nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_phone_verification_codes_phone_number"), "phone_verification_codes", ["phone_number"], unique=False)
    op.create_index(op.f("ix_phone_verification_codes_user_id"), "phone_verification_codes", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_phone_verification_codes_user_id"), table_name="phone_verification_codes")
    op.drop_index(op.f("ix_phone_verification_codes_phone_number"), table_name="phone_verification_codes")
    op.drop_table("phone_verification_codes")
    op.drop_index(op.f("ix_users_phone_number"), table_name="users")
    op.drop_column("users", "phone_number")
