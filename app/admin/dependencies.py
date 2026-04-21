from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer

from app.admin.security import ADMIN_SUBJECT_PREFIX, decode_admin_access_token
from app.core.config import get_settings
from app.core.errors import DomainError

admin_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/admin/auth/login")


def get_current_admin_username(token: str = Depends(admin_oauth2_scheme)) -> str:
    try:
        payload = decode_admin_access_token(token)
    except ValueError as exc:
        raise DomainError(code="invalid_admin_token", message="Invalid admin access token", status_code=status.HTTP_401_UNAUTHORIZED) from exc

    if payload.get("type") != "admin_access":
        raise DomainError(code="invalid_admin_token", message="Invalid admin access token", status_code=status.HTTP_401_UNAUTHORIZED)

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject.startswith(ADMIN_SUBJECT_PREFIX):
        raise DomainError(code="invalid_admin_token", message="Invalid admin access token", status_code=status.HTTP_401_UNAUTHORIZED)

    username = subject.removeprefix(ADMIN_SUBJECT_PREFIX)
    settings = get_settings()
    if not settings.admin_panel_username or username != settings.admin_panel_username:
        raise DomainError(code="invalid_admin_token", message="Invalid admin access token", status_code=status.HTTP_401_UNAUTHORIZED)
    return username
