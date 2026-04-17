from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import AuthResponse, ChangePasswordRequest, TokenPair, TokenRefreshRequest, UserCreateByInviter, UserLogin, UserRegister, UserResponse
from app.services.auth_service import change_password, create_user_by_inviter, login_user, refresh_tokens, register_user

router = APIRouter()


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(payload: UserRegister, db: Session = Depends(get_db)) -> AuthResponse:
    return register_user(db, payload)


@router.post("/login", response_model=AuthResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> AuthResponse:
    return login_user(db, payload)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: TokenRefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    return refresh_tokens(db, payload.refresh_token)


@router.post("/users", response_model=UserResponse, status_code=201)
def create_user_for_member_add(
    payload: UserCreateByInviter,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> UserResponse:
    return create_user_by_inviter(db, payload)


@router.post("/change-password", response_model=UserResponse)
def change_current_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return change_password(db, current_user, payload)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)
