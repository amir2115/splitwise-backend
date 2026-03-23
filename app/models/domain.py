from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import OwnedByUserMixin, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class SplitType(str, Enum):
    EQUAL = "EQUAL"
    EXACT = "EXACT"


class Group(UUIDPrimaryKeyMixin, OwnedByUserMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "groups"

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    user = relationship("User", back_populates="groups")
    members = relationship("Member", back_populates="group", cascade="all, delete-orphan")
    expenses = relationship("Expense", back_populates="group", cascade="all, delete-orphan")
    settlements = relationship("Settlement", back_populates="group", cascade="all, delete-orphan")


class Member(UUIDPrimaryKeyMixin, OwnedByUserMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "members"

    group_id: Mapped[str] = mapped_column(String(36), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    group = relationship("Group", back_populates="members")


class Expense(UUIDPrimaryKeyMixin, OwnedByUserMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "expenses"

    group_id: Mapped[str] = mapped_column(String(36), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
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
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    group = relationship("Group", back_populates="settlements")
    from_member = relationship("Member", foreign_keys=[from_member_id])
    to_member = relationship("Member", foreign_keys=[to_member_id])
