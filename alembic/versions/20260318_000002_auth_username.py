"""switch auth to username

Revision ID: 20260318_000002
Revises: 20260317_000001
Create Date: 2026-03-18 00:00:02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260318_000002"
down_revision = "20260317_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("name", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("username", sa.String(length=64), nullable=True))

    op.execute("UPDATE users SET name = split_part(email, '@', 1) WHERE name IS NULL")
    op.execute("UPDATE users SET username = split_part(email, '@', 1) WHERE username IS NULL")

    op.alter_column("users", "name", existing_type=sa.String(length=255), nullable=False)
    op.alter_column("users", "username", existing_type=sa.String(length=64), nullable=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_column("users", "email")


def downgrade() -> None:
    op.add_column("users", sa.Column("email", sa.String(length=320), nullable=True))
    op.execute("UPDATE users SET email = username || '@example.local' WHERE email IS NULL")
    op.alter_column("users", "email", existing_type=sa.String(length=320), nullable=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_column("users", "username")
    op.drop_column("users", "name")
