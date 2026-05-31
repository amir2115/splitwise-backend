from __future__ import annotations

import re

from fastapi import status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.core.time import utcnow
from app.models.domain import AppRelease
from app.schemas.app_download import AppDownloadUpdate
from app.schemas.app_releases import (
    AppReleaseApkUploadResponse,
    AppReleaseCreateRequest,
    AppReleaseListResponse,
    AppReleaseResponse,
)
from app.services.app_download_service import APP_DOWNLOAD_SLUG, update_app_download_content
from app.services.file_storage_service import build_storage_key, get_file_storage
from app.services.runtime_settings_service import set_runtime_settings

def _apk_filename_for_version(version_name: str) -> str:
    safe_version = re.sub(r"[^A-Za-z0-9._-]+", "-", version_name.strip()).strip(".-_")
    if not safe_version:
        raise DomainError(code="invalid_app_release_version_name", message="Version name cannot be used as a filename")
    return f"app-release_{safe_version}.apk"


def _release_response(release: AppRelease) -> AppReleaseResponse:
    return AppReleaseResponse(
        id=release.id,
        version_name=release.version_name,
        version_code=release.version_code,
        title=release.title,
        subtitle=release.subtitle,
        app_icon_url=release.app_icon_url,
        release_date=release.release_date,
        file_size=release.file_size,
        bazaar_url=release.bazaar_url,
        myket_url=release.myket_url,
        release_notes=release.release_notes,
        primary_badge_text=release.primary_badge_text,
        min_supported_version_code=release.min_supported_version_code,
        update_mode=release.update_mode,
        update_title=release.update_title,
        update_message=release.update_message,
        apk_object_key=release.apk_object_key,
        apk_url=release.apk_url,
        is_published=release.is_published,
        published_at=release.published_at,
        created_at=release.created_at,
        updated_at=release.updated_at,
    )


def list_app_releases(db: Session) -> AppReleaseListResponse:
    releases = db.scalars(select(AppRelease).order_by(AppRelease.version_code.desc(), AppRelease.created_at.desc())).all()
    return AppReleaseListResponse(items=[_release_response(release) for release in releases])


def create_app_release(db: Session, payload: AppReleaseCreateRequest) -> AppReleaseResponse:
    release = AppRelease(**payload.model_dump())
    db.add(release)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DomainError(code="app_release_version_code_taken", message="Version code already exists", status_code=status.HTTP_409_CONFLICT) from exc
    db.refresh(release)
    return _release_response(release)


def _find_release(db: Session, release_id: str) -> AppRelease:
    release = db.get(AppRelease, release_id)
    if not release:
        raise DomainError(code="app_release_not_found", message="App release not found", status_code=status.HTTP_404_NOT_FOUND)
    return release


def upload_app_release_apk(db: Session, release_id: str, *, filename: str | None, content: bytes) -> AppReleaseApkUploadResponse:
    if not filename:
        raise DomainError(code="invalid_app_release_apk", message="APK file is required")
    if not filename.lower().endswith(".apk"):
        raise DomainError(code="invalid_app_release_apk", message="Only .apk files are supported")
    if not content:
        raise DomainError(code="invalid_app_release_apk", message="APK file is empty")

    release = _find_release(db, release_id)
    stored_filename = _apk_filename_for_version(release.version_name)
    key = build_storage_key("app-releases", stored_filename)
    stored = get_file_storage().put_bytes(
        key=key,
        content=content,
        content_type="application/vnd.android.package-archive",
    )
    release.apk_object_key = stored.key
    release.apk_url = stored.public_url
    db.commit()
    db.refresh(release)
    return AppReleaseApkUploadResponse(
        id=release.id,
        filename=stored_filename,
        apk_object_key=stored.key,
        apk_url=stored.public_url,
    )


def publish_app_release(db: Session, release_id: str) -> AppReleaseResponse:
    release = _find_release(db, release_id)
    if not release.apk_url or not release.apk_object_key:
        raise DomainError(code="app_release_apk_required", message="Upload an APK before publishing", status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

    now = utcnow()
    db.execute(update(AppRelease).where(AppRelease.id != release.id).values(is_published=False, published_at=None))
    release.is_published = True
    release.published_at = now

    update_app_download_content(
        db,
        AppDownloadUpdate(
            title=release.title,
            subtitle=release.subtitle,
            app_icon_url=release.app_icon_url,
            version_name=release.version_name,
            version_code=release.version_code,
            release_date=release.release_date,
            file_size=release.file_size,
            bazaar_url=release.bazaar_url,
            myket_url=release.myket_url,
            direct_download_url=release.apk_url,
            release_notes=release.release_notes,
            primary_badge_text=release.primary_badge_text,
            min_supported_version_code=release.min_supported_version_code,
            update_mode=release.update_mode,
            update_title=release.update_title,
            update_message=release.update_message,
        ),
    )
    release.is_published = True
    release.published_at = now
    set_runtime_settings(db, {"apk_url": release.apk_url})
    db.commit()
    db.refresh(release)
    return _release_response(release)
