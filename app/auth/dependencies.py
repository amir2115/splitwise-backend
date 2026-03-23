from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.security import decode_token
from app.core.errors import DomainError
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise DomainError(code="invalid_token", message="Invalid access token", status_code=status.HTTP_401_UNAUTHORIZED) from exc

    if payload.get("type") != "access":
        raise DomainError(code="invalid_token", message="Invalid access token", status_code=status.HTTP_401_UNAUTHORIZED)

    user = db.get(User, payload["sub"])
    if not user:
        raise DomainError(code="invalid_token", message="User not found", status_code=status.HTTP_401_UNAUTHORIZED)
    return user
