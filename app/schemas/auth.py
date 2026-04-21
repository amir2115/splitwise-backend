from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.common import ORMModel


class UserRegister(BaseModel):
    name: str
    username: str
    password: str
    phone_number: Optional[str] = None


class UserCreateByInviter(BaseModel):
    name: str
    username: str
    password: str
    phone_number: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class PhoneVerificationRequest(BaseModel):
    phone_number: str


class PhoneVerificationRequestResponse(BaseModel):
    phone_number: str
    expires_in_seconds: int
    resend_available_in_seconds: int
    message_id: Optional[int] = None


class PhoneVerificationConfirmRequest(BaseModel):
    phone_number: str
    code: str


class PasswordResetRequest(BaseModel):
    identifier: str


class PasswordResetRequestResponse(BaseModel):
    masked_phone_number: Optional[str]
    expires_in_seconds: int
    resend_available_in_seconds: int
    message_id: Optional[int] = None


class PasswordResetVerifyRequest(BaseModel):
    identifier: str
    code: str


class PasswordResetVerifyResponse(BaseModel):
    reset_token: str


class PasswordResetConfirmRequest(BaseModel):
    reset_token: str
    new_password: str


class RegisterRequest(BaseModel):
    name: str
    username: str
    password: str
    phone_number: str


class RegisterRequestResponse(BaseModel):
    registration_id: str
    phone_number: str
    expires_in_seconds: int
    resend_available_in_seconds: int
    message_id: Optional[int] = None


class RegisterVerifyRequest(BaseModel):
    registration_id: str
    code: str


class RegisterResendRequest(BaseModel):
    registration_id: str


class InvitedAccountRequest(BaseModel):
    token: str


class InvitedAccountRequestResponse(BaseModel):
    requires_phone_verification: bool
    masked_phone_number: Optional[str]
    expires_in_seconds: Optional[int] = None
    resend_available_in_seconds: Optional[int] = None
    message_id: Optional[int] = None


class InvitedAccountVerifyPhoneRequest(BaseModel):
    token: str
    code: str


class InvitedAccountCompleteRequest(BaseModel):
    token: str
    new_password: str


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(ORMModel):
    id: str
    name: str
    username: str
    phone_number: Optional[str]
    is_phone_verified: bool
    must_change_password: bool
    created_at: datetime
    updated_at: datetime


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    user: UserResponse
    tokens: TokenPair
