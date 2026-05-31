"""add app releases

Revision ID: 20260530_000017
Revises: 20260529_000016
Create Date: 2026-05-30 00:00:17
"""

from alembic import op
import sqlalchemy as sa


revision = "20260530_000017"
down_revision = "20260529_000016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_releases",
        sa.Column("version_name", sa.String(length=64), nullable=False),
        sa.Column("version_code", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), server_default="دانلود اپلیکیشن", nullable=False),
        sa.Column("subtitle", sa.String(length=1000), server_default="آخرین نسخه دنگینو را از استور دلخواهت نصب کن.", nullable=False),
        sa.Column("app_icon_url", sa.String(length=2048), nullable=True),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column("file_size", sa.String(length=64), nullable=True),
        sa.Column("bazaar_url", sa.String(length=2048), nullable=True),
        sa.Column("myket_url", sa.String(length=2048), nullable=True),
        sa.Column("release_notes", sa.JSON(), nullable=False),
        sa.Column("primary_badge_text", sa.String(length=64), nullable=True),
        sa.Column("min_supported_version_code", sa.Integer(), nullable=True),
        sa.Column("update_mode", sa.String(length=16), nullable=True),
        sa.Column("update_title", sa.String(length=255), nullable=True),
        sa.Column("update_message", sa.String(length=1000), nullable=True),
        sa.Column("apk_object_key", sa.String(length=1024), nullable=True),
        sa.Column("apk_url", sa.String(length=2048), nullable=True),
        sa.Column("is_published", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version_code", name="uq_app_releases_version_code"),
    )
    op.create_index("idx_app_releases_published", "app_releases", ["is_published", "published_at"])


def downgrade() -> None:
    op.drop_index("idx_app_releases_published", table_name="app_releases")
    op.drop_table("app_releases")
