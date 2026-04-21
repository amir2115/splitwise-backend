from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlalchemy import JSON, Boolean, Date, DateTime, Enum as SqlEnum, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import OwnedByUserMixin, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class SplitType(str, Enum):
    EQUAL = "EQUAL"
    EXACT = "EXACT"


class MembershipStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PENDING_INVITE = "PENDING_INVITE"


class GroupInviteStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class Group(UUIDPrimaryKeyMixin, OwnedByUserMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "groups"

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    user = relationship("User", back_populates="groups")
    memberships = relationship("GroupMembership", back_populates="group", cascade="all, delete-orphan")
    members = relationship("Member", back_populates="group", cascade="all, delete-orphan")
    invites = relationship("GroupInvite", back_populates="group", cascade="all, delete-orphan")
    group_cards = relationship("GroupCard", back_populates="group", cascade="all, delete-orphan")
    expenses = relationship("Expense", back_populates="group", cascade="all, delete-orphan")
    settlements = relationship("Settlement", back_populates="group", cascade="all, delete-orphan")


class Member(UUIDPrimaryKeyMixin, OwnedByUserMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "members"
    __table_args__ = (
        Index(
            "uq_members_group_username",
            "group_id",
            "username",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
            sqlite_where=text("deleted_at IS NULL"),
        ),
    )

    group_id: Mapped[str] = mapped_column(String(36), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    linked_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    membership_status: Mapped[MembershipStatus] = mapped_column(
        SqlEnum(MembershipStatus, name="membership_status"),
        nullable=False,
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    group = relationship("Group", back_populates="members")
    linked_user = relationship("User", foreign_keys=[linked_user_id])


class GroupMembership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "group_memberships"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_group_memberships_group_user"),)

    group_id: Mapped[str] = mapped_column(String(36), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[MembershipStatus] = mapped_column(SqlEnum(MembershipStatus, name="membership_status"), nullable=False)

    group = relationship("Group", back_populates="memberships")
    user = relationship("User")


class GroupInvite(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "group_invites"

    group_id: Mapped[str] = mapped_column(String(36), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    inviter_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    invitee_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    member_id: Mapped[str] = mapped_column(String(36), ForeignKey("members.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[GroupInviteStatus] = mapped_column(SqlEnum(GroupInviteStatus, name="group_invite_status"), nullable=False)
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    group = relationship("Group", back_populates="invites")
    inviter_user = relationship("User", foreign_keys=[inviter_user_id])
    invitee_user = relationship("User", foreign_keys=[invitee_user_id])
    member = relationship("Member")


class GroupCard(UUIDPrimaryKeyMixin, OwnedByUserMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "group_cards"
    __table_args__ = (
        Index(
            "uq_group_cards_group_card_number",
            "group_id",
            "card_number",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
            sqlite_where=text("deleted_at IS NULL"),
        ),
    )

    group_id: Mapped[str] = mapped_column(String(36), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    member_id: Mapped[str] = mapped_column(String(36), ForeignKey("members.id", ondelete="RESTRICT"), nullable=False, index=True)
    card_number: Mapped[str] = mapped_column(String(16), nullable=False)

    group = relationship("Group", back_populates="group_cards")
    member = relationship("Member")


class UserConnection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_connections"
    __table_args__ = (UniqueConstraint("user_low_id", "user_high_id", name="uq_user_connections_pair"),)

    user_low_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    user_high_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    user_low = relationship("User", foreign_keys=[user_low_id])
    user_high = relationship("User", foreign_keys=[user_high_id])


class AppDownloadContent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "app_download_content"
    __table_args__ = (UniqueConstraint("slug", name="uq_app_download_content_slug"),)

    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subtitle: Mapped[str] = mapped_column(String(1000), nullable=False)
    app_icon_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    version_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    version_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    release_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    file_size: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    bazaar_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    myket_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    direct_download_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    release_notes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    primary_badge_text: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    min_supported_version_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    update_mode: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    update_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    update_message: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)


class AppSetting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "app_settings"
    __table_args__ = (UniqueConstraint("key", name="uq_app_settings_key"),)

    key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    value: Mapped[str] = mapped_column(String(4096), nullable=False)


class Expense(UUIDPrimaryKeyMixin, OwnedByUserMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "expenses"

    group_id: Mapped[str] = mapped_column(String(36), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    total_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    split_type: Mapped[SplitType] = mapped_column(SqlEnum(SplitType, name="split_type"), nullable=False)

    group = relationship("Group", back_populates="expenses")
    payers = relationship("ExpensePayer", back_populates="expense", cascade="all, delete-orphan")
    shares = relationship("ExpenseShare", back_populates="expense", cascade="all, delete-orphan")


class ExpensePayer(Base):
    __tablename__ = "expense_payers"
    __table_args__ = (UniqueConstraint("expense_id", "member_id", name="uq_expense_payers_expense_member"),)

    expense_id: Mapped[str] = mapped_column(String(36), ForeignKey("expenses.id", ondelete="CASCADE"), primary_key=True)
    member_id: Mapped[str] = mapped_column(String(36), ForeignKey("members.id", ondelete="CASCADE"), primary_key=True)
    amount_paid: Mapped[int] = mapped_column(Integer, nullable=False)

    expense = relationship("Expense", back_populates="payers")
    member = relationship("Member")


class ExpenseShare(Base):
    __tablename__ = "expense_shares"
    __table_args__ = (UniqueConstraint("expense_id", "member_id", name="uq_expense_shares_expense_member"),)

    expense_id: Mapped[str] = mapped_column(String(36), ForeignKey("expenses.id", ondelete="CASCADE"), primary_key=True)
    member_id: Mapped[str] = mapped_column(String(36), ForeignKey("members.id", ondelete="CASCADE"), primary_key=True)
    amount_owed: Mapped[int] = mapped_column(Integer, nullable=False)

    expense = relationship("Expense", back_populates="shares")
    member = relationship("Member")


class Settlement(UUIDPrimaryKeyMixin, OwnedByUserMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "settlements"

    group_id: Mapped[str] = mapped_column(String(36), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    from_member_id: Mapped[str] = mapped_column(String(36), ForeignKey("members.id", ondelete="RESTRICT"), nullable=False)
    to_member_id: Mapped[str] = mapped_column(String(36), ForeignKey("members.id", ondelete="RESTRICT"), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    group = relationship("Group", back_populates="settlements")
    from_member = relationship("Member", foreign_keys=[from_member_id])
    to_member = relationship("Member", foreign_keys=[to_member_id])
