"""shared group invites and username members

Revision ID: 20260324_000003
Revises: 20260318_000002
Create Date: 2026-03-24 00:00:03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid


revision = "20260324_000003"
down_revision = "20260318_000002"
branch_labels = None
depends_on = None


membership_status = postgresql.ENUM("ACTIVE", "PENDING_INVITE", name="membership_status", create_type=False)
group_invite_status = postgresql.ENUM("PENDING", "ACCEPTED", "REJECTED", name="group_invite_status", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    membership_status.create(bind, checkfirst=True)
    group_invite_status.create(bind, checkfirst=True)

    op.create_table(
        "group_memberships",
        sa.Column("group_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("status", membership_status, nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "user_id", name="uq_group_memberships_group_user"),
    )
    op.create_index(op.f("ix_group_memberships_group_id"), "group_memberships", ["group_id"], unique=False)
    op.create_index(op.f("ix_group_memberships_user_id"), "group_memberships", ["user_id"], unique=False)

    op.create_table(
        "user_connections",
        sa.Column("user_low_id", sa.String(length=36), nullable=False),
        sa.Column("user_high_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_high_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_low_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_low_id", "user_high_id", name="uq_user_connections_pair"),
    )
    op.create_index(op.f("ix_user_connections_user_high_id"), "user_connections", ["user_high_id"], unique=False)
    op.create_index(op.f("ix_user_connections_user_low_id"), "user_connections", ["user_low_id"], unique=False)

    op.alter_column("members", "name", new_column_name="username")
    op.add_column("members", sa.Column("linked_user_id", sa.String(length=36), nullable=True))
    op.add_column("members", sa.Column("membership_status", membership_status, nullable=True))
    op.create_index(op.f("ix_members_linked_user_id"), "members", ["linked_user_id"], unique=False)
    members = bind.execute(sa.text("SELECT id, group_id, username FROM members ORDER BY created_at, id")).fetchall()
    seen_usernames: set[tuple[str, str]] = set()
    for member_id, group_id, raw_username in members:
        base_username = (raw_username or "").strip().lower().replace(" ", "_")[:48] or f"member_{member_id[:8]}"
        candidate = base_username
        suffix = 1
        while (group_id, candidate) in seen_usernames:
            candidate = f"{base_username[:40]}_{suffix}"
            suffix += 1
        seen_usernames.add((group_id, candidate))
        if candidate != raw_username:
            bind.execute(
                sa.text("UPDATE members SET username = :username WHERE id = :id"),
                {"id": member_id, "username": candidate},
            )
    op.create_unique_constraint("uq_members_group_username", "members", ["group_id", "username"])
    op.create_foreign_key("fk_members_linked_user_id_users", "members", "users", ["linked_user_id"], ["id"], ondelete="SET NULL")
    op.execute("UPDATE members SET membership_status = 'ACTIVE' WHERE membership_status IS NULL")
    op.alter_column("members", "membership_status", nullable=False)

    op.create_table(
        "group_invites",
        sa.Column("group_id", sa.String(length=36), nullable=False),
        sa.Column("inviter_user_id", sa.String(length=36), nullable=False),
        sa.Column("invitee_user_id", sa.String(length=36), nullable=False),
        sa.Column("member_id", sa.String(length=36), nullable=False),
        sa.Column("status", group_invite_status, nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["inviter_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invitee_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_group_invites_group_id"), "group_invites", ["group_id"], unique=False)
    op.create_index(op.f("ix_group_invites_invitee_user_id"), "group_invites", ["invitee_user_id"], unique=False)
    op.create_index(op.f("ix_group_invites_inviter_user_id"), "group_invites", ["inviter_user_id"], unique=False)
    op.create_index(op.f("ix_group_invites_member_id"), "group_invites", ["member_id"], unique=False)

    groups = bind.execute(sa.text("SELECT id, user_id, created_at, updated_at FROM groups")).fetchall()
    for group_id, user_id, created_at, updated_at in groups:
        bind.execute(
            sa.text(
                """
                INSERT INTO group_memberships (id, group_id, user_id, status, created_at, updated_at)
                VALUES (:id, :group_id, :user_id, :status, :created_at, :updated_at)
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "group_id": group_id,
                "user_id": user_id,
                "status": "ACTIVE",
                "created_at": created_at,
                "updated_at": updated_at,
            },
        )


def downgrade() -> None:
    op.drop_index(op.f("ix_group_invites_member_id"), table_name="group_invites")
    op.drop_index(op.f("ix_group_invites_inviter_user_id"), table_name="group_invites")
    op.drop_index(op.f("ix_group_invites_invitee_user_id"), table_name="group_invites")
    op.drop_index(op.f("ix_group_invites_group_id"), table_name="group_invites")
    op.drop_table("group_invites")

    op.drop_constraint("fk_members_linked_user_id_users", "members", type_="foreignkey")
    op.drop_constraint("uq_members_group_username", "members", type_="unique")
    op.drop_index(op.f("ix_members_linked_user_id"), table_name="members")
    op.drop_column("members", "membership_status")
    op.drop_column("members", "linked_user_id")
    op.alter_column("members", "username", new_column_name="name")

    op.drop_index(op.f("ix_user_connections_user_low_id"), table_name="user_connections")
    op.drop_index(op.f("ix_user_connections_user_high_id"), table_name="user_connections")
    op.drop_table("user_connections")

    op.drop_index(op.f("ix_group_memberships_user_id"), table_name="group_memberships")
    op.drop_index(op.f("ix_group_memberships_group_id"), table_name="group_memberships")
    op.drop_table("group_memberships")

    group_invite_status.drop(op.get_bind(), checkfirst=True)
    membership_status.drop(op.get_bind(), checkfirst=True)
