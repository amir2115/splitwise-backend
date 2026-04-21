from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(16), unique=True, nullable=True, index=True)
    is_phone_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")

    groups = relationship("Group", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    phone_verification_codes = relationship("PhoneVerificationCode", back_populates="user", cascade="all, delete-orphan")
    password_reset_codes = relationship("PasswordResetCode", back_populates="user", cascade="all, delete-orphan")
    invited_account_tokens = relationship("InvitedAccountToken", back_populates="user", cascade="all, delete-orphan")


class RefreshToken(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (UniqueConstraint("token_jti", name="uq_refresh_tokens_token_jti"),)

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_jti: Mapped[str] = mapped_column(String(36), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="refresh_tokens")


class PhoneVerificationCode(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "phone_verification_codes"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    phone_number: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    send_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    verify_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    user = relationship("User", back_populates="phone_verification_codes")


class PasswordResetCode(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "password_reset_codes"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    identifier_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    send_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    verify_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    reset_token_jti: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    reset_token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="password_reset_codes")


class PendingRegistration(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "pending_registrations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    send_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    verify_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")


class InvitedAccountToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "invited_account_tokens"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_jti: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    send_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    verify_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    code_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    code_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="invited_account_tokens")
