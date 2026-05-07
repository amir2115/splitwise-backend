"""add article hero image url

Revision ID: 20260503_000013
Revises: 20260430_000012
Create Date: 2026-05-03 00:00:13.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260503_000013"
down_revision = "20260430_000012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("articles", sa.Column("hero_image_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("articles", "hero_image_url")
