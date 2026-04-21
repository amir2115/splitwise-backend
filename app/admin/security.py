from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import get_settings

ALGORITHM = "HS256"
ADMIN_SUBJECT_PREFIX = "admin:"


def create_admin_access_token(username: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": f"{ADMIN_SUBJECT_PREFIX}{username}",
        "type": "admin_access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.admin_panel_access_token_expire_minutes)).timestamp()),
    }
    secret = settings.admin_panel_jwt_secret or settings.jwt_secret_key
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_admin_access_token(token: str) -> dict:
    settings = get_settings()
    secret = settings.admin_panel_jwt_secret or settings.jwt_secret_key
    try:
        return jwt.decode(token, secret, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid admin token") from exc
