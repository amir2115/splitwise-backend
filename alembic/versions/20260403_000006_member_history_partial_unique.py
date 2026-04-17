"""allow historical duplicate member usernames within a group

Revision ID: 20260403_000006
Revises: 20260327_000005
Create Date: 2026-04-03 00:00:06
"""

from alembic import op
import sqlalchemy as sa


revision = "20260403_000006"
down_revision = "20260327_000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_members_group_username", "members", type_="unique")
    op.create_index(
        "uq_members_group_username",
        "members",
        ["group_id", "username"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_members_group_username", table_name="members")
    op.create_unique_constraint("uq_members_group_username", "members", ["group_id", "username"])
