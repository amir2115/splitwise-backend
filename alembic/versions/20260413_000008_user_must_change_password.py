"""add must_change_password to users

Revision ID: 20260413_000008
Revises: 20260405_000007
Create Date: 2026-04-13 00:00:08.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260413_000008"
down_revision = "20260405_000007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column(
        "users",
        "must_change_password",
        existing_type=sa.Boolean(),
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("users", "must_change_password")
