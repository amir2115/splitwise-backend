from __future__ import annotations

from pathlib import Path

from app.models.domain import AppDownloadContent, Article, ArticleAuthor, ArticleCategory, ArticleStatus
from scripts.migrate_files_to_s3 import migrate_files


class FakeStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_bytes(self, *, key: str, content: bytes, content_type: str | None = None):
        self.objects[key] = content
        return type("Stored", (), {"key": key, "public_url": f"https://cdn.example.com/files/{key}"})()

    def public_url(self, key: str) -> str:
        return f"https://cdn.example.com/files/{key}".rstrip("/")


def test_migrate_files_to_s3_uploads_legacy_files_and_updates_urls(db_session, tmp_path: Path) -> None:
    articles_dir = tmp_path / "articles"
    articles_dir.mkdir()
    (articles_dir / "legacy.webp").write_bytes(b"image")
    (tmp_path / "app-organic-release.apk").write_bytes(b"apk")

    category = ArticleCategory(slug="guides", name="Guides", display_order=1)
    author = ArticleAuthor(slug="editor", name="Editor")
    db_session.add_all([category, author])
    db_session.flush()
    article = Article(
        slug="legacy",
        title="Legacy",
        summary="Summary",
        tldr="TLDR",
        hero_icon="*",
        hero_image_url="https://api.splitwise.ir/files/articles/legacy.webp",
        reading_minutes=3,
        category=category,
        author=author,
        body=[],
        toc=[],
        audience=[],
        related_slugs=[],
        og_image_url="https://api.splitwise.ir/files/articles/legacy.webp",
        status=ArticleStatus.PUBLISHED,
    )
    app_download = AppDownloadContent(
        slug="app_download",
        title="Download",
        subtitle="Subtitle",
        direct_download_url="https://api.splitwise.ir/files/app-organic-release.apk",
        release_notes=["note"],
    )
    db_session.add_all([article, app_download])
    db_session.commit()

    storage = FakeStorage()
    stats = migrate_files(db_session, files_root=tmp_path, storage=storage)

    assert stats == {"uploaded": 2, "articles_updated": 1, "app_download_updated": 1, "missing_files": 0}
    assert storage.objects["articles/legacy.webp"] == b"image"
    assert storage.objects["app-organic-release.apk"] == b"apk"
    assert article.hero_image_url == "https://cdn.example.com/files/articles/legacy.webp"
    assert article.og_image_url == "https://cdn.example.com/files/articles/legacy.webp"
    assert app_download.direct_download_url == "https://cdn.example.com/files/app-organic-release.apk"

    second_stats = migrate_files(db_session, files_root=tmp_path, storage=storage)
    assert second_stats == {"uploaded": 0, "articles_updated": 0, "app_download_updated": 0, "missing_files": 0}
