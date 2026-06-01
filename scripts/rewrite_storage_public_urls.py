from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.domain import AppDownloadContent, AppRelease, AppSetting, Article
from app.services.app_download_service import APP_DOWNLOAD_SLUG
from app.services.file_storage_service import FileStorage, get_file_storage, normalize_object_key


DEFAULT_OLD_BASE_URLS = (
    "https://cdn.splitwise.ir/files",
    "https://api.splitwise.ir/files",
)


def _rewrite_url(value: str | None, *, old_base_urls: tuple[str, ...], storage: FileStorage) -> str | None:
    if not value:
        return value
    current_base = storage.public_url("").rstrip("/")
    if value.rstrip("/").startswith(current_base):
        return value

    normalized_value = value.rstrip("/")
    for old_base_url in old_base_urls:
        old_base = old_base_url.rstrip("/")
        if not normalized_value.startswith(f"{old_base}/"):
            continue
        key = normalize_object_key(normalized_value[len(old_base) + 1 :])
        return storage.public_url(key)
    return value


def _rewrite_attr(record, attr: str, *, old_base_urls: tuple[str, ...], storage: FileStorage) -> int:
    old_value = getattr(record, attr)
    new_value = _rewrite_url(old_value, old_base_urls=old_base_urls, storage=storage)
    if new_value == old_value:
        return 0
    setattr(record, attr, new_value)
    return 1


def rewrite_storage_public_urls(db, *, old_base_urls: tuple[str, ...], storage: FileStorage) -> dict[str, int]:
    stats = {
        "app_releases_updated": 0,
        "articles_updated": 0,
        "app_download_updated": 0,
        "runtime_settings_updated": 0,
    }

    for release in db.scalars(select(AppRelease)).all():
        stats["app_releases_updated"] += _rewrite_attr(release, "apk_url", old_base_urls=old_base_urls, storage=storage)

    for article in db.scalars(select(Article)).all():
        changed = 0
        changed += _rewrite_attr(article, "hero_image_url", old_base_urls=old_base_urls, storage=storage)
        changed += _rewrite_attr(article, "og_image_url", old_base_urls=old_base_urls, storage=storage)
        if changed:
            stats["articles_updated"] += 1

    app_download = db.scalar(select(AppDownloadContent).where(AppDownloadContent.slug == APP_DOWNLOAD_SLUG))
    if app_download:
        stats["app_download_updated"] += _rewrite_attr(app_download, "direct_download_url", old_base_urls=old_base_urls, storage=storage)

    apk_setting = db.scalar(select(AppSetting).where(AppSetting.key == "apk_url"))
    if apk_setting:
        stats["runtime_settings_updated"] += _rewrite_attr(apk_setting, "value", old_base_urls=old_base_urls, storage=storage)

    db.commit()
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Rewrite stored public file URLs to the configured FILE_STORAGE_PUBLIC_BASE_URL.")
    parser.add_argument(
        "--old-base-url",
        action="append",
        dest="old_base_urls",
        help="Old public base URL to rewrite. Can be passed multiple times.",
    )
    args = parser.parse_args()
    old_base_urls = tuple(args.old_base_urls or DEFAULT_OLD_BASE_URLS)

    db = SessionLocal()
    try:
        stats = rewrite_storage_public_urls(db, old_base_urls=old_base_urls, storage=get_file_storage())
    finally:
        db.close()
    print(stats)


if __name__ == "__main__":
    main()
