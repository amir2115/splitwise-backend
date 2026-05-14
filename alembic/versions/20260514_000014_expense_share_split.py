"""expense by-share split mode

Revision ID: 20260514_000014
Revises: 20260503_000013
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260514_000014"
down_revision = "20260503_000013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add the weight column on expense_shares (nullable; existing rows unaffected).
    op.add_column(
        "expense_shares",
        sa.Column("weight", sa.Float(), nullable=True),
    )

    # 2. Extend the Postgres ENUM with the new SHARE value. Other dialects (e.g.
    # SQLite used in some local test setups) do not have a real ENUM type — the
    # split_type column is just a VARCHAR with no DB-level constraint, so the
    # ALTER TYPE is unnecessary there.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE split_type ADD VALUE IF NOT EXISTS 'SHARE'")


def downgrade() -> None:
    # Postgres does not support DROP VALUE on an ENUM, so this downgrade only
    # removes the weight column. The 'SHARE' value remains reachable but no
    # surviving rows will reference it after the column is gone.
    op.drop_column("expense_shares", "weight")
