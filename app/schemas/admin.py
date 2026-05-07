from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminResponse(BaseModel):
    username: str


class AdminAuthResponse(BaseModel):
    admin: AdminResponse
    access_token: str
    token_type: str = "bearer"


class AdminUserListItem(BaseModel):
    id: str
    name: str
    username: str
    phone_number: Optional[str]
    is_phone_verified: bool
    must_change_password: bool
    created_at: datetime
    updated_at: datetime
    groups_count: int
    active_refresh_tokens_count: int


class AdminUserUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    phone_number: Optional[str] = None
    is_phone_verified: Optional[bool] = None


class AdminRuntimeSettingsResponse(BaseModel):
    phone_verification_required: bool
    sms_ir_api_key_masked: Optional[str]
    sms_ir_api_key_configured: bool
    sms_ir_verify_template_id: Optional[str]
    sms_ir_verify_template_id_android: Optional[str]
    sms_ir_verify_parameter_name: Optional[str]
    sms_otp_bypass_enabled: bool
    sms_ir_invited_account_template_id: Optional[str]
    sms_ir_invited_account_link_parameter_name: Optional[str]
    sms_ir_invited_account_group_name_parameter_name: Optional[str]
    web_app_base_url: Optional[str]


class AdminRuntimeSettingsUpdateRequest(BaseModel):
    phone_verification_required: Optional[bool] = None
    sms_ir_api_key: Optional[str] = None
    sms_ir_verify_template_id: Optional[str] = None
    sms_ir_verify_template_id_android: Optional[str] = None
    sms_ir_verify_parameter_name: Optional[str] = None
    sms_otp_bypass_enabled: Optional[bool] = None
    sms_ir_invited_account_template_id: Optional[str] = None
    sms_ir_invited_account_link_parameter_name: Optional[str] = None
    sms_ir_invited_account_group_name_parameter_name: Optional[str] = None
    web_app_base_url: Optional[str] = None


class AdminUsersPagination(BaseModel):
    page: int
    page_size: int
    total: int


class AdminUsersSummary(BaseModel):
    total_users: int
    must_change_password_count: int


class AdminUserListResponse(BaseModel):
    items: list[AdminUserListItem]
    pagination: AdminUsersPagination
    summary: AdminUsersSummary


class AdminUsersQuery(BaseModel):
    search: Optional[str] = None
    must_change_password: Optional[bool] = None
    sort_by: Literal[
        "created_at",
        "updated_at",
        "name",
        "username",
        "groups_count",
        "active_refresh_tokens_count",
        "has_phone_number",
        "is_phone_verified",
    ] = "created_at"
    sort_order: Literal["asc", "desc"] = "desc"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
