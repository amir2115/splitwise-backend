from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
settings = get_settings()
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def _create_token(subject: str, expires_delta: timedelta, token_type: str, jti: str | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": jti or str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)


def create_access_token(subject: str) -> str:
    return _create_token(subject, timedelta(minutes=settings.jwt_access_token_expire_minutes), "access")


def create_password_reset_token(subject: str, *, minutes: int = 15, jti: str | None = None) -> tuple[str, str, datetime]:
    token_jti = jti or str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    token = _create_token(subject, timedelta(minutes=minutes), "password_reset", token_jti)
    return token, token_jti, expires_at


def create_invited_account_token(subject: str, *, minutes: int = 60 * 24 * 7, jti: str | None = None) -> tuple[str, str, datetime]:
    token_jti = jti or str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    token = _create_token(subject, timedelta(minutes=minutes), "invited_account", token_jti)
    return token, token_jti, expires_at


def create_refresh_token(subject: str, *, jti: str | None = None) -> tuple[str, str, datetime]:
    token_jti = jti or str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
    token = _create_token(subject, timedelta(days=settings.jwt_refresh_token_expire_days), "refresh", token_jti)
    return token, token_jti, expires_at


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
