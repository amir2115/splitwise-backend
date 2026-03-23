from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.core.errors import DomainError
from app.core.time import ensure_utc, utcnow
from app.models.user import RefreshToken, User
from app.schemas.auth import AuthResponse, TokenPair, UserLogin, UserRegister, UserResponse


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


def _issue_tokens(db: Session, user: User) -> TokenPair:
    access_token = create_access_token(user.id)
    refresh_token, token_jti, expires_at = create_refresh_token(user.id)
    db.add(RefreshToken(user_id=user.id, token_jti=token_jti, expires_at=expires_at))
    db.flush()
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


def register_user(db: Session, payload: UserRegister) -> AuthResponse:
    name = _normalize_name(payload.name)
    username = _normalize_username(payload.username)
    _validate_password(payload.password)
    existing = db.scalar(select(User).where(User.username == username))
    if existing:
        raise DomainError(code="username_taken", message="Username is already registered", status_code=status.HTTP_409_CONFLICT)

    user = User(name=name, username=username, password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()
    tokens = _issue_tokens(db, user)
    db.commit()
    db.refresh(user)
    return AuthResponse(user=UserResponse.model_validate(user), tokens=tokens)


def login_user(db: Session, payload: UserLogin) -> AuthResponse:
    username = _normalize_username(payload.username)
    user = db.scalar(select(User).where(User.username == username))
    if not user or not verify_password(payload.password, user.password_hash):
        raise DomainError(code="invalid_credentials", message="Invalid username or password", status_code=status.HTTP_401_UNAUTHORIZED)

    tokens = _issue_tokens(db, user)
    db.commit()
    return AuthResponse(user=UserResponse.model_validate(user), tokens=tokens)


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
