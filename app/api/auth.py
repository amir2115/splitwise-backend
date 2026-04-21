from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
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
    TokenRefreshRequest,
    UserCreateByInviter,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services.auth_service import (
    change_password,
    complete_invited_account,
    confirm_password_reset,
    create_user_by_inviter,
    login_user,
    request_invited_account,
    request_password_reset,
    request_register,
    refresh_tokens,
    register_user,
    resend_register_code,
    request_phone_verification,
    verify_invited_account_phone,
    verify_password_reset,
    verify_register,
    verify_phone_number,
)

router = APIRouter()


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(payload: UserRegister, db: Session = Depends(get_db)) -> AuthResponse:
    return register_user(db, payload)


@router.post("/register/request", response_model=RegisterRequestResponse)
def register_request(payload: RegisterRequest, db: Session = Depends(get_db)) -> RegisterRequestResponse:
    return request_register(db, payload)


@router.post("/register/verify", response_model=AuthResponse)
def register_verify(payload: RegisterVerifyRequest, db: Session = Depends(get_db)) -> AuthResponse:
    return verify_register(db, payload)


@router.post("/register/resend", response_model=RegisterRequestResponse)
def register_resend(payload: RegisterResendRequest, db: Session = Depends(get_db)) -> RegisterRequestResponse:
    return resend_register_code(db, payload)


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


@router.post("/forgot-password/request", response_model=PasswordResetRequestResponse)
def request_forgot_password(
    payload: PasswordResetRequest,
    db: Session = Depends(get_db),
) -> PasswordResetRequestResponse:
    return request_password_reset(db, payload)


@router.post("/forgot-password/verify", response_model=PasswordResetVerifyResponse)
def verify_forgot_password_code(
    payload: PasswordResetVerifyRequest,
    db: Session = Depends(get_db),
) -> PasswordResetVerifyResponse:
    return verify_password_reset(db, payload)


@router.post("/forgot-password/confirm", response_model=AuthResponse)
def confirm_forgot_password(
    payload: PasswordResetConfirmRequest,
    db: Session = Depends(get_db),
) -> AuthResponse:
    return confirm_password_reset(db, payload)


@router.post("/invited-account/request", response_model=InvitedAccountRequestResponse)
def request_invited_account_flow(
    payload: InvitedAccountRequest,
    db: Session = Depends(get_db),
) -> InvitedAccountRequestResponse:
    return request_invited_account(db, payload)


@router.post("/invited-account/verify-phone", response_model=UserResponse)
def verify_invited_account_flow_phone(
    payload: InvitedAccountVerifyPhoneRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    return verify_invited_account_phone(db, payload)


@router.post("/invited-account/complete", response_model=AuthResponse)
def complete_invited_account_flow(
    payload: InvitedAccountCompleteRequest,
    db: Session = Depends(get_db),
) -> AuthResponse:
    return complete_invited_account(db, payload)


@router.post("/phone/request-verification", response_model=PhoneVerificationRequestResponse)
def request_current_user_phone_verification(
    payload: PhoneVerificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PhoneVerificationRequestResponse:
    return request_phone_verification(db, current_user, payload)


@router.post("/phone/verify", response_model=UserResponse)
def verify_current_user_phone_number(
    payload: PhoneVerificationConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return verify_phone_number(db, current_user, payload)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)
