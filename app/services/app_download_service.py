from __future__ import annotations

from pathlib import Path
from urllib.parse import urljoin

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import DomainError
from app.models.domain import AppDownloadContent
from app.schemas.app_download import AppDownloadApkUploadResponse, AppDownloadResponse, AppDownloadSnapshot, AppDownloadUpdate

APP_DOWNLOAD_SLUG = "app_download"
APP_DOWNLOAD_APK_FILENAME = "app-organic-release.apk"
DEFAULT_APP_DOWNLOAD_PAYLOAD = {
    "title": "دانلود اپلیکیشن",
    "subtitle": "آخرین نسخه دنگینو را از استور دلخواهت نصب کن.",
    "app_icon_url": None,
    "version_name": None,
    "version_code": None,
    "release_date": None,
    "file_size": None,
    "bazaar_url": None,
    "myket_url": None,
    "direct_download_url": None,
    "release_notes": [],
    "primary_badge_text": None,
    "min_supported_version_code": None,
    "update_mode": None,
    "update_title": None,
    "update_message": None,
}
settings = get_settings()


def _default_payload() -> dict:
    return dict(DEFAULT_APP_DOWNLOAD_PAYLOAD)


def _snapshot_to_response(snapshot: AppDownloadSnapshot) -> AppDownloadResponse:
    payload = snapshot.model_dump(mode="json")
    payload["is_direct_download_enabled"] = payload["direct_download_url"] is not None
    return AppDownloadResponse(**payload)


def _get_record(db: Session) -> AppDownloadContent | None:
    return db.scalar(select(AppDownloadContent).where(AppDownloadContent.slug == APP_DOWNLOAD_SLUG))


def get_app_download_record(db: Session) -> AppDownloadContent | None:
    return _get_record(db)


def get_app_download_content(db: Session) -> AppDownloadResponse:
    record = _get_record(db)
    if not record:
        payload = _default_payload()
        payload["is_direct_download_enabled"] = payload["direct_download_url"] is not None
        return AppDownloadResponse(**payload)

    snapshot = AppDownloadSnapshot(
        title=record.title,
        subtitle=record.subtitle,
        app_icon_url=record.app_icon_url,
        version_name=record.version_name,
        version_code=record.version_code,
        release_date=record.release_date,
        file_size=record.file_size,
        bazaar_url=record.bazaar_url,
        myket_url=record.myket_url,
        direct_download_url=record.direct_download_url,
        release_notes=record.release_notes,
        primary_badge_text=record.primary_badge_text,
        min_supported_version_code=record.min_supported_version_code,
        update_mode=record.update_mode,
        update_title=record.update_title,
        update_message=record.update_message,
    )
    return _snapshot_to_response(snapshot)


def update_app_download_content(db: Session, payload: AppDownloadUpdate) -> AppDownloadResponse:
    updates = payload.model_dump(exclude_unset=True, mode="json")
    record = _get_record(db)
    if not record:
        base_payload = _default_payload()
    else:
        base_payload = {
            "title": record.title,
            "subtitle": record.subtitle,
            "app_icon_url": record.app_icon_url,
            "version_name": record.version_name,
            "version_code": record.version_code,
            "release_date": record.release_date,
            "file_size": record.file_size,
            "bazaar_url": record.bazaar_url,
            "myket_url": record.myket_url,
            "direct_download_url": record.direct_download_url,
            "release_notes": record.release_notes,
            "primary_badge_text": record.primary_badge_text,
            "min_supported_version_code": record.min_supported_version_code,
            "update_mode": record.update_mode,
            "update_title": record.update_title,
            "update_message": record.update_message,
        }
    merged_payload = {**base_payload, **updates}

    try:
        snapshot = AppDownloadSnapshot(**merged_payload)
    except ValidationError as exc:
        raise DomainError(code="invalid_app_download_content", message=str(exc)) from exc

    if not record:
        record = AppDownloadContent(slug=APP_DOWNLOAD_SLUG)
        db.add(record)

    record.title = snapshot.title
    record.subtitle = snapshot.subtitle
    record.app_icon_url = None if snapshot.app_icon_url is None else str(snapshot.app_icon_url)
    record.version_name = snapshot.version_name
    record.version_code = snapshot.version_code
    record.release_date = snapshot.release_date
    record.file_size = snapshot.file_size
    record.bazaar_url = None if snapshot.bazaar_url is None else str(snapshot.bazaar_url)
    record.myket_url = None if snapshot.myket_url is None else str(snapshot.myket_url)
    record.direct_download_url = None if snapshot.direct_download_url is None else str(snapshot.direct_download_url)
    record.release_notes = snapshot.release_notes
    record.primary_badge_text = snapshot.primary_badge_text
    record.min_supported_version_code = snapshot.min_supported_version_code
    record.update_mode = snapshot.update_mode
    record.update_title = snapshot.update_title
    record.update_message = snapshot.update_message

    db.commit()
    db.refresh(record)
    return get_app_download_content(db)


def upload_app_download_apk(*, filename: str | None, content: bytes) -> AppDownloadApkUploadResponse:
    if not filename:
        raise DomainError(code="invalid_app_download_apk", message="APK file is required")
    if not filename.lower().endswith(".apk"):
        raise DomainError(code="invalid_app_download_apk", message="Only .apk files are supported")

    upload_dir = Path(settings.app_download_upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    stored_path = upload_dir / APP_DOWNLOAD_APK_FILENAME
    stored_path.write_bytes(content)

    base_url = settings.app_download_public_base_url.rstrip("/") + "/"
    direct_download_url = urljoin(base_url, f"files/{APP_DOWNLOAD_APK_FILENAME}")

    return AppDownloadApkUploadResponse(
        filename=APP_DOWNLOAD_APK_FILENAME,
        stored_path=str(stored_path),
        direct_download_url=direct_download_url,
    )
