from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import AnyHttpUrl, BaseModel, Field, field_validator, model_validator


VALID_UPDATE_MODES = {"none", "soft", "hard"}


def normalize_update_mode(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    if normalized not in VALID_UPDATE_MODES:
        raise ValueError("update_mode must be one of: none, soft, hard")
    return normalized


class AppDownloadResponse(BaseModel):
    title: str
    subtitle: str
    app_icon_url: Optional[str] = None
    version_name: Optional[str] = None
    version_code: Optional[int] = Field(default=None, ge=0)
    release_date: Optional[date] = None
    file_size: Optional[str] = None
    bazaar_url: Optional[str] = None
    myket_url: Optional[str] = None
    direct_download_url: Optional[str] = None
    release_notes: list[str]
    primary_badge_text: Optional[str] = None
    min_supported_version_code: Optional[int] = Field(default=None, ge=0)
    update_mode: Optional[str] = None
    update_title: Optional[str] = None
    update_message: Optional[str] = None
    is_direct_download_enabled: bool


class AppDownloadApkUploadResponse(BaseModel):
    filename: str
    stored_path: str
    direct_download_url: str


class AppDownloadSnapshot(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    subtitle: str = Field(min_length=1, max_length=1000)
    app_icon_url: Optional[AnyHttpUrl] = None
    version_name: Optional[str] = Field(default=None, min_length=1, max_length=64)
    version_code: Optional[int] = Field(default=None, ge=0)
    release_date: Optional[date] = None
    file_size: Optional[str] = Field(default=None, min_length=1, max_length=64)
    bazaar_url: Optional[AnyHttpUrl] = None
    myket_url: Optional[AnyHttpUrl] = None
    direct_download_url: Optional[AnyHttpUrl] = None
    release_notes: list[str] = Field(min_length=1)
    primary_badge_text: Optional[str] = Field(default=None, min_length=1, max_length=64)
    min_supported_version_code: Optional[int] = Field(default=None, ge=0)
    update_mode: Optional[str] = None
    update_title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    update_message: Optional[str] = Field(default=None, min_length=1, max_length=1000)

    @field_validator("update_mode", mode="before")
    @classmethod
    def validate_update_mode(cls, value: Optional[str]) -> Optional[str]:
        return normalize_update_mode(value)

    @model_validator(mode="after")
    def validate_links(self) -> "AppDownloadSnapshot":
        if not any((self.bazaar_url, self.myket_url, self.direct_download_url)):
            raise ValueError("at least one download link is required")
        return self


class AppDownloadUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    subtitle: Optional[str] = Field(default=None, min_length=1, max_length=1000)
    app_icon_url: Optional[AnyHttpUrl] = None
    version_name: Optional[str] = Field(default=None, min_length=1, max_length=64)
    version_code: Optional[int] = Field(default=None, ge=0)
    release_date: Optional[date] = None
    file_size: Optional[str] = Field(default=None, min_length=1, max_length=64)
    bazaar_url: Optional[AnyHttpUrl] = None
    myket_url: Optional[AnyHttpUrl] = None
    direct_download_url: Optional[AnyHttpUrl] = None
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
