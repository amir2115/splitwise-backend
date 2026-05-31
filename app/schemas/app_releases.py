from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.app_download import normalize_update_mode


class AppReleaseCreateRequest(BaseModel):
    version_name: str = Field(min_length=1, max_length=64)
    version_code: int = Field(ge=0)
    title: str = Field(default="دانلود اپلیکیشن", min_length=1, max_length=255)
    subtitle: str = Field(default="آخرین نسخه دنگینو را از استور دلخواهت نصب کن.", min_length=1, max_length=1000)
    app_icon_url: Optional[str] = Field(default=None, min_length=1, max_length=2048)
    release_date: Optional[date] = None
    file_size: Optional[str] = Field(default=None, min_length=1, max_length=64)
    bazaar_url: Optional[str] = Field(default=None, min_length=1, max_length=2048)
    myket_url: Optional[str] = Field(default=None, min_length=1, max_length=2048)
    release_notes: list[str] = Field(min_length=1)
    primary_badge_text: Optional[str] = Field(default="نسخه جدید", min_length=1, max_length=64)
    min_supported_version_code: Optional[int] = Field(default=None, ge=0)
    update_mode: Optional[str] = None
    update_title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    update_message: Optional[str] = Field(default=None, min_length=1, max_length=1000)

    @field_validator("update_mode", mode="before")
    @classmethod
    def validate_update_mode(cls, value: Optional[str]) -> Optional[str]:
        return normalize_update_mode(value)

    @field_validator("release_notes")
    @classmethod
    def normalize_release_notes(cls, value: list[str]) -> list[str]:
        notes = [item.strip() for item in value if item.strip()]
        if not notes:
            raise ValueError("release_notes must include at least one item")
        return notes


class AppReleaseUpdateRequest(BaseModel):
    version_name: Optional[str] = Field(default=None, min_length=1, max_length=64)
    version_code: Optional[int] = Field(default=None, ge=0)
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    subtitle: Optional[str] = Field(default=None, min_length=1, max_length=1000)
    app_icon_url: Optional[str] = Field(default=None, min_length=1, max_length=2048)
    release_date: Optional[date] = None
    file_size: Optional[str] = Field(default=None, min_length=1, max_length=64)
    bazaar_url: Optional[str] = Field(default=None, min_length=1, max_length=2048)
    myket_url: Optional[str] = Field(default=None, min_length=1, max_length=2048)
    release_notes: Optional[list[str]] = None
    primary_badge_text: Optional[str] = Field(default=None, min_length=1, max_length=64)
    min_supported_version_code: Optional[int] = Field(default=None, ge=0)
    update_mode: Optional[str] = None
    update_title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    update_message: Optional[str] = Field(default=None, min_length=1, max_length=1000)

    @field_validator("update_mode", mode="before")
    @classmethod
    def validate_update_mode(cls, value: Optional[str]) -> Optional[str]:
        return normalize_update_mode(value)

    @field_validator("release_notes")
    @classmethod
    def normalize_release_notes(cls, value: Optional[list[str]]) -> Optional[list[str]]:
        if value is None:
            return None
        notes = [item.strip() for item in value if item.strip()]
        if not notes:
            raise ValueError("release_notes must include at least one item")
        return notes


class AppReleaseResponse(BaseModel):
    id: str
    version_name: str
    version_code: int
    title: str
    subtitle: str
    app_icon_url: Optional[str]
    release_date: Optional[date]
    file_size: Optional[str]
    bazaar_url: Optional[str]
    myket_url: Optional[str]
    release_notes: list[str]
    primary_badge_text: Optional[str]
    min_supported_version_code: Optional[int]
    update_mode: Optional[str]
    update_title: Optional[str]
    update_message: Optional[str]
    apk_object_key: Optional[str]
    apk_url: Optional[str]
    is_published: bool
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class AppReleaseListResponse(BaseModel):
    items: list[AppReleaseResponse]


class AppReleaseApkUploadResponse(BaseModel):
    id: str
    filename: str
    apk_object_key: str
    apk_url: str
