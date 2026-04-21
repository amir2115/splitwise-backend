from __future__ import annotations

import secrets
from datetime import timedelta

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.config import get_settings
from app.core.errors import DomainError
from app.core.time import ensure_utc, utcnow
from app.models.domain import Group
from app.models.user import InvitedAccountToken, PasswordResetCode, PendingRegistration, PhoneVerificationCode, RefreshToken, User
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    InvitedAccountCompleteRequest,
    InvitedAccountRequest,
    InvitedAccountRequestResponse,
    InvitedAccountVerifyPhoneRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    PasswordResetRequestResponse,
    PasswordResetVerifyRequest,
    PasswordResetVerifyResponse,
    RegisterRequest,
    RegisterRequestResponse,
    RegisterResendRequest,
    RegisterVerifyRequest,
    PhoneVerificationConfirmRequest,
    PhoneVerificationRequest,
    PhoneVerificationRequestResponse,
    TokenPair,
    UserCreateByInviter,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services.runtime_settings_service import get_runtime_setting, get_runtime_setting_int
from app.services.sms_service import SmsVerifyResult, send_template_sms, send_verify_sms

PASSWORD_RESET_TOKEN_MINUTES = 15
INVITED_ACCOUNT_TOKEN_MINUTES = 60 * 24 * 7


def _validate_password(password: str) -> None:
    if len(password) < 8:
        raise DomainError(code="weak_password", message="Password must be at least 8 characters long")


def _normalize_name(name: str) -> str:
    normalized = " ".join(name.split()).strip()
    if len(normalized) < 2:
        raise DomainError(code="invalid_name", message="Name must be at least 2 characters long")
    return normalized


def _normalize_username(username: str) -> str:
    normalized = username.strip().lower()
    if len(normalized) < 3:
        raise DomainError(code="invalid_username", message="Username must be at least 3 characters long")
    if len(normalized) > 64:
        raise DomainError(code="invalid_username", message="Username must be at most 64 characters long")
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_.")
    if any(char not in allowed for char in normalized):
        raise DomainError(
            code="invalid_username",
            message="Username can only contain lowercase letters, numbers, dots, and underscores",
        )
    return normalized


def _normalize_username_reference(username: str) -> str:
    candidate = username.strip()
    while candidate.startswith("@"):
        candidate = candidate[1:]
    return _normalize_username(candidate)


def _normalize_phone_number(phone_number: str) -> str:
    translation_table = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    normalized = phone_number.strip().translate(translation_table)
    for char in (" ", "-", "(", ")"):
        normalized = normalized.replace(char, "")
    if normalized.startswith("+"):
        normalized = normalized[1:]
    if normalized.startswith("09") and len(normalized) == 11:
        normalized = f"98{normalized[1:]}"
    if len(normalized) != 12 or not normalized.isdigit() or not normalized.startswith("989"):
        raise DomainError(code="invalid_phone_number", message="Phone number must be a valid Iranian mobile number")
    return normalized


