"""app download content singleton

Revision ID: 20260327_000004
Revises: 20260324_000003
Create Date: 2026-03-27 00:00:04
"""

from alembic import op
import sqlalchemy as sa


revision = "20260327_000004"
down_revision = "20260324_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_download_content",
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("subtitle", sa.String(length=1000), nullable=False),
        sa.Column("app_icon_url", sa.String(length=2048), nullable=True),
        sa.Column("version_name", sa.String(length=64), nullable=True),
        sa.Column("version_code", sa.Integer(), nullable=True),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column("file_size", sa.String(length=64), nullable=True),
        sa.Column("bazaar_url", sa.String(length=2048), nullable=True),
        sa.Column("myket_url", sa.String(length=2048), nullable=True),
        sa.Column("direct_download_url", sa.String(length=2048), nullable=True),
        sa.Column("release_notes", sa.JSON(), nullable=False),
        sa.Column("primary_badge_text", sa.String(length=64), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_app_download_content_slug"),
    )


def downgrade() -> None:
    op.drop_table("app_download_content")
