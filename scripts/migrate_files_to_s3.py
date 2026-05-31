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
from app.models.domain import AppDownloadContent, Article
from app.services.app_download_service import APP_DOWNLOAD_APK_FILENAME, APP_DOWNLOAD_SLUG
from app.services.file_storage_service import FileStorage, build_storage_key, get_file_storage


def _filename_from_legacy_url(value: str | None, *, prefix: str) -> str | None:
    if not value:
        return None
    parsed_path = urlparse(value).path
    marker = f"/files/{prefix.strip('/')}/" if prefix else "/files/"
    if marker not in parsed_path:
        return None
    return parsed_path.rsplit("/", 1)[-1] or None


def _is_storage_url(value: str | None, storage: FileStorage) -> bool:
    if not value:
        return False
    try:
        root_url = storage.public_url("").rstrip("/")
    except Exception:
        return False
    return value.rstrip("/").startswith(root_url)


def migrate_files(db, *, files_root: Path, storage: FileStorage) -> dict[str, int]:
    stats = {"uploaded": 0, "articles_updated": 0, "app_download_updated": 0, "missing_files": 0}

    articles_dir = files_root / "articles"
    articles = list(db.scalars(select(Article)).all())
    for article in articles:
        filename = _filename_from_legacy_url(article.hero_image_url, prefix="articles")
        if not filename or _is_storage_url(article.hero_image_url, storage):
            continue
        source = articles_dir / filename
        if not source.is_file():
            stats["missing_files"] += 1
            continue
        key = build_storage_key("articles", filename)
        stored = storage.put_bytes(key=key, content=source.read_bytes())
        old_hero_url = article.hero_image_url
        article.hero_image_url = stored.public_url
        if article.og_image_url == old_hero_url:
            article.og_image_url = stored.public_url
        stats["uploaded"] += 1
        stats["articles_updated"] += 1

    app_download = db.scalar(select(AppDownloadContent).where(AppDownloadContent.slug == APP_DOWNLOAD_SLUG))
    if app_download and not _is_storage_url(app_download.direct_download_url, storage):
        filename = _filename_from_legacy_url(app_download.direct_download_url, prefix="")
        if filename in {APP_DOWNLOAD_APK_FILENAME, "app.apk"}:
            source = files_root / filename
            if not source.is_file() and filename == "app.apk":
                source = files_root / APP_DOWNLOAD_APK_FILENAME
            if source.is_file():
                stored = storage.put_bytes(
                    key=build_storage_key(APP_DOWNLOAD_APK_FILENAME),
                    content=source.read_bytes(),
                    content_type="application/vnd.android.package-archive",
                )
                app_download.direct_download_url = stored.public_url
                stats["uploaded"] += 1
                stats["app_download_updated"] += 1
            else:
                stats["missing_files"] += 1

    db.commit()
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload legacy /files assets to configured file storage.")
    parser.add_argument("--files-root", default="/files", help="Legacy files root directory")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        stats = migrate_files(db, files_root=Path(args.files_root), storage=get_file_storage())
    finally:
        db.close()
    print(stats)


if __name__ == "__main__":
    main()
