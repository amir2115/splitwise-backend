from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.common import ORMModel


class UserRegister(BaseModel):
    name: str
    username: str
    password: str


class UserCreateByInviter(BaseModel):
    name: str
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(ORMModel):
    id: str
    name: str
    username: str
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
