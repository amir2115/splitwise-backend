"""add group cards

Revision ID: 20260405_000007
Revises: 20260403_000006
Create Date: 2026-04-05 00:00:07
"""

from alembic import op
import sqlalchemy as sa


revision = "20260405_000007"
down_revision = "20260403_000006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "group_cards",
        sa.Column("group_id", sa.String(length=36), nullable=False),
        sa.Column("member_id", sa.String(length=36), nullable=False),
        sa.Column("card_number", sa.String(length=16), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_group_cards_group_id"), "group_cards", ["group_id"], unique=False)
    op.create_index(op.f("ix_group_cards_member_id"), "group_cards", ["member_id"], unique=False)
    op.create_index(op.f("ix_group_cards_user_id"), "group_cards", ["user_id"], unique=False)
    op.create_index(
        "uq_group_cards_group_card_number",
        "group_cards",
        ["group_id", "card_number"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_group_cards_group_card_number", table_name="group_cards")
    op.drop_index(op.f("ix_group_cards_user_id"), table_name="group_cards")
    op.drop_index(op.f("ix_group_cards_member_id"), table_name="group_cards")
    op.drop_index(op.f("ix_group_cards_group_id"), table_name="group_cards")
    op.drop_table("group_cards")
