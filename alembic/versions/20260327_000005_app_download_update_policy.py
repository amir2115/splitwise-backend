"""add app update policy fields to app download content

Revision ID: 20260327_000005
Revises: 20260327_000004
Create Date: 2026-03-27 23:45:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260327_000005"
down_revision = "20260327_000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("app_download_content", sa.Column("min_supported_version_code", sa.Integer(), nullable=True))
    op.add_column("app_download_content", sa.Column("update_mode", sa.String(length=16), nullable=True))
    op.add_column("app_download_content", sa.Column("update_title", sa.String(length=255), nullable=True))
    op.add_column("app_download_content", sa.Column("update_message", sa.String(length=1000), nullable=True))


def downgrade() -> None:
    op.drop_column("app_download_content", "update_message")
    op.drop_column("app_download_content", "update_title")
    op.drop_column("app_download_content", "update_mode")
    op.drop_column("app_download_content", "min_supported_version_code")
