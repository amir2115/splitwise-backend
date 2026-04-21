from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Lock

from fastapi import status
from sqlalchemy import Select, case, delete, func, or_, select, update
from sqlalchemy.orm import Session

from app.admin.security import create_admin_access_token
from app.auth.security import verify_password
from app.core.config import get_settings
from app.core.errors import DomainError
from app.core.time import ensure_utc, utcnow
from app.models.domain import Expense, Group, GroupCard, GroupInvite, GroupMembership, Member, Settlement, UserConnection
from app.models.user import RefreshToken, User
from app.schemas.admin import (
    AdminAuthResponse,
    AdminResponse,
    AdminRuntimeSettingsResponse,
    AdminRuntimeSettingsUpdateRequest,
    AdminUserListItem,
    AdminUserListResponse,
    AdminUserUpdateRequest,
    AdminUsersPagination,
    AdminUsersQuery,
    AdminUsersSummary,
)
from app.services.auth_service import _normalize_name, _normalize_phone_number
from app.services.runtime_settings_service import list_runtime_settings, set_runtime_settings


@dataclass
class _RateLimitState:
    attempts: list[datetime] = field(default_factory=list)
    locked_until: datetime | None = None


class AdminLoginRateLimiter:
    def __init__(self) -> None:
        self._states: dict[str, _RateLimitState] = defaultdict(_RateLimitState)
        self._lock = Lock()

    def _build_key(self, ip_address: str, username: str) -> str:
        normalized_username = username.strip().lower()
        return f"{ip_address}:{normalized_username}"

    def check_allowed(self, ip_address: str, username: str) -> None:
        settings = get_settings()
        key = self._build_key(ip_address, username)
        now = utcnow()
        with self._lock:
            state = self._states.get(key)
            if not state:
                return
            window_start = now.timestamp() - settings.admin_panel_rate_limit_window_minutes * 60
            state.attempts = [attempt for attempt in state.attempts if attempt.timestamp() >= window_start]
            if state.locked_until and ensure_utc(state.locked_until) > now:
                raise DomainError(
                    code="admin_rate_limited",
                    message="Too many failed login attempts. Please try again later.",
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            if state.locked_until and ensure_utc(state.locked_until) <= now:
                state.locked_until = None
            if not state.attempts and not state.locked_until:
                self._states.pop(key, None)

    def register_failure(self, ip_address: str, username: str) -> None:
        settings = get_settings()
        key = self._build_key(ip_address, username)
        now = utcnow()
        with self._lock:
            state = self._states[key]
            window_start = now.timestamp() - settings.admin_panel_rate_limit_window_minutes * 60
            state.attempts = [attempt for attempt in state.attempts if attempt.timestamp() >= window_start]
            state.attempts.append(now)
            if len(state.attempts) >= settings.admin_panel_rate_limit_attempts:
                state.locked_until = now + timedelta(minutes=settings.admin_panel_rate_limit_lockout_minutes)

    def register_success(self, ip_address: str, username: str) -> None:
        key = self._build_key(ip_address, username)
        with self._lock:
            self._states.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._states.clear()


admin_login_rate_limiter = AdminLoginRateLimiter()


def authenticate_admin(username: str, password: str, ip_address: str) -> AdminAuthResponse:
    settings = get_settings()
    admin_login_rate_limiter.check_allowed(ip_address, username)

    configured_username = (settings.admin_panel_username or "").strip().lower()
    provided_username = username.strip().lower()
    if not configured_username or (not settings.admin_panel_password and not settings.admin_panel_password_hash):
        raise DomainError(code="admin_not_configured", message="Admin panel authentication is not configured", status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

    is_valid_username = provided_username == configured_username
    is_valid_password = False
    if settings.admin_panel_password_hash:
        is_valid_password = verify_password(password, settings.admin_panel_password_hash)
    elif settings.admin_panel_password:
        is_valid_password = password == settings.admin_panel_password

    if not is_valid_username or not is_valid_password:
        admin_login_rate_limiter.register_failure(ip_address, username)
        raise DomainError(code="invalid_credentials", message="Invalid username or password", status_code=status.HTTP_401_UNAUTHORIZED)

    admin_login_rate_limiter.register_success(ip_address, username)
    return AdminAuthResponse(
        admin=AdminResponse(username=configured_username),
        access_token=create_admin_access_token(configured_username),
    )


def build_admin_session(username: str) -> AdminResponse:
    return AdminResponse(username=username)


def _mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"


def _build_admin_user_item(db: Session, user: User) -> AdminUserListItem:
    now = utcnow()
    groups_count = int(
        db.scalar(
            select(func.count(Group.id)).where(
                Group.user_id == user.id,
                Group.deleted_at.is_(None),
            )
        )
        or 0
    )
    active_refresh_tokens_count = int(
        db.scalar(
            select(func.count(RefreshToken.id)).where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
        )
        or 0
    )
    return AdminUserListItem(
        id=user.id,
        name=user.name,
        username=user.username,
        phone_number=user.phone_number,
        is_phone_verified=user.is_phone_verified,
        must_change_password=user.must_change_password,
        created_at=user.created_at,
        updated_at=user.updated_at,
        groups_count=groups_count,
        active_refresh_tokens_count=active_refresh_tokens_count,
    )


def list_users(db: Session, query: AdminUsersQuery) -> AdminUserListResponse:
    now = utcnow()
    group_counts_subquery = (
        select(Group.user_id.label("user_id"), func.count(Group.id).label("groups_count"))
        .where(Group.deleted_at.is_(None))
        .group_by(Group.user_id)
        .subquery()
    )
    active_refresh_tokens_subquery = (
        select(RefreshToken.user_id.label("user_id"), func.count(RefreshToken.id).label("active_refresh_tokens_count"))
        .where(RefreshToken.revoked_at.is_(None), RefreshToken.expires_at > now)
        .group_by(RefreshToken.user_id)
        .subquery()
    )

    base_query = (
        select(
            User.id,
            User.name,
            User.username,
            User.phone_number,
            User.is_phone_verified,
            User.must_change_password,
            User.created_at,
            User.updated_at,
            func.coalesce(group_counts_subquery.c.groups_count, 0).label("groups_count"),
            func.coalesce(active_refresh_tokens_subquery.c.active_refresh_tokens_count, 0).label("active_refresh_tokens_count"),
        )
        .outerjoin(group_counts_subquery, group_counts_subquery.c.user_id == User.id)
        .outerjoin(active_refresh_tokens_subquery, active_refresh_tokens_subquery.c.user_id == User.id)
    )

    if query.search:
        pattern = f"%{query.search.strip()}%"
        base_query = base_query.where(or_(User.name.ilike(pattern), User.username.ilike(pattern)))
    if query.must_change_password is not None:
        base_query = base_query.where(User.must_change_password.is_(query.must_change_password))

    subquery = base_query.subquery()
    summary_row = db.execute(
        select(
            func.count(subquery.c.id),
            func.sum(case((subquery.c.must_change_password.is_(True), 1), else_=0)),
        )
    ).one()
    total = int(summary_row[0] or 0)
    must_change_password_count = int(summary_row[1] or 0)

    sort_columns = {
        "created_at": subquery.c.created_at,
        "updated_at": subquery.c.updated_at,
        "name": subquery.c.name,
        "username": subquery.c.username,
        "groups_count": subquery.c.groups_count,
        "active_refresh_tokens_count": subquery.c.active_refresh_tokens_count,
    }
    sort_column = sort_columns[query.sort_by]
    ordered_query: Select = select(subquery)
    ordered_query = ordered_query.order_by(sort_column.asc() if query.sort_order == "asc" else sort_column.desc(), subquery.c.id.asc())
    ordered_query = ordered_query.offset((query.page - 1) * query.page_size).limit(query.page_size)

    rows = db.execute(ordered_query).all()
    items = [
        AdminUserListItem(
            id=row.id,
            name=row.name,
            username=row.username,
            phone_number=row.phone_number,
            is_phone_verified=row.is_phone_verified,
            must_change_password=row.must_change_password,
            created_at=row.created_at,
            updated_at=row.updated_at,
            groups_count=int(row.groups_count or 0),
            active_refresh_tokens_count=int(row.active_refresh_tokens_count or 0),
        )
        for row in rows
    ]
    return AdminUserListResponse(
        items=items,
        pagination=AdminUsersPagination(page=query.page, page_size=query.page_size, total=total),
        summary=AdminUsersSummary(total_users=total, must_change_password_count=must_change_password_count),
    )


def update_user(db: Session, *, user_id: str, payload: AdminUserUpdateRequest) -> AdminUserListItem:
    user = db.get(User, user_id)
    if not user:
        raise DomainError(code="admin_user_not_found", message="User not found", status_code=status.HTTP_404_NOT_FOUND)

    if payload.name is None and payload.phone_number is None:
        raise DomainError(code="validation_error", message="At least one field must be provided", status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

    if payload.name is not None:
        user.name = _normalize_name(payload.name)

    if payload.phone_number is not None:
        normalized_phone_number = payload.phone_number.strip()
        if normalized_phone_number == "":
            user.phone_number = None
            user.is_phone_verified = False
        else:
            normalized_phone_number = _normalize_phone_number(normalized_phone_number)
            existing = db.scalar(select(User).where(User.phone_number == normalized_phone_number, User.id != user.id))
            if existing:
                raise DomainError(code="phone_number_taken", message="Phone number is already registered", status_code=status.HTTP_409_CONFLICT)
            user.phone_number = normalized_phone_number
            user.is_phone_verified = True

    user.updated_at = utcnow()
    db.commit()
    db.refresh(user)
    return _build_admin_user_item(db, user)


def delete_user(db: Session, *, user_id: str) -> None:
    user = db.get(User, user_id)
    if not user:
        raise DomainError(code="admin_user_not_found", message="User not found", status_code=status.HTTP_404_NOT_FOUND)

    owned_groups = db.scalars(select(Group).where(Group.user_id == user_id)).all()
    for group in owned_groups:
        db.delete(group)

    db.execute(update(Member).where(Member.linked_user_id == user_id).values(linked_user_id=None))
    db.execute(delete(GroupInvite).where(or_(GroupInvite.inviter_user_id == user_id, GroupInvite.invitee_user_id == user_id)))
    db.execute(delete(GroupMembership).where(GroupMembership.user_id == user_id))
    db.execute(delete(UserConnection).where(or_(UserConnection.user_low_id == user_id, UserConnection.user_high_id == user_id)))
    db.execute(delete(GroupCard).where(GroupCard.user_id == user_id))
    db.execute(delete(Expense).where(Expense.user_id == user_id))
    db.execute(delete(Settlement).where(Settlement.user_id == user_id))
    db.execute(delete(Member).where(Member.user_id == user_id))
    db.delete(user)
    db.commit()


def get_runtime_settings(db: Session) -> AdminRuntimeSettingsResponse:
    values = list_runtime_settings(db)
    api_key = values.get("sms_ir_api_key")
    return AdminRuntimeSettingsResponse(
        sms_ir_api_key_masked=_mask_secret(api_key),
        sms_ir_api_key_configured=bool(api_key),
        sms_ir_verify_template_id=str(values["sms_ir_verify_template_id"]) if values.get("sms_ir_verify_template_id") is not None else None,
        sms_ir_verify_parameter_name=values.get("sms_ir_verify_parameter_name"),
        sms_ir_invited_account_template_id=str(values["sms_ir_invited_account_template_id"]) if values.get("sms_ir_invited_account_template_id") is not None else None,
        sms_ir_invited_account_link_parameter_name=values.get("sms_ir_invited_account_link_parameter_name"),
        sms_ir_invited_account_group_name_parameter_name=values.get("sms_ir_invited_account_group_name_parameter_name"),
        web_app_base_url=values.get("web_app_base_url"),
    )


def update_runtime_settings(db: Session, payload: AdminRuntimeSettingsUpdateRequest) -> AdminRuntimeSettingsResponse:
    set_runtime_settings(
        db,
        {
            "sms_ir_api_key": payload.sms_ir_api_key,
            "sms_ir_verify_template_id": payload.sms_ir_verify_template_id,
            "sms_ir_verify_parameter_name": payload.sms_ir_verify_parameter_name,
            "sms_ir_invited_account_template_id": payload.sms_ir_invited_account_template_id,
            "sms_ir_invited_account_link_parameter_name": payload.sms_ir_invited_account_link_parameter_name,
            "sms_ir_invited_account_group_name_parameter_name": payload.sms_ir_invited_account_group_name_parameter_name,
            "web_app_base_url": payload.web_app_base_url,
        },
    )
    return get_runtime_settings(db)
