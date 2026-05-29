from fastapi import Depends, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.security import decode_token
from app.core.errors import DomainError
from app.db.session import get_db
from app.models.user import User
from app.services.client_tracking import parse_client_metadata, track_user_client_metadata

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(request: Request, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise DomainError(code="invalid_token", message="Invalid access token", status_code=status.HTTP_401_UNAUTHORIZED) from exc

    if payload.get("type") != "access":
        raise DomainError(code="invalid_token", message="Invalid access token", status_code=status.HTTP_401_UNAUTHORIZED)

    user = db.get(User, payload["sub"])
    if not user:
        raise DomainError(code="invalid_token", message="User not found", status_code=status.HTTP_401_UNAUTHORIZED)
    track_user_client_metadata(
        db,
        user,
        parse_client_metadata(
            request.headers.get("X-Client-Platform"),
            request.headers.get("X-App-Store"),
        ),
    )
    return user