def _normalize_identifier(identifier: str) -> tuple[str, str]:
    candidate = identifier.strip()
    if not candidate:
        raise DomainError(code="validation_error", message="Identifier is required", status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
    try:
        return "phone", _normalize_phone_number(candidate)
    except DomainError as exc:
        error_code = None
        if isinstance(exc.detail, dict):
            error = exc.detail.get("error")
            if isinstance(error, dict):
                error_code = error.get("code")
        if error_code != "invalid_phone_number":
            raise
    return "username", _normalize_username_reference(candidate)


def _generate_verification_code(length: int) -> str:
    return "".join(secrets.choice("0123456789") for _ in range(length))


def _mask_phone_number(phone_number: str) -> str:
    if len(phone_number) < 7:
        return phone_number
    return f"{phone_number[:5]}***{phone_number[-3:]}"


def _get_latest_phone_verification_record(
    db: Session,
    *,
    user_id: str,
    phone_number: str | None = None,
) -> PhoneVerificationCode | None:
    filters = [PhoneVerificationCode.user_id == user_id]
    if phone_number is not None:
        filters.append(PhoneVerificationCode.phone_number == phone_number)
    return db.scalar(select(PhoneVerificationCode).where(*filters).order_by(PhoneVerificationCode.created_at.desc()))


def _get_active_phone_verification_record(db: Session, *, user_id: str) -> PhoneVerificationCode | None:
    now = utcnow()
    return db.scalar(
        select(PhoneVerificationCode)
        .where(
            PhoneVerificationCode.user_id == user_id,
            PhoneVerificationCode.consumed_at.is_(None),
            PhoneVerificationCode.expires_at > now,
        )
        .order_by(PhoneVerificationCode.created_at.desc())
    )


def _invalidate_other_active_phone_verifications(db: Session, *, user_id: str, keep_id: str | None = None) -> None:
    now = utcnow()
    query = select(PhoneVerificationCode).where(
        PhoneVerificationCode.user_id == user_id,
        PhoneVerificationCode.consumed_at.is_(None),
        PhoneVerificationCode.expires_at > now,
    )
    if keep_id is not None:
        query = query.where(PhoneVerificationCode.id != keep_id)
    active_records = db.scalars(query).all()
    for record in active_records:
        record.consumed_at = now
        record.updated_at = now


def _get_latest_password_reset_record(db: Session, *, user_id: str) -> PasswordResetCode | None:
    return db.scalar(select(PasswordResetCode).where(PasswordResetCode.user_id == user_id).order_by(PasswordResetCode.created_at.desc()))


def _get_active_password_reset_record(db: Session, *, user_id: str) -> PasswordResetCode | None:
    now = utcnow()
    return db.scalar(
        select(PasswordResetCode)
        .where(
            PasswordResetCode.user_id == user_id,
            PasswordResetCode.consumed_at.is_(None),
            PasswordResetCode.expires_at > now,
        )
        .order_by(PasswordResetCode.created_at.desc())
    )


def _invalidate_other_active_password_resets(db: Session, *, user_id: str, keep_id: str | None = None) -> None:
    now = utcnow()
    query = select(PasswordResetCode).where(
        PasswordResetCode.user_id == user_id,
        PasswordResetCode.consumed_at.is_(None),
        PasswordResetCode.expires_at > now,
    )
    if keep_id is not None:
        query = query.where(PasswordResetCode.id != keep_id)
    active_records = db.scalars(query).all()
    for record in active_records:
        record.consumed_at = now
        record.updated_at = now


def _issue_tokens(db: Session, user: User) -> TokenPair:
    access_token = create_access_token(user.id)
    refresh_token, token_jti, expires_at = create_refresh_token(user.id)
    db.add(RefreshToken(user_id=user.id, token_jti=token_jti, expires_at=expires_at))
    db.flush()
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


def _build_user_response(user: User) -> UserResponse:
    return UserResponse.model_validate(user)


def _create_user_record(db: Session, *, name: str, username: str, password: str, must_change_password: bool) -> User:
    user = User(
        name=name,
        username=username,
        password_hash=hash_password(password),
        must_change_password=must_change_password,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise DomainError(code="username_taken", message="Username is already registered", status_code=status.HTTP_409_CONFLICT) from exc
    return user


def _ensure_phone_verification_is_configured(db: Session) -> tuple[str, int, str]:
    api_key = get_runtime_setting(db, "sms_ir_api_key")
    template_id = get_runtime_setting_int(db, "sms_ir_verify_template_id")
    parameter_name = get_runtime_setting(db, "sms_ir_verify_parameter_name") or "OTP"
    if not api_key or template_id is None:
        raise DomainError(
            code="phone_verification_not_configured",
            message="Phone verification is not configured",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return api_key, template_id, parameter_name


def _ensure_invited_account_sms_is_configured(db: Session) -> tuple[str, int, str, str]:
    api_key = get_runtime_setting(db, "sms_ir_api_key")
    template_id = get_runtime_setting_int(db, "sms_ir_invited_account_template_id")
    link_parameter_name = get_runtime_setting(db, "sms_ir_invited_account_link_parameter_name") or "TOKEN"
    group_name_parameter_name = get_runtime_setting(db, "sms_ir_invited_account_group_name_parameter_name") or "GROUP_NAME"
    if not api_key or template_id is None:
        raise DomainError(
            code="phone_verification_not_configured",
            message="Invited account SMS is not configured",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return api_key, template_id, link_parameter_name, group_name_parameter_name


def _ensure_phone_number_is_available(db: Session, *, phone_number: str, current_user_id: str) -> None:
    existing = db.scalar(select(User).where(User.phone_number == phone_number, User.id != current_user_id))
    if existing:
        raise DomainError(code="phone_number_taken", message="Phone number is already registered", status_code=status.HTTP_409_CONFLICT)


def _request_phone_verification_for_user(db: Session, *, user: User, phone_number: str) -> PhoneVerificationRequestResponse:
    settings = get_settings()
    if user.phone_number == phone_number and user.is_phone_verified:
        return PhoneVerificationRequestResponse(
            phone_number=phone_number,
            expires_in_seconds=0,
            resend_available_in_seconds=0,
            message_id=None,
        )

    _ensure_phone_number_is_available(db, phone_number=phone_number, current_user_id=user.id)
    api_key, template_id, parameter_name = _ensure_phone_verification_is_configured(db)
    now = utcnow()
    active_record = _get_active_phone_verification_record(db, user_id=user.id)
    if active_record and active_record.phone_number == phone_number:
        resend_available_at = ensure_utc(active_record.last_sent_at) + timedelta(seconds=settings.phone_verification_resend_cooldown_seconds)
        if resend_available_at > now:
            raise DomainError(
                code="phone_verification_rate_limited",
                message="Please wait before requesting another verification code",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                details={"resend_available_in_seconds": int((resend_available_at - now).total_seconds())},
            )
        if active_record.send_attempts >= settings.phone_verification_max_send_attempts_per_window:
            raise DomainError(
                code="phone_verification_rate_limited",
                message="Verification code request limit reached",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )
    elif active_record:
        active_record.consumed_at = now
        active_record.updated_at = now

    code = _generate_verification_code(settings.phone_verification_code_length)
    expires_at = now + timedelta(seconds=settings.phone_verification_ttl_seconds)
    if active_record and active_record.phone_number == phone_number:
        record = active_record
        record.code_hash = hash_password(code)
        record.expires_at = expires_at
        record.last_sent_at = now
        record.send_attempts += 1
        record.verify_attempts = 0
        record.consumed_at = None
        record.updated_at = now
    else:
        record = PhoneVerificationCode(
            user_id=user.id,
            phone_number=phone_number,
            code_hash=hash_password(code),
            expires_at=expires_at,
            last_sent_at=now,
            send_attempts=1,
            verify_attempts=0,
        )
        db.add(record)
        db.flush()

    _invalidate_other_active_phone_verifications(db, user_id=user.id, keep_id=record.id)
    try:
        sms_result = send_verify_sms(
            api_key=api_key,
            template_id=template_id,
            parameter_name=parameter_name,
            mobile=phone_number,
            code=code,
        )
    except Exception:
        db.rollback()
        raise
    db.commit()
    return PhoneVerificationRequestResponse(
        phone_number=phone_number,
        expires_in_seconds=settings.phone_verification_ttl_seconds,
        resend_available_in_seconds=settings.phone_verification_resend_cooldown_seconds,
        message_id=sms_result.message_id,
    )


def _verify_phone_number_for_user(db: Session, *, user: User, phone_number: str, code: str) -> UserResponse:
    settings = get_settings()
    record = _get_latest_phone_verification_record(db, user_id=user.id, phone_number=phone_number)
    if not record or record.consumed_at is not None:
        raise DomainError(code="phone_verification_code_not_found", message="Verification code not found", status_code=status.HTTP_404_NOT_FOUND)

    now = utcnow()
    if ensure_utc(record.expires_at) <= now:
        raise DomainError(code="phone_verification_code_expired", message="Verification code has expired", status_code=status.HTTP_400_BAD_REQUEST)

    if record.verify_attempts >= settings.phone_verification_max_verify_attempts:
        raise DomainError(
            code="phone_verification_attempts_exceeded",
            message="Verification attempts exceeded",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if not verify_password(code, record.code_hash):
        record.verify_attempts += 1
        record.updated_at = now
        if record.verify_attempts >= settings.phone_verification_max_verify_attempts:
            record.consumed_at = now
            db.commit()
            raise DomainError(
                code="phone_verification_attempts_exceeded",
                message="Verification attempts exceeded",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        db.commit()
        raise DomainError(
            code="phone_verification_code_invalid",
            message="Verification code is invalid",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    _ensure_phone_number_is_available(db, phone_number=phone_number, current_user_id=user.id)
    user.phone_number = phone_number
    user.is_phone_verified = True
    user.updated_at = now
    record.consumed_at = now
    record.updated_at = now
    db.commit()
    db.refresh(user)
    return _build_user_response(user)


def register_user(db: Session, payload: UserRegister) -> AuthResponse:
    name = _normalize_name(payload.name)
    username = _normalize_username(payload.username)
    phone_number = _normalize_phone_number(payload.phone_number) if payload.phone_number else None
    _validate_password(payload.password)
    existing = db.scalar(select(User).where(User.username == username))
    if existing:
        raise DomainError(code="username_taken", message="Username is already registered", status_code=status.HTTP_409_CONFLICT)
    if phone_number:
        _ensure_phone_number_is_available(db, phone_number=phone_number, current_user_id="")

    user = _create_user_record(db, name=name, username=username, password=payload.password, must_change_password=False)
    user.phone_number = phone_number
    user.is_phone_verified = bool(phone_number)
    tokens = _issue_tokens(db, user)
    db.commit()
    db.refresh(user)
    return AuthResponse(user=_build_user_response(user), tokens=tokens)


def create_user_by_inviter(db: Session, payload: UserCreateByInviter) -> UserResponse:
    name = _normalize_name(payload.name)
    username = _normalize_username(payload.username)
    _validate_password(payload.password)
    normalized_phone_number = _normalize_phone_number(payload.phone_number) if payload.phone_number else None
    if normalized_phone_number:
        _ensure_phone_number_is_available(db, phone_number=normalized_phone_number, current_user_id="")
    user = _create_user_record(db, name=name, username=username, password=payload.password, must_change_password=True)
    user.phone_number = normalized_phone_number
    user.is_phone_verified = False
    db.commit()
    db.refresh(user)
    return _build_user_response(user)


def _get_pending_registration(db: Session, registration_id: str) -> PendingRegistration | None:
    return db.get(PendingRegistration, registration_id)


def request_register(db: Session, payload: RegisterRequest) -> RegisterRequestResponse:
    settings = get_settings()
    name = _normalize_name(payload.name)
    username = _normalize_username(payload.username)
    _validate_password(payload.password)
    phone_number = _normalize_phone_number(payload.phone_number)

    if db.scalar(select(User).where(User.username == username)):
        raise DomainError(code="registration_username_taken", message="Username is already registered", status_code=status.HTTP_409_CONFLICT)
    if db.scalar(select(User).where(User.phone_number == phone_number)):
        raise DomainError(code="registration_phone_taken", message="Phone number is already registered", status_code=status.HTTP_409_CONFLICT)

    existing_records = db.scalars(
        select(PendingRegistration).where(
            PendingRegistration.consumed_at.is_(None),
            (PendingRegistration.username == username) | (PendingRegistration.phone_number == phone_number),
        )
    ).all()
    now = utcnow()
    for record in existing_records:
        record.consumed_at = now
        record.updated_at = now

    code = _generate_verification_code(settings.phone_verification_code_length)
    expires_at = now + timedelta(seconds=settings.phone_verification_ttl_seconds)
    record = PendingRegistration(
        name=name,
        username=username,
        password_hash=hash_password(payload.password),
        phone_number=phone_number,
        code_hash=hash_password(code),
        expires_at=expires_at,
        last_sent_at=now,
        send_attempts=1,
        verify_attempts=0,
    )
    db.add(record)
    db.flush()
    api_key, template_id, parameter_name = _ensure_phone_verification_is_configured(db)
    try:
        sms_result = send_verify_sms(
            api_key=api_key,
            template_id=template_id,
            parameter_name=parameter_name,
            mobile=phone_number,
            code=code,
        )
    except Exception:
        db.rollback()
        raise
    db.commit()
    return RegisterRequestResponse(
        registration_id=record.id,
        phone_number=phone_number,
        expires_in_seconds=settings.phone_verification_ttl_seconds,
        resend_available_in_seconds=settings.phone_verification_resend_cooldown_seconds,
        message_id=sms_result.message_id,
    )


def resend_register_code(db: Session, payload: RegisterResendRequest) -> RegisterRequestResponse:
    settings = get_settings()
    record = _get_pending_registration(db, payload.registration_id)
    if not record or record.consumed_at is not None:
        raise DomainError(code="registration_not_found", message="Registration request not found", status_code=status.HTTP_404_NOT_FOUND)
    now = utcnow()
    resend_available_at = ensure_utc(record.last_sent_at) + timedelta(seconds=settings.phone_verification_resend_cooldown_seconds)
    if resend_available_at > now:
        raise DomainError(code="registration_rate_limited", message="Please wait before requesting another code", status_code=status.HTTP_429_TOO_MANY_REQUESTS)
    if record.send_attempts >= settings.phone_verification_max_send_attempts_per_window:
        raise DomainError(code="registration_rate_limited", message="Registration code request limit reached", status_code=status.HTTP_429_TOO_MANY_REQUESTS)

    code = _generate_verification_code(settings.phone_verification_code_length)
    record.code_hash = hash_password(code)
    record.expires_at = now + timedelta(seconds=settings.phone_verification_ttl_seconds)
    record.last_sent_at = now
    record.send_attempts += 1
    record.verify_attempts = 0
    record.updated_at = now
    api_key, template_id, parameter_name = _ensure_phone_verification_is_configured(db)
    try:
        sms_result = send_verify_sms(
            api_key=api_key,
            template_id=template_id,
            parameter_name=parameter_name,
            mobile=record.phone_number,
            code=code,
        )
    except Exception:
        db.rollback()
        raise
    db.commit()
    return RegisterRequestResponse(
        registration_id=record.id,
        phone_number=record.phone_number,
        expires_in_seconds=settings.phone_verification_ttl_seconds,
        resend_available_in_seconds=settings.phone_verification_resend_cooldown_seconds,
        message_id=sms_result.message_id,
    )


def verify_register(db: Session, payload: RegisterVerifyRequest) -> AuthResponse:
    settings = get_settings()
    record = _get_pending_registration(db, payload.registration_id)
    if not record or record.consumed_at is not None:
        raise DomainError(code="registration_not_found", message="Registration request not found", status_code=status.HTTP_404_NOT_FOUND)

    now = utcnow()
    if ensure_utc(record.expires_at) <= now:
        raise DomainError(code="registration_code_expired", message="Registration code has expired", status_code=status.HTTP_400_BAD_REQUEST)
    if record.verify_attempts >= settings.phone_verification_max_verify_attempts:
        raise DomainError(code="registration_attempts_exceeded", message="Registration attempts exceeded", status_code=status.HTTP_400_BAD_REQUEST)
    if db.scalar(select(User).where(User.username == record.username)):
        raise DomainError(code="registration_username_taken", message="Username is already registered", status_code=status.HTTP_409_CONFLICT)
    if db.scalar(select(User).where(User.phone_number == record.phone_number)):
        raise DomainError(code="registration_phone_taken", message="Phone number is already registered", status_code=status.HTTP_409_CONFLICT)

    if not verify_password(payload.code, record.code_hash):
        record.verify_attempts += 1
        record.updated_at = now
        if record.verify_attempts >= settings.phone_verification_max_verify_attempts:
            record.consumed_at = now
            db.commit()
            raise DomainError(code="registration_attempts_exceeded", message="Registration attempts exceeded", status_code=status.HTTP_400_BAD_REQUEST)
        db.commit()
        raise DomainError(code="registration_code_invalid", message="Registration code is invalid", status_code=status.HTTP_400_BAD_REQUEST)

    user = User(
        name=record.name,
        username=record.username,
        phone_number=record.phone_number,
        is_phone_verified=True,
        password_hash=record.password_hash,
        must_change_password=False,
    )
    db.add(user)
    db.flush()
    record.consumed_at = now
    record.updated_at = now
    tokens = _issue_tokens(db, user)
    db.commit()
    db.refresh(user)
    return AuthResponse(user=_build_user_response(user), tokens=tokens)


def send_invited_account_completion_sms(db: Session, *, user: User, group_name: str) -> None:
    if not user.phone_number:
        return
    now = utcnow()
    api_key, template_id, link_parameter_name, group_name_parameter_name = _ensure_invited_account_sms_is_configured(db)
    token_jti = secrets.token_urlsafe(12)
    while db.scalar(select(InvitedAccountToken).where(InvitedAccountToken.token_jti == token_jti)):
        token_jti = secrets.token_urlsafe(12)
    expires_at = utcnow() + timedelta(minutes=INVITED_ACCOUNT_TOKEN_MINUTES)
    existing = db.scalar(
        select(InvitedAccountToken)
        .where(
            InvitedAccountToken.user_id == user.id,
            InvitedAccountToken.consumed_at.is_(None),
            InvitedAccountToken.expires_at > now,
        )
        .order_by(InvitedAccountToken.created_at.desc())
    )
    if existing:
        existing.consumed_at = now
        existing.updated_at = now
    invitation = InvitedAccountToken(
        user_id=user.id,
        token_jti=token_jti,
        expires_at=expires_at,
        last_sent_at=now,
        send_attempts=1,
    )
    db.add(invitation)
    db.flush()
    try:
        send_template_sms(
            api_key=api_key,
            template_id=template_id,
            mobile=user.phone_number,
            parameters=[
                {"name": group_name_parameter_name, "value": group_name[:25]},
                {"name": link_parameter_name, "value": token_jti},
            ],
        )
    except Exception:
        db.rollback()
        raise
    db.commit()


def _get_invited_account_token_record(db: Session, token: str) -> tuple[InvitedAccountToken, User]:
    now = utcnow()
    direct_record = db.scalar(select(InvitedAccountToken).where(InvitedAccountToken.token_jti == token))
    if direct_record:
        user = db.get(User, direct_record.user_id)
        if not user or direct_record.consumed_at is not None or ensure_utc(direct_record.expires_at) <= now:
            raise DomainError(code="invited_account_token_invalid", message="Invalid invited account token", status_code=status.HTTP_401_UNAUTHORIZED)
        return direct_record, user

    try:
        token_payload = decode_token(token)
    except ValueError as exc:
        raise DomainError(code="invited_account_token_invalid", message="Invalid invited account token", status_code=status.HTTP_401_UNAUTHORIZED) from exc
    if token_payload.get("type") != "invited_account":
        raise DomainError(code="invited_account_token_invalid", message="Invalid invited account token", status_code=status.HTTP_401_UNAUTHORIZED)
    record = db.scalar(select(InvitedAccountToken).where(InvitedAccountToken.token_jti == token_payload["jti"]))
    user = db.get(User, token_payload["sub"])
    if not record or not user or record.user_id != user.id or record.consumed_at is not None or ensure_utc(record.expires_at) <= now:
        raise DomainError(code="invited_account_token_invalid", message="Invalid invited account token", status_code=status.HTTP_401_UNAUTHORIZED)
    return record, user


def request_invited_account(db: Session, payload: InvitedAccountRequest) -> InvitedAccountRequestResponse:
    _, user = _get_invited_account_token_record(db, payload.token)
    masked_phone_number = _mask_phone_number(user.phone_number) if user.phone_number else None
    return InvitedAccountRequestResponse(requires_phone_verification=False, masked_phone_number=masked_phone_number)


def verify_invited_account_phone(db: Session, payload: InvitedAccountVerifyPhoneRequest) -> UserResponse:
    _, user = _get_invited_account_token_record(db, payload.token)
    if not user.phone_number:
        raise DomainError(code="invited_account_phone_missing", message="Invited account has no phone number", status_code=status.HTTP_400_BAD_REQUEST)
    return _verify_phone_number_for_user(db, user=user, phone_number=user.phone_number, code=payload.code)


def complete_invited_account(db: Session, payload: InvitedAccountCompleteRequest) -> AuthResponse:
    record, user = _get_invited_account_token_record(db, payload.token)
    _validate_password(payload.new_password)
    now = utcnow()
    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    user.updated_at = now
    record.consumed_at = now
    record.updated_at = now
    tokens = _issue_tokens(db, user)
    db.commit()
    db.refresh(user)
    return AuthResponse(user=_build_user_response(user), tokens=tokens)


def login_user(db: Session, payload: UserLogin) -> AuthResponse:
    username = _normalize_username_reference(payload.username)
    user = db.scalar(select(User).where(User.username == username))
    if not user or not verify_password(payload.password, user.password_hash):
        raise DomainError(code="invalid_credentials", message="Invalid username or password", status_code=status.HTTP_401_UNAUTHORIZED)

    tokens = _issue_tokens(db, user)
    db.commit()
    return AuthResponse(user=_build_user_response(user), tokens=tokens)


def refresh_tokens(db: Session, refresh_token: str) -> TokenPair:
    try:
        payload = decode_token(refresh_token)
    except ValueError as exc:
        raise DomainError(code="invalid_token", message="Invalid refresh token", status_code=status.HTTP_401_UNAUTHORIZED) from exc

    if payload.get("type") != "refresh":
        raise DomainError(code="invalid_token", message="Invalid refresh token", status_code=status.HTTP_401_UNAUTHORIZED)

    record = db.scalar(select(RefreshToken).where(RefreshToken.token_jti == payload["jti"]))
    if not record or record.revoked_at is not None or ensure_utc(record.expires_at) <= utcnow():
        raise DomainError(code="invalid_token", message="Refresh token is no longer valid", status_code=status.HTTP_401_UNAUTHORIZED)

    user = db.get(User, payload["sub"])
    if not user:
        raise DomainError(code="invalid_token", message="User not found", status_code=status.HTTP_401_UNAUTHORIZED)

    record.revoked_at = utcnow()
    tokens = _issue_tokens(db, user)
    db.commit()
    return tokens


def change_password(db: Session, user: User, payload: ChangePasswordRequest) -> UserResponse:
    if not verify_password(payload.current_password, user.password_hash):
        raise DomainError(code="invalid_current_password", message="Current password is incorrect", status_code=status.HTTP_401_UNAUTHORIZED)
    _validate_password(payload.new_password)
    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    user.updated_at = utcnow()
    db.commit()
    db.refresh(user)
    return _build_user_response(user)


def request_phone_verification(db: Session, user: User, payload: PhoneVerificationRequest) -> PhoneVerificationRequestResponse:
    phone_number = _normalize_phone_number(payload.phone_number)
    return _request_phone_verification_for_user(db, user=user, phone_number=phone_number)


def verify_phone_number(db: Session, user: User, payload: PhoneVerificationConfirmRequest) -> UserResponse:
    phone_number = _normalize_phone_number(payload.phone_number)
    return _verify_phone_number_for_user(db, user=user, phone_number=phone_number, code=payload.code)


def request_password_reset(db: Session, payload: PasswordResetRequest) -> PasswordResetRequestResponse:
    settings = get_settings()
    identifier_kind, normalized_identifier = _normalize_identifier(payload.identifier)
    user = db.scalar(
        select(User).where(User.phone_number == normalized_identifier if identifier_kind == "phone" else User.username == normalized_identifier)
    )
    if not user:
        raise DomainError(code="reset_account_not_found", message="Account not found", status_code=status.HTTP_404_NOT_FOUND)
    if not user.phone_number:
        raise DomainError(
            code="password_reset_phone_missing",
            message="This account does not have a phone number. Please contact support.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    api_key, template_id, parameter_name = _ensure_phone_verification_is_configured(db)
    now = utcnow()
    active_record = _get_active_password_reset_record(db, user_id=user.id)
    if active_record:
        resend_available_at = ensure_utc(active_record.last_sent_at) + timedelta(seconds=settings.phone_verification_resend_cooldown_seconds)
        if active_record.identifier_snapshot == normalized_identifier and resend_available_at > now:
            raise DomainError(
                code="password_reset_rate_limited",
                message="Please wait before requesting another reset code",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                details={"resend_available_in_seconds": int((resend_available_at - now).total_seconds())},
            )
        if active_record.identifier_snapshot == normalized_identifier and active_record.send_attempts >= settings.phone_verification_max_send_attempts_per_window:
            raise DomainError(
                code="password_reset_rate_limited",
                message="Password reset request limit reached",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        active_record.consumed_at = now
        active_record.updated_at = now

    code = _generate_verification_code(settings.phone_verification_code_length)
    expires_at = now + timedelta(seconds=settings.phone_verification_ttl_seconds)
    if active_record and active_record.identifier_snapshot == normalized_identifier:
        record = active_record
        record.code_hash = hash_password(code)
        record.expires_at = expires_at
        record.last_sent_at = now
        record.send_attempts += 1
        record.verify_attempts = 0
        record.consumed_at = None
        record.reset_token_jti = None
        record.reset_token_expires_at = None
        record.updated_at = now
    else:
        record = PasswordResetCode(
            user_id=user.id,
            identifier_snapshot=normalized_identifier,
            phone_number=user.phone_number,
            code_hash=hash_password(code),
            expires_at=expires_at,
            last_sent_at=now,
            send_attempts=1,
            verify_attempts=0,
        )
        db.add(record)
        db.flush()

    _invalidate_other_active_password_resets(db, user_id=user.id, keep_id=record.id)
    try:
        sms_result: SmsVerifyResult = send_verify_sms(
            api_key=api_key,
            template_id=template_id,
            parameter_name=parameter_name,
            mobile=user.phone_number,
            code=code,
        )
    except Exception:
        db.rollback()
        raise

    db.commit()
    return PasswordResetRequestResponse(
        masked_phone_number=_mask_phone_number(user.phone_number),
        expires_in_seconds=settings.phone_verification_ttl_seconds,
        resend_available_in_seconds=settings.phone_verification_resend_cooldown_seconds,
        message_id=sms_result.message_id,
    )


def verify_password_reset(db: Session, payload: PasswordResetVerifyRequest) -> PasswordResetVerifyResponse:
    settings = get_settings()
    identifier_kind, normalized_identifier = _normalize_identifier(payload.identifier)
    user = db.scalar(
        select(User).where(User.phone_number == normalized_identifier if identifier_kind == "phone" else User.username == normalized_identifier)
    )
    if not user:
        raise DomainError(code="reset_account_not_found", message="Account not found", status_code=status.HTTP_404_NOT_FOUND)

    record = _get_latest_password_reset_record(db, user_id=user.id)
    if not record or record.consumed_at is not None:
        raise DomainError(code="password_reset_code_not_found", message="Password reset code not found", status_code=status.HTTP_404_NOT_FOUND)

    now = utcnow()
    if ensure_utc(record.expires_at) <= now:
        raise DomainError(code="password_reset_code_expired", message="Password reset code has expired", status_code=status.HTTP_400_BAD_REQUEST)

    if record.verify_attempts >= settings.phone_verification_max_verify_attempts:
        raise DomainError(
            code="password_reset_attempts_exceeded",
            message="Password reset attempts exceeded",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if not verify_password(payload.code, record.code_hash):
        record.verify_attempts += 1
        record.updated_at = now
        if record.verify_attempts >= settings.phone_verification_max_verify_attempts:
            record.consumed_at = now
            db.commit()
            raise DomainError(
                code="password_reset_attempts_exceeded",
                message="Password reset attempts exceeded",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        db.commit()
        raise DomainError(
            code="password_reset_code_invalid",
            message="Password reset code is invalid",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    reset_token, reset_token_jti, reset_token_expires_at = create_password_reset_token(user.id, minutes=PASSWORD_RESET_TOKEN_MINUTES)
    record.reset_token_jti = reset_token_jti
    record.reset_token_expires_at = reset_token_expires_at
    record.updated_at = now
    db.commit()
    return PasswordResetVerifyResponse(reset_token=reset_token)


def confirm_password_reset(db: Session, payload: PasswordResetConfirmRequest) -> AuthResponse:
    try:
        token_payload = decode_token(payload.reset_token)
    except ValueError as exc:
        raise DomainError(code="password_reset_token_invalid", message="Invalid password reset token", status_code=status.HTTP_401_UNAUTHORIZED) from exc

    if token_payload.get("type") != "password_reset":
        raise DomainError(code="password_reset_token_invalid", message="Invalid password reset token", status_code=status.HTTP_401_UNAUTHORIZED)

    record = db.scalar(select(PasswordResetCode).where(PasswordResetCode.reset_token_jti == token_payload["jti"]))
    now = utcnow()
    if (
        not record
        or record.consumed_at is not None
        or record.reset_token_expires_at is None
        or ensure_utc(record.reset_token_expires_at) <= now
    ):
        raise DomainError(code="password_reset_token_invalid", message="Invalid password reset token", status_code=status.HTTP_401_UNAUTHORIZED)

    user = db.get(User, token_payload["sub"])
    if not user or user.id != record.user_id:
        raise DomainError(code="password_reset_token_invalid", message="Invalid password reset token", status_code=status.HTTP_401_UNAUTHORIZED)

    _validate_password(payload.new_password)
    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    user.updated_at = now
    record.consumed_at = now
    record.updated_at = now

    active_refresh_tokens = db.scalars(
        select(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
    ).all()
    for refresh_token in active_refresh_tokens:
        refresh_token.revoked_at = now

    tokens = _issue_tokens(db, user)
    db.commit()
    db.refresh(user)
    return AuthResponse(user=_build_user_response(user), tokens=tokens)
