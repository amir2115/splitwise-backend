from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class FcmTokenUpsertRequest(BaseModel):
    token: str = Field(min_length=1, max_length=4096)
    device_id: str = Field(min_length=1, max_length=128)
    platform: str = Field(default="android", max_length=16)
    store_channel: Optional[str] = Field(default=None, max_length=32)
    app_version_name: Optional[str] = Field(default=None, max_length=64)
    app_version_code: Optional[int] = None

    @field_validator("platform", "store_channel", mode="before")
    @classmethod
    def normalize_optional_lower(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip().lower()
            return normalized or None
        return value


class FcmTokenDeleteRequest(BaseModel):
    token: Optional[str] = Field(default=None, max_length=4096)
    device_id: Optional[str] = Field(default=None, max_length=128)


class FcmTokenResponse(BaseModel):
    id: str
    is_active: bool


class NotificationTargetType(str, Enum):
    ALL = "all"
    USER_IDS = "user_ids"


class AdminNotificationSendRequest(BaseModel):
    target_type: NotificationTargetType
    user_ids: list[str] = Field(default_factory=list)
    title: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1, max_length=1000)
    data: dict[str, str] = Field(default_factory=dict)


class AdminNotificationSendResponse(BaseModel):
    attempted: int
    sent: int
    failed: int
