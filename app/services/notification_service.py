from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import DomainError
from app.core.time import utcnow
from app.models.user import FcmDeviceToken, User
from app.schemas.notifications import AdminNotificationSendRequest, FcmTokenUpsertRequest, NotificationTargetType


@dataclass(frozen=True)
class NotificationSendResult:
    attempted: int
    sent: int
    failed: int


class FirebaseNotificationSender:
    def send(self, *, tokens: list[str], title: str, body: str, data: dict[str, str]) -> tuple[int, list[str]]:
        if not tokens:
            return 0, []
        app = self._get_app()
        from firebase_admin import messaging

        message = messaging.MulticastMessage(
            tokens=tokens,
            notification=messaging.Notification(title=title, body=body),
            data=data,
        )
        response = messaging.send_each_for_multicast(message, app=app)
        invalid_tokens: list[str] = []
        for token, send_response in zip(tokens, response.responses):
            if send_response.success:
                continue
            code = getattr(send_response.exception, "code", None)
            if code in {"UNREGISTERED", "INVALID_ARGUMENT", "registration-token-not-registered"}:
                invalid_tokens.append(token)
        return response.success_count, invalid_tokens

    def _get_app(self):
        settings = get_settings()
        if not settings.firebase_admin_credentials_path:
            raise DomainError(
                code="firebase_not_configured",
                message="Firebase Admin credentials are not configured",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        try:
            import firebase_admin
            from firebase_admin import credentials
        except ImportError as exc:
            raise DomainError(
                code="firebase_not_installed",
                message="Firebase Admin SDK is not installed",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc

        if firebase_admin._apps:
            return firebase_admin.get_app()
        credential = credentials.Certificate(settings.firebase_admin_credentials_path)
        return firebase_admin.initialize_app(credential)


def register_fcm_token(db: Session, user: User, payload: FcmTokenUpsertRequest) -> FcmDeviceToken:
    now = utcnow()
    existing = db.scalar(
        select(FcmDeviceToken).where(
            FcmDeviceToken.user_id == user.id,
            FcmDeviceToken.device_id == payload.device_id,
        )
    )
    for duplicate in db.scalars(
        select(FcmDeviceToken).where(
            FcmDeviceToken.token == payload.token,
            FcmDeviceToken.is_active.is_(True),
        )
    ):
        if existing is None or duplicate.id != existing.id:
            duplicate.is_active = False

    if existing is None:
        existing = FcmDeviceToken(
            user_id=user.id,
            device_id=payload.device_id,
            token=payload.token,
            platform=payload.platform or "android",
            android_variant=payload.store_channel,
            app_version_name=payload.app_version_name,
            app_version_code=payload.app_version_code,
            is_active=True,
            last_seen_at=now,
        )
        db.add(existing)
    else:
        existing.token = payload.token
        existing.platform = payload.platform or "android"
        existing.android_variant = payload.store_channel
        existing.app_version_name = payload.app_version_name
        existing.app_version_code = payload.app_version_code
        existing.is_active = True
        existing.last_seen_at = now
    db.commit()
    db.refresh(existing)
    return existing


def deactivate_fcm_token(db: Session, user: User, *, token: str | None = None, device_id: str | None = None) -> int:
    filters = [FcmDeviceToken.user_id == user.id, FcmDeviceToken.is_active.is_(True)]
    if token:
        filters.append(FcmDeviceToken.token == token)
    if device_id:
        filters.append(FcmDeviceToken.device_id == device_id)
    records = db.scalars(select(FcmDeviceToken).where(*filters)).all()
    for record in records:
        record.is_active = False
    db.commit()
    return len(records)


def send_admin_notification(
    db: Session,
    payload: AdminNotificationSendRequest,
    sender: FirebaseNotificationSender | None = None,
) -> NotificationSendResult:
    query = select(FcmDeviceToken).where(FcmDeviceToken.is_active.is_(True))
    if payload.target_type == NotificationTargetType.USER_IDS:
        if not payload.user_ids:
            raise DomainError(code="validation_error", message="user_ids is required for user_ids target", status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
        query = query.where(FcmDeviceToken.user_id.in_(payload.user_ids))
    records = db.scalars(query).all()
    tokens = [record.token for record in records]
    attempted = len(tokens)
    sender = sender or FirebaseNotificationSender()
    sent, invalid_tokens = sender.send(tokens=tokens, title=payload.title, body=payload.body, data=payload.data)
    _deactivate_tokens(db, invalid_tokens)
    failed = attempted - sent
    return NotificationSendResult(attempted=attempted, sent=sent, failed=failed)


def _deactivate_tokens(db: Session, tokens: Iterable[str]) -> None:
    token_list = list(tokens)
    if not token_list:
        return
    records = db.scalars(select(FcmDeviceToken).where(FcmDeviceToken.token.in_(token_list))).all()
    for record in records:
        record.is_active = False
    db.commit()
